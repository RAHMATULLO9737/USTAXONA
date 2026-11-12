from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import TruncMonth
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Vehicle, Service, Part, Order, OrderService, OrderPart, Payment, OrderHistory, StockMovement, PartRequest, Review, Notification
from .serializers import (RegisterSerializer, UserSerializer, VehicleSerializer, ServiceSerializer,
                          PartSerializer, OrderSerializer, PaymentSerializer, HistorySerializer, StaffCreateSerializer, StockMovementSerializer,
                          ClientSerializer, PartRequestSerializer, ReviewSerializer)
from .permissions import IsManagerOrAdmin, IsStaff, IsAdmin
User = get_user_model()

def notify(user, message, order=None):
    if not user: return
    Notification.objects.create(user=user, order=order, message=message[:255])
    if user.email:
        try: send_mail("AutoService", message, None, [user.email], fail_silently=True)
        except Exception: pass

def notify_staff(message, order=None):
    for u in User.objects.filter(role__in=["admin", "manager"], is_active=True): notify(u, message, order)

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    if request.method == "PATCH":
        for field in ("first_name", "last_name", "email", "phone"):
            if field in request.data: setattr(user, field, str(request.data[field]))
        new_pw = request.data.get("new_password")
        if new_pw:
            if not user.check_password(request.data.get("old_password", "")):
                return Response({"detail": "Eski parol noto'g'ri."}, status=400)
            if len(new_pw) < 8:
                return Response({"detail": "Yangi parol kamida 8 belgi bo'lishi kerak."}, status=400)
            user.set_password(new_pw)
        user.save()
    return Response(UserSerializer(user).data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    user = request.user
    role = user.role
    orders = Order.objects.all()
    if role == "client":
        orders = orders.filter(vehicle__owner=user)
    elif role == "mechanic":
        orders = orders.filter(mechanic=user)
    today = timezone.localdate()
    unpaid_ids = [o.id for o in orders.filter(status="completed").prefetch_related("payments")
                  if sum((p.amount for p in o.payments.all()), Decimal("0")) < o.total_amount]
    data = {
        "total_orders": orders.count(),
        "active_orders": orders.exclude(status__in=["completed", "cancelled"]).count(),
        "completed_orders": orders.filter(status="completed").count(),
        "new_orders": orders.filter(status="new").count(),
        "in_progress_orders": orders.filter(status="in_progress").count(),
        "waiting_orders": orders.filter(status__in=["new", "diagnostics", "waiting_parts"]).count(),
        "today_orders": orders.filter(created_at__date=today).count(),
        "status_counts": {r["status"]: r["n"] for r in orders.order_by().values("status").annotate(n=Count("id"))},
        "awaiting_payment": len(unpaid_ids),
        "revenue": str(Payment.objects.filter(order__in=orders).aggregate(v=Sum("amount"))["v"] or 0),
        "recent_orders": OrderSerializer(orders.select_related("vehicle", "vehicle__owner", "mechanic").order_by("-created_at")[:6], many=True).data,
        "low_stock": Part.objects.filter(stock__lte=F("min_stock")).count() if role in ("admin", "manager") else 0,
    }
    if role == "client":
        data["vehicles_count"] = Vehicle.objects.filter(owner=user).count()
    if role == "mechanic":
        data["part_requests"] = PartRequest.objects.filter(requested_by=user).count()
    if role in ("admin", "manager"):
        data["pending_part_requests"] = PartRequest.objects.filter(status="pending").count()
    if role == "admin":
        data.update({
            "clients_count": User.objects.filter(role="client").count(),
            "vehicles_count": Vehicle.objects.count(),
            "parts_count": Part.objects.count(),
            "parts_stock_total": Part.objects.aggregate(v=Sum("stock"))["v"] or 0,
            "top_mechanics": [
                {"name": u.get_full_name() or u.username, "completed": u.done}
                for u in User.objects.filter(role="mechanic").annotate(done=Count("mechanic_orders", filter=Q(mechanic_orders__status="completed"))).order_by("-done")[:5]
            ],
        })
    return Response(data)

class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    def get_queryset(self):
        qs = Vehicle.objects.select_related("owner")
        if self.request.user.role not in ("admin", "manager"):
            qs = qs.filter(owner=self.request.user)
        return qs
    def perform_create(self, serializer):
        user = self.request.user
        owner = user
        if user.role in ("admin", "manager"):
            owner = User.objects.filter(pk=self.request.data.get("owner"), role="client").first()
            if not owner:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"owner": "Mijozni tanlang."})
        serializer.save(owner=owner)
    def get_permissions(self):
        if self.request.user.is_authenticated and self.request.user.role == "mechanic":
            return [IsStaff()] if self.action in ("list", "retrieve") else [IsManagerOrAdmin()]
        return [IsAuthenticated()]

