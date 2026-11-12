from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from rest_framework import serializers
from .models import Vehicle, Service, Part, Order, OrderService, OrderPart, Payment, OrderHistory, StockMovement, PartRequest, Review
User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email", "phone", "password")
    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(**validated_data, password=password, role="client")

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "full_name", "email", "phone", "role", "is_active")
    def get_full_name(self, obj): return obj.get_full_name() or obj.username

class VehicleSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    class Meta:
        model = Vehicle
        fields = "__all__"
        read_only_fields = ("owner", "created_at")

class ServiceSerializer(serializers.ModelSerializer):
    class Meta: model = Service; fields = "__all__"

class PartSerializer(serializers.ModelSerializer):
    low_stock = serializers.SerializerMethodField()
    class Meta: model = Part; fields = "__all__"
    def get_low_stock(self, obj): return obj.stock <= obj.min_stock
    def to_representation(self, obj):
        data = super().to_representation(obj)
        req = self.context.get("request")
        if not req or getattr(req.user, "role", None) not in ("admin", "manager"):
            data.pop("purchase_price", None)
        return data

class StaffCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email", "phone", "role", "password")
    def validate_role(self, value):
        request = self.context.get("request")
        if request and request.user.role == "manager" and value != "mechanic":
            raise serializers.ValidationError("Menejer faqat mexanik hisobini yaratishi mumkin.")
        if value not in ("manager", "mechanic"):
            raise serializers.ValidationError("Faqat manager yoki mechanic roli beriladi.")
        return value
    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(**validated_data, password=password)

class StockMovementSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="part.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)
    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = ("created_by", "created_at")

class PaymentSerializer(serializers.ModelSerializer):
    class Meta: model = Payment; fields = ("id", "amount", "method", "note", "paid_at")
    read_only_fields = ("id", "paid_at")

class HistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)
    class Meta: model = OrderHistory; fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):
    vehicle_label = serializers.CharField(source="vehicle.__str__", read_only=True)
    client_name = serializers.CharField(source="vehicle.owner.get_full_name", read_only=True)
    mechanic_name = serializers.CharField(source="mechanic.get_full_name", read_only=True)
    services = serializers.SerializerMethodField()
    parts = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()
    class Meta:
        model = Order
        fields = ("id", "vehicle", "vehicle_label", "client_name", "created_by", "mechanic",
                  "mechanic_name", "complaint", "diagnosis", "status", "labor_cost",
                  "total_amount", "paid_amount", "balance", "services", "parts",
                  "created_at", "updated_at", "completed_at", "extra_issues", "work_notes",
                  "spent_minutes", "payment_status", "review")
        read_only_fields = ("created_by", "total_amount", "created_at", "updated_at", "completed_at")
    def get_services(self, obj):
        return [{"id": x.service_id, "name": x.service.name, "price": str(x.price)} for x in obj.order_services.select_related("service")]
    def get_parts(self, obj):
        return [{"id": x.part_id, "name": x.part.name, "quantity": x.quantity, "unit_price": str(x.unit_price)} for x in obj.order_parts.select_related("part")]
    def get_paid_amount(self, obj): return str(sum((p.amount for p in obj.payments.all()), 0))
    def get_balance(self, obj): return str(obj.total_amount - sum((p.amount for p in obj.payments.all()), 0))

    def get_payment_status(self, obj):
        paid = sum((p.amount for p in obj.payments.all()), 0)
        if paid <= 0: return "unpaid"
        return "paid" if paid >= obj.total_amount else "partial"
    def get_review(self, obj):
        r = getattr(obj, "review", None)
        return {"rating": r.rating, "comment": r.comment} if r else None

class ClientSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    full_name = serializers.SerializerMethodField()
    vehicles_count = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "full_name", "email", "phone", "password", "is_active", "vehicles_count")
    def get_full_name(self, obj): return obj.get_full_name() or obj.username
    def get_vehicles_count(self, obj): return obj.vehicles.count()
    def create(self, data):
        pw = data.pop("password", None) or get_random_string(14)
        return User.objects.create_user(**data, password=pw, role="client")

class PartRequestSerializer(serializers.ModelSerializer):
    part_name = serializers.CharField(source="part.name", read_only=True)
    mechanic_name = serializers.CharField(source="requested_by.get_full_name", read_only=True)
    class Meta:
        model = PartRequest
        fields = ("id", "order", "part", "part_name", "quantity", "status", "note", "mechanic_name", "created_at")
        read_only_fields = ("order", "status", "created_at")

class ReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="author.get_full_name", read_only=True)
    class Meta:
        model = Review
        fields = ("id", "order", "rating", "comment", "client_name", "created_at")
        read_only_fields = ("order", "created_at")
    def validate_rating(self, v):
        if not 1 <= v <= 5: raise serializers.ValidationError("Baho 1 dan 5 gacha bo'lishi kerak.")
        return v
