from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import register, me, dashboard, staff_list, stock_movement, reports, staff_detail, part_requests, part_request_decide, reviews_list, clients, client_detail, users_list, user_toggle, activity_log, notifications, notifications_read, VehicleViewSet, ServiceViewSet, PartViewSet, OrderViewSet
router = DefaultRouter()
router.register("vehicles", VehicleViewSet, basename="vehicle")
router.register("services", ServiceViewSet)
router.register("parts", PartViewSet)
router.register("orders", OrderViewSet, basename="order")
urlpatterns = [
    path("auth/register/", register),
    path("auth/me/", me),
    path("dashboard/", dashboard),
    path("staff/", staff_list),
    path("staff/<int:pk>/", staff_detail),
    path("stock/movements/", stock_movement),
    path("reports/", reports),
    path("part-requests/", part_requests),
    path("part-requests/<int:pk>/decide/", part_request_decide),
    path("reviews/", reviews_list),
    path("clients/", clients),
    path("clients/<int:pk>/", client_detail),
    path("users/", users_list),
    path("users/<int:pk>/", user_toggle),
    path("activity/", activity_log),
    path("notifications/", notifications),
    path("notifications/read/", notifications_read),
    path("", include(router.urls)),
]