class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by("name")
    serializer_class = ServiceSerializer
    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"): return [IsManagerOrAdmin()]
        return [IsAuthenticated()]

class PartViewSet(viewsets.ModelViewSet):
    queryset = Part.objects.all().order_by("name")
    serializer_class = PartSerializer
    def get_permissions(self):
        if self.request.method in ("POST", "PUT", "PATCH", "DELETE"): return [IsManagerOrAdmin()]
        return [IsAuthenticated()]
    def get_queryset(self):
        qs = super().get_queryset()
        return qs

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    def get_queryset(self):
        qs = Order.objects.select_related("vehicle", "vehicle__owner", "mechanic").prefetch_related("payments", "order_services__service", "order_parts__part")
        user = self.request.user
        if user.role == "client": return qs.filter(vehicle__owner=user)
        if user.role == "mechanic": return qs.filter(mechanic=user)
        qs = qs.order_by("-created_at")
        if self.action == "list":
            p = self.request.query_params
            if p.get("status"): qs = qs.filter(status=p["status"])
            if p.get("mechanic") and user.role in ("admin", "manager"): qs = qs.filter(mechanic_id=p["mechanic"])
            if p.get("client") and user.role in ("admin", "manager"): qs = qs.filter(vehicle__owner_id=p["client"])
            if p.get("date_from"): qs = qs.filter(created_at__date__gte=p["date_from"])
            if p.get("date_to"): qs = qs.filter(created_at__date__lte=p["date_to"])
            if p.get("q"):
                q = p["q"]
                qs = qs.filter(Q(vehicle__plate_number__icontains=q) | Q(vehicle__owner__first_name__icontains=q) |
                               Q(vehicle__owner__last_name__icontains=q) | Q(complaint__icontains=q))
        return qs
    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated()]
        if self.action in ("update", "partial_update", "destroy", "assign_mechanic", "add_part", "add_service", "payments", "remove_service", "remove_part", "decide_part_request"):
            return [IsManagerOrAdmin()]
        if self.action in ("set_status", "work_update", "request_part"):
            return [IsStaff()]
        return [IsAuthenticated()]
    def perform_create(self, serializer):
        vehicle = serializer.validated_data["vehicle"]
        if self.request.user.role == "client" and vehicle.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Faqat o'zingizning avtomobilingiz uchun buyurtma ochishingiz mumkin.")
        if self.request.user.role == "client":
            order = serializer.save(created_by=self.request.user, status="new", labor_cost=0, mechanic=None, diagnosis="")
            notify_staff(f"Yangi so'rov: AS-{order.pk} ({order.vehicle.plate_number})", order)
        else:
            serializer.save(created_by=self.request.user)
    def _history(self, order, actor, new_status, note=""):
        old = order.status
        order.status = new_status
        if new_status == "completed": order.completed_at = timezone.now()
        order.save()
        OrderHistory.objects.create(order=order, actor=actor, from_status=old, to_status=new_status, note=note)
        label = dict(Order.Status.choices).get(new_status, new_status)
        notify(order.vehicle.owner, f"AS-{order.pk} buyurtmangiz holati: {label}", order)
        if actor and actor.role == "mechanic": notify_staff(f"Usta AS-{order.pk} holatini o'zgartirdi: {label}", order)
    @action(detail=True, methods=["post"])
    def assign_mechanic(self, request, pk=None):
        order = self.get_object()
        mechanic = User.objects.filter(pk=request.data.get("mechanic_id"), role="mechanic").first()
        if not mechanic: return Response({"detail": "Usta topilmadi."}, status=400)
        order.mechanic = mechanic
        order.save(update_fields=["mechanic", "updated_at"])
        notify(mechanic, f"Sizga AS-{order.pk} buyurtma biriktirildi", order)
        notify(order.vehicle.owner, f"AS-{order.pk} buyurtmangizga usta biriktirildi: {mechanic.get_full_name() or mechanic.username}", order)
        return Response(OrderSerializer(order).data)
    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get("status")
        valid = [x[0] for x in Order.Status.choices]
        if new_status not in valid: return Response({"detail": "Noto'g'ri status."}, status=400)
        if request.user.role == "mechanic" and order.mechanic_id != request.user.id:
            return Response({"detail": "Bu buyurtma sizga biriktirilmagan."}, status=403)
        if request.user.role == "mechanic" and new_status in ("new", "cancelled"):
            return Response({"detail": "Usta bu statusni o'rnata olmaydi."}, status=403)
        self._history(order, request.user, new_status, request.data.get("note", ""))
        return Response(OrderSerializer(order).data)
    @action(detail=True, methods=["post"])
    def add_service(self, request, pk=None):
        order = self.get_object()
        service = Service.objects.filter(pk=request.data.get("service_id"), is_active=True).first()
        if not service: return Response({"detail": "Xizmat topilmadi."}, status=404)
        OrderService.objects.get_or_create(order=order, service=service, defaults={"price": service.price})
        order.recalculate()
        return Response(OrderSerializer(order).data)
    @action(detail=True, methods=["post"])
    def add_part(self, request, pk=None):
        order = self.get_object()
        try: quantity = int(request.data.get("quantity", 1))
        except (TypeError, ValueError): return Response({"detail": "Miqdor noto'g'ri."}, status=400)
        if quantity < 1: return Response({"detail": "Miqdor kamida 1 bo'lishi kerak."}, status=400)
        err = self._add_part_line(order, request.data.get("part_id"), quantity, request.user)
        if err: return Response({"detail": err}, status=404 if "topilmadi" in err else 400)
        return Response(OrderSerializer(order).data)
    @action(detail=True, methods=["post"])
    def remove_service(self, request, pk=None):
        order = self.get_object()
        OrderService.objects.filter(order=order, service_id=request.data.get("service_id")).delete()
        order.recalculate()
        return Response(OrderSerializer(order).data)
    @action(detail=True, methods=["post"])
    def remove_part(self, request, pk=None):
        order = self.get_object()
        with transaction.atomic():
            line = OrderPart.objects.filter(order=order, part_id=request.data.get("part_id")).first()
            if line:
                part = Part.objects.select_for_update().get(pk=line.part_id)
                part.stock += line.quantity
                part.save(update_fields=["stock", "updated_at"])
                StockMovement.objects.create(part=part, kind="in", quantity=line.quantity, note=f"AS-{order.pk} dan qaytarildi", created_by=request.user)
                line.delete()
                order.recalculate()
        return Response(OrderSerializer(order).data)
    @action(detail=True, methods=["post"])
    def work_update(self, request, pk=None):
        order = self.get_object()
        if request.user.role == "mechanic" and order.mechanic_id != request.user.id:
            return Response({"detail": "Bu buyurtma sizga biriktirilmagan."}, status=403)
        for field in ("diagnosis", "extra_issues", "work_notes"):
            if field in request.data: setattr(order, field, str(request.data[field]))
        if "add_minutes" in request.data:
            try: minutes = int(request.data["add_minutes"])
            except (TypeError, ValueError): return Response({"detail": "Vaqt noto'g'ri."}, status=400)
            if minutes < 0: return Response({"detail": "Vaqt manfiy bo'lmaydi."}, status=400)
            order.spent_minutes += minutes
        order.save()
        return Response(OrderSerializer(order).data)
    def _add_part_line(self, order, part_id, quantity, user):
        with transaction.atomic():
            part = Part.objects.select_for_update().filter(pk=part_id).first()
            if not part: return "Ehtiyot qism topilmadi."
            if part.stock < quantity: return "Omborda yetarli qoldiq yo'q."
            line, created = OrderPart.objects.get_or_create(order=order, part=part, defaults={"quantity": quantity, "unit_price": part.sale_price})
            if not created:
                line.quantity += quantity
                line.save(update_fields=["quantity"])
            part.stock -= quantity
            part.save(update_fields=["stock", "updated_at"])
            StockMovement.objects.create(part=part, kind="out", quantity=quantity, note=f"AS-{order.pk} buyurtmaga sarflandi", created_by=user)
            order.recalculate()
        return None
    @action(detail=True, methods=["post"])
    def request_part(self, request, pk=None):
        order = self.get_object()
        if request.user.role == "mechanic" and order.mechanic_id != request.user.id:
            return Response({"detail": "Bu buyurtma sizga biriktirilmagan."}, status=403)
        try: quantity = int(request.data.get("quantity", 1))
        except (TypeError, ValueError): return Response({"detail": "Miqdor noto'g'ri."}, status=400)
        part = Part.objects.filter(pk=request.data.get("part_id")).first()
        if not part or quantity < 1: return Response({"detail": "Ehtiyot qism yoki miqdor noto'g'ri."}, status=400)
        pr = PartRequest.objects.create(order=order, part=part, quantity=quantity, requested_by=request.user, note=str(request.data.get("note", ""))[:255])
        notify_staff(f"AS-{order.pk}: usta {part.name} x{quantity} so'radi", order)
        return Response(PartRequestSerializer(pr).data, status=201)
    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        order = self.get_object()
        if request.user.role != "client" or order.vehicle.owner_id != request.user.id:
            return Response({"detail": "Faqat buyurtma egasi fikr qoldira oladi."}, status=403)
        if order.status != "completed": return Response({"detail": "Fikr faqat yakunlangan buyurtmaga qoldiriladi."}, status=400)
        if Review.objects.filter(order=order).exists(): return Response({"detail": "Siz allaqachon fikr qoldirgansiz."}, status=400)
        ser = ReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(order=order, author=request.user)
        return Response(ser.data, status=201)
    @action(detail=True, methods=["get"])
    def invoice(self, request, pk=None):
        order = self.get_object()
        if request.user.role == "mechanic": return Response({"detail": "Ruxsat yo'q."}, status=403)
        if order.status != "completed": return Response({"detail": "Hisob-faktura faqat yakunlangan buyurtma uchun."}, status=400)
        ser = OrderSerializer(order).data
        return Response({"number": f"INV-{order.pk:05d}", "date": order.completed_at, "client": ser["client_name"], "vehicle": ser["vehicle_label"],
                         "services": ser["services"], "parts": ser["parts"], "labor_cost": str(order.labor_cost), "total": str(order.total_amount),
                         "paid": ser["paid_amount"], "balance": ser["balance"], "payment_status": ser["payment_status"],
                         "payments": PaymentSerializer(order.payments.all(), many=True).data})
    @action(detail=True, methods=["post"])
    def payments(self, request, pk=None):
        order = self.get_object()
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        already_paid = sum((p.amount for p in order.payments.all()), 0)
        if serializer.validated_data["amount"] > order.total_amount - already_paid:
            return Response({"detail": "To'lov qoldiq summadan katta."}, status=400)
        serializer.save(order=order)
        notify(order.vehicle.owner, f"AS-{order.pk} bo'yicha to'lov qabul qilindi: {serializer.validated_data['amount']} so'm", order)
        return Response(OrderSerializer(order).data, status=201)
    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        return Response(HistorySerializer(self.get_object().history.select_related("actor"), many=True).data)

