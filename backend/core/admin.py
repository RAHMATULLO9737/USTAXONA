from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Vehicle, Service, Part, Order, OrderService, OrderPart, Payment, OrderHistory, StockMovement, PartRequest, Review, Notification

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("AutoService", {"fields": ("role", "phone")}),)
    list_display = ("username", "email", "role", "is_staff")
for model in (Vehicle, Service, Part, Order, OrderService, OrderPart, Payment, OrderHistory, StockMovement, PartRequest, Review, Notification):
    admin.site.register(model)
