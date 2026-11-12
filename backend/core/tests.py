from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Vehicle, Service, Order, Part
from rest_framework.test import APIClient

class CoreApiTests(TestCase):
    def setUp(self):
        self.client_user = get_user_model().objects.create_user(username="client1", password="StrongPass123", role="client")
        self.vehicle = Vehicle.objects.create(owner=self.client_user, make="Toyota", model="Camry", plate_number="01A123AA")
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)
    def test_client_can_list_own_vehicles(self):
        response = self.api.get("/api/vehicles/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
    def test_client_can_create_order_for_own_vehicle(self):
        response = self.api.post("/api/orders/", {"vehicle": self.vehicle.id, "complaint": "Dvigatel tekshirish"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_client_reports_are_scoped_to_own_orders(self):
        response = self.api.get("/api/reports/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["scope"], "own_orders")
        self.assertNotIn("by_mechanic", response.data)

    def test_client_cannot_create_stock_movement(self):
        part = Part.objects.create(name="Filtr", sku="TEST-FLT", sale_price=100)
        response = self.api.post("/api/stock/movements/", {"part": part.id, "kind": "in", "quantity": 2}, format="json")
        self.assertEqual(response.status_code, 403)


class WorkflowTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.admin = U.objects.create_user(username="a", password="x12345678", role="admin", is_superuser=True)
        self.manager = U.objects.create_user(username="m", password="x12345678", role="manager")
        self.mech = U.objects.create_user(username="me", password="x12345678", role="mechanic")
        self.mech2 = U.objects.create_user(username="me2", password="x12345678", role="mechanic")
        self.cl = U.objects.create_user(username="c", password="x12345678", role="client")
        self.vehicle = Vehicle.objects.create(owner=self.cl, make="Chevrolet", model="Gentra", plate_number="01X111XX")
        self.part = Part.objects.create(name="Filtr", sku="F1", sale_price=1000, stock=5)
        self.order = Order.objects.create(vehicle=self.vehicle, created_by=self.manager, mechanic=self.mech, complaint="test")
    def as_user(self, user):
        api = APIClient(); api.force_authenticate(user); return api

    def test_client_cannot_set_price_or_status_on_create(self):
        r = self.as_user(self.cl).post("/api/orders/", {"vehicle": self.vehicle.id, "complaint": "x", "labor_cost": "1", "status": "completed"}, format="json")
        self.assertEqual(r.status_code, 201)
        o = Order.objects.get(pk=r.data["id"])
        self.assertEqual(o.status, "new"); self.assertEqual(o.labor_cost, 0)

    def test_client_cannot_patch_order(self):
        r = self.as_user(self.cl).patch(f"/api/orders/{self.order.id}/", {"labor_cost": "1"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_mechanic_cannot_touch_foreign_order(self):
        r = self.as_user(self.mech2).post(f"/api/orders/{self.order.id}/set_status/", {"status": "in_progress"}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_mechanic_work_update_and_status(self):
        api = self.as_user(self.mech)
        r = api.post(f"/api/orders/{self.order.id}/work_update/", {"work_notes": "ok", "add_minutes": 30}, format="json")
        self.assertEqual(r.status_code, 200); self.assertEqual(r.data["spent_minutes"], 30)
        r = api.post(f"/api/orders/{self.order.id}/set_status/", {"status": "in_progress"}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_mechanic_cannot_add_part_directly_but_can_request(self):
        api = self.as_user(self.mech)
        self.assertEqual(api.post(f"/api/orders/{self.order.id}/add_part/", {"part_id": self.part.id, "quantity": 1}, format="json").status_code, 403)
        self.assertEqual(api.post(f"/api/orders/{self.order.id}/request_part/", {"part_id": self.part.id, "quantity": 2}, format="json").status_code, 201)

    def test_manager_approves_part_request_and_stock_decreases(self):
        self.as_user(self.mech).post(f"/api/orders/{self.order.id}/request_part/", {"part_id": self.part.id, "quantity": 2}, format="json")
        pr = self.order.part_requests.first()
        r = self.as_user(self.manager).post(f"/api/part-requests/{pr.id}/decide/", {"decision": "approve"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.part.refresh_from_db(); self.assertEqual(self.part.stock, 3)

    def test_review_only_for_completed_own_order(self):
        api = self.as_user(self.cl)
        self.assertEqual(api.post(f"/api/orders/{self.order.id}/review/", {"rating": 5}, format="json").status_code, 400)
        self.order.status = "completed"; self.order.save()
        self.assertEqual(api.post(f"/api/orders/{self.order.id}/review/", {"rating": 5, "comment": "good"}, format="json").status_code, 201)
        self.assertEqual(api.post(f"/api/orders/{self.order.id}/review/", {"rating": 4}, format="json").status_code, 400)

    def test_only_admin_lists_users_and_blocks(self):
        self.assertEqual(self.as_user(self.manager).get("/api/users/").status_code, 403)
        r = self.as_user(self.admin).patch(f"/api/users/{self.cl.id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.cl.refresh_from_db(); self.assertFalse(self.cl.is_active)

    def test_manager_creates_client_and_vehicle_for_client(self):
        api = self.as_user(self.manager)
        r = api.post("/api/clients/", {"username": "newc", "first_name": "N", "password": "StrongPass123"}, format="json")
        self.assertEqual(r.status_code, 201)
        r = api.post("/api/vehicles/", {"owner": r.data["id"], "make": "Kia", "model": "K5", "plate_number": "01K555KK"}, format="json")
        self.assertEqual(r.status_code, 201)

    def test_client_does_not_see_purchase_price_and_can_edit_profile(self):
        api = self.as_user(self.cl)
        r = api.get("/api/parts/")
        self.assertNotIn("purchase_price", r.data[0])
        r = api.patch("/api/auth/me/", {"first_name": "Yangi", "phone": "+998900000000"}, format="json")
        self.assertEqual(r.status_code, 200); self.assertEqual(r.data["first_name"], "Yangi")

    def test_notifications_on_status_change_and_assignment(self):
        self.as_user(self.manager).post(f"/api/orders/{self.order.id}/assign_mechanic/", {"mechanic_id": self.mech2.id}, format="json")
        self.assertEqual(self.mech2.notifications.count(), 1)
        self.as_user(self.mech2).post(f"/api/orders/{self.order.id}/set_status/", {"status": "in_progress"}, format="json")
        r = self.as_user(self.cl).get("/api/notifications/")
        self.assertGreaterEqual(r.data["unread"], 1)
        self.as_user(self.cl).post("/api/notifications/read/", {}, format="json")
        self.assertEqual(self.as_user(self.cl).get("/api/notifications/").data["unread"], 0)

    def test_mechanic_report_has_no_money_and_date_filter_works(self):
        r = self.as_user(self.mech).get("/api/reports/")
        self.assertNotIn("revenue", r.data)
        r = self.as_user(self.manager).get("/api/reports/", {"date_from": "2999-01-01"})
        self.assertEqual(r.data["orders_count"], 0)
        self.assertIn("by_mechanic", r.data)