@api_view(["GET", "POST"])
@permission_classes([IsManagerOrAdmin])
def staff_list(request):
    if request.method == "POST":
        if request.user.role not in ("admin", "manager"):
            return Response({"detail": "Ruxsat yo'q."}, status=403)
        serializer = StaffCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(UserSerializer(serializer.save()).data, status=201)
    users = User.objects.filter(role__in=["manager", "mechanic"]).order_by("first_name")
    if request.user.role == "manager": users = users.filter(role="mechanic")
    return Response(UserSerializer(users, many=True).data)

@api_view(["GET", "POST"])
@permission_classes([IsManagerOrAdmin])
def stock_movement(request):
    if request.method == "GET":
        movements = StockMovement.objects.select_related("part", "created_by").order_by("-created_at")[:200]
        return Response(StockMovementSerializer(movements, many=True).data)
    serializer = StockMovementSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    part = serializer.validated_data["part"]
    qty = serializer.validated_data["quantity"]
    kind = serializer.validated_data["kind"]
    with transaction.atomic():
        part = Part.objects.select_for_update().get(pk=part.pk)
        if kind == "in": part.stock += qty
        elif kind == "out":
            if part.stock < qty: return Response({"detail": "Omborda yetarli qoldiq yo'q."}, status=400)
            part.stock -= qty
        else: part.stock = qty
        part.save(update_fields=["stock", "updated_at"])
        movement = serializer.save(created_by=request.user)
    return Response(StockMovementSerializer(movement).data, status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports(request):
    user = request.user
    role = user.role
    d_from = parse_date(request.query_params.get("date_from", "") or "")
    d_to = parse_date(request.query_params.get("date_to", "") or "")
    orders = Order.objects.all()
    if role == "client": orders = orders.filter(vehicle__owner=user)
    elif role == "mechanic": orders = orders.filter(mechanic=user)
    if d_from: orders = orders.filter(created_at__date__gte=d_from)
    if d_to: orders = orders.filter(created_at__date__lte=d_to)
    payments = Payment.objects.filter(order__in=orders)
    data = {
        "scope": {"admin": "all", "manager": "all", "mechanic": "own_work", "client": "own_orders"}[role],
        "orders_count": orders.count(),
        "completed_count": orders.filter(status="completed").count(),
        "active_count": orders.exclude(status__in=["completed", "cancelled"]).count(),
        "cancelled_count": orders.filter(status="cancelled").count(),
        "spent_minutes": orders.aggregate(v=Sum("spent_minutes"))["v"] or 0,
    }
    if role != "mechanic":
        data.update({
            "revenue": str(payments.aggregate(v=Sum("amount"))["v"] or 0),
            "orders_total": str(orders.aggregate(v=Sum("total_amount"))["v"] or 0),
            "payments_count": payments.count(),
            "monthly_revenue": [{"month": r["month"].strftime("%Y-%m"), "amount": str(r["amount"])} for r in payments.annotate(month=TruncMonth("paid_at")).values("month").annotate(amount=Sum("amount")).order_by("month")],
        })
    if role in ("admin", "manager"):
        data["by_mechanic"] = [
            {"name": u.get_full_name() or u.username, "orders": u.total, "completed": u.done, "minutes": u.mins or 0}
            for u in User.objects.filter(role="mechanic").annotate(
                total=Count("mechanic_orders", filter=Q(mechanic_orders__in=orders)),
                done=Count("mechanic_orders", filter=Q(mechanic_orders__in=orders, mechanic_orders__status="completed")),
                mins=Sum("mechanic_orders__spent_minutes", filter=Q(mechanic_orders__in=orders))).order_by("-done")]
    if role in ("admin", "manager", "mechanic"):
        reviews = Review.objects.filter(order__in=orders)
        data["reviews_count"] = reviews.count()
        data["reviews_avg"] = round(reviews.aggregate(v=Sum("rating"))["v"] / reviews.count(), 2) if reviews.exists() else None
    return Response(data)

@api_view(["PATCH", "DELETE"])
@permission_classes([IsStaff])
def staff_detail(request, pk):
    target = User.objects.filter(pk=pk, role__in=["manager", "mechanic"]).first()
    if not target: return Response({"detail": "Xodim topilmadi."}, status=404)
    if request.user.role == "manager" and target.role != "mechanic": return Response({"detail": "Faqat mexaniklarni boshqarishingiz mumkin."}, status=403)
    if request.method == "DELETE":
        if target.pk == request.user.pk: return Response({"detail": "O'zingizni o'chira olmaysiz."}, status=400)
        target.delete(); return Response(status=204)
    for field in ("first_name", "last_name", "email", "phone"):
        if field in request.data: setattr(target, field, request.data[field])
    if request.user.role == "admin" and request.data.get("role") in ("manager", "mechanic"): target.role = request.data["role"]
    target.save(); return Response(UserSerializer(target).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def part_requests(request):
    user = request.user
    if user.role == "client": return Response({"detail": "Ruxsat yo'q."}, status=403)
    qs = PartRequest.objects.select_related("part", "requested_by", "order").order_by("-created_at")
    if user.role == "mechanic": qs = qs.filter(requested_by=user)
    return Response(PartRequestSerializer(qs[:200], many=True).data)

@api_view(["POST"])
@permission_classes([IsManagerOrAdmin])
def part_request_decide(request, pk):
    pr = PartRequest.objects.select_related("order").filter(pk=pk, status="pending").first()
    if not pr: return Response({"detail": "So'rov topilmadi yoki allaqachon ko'rib chiqilgan."}, status=404)
    if request.data.get("decision") == "approve":
        err = OrderViewSet()._add_part_line(pr.order, pr.part_id, pr.quantity, request.user)
        if err: return Response({"detail": err}, status=400)
        pr.status = "approved"
    else:
        pr.status = "rejected"
    pr.save(update_fields=["status"])
    notify(pr.requested_by, f"AS-{pr.order_id}: {pr.part.name} so'rovi {'tasdiqlandi' if pr.status == 'approved' else 'rad etildi'}", pr.order)
    return Response(PartRequestSerializer(pr).data)

@api_view(["GET"])
@permission_classes([IsManagerOrAdmin])
def reviews_list(request):
    return Response(ReviewSerializer(Review.objects.select_related("author").order_by("-created_at")[:200], many=True).data)

@api_view(["GET", "POST"])
@permission_classes([IsManagerOrAdmin])
def clients(request):
    if request.method == "POST":
        ser = ClientSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return Response(ClientSerializer(ser.save()).data, status=201)
    return Response(ClientSerializer(User.objects.filter(role="client").order_by("first_name", "username"), many=True).data)

@api_view(["PATCH"])
@permission_classes([IsManagerOrAdmin])
def client_detail(request, pk):
    target = User.objects.filter(pk=pk, role="client").first()
    if not target: return Response({"detail": "Mijoz topilmadi."}, status=404)
    for field in ("first_name", "last_name", "email", "phone"):
        if field in request.data: setattr(target, field, request.data[field])
    if "is_active" in request.data and request.user.role == "admin": target.is_active = bool(request.data["is_active"])
    target.save()
    return Response(ClientSerializer(target).data)

@api_view(["GET"])
@permission_classes([IsAdmin])
def users_list(request):
    return Response(UserSerializer(User.objects.order_by("role", "username"), many=True).data)

@api_view(["PATCH"])
@permission_classes([IsAdmin])
def user_toggle(request, pk):
    target = User.objects.filter(pk=pk).first()
    if not target: return Response({"detail": "Foydalanuvchi topilmadi."}, status=404)
    if target.pk == request.user.pk: return Response({"detail": "O'zingizni bloklay yoki rolingizni o'zgartira olmaysiz."}, status=400)
    if "is_active" in request.data: target.is_active = bool(request.data["is_active"])
    if request.data.get("role") in ("manager", "mechanic", "client") and not target.is_superuser: target.role = request.data["role"]
    target.save()
    return Response(UserSerializer(target).data)

@api_view(["GET"])
@permission_classes([IsAdmin])
def activity_log(request):
    rows = OrderHistory.objects.select_related("actor", "order").order_by("-created_at")[:200]
    return Response([{"id": h.id, "order": h.order_id, "actor": h.actor.username if h.actor else "—", "from_status": h.from_status,
                      "to_status": h.to_status, "note": h.note, "created_at": h.created_at} for h in rows])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notifications(request):
    qs = Notification.objects.filter(user=request.user)
    return Response({"unread": qs.filter(is_read=False).count(),
                     "items": [{"id": n.id, "order": n.order_id, "message": n.message, "is_read": n.is_read, "created_at": n.created_at} for n in qs[:30]]})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notifications_read(request):
    qs = Notification.objects.filter(user=request.user, is_read=False)
    if request.data.get("id"): qs = qs.filter(pk=request.data["id"])
    qs.update(is_read=True)
    return Response({"ok": True})
