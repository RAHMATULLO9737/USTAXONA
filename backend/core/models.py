from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.core.validators import MinValueValidator

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        MECHANIC = "mechanic", "Mechanic"
        CLIENT = "client", "Client"
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.CLIENT)
    phone = models.CharField(max_length=30, blank=True)

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

class Vehicle(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vehicles")
    make = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    plate_number = models.CharField(max_length=20, unique=True)
    vin = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.make} {self.model} — {self.plate_number}"

class Service(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    estimated_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Part(models.Model):
    name = models.CharField(max_length=120)
    sku = models.CharField(max_length=50, unique=True)
    unit = models.CharField(max_length=20, default="dona")
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    stock = models.PositiveIntegerField(default=0)
    min_stock = models.PositiveIntegerField(default=2)
    image = models.ImageField(upload_to="parts/", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.name} ({self.stock})"

class StockMovement(models.Model):
    class Kind(models.TextChoices):
        IN = "in", "Kirim"
        OUT = "out", "Chiqim"
        ADJUST = "adjust", "Tuzatish"
    part = models.ForeignKey(Part, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        DIAGNOSTICS = "diagnostics", "Diagnostika"
        WAITING_PARTS = "waiting_parts", "Ehtiyot qism kutilmoqda"
        IN_PROGRESS = "in_progress", "Ta'mirlanmoqda"
        COMPLETED = "completed", "Yakunlandi"
        CANCELLED = "cancelled", "Bekor qilindi"
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="orders")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_orders")
    mechanic = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="mechanic_orders")
    complaint = models.TextField()
    diagnosis = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    extra_issues = models.TextField(blank=True)
    work_notes = models.TextField(blank=True)
    spent_minutes = models.PositiveIntegerField(default=0)
    def __str__(self): return f"AS-{self.pk or 'NEW'} · {self.vehicle.plate_number}"
    def recalculate(self):
        service_total = sum((x.price for x in self.order_services.all()), Decimal("0"))
        part_total = sum((x.quantity * x.unit_price for x in self.order_parts.all()), Decimal("0"))
        self.total_amount = service_total + part_total + self.labor_cost
        self.save(update_fields=["total_amount", "updated_at"])

class OrderService(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_services")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    class Meta: unique_together = ("order", "service")

class OrderPart(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_parts")
    part = models.ForeignKey(Part, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    class Meta: unique_together = ("order", "part")

class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Naqd"
        CARD = "card", "Karta"
        TRANSFER = "transfer", "O'tkazma"
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    method = models.CharField(max_length=12, choices=Method.choices, default=Method.CASH)
    note = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)

class OrderHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)



class PartRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Kutilmoqda"
        APPROVED = "approved", "Tasdiqlandi"
        REJECTED = "rejected", "Rad etildi"
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="part_requests")
    part = models.ForeignKey(Part, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="part_requests")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Review(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="review")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
