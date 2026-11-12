from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Vehicle, Service, Part, Order, OrderService, OrderPart, Payment, OrderHistory, PartRequest, Review

User = get_user_model()

# FAQAT lokal ishlab chiqish uchun. Productionda ishlatmang!
ACCOUNTS = [
    # username, parol, ism, familiya, rol
    ("admin", "Admin@12345", "Aziz", "Administrator", "admin"),
    ("manager", "Manager@12345", "Malika", "Menejerova", "manager"),
    ("mechanic", "Mechanic@12345", "Jasur", "Ustaev", "mechanic"),
    ("mechanic2", "Mechanic@12345", "Bobur", "Ustaev", "mechanic"),
    ("client", "Client@12345", "Dilshod", "Mijozov", "client"),
]

SERVICES = [
    ("Kompyuter diagnostikasi", "Elektron tizimlarni diagnostika qilish", "150000", 45),
    ("Moy almashtirish", "Dvigatel moyi va filtrni almashtirish", "80000", 30),
    ("Tormoz tizimi tekshiruvi", "Kolodka va disklarni tekshirish", "120000", 45),
    ("G'ildirak balansirovkasi", "G'ildiraklarni balanslash", "100000", 40),
    ("Konditsioner xizmati", "Konditsioner diagnostikasi va to'ldirish", "180000", 60),
    ("Dvigatel ta'miri", "Dvigatel bo'yicha boshlang'ich ish haqi", "500000", 240),
    ("Uzatmalar qutisi diagnostikasi", "KPP tekshiruvi", "200000", 90),
    ("Podveska ta'miri", "Amortizator va richaglar", "300000", 120),
    ("Akkumulyator almashtirish", "Akkumulyatorni o'rnatish", "50000", 20),
]

PARTS = [
    ("Motor moyi 5W-30", "OIL-5W30", "litr", "65000", "85000", 40),
    ("Motor moyi 10W-40", "OIL-10W40", "litr", "55000", "75000", 30),
    ("Moy filtri", "FLT-OIL-001", "dona", "35000", "50000", 25),
    ("Havo filtri", "FLT-AIR-001", "dona", "45000", "65000", 20),
    ("Salon filtri", "FLT-CAB-001", "dona", "40000", "60000", 20),
    ("Yonilg'i filtri", "FLT-FUEL-001", "dona", "60000", "85000", 12),
    ("Tormoz kolodkasi (old)", "BRK-PAD-001", "komplekt", "180000", "240000", 12),
    ("Tormoz kolodkasi (orqa)", "BRK-PAD-002", "komplekt", "150000", "210000", 10),
    ("Tormoz diski", "BRK-DSK-001", "dona", "250000", "340000", 8),
    ("Tormoz suyuqligi DOT4", "BRK-FLD-001", "litr", "40000", "60000", 15),
    ("Sham (svecha)", "SPK-001", "dona", "30000", "45000", 40),
    ("Antifriz", "CLT-001", "litr", "40000", "55000", 25),
    ("Akkumulyator 60Ah", "BAT-60AH", "dona", "850000", "980000", 6),
    ("Akkumulyator 75Ah", "BAT-75AH", "dona", "1050000", "1200000", 4),
    ("Amortizator (old)", "SUS-SHK-001", "dona", "320000", "430000", 8),
    ("Rul uchi", "SUS-TRE-001", "dona", "120000", "170000", 10),
    ("Generator kamari", "BLT-ALT-001", "dona", "90000", "130000", 10),
    ("Lampochka H7", "LMP-H7", "dona", "25000", "40000", 30),
    ("Shisha yuvish suyuqligi", "WSH-001", "litr", "10000", "18000", 30),
    ("G'ildirak balans yuki", "WHL-WGT-001", "dona", "2000", "5000", 200),
]


class Command(BaseCommand):
    help = "Demo hisoblar (admin/manager/mechanic/client), mahsulotlar va namunaviy buyurtmalarni yaratadi. Faqat lokal rivojlantirish uchun."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="DEBUG=False bo'lsa ham ishga tushirish (tavsiya etilmaydi)")

    @transaction.atomic
    def handle(self, *args, **opts):
        if not settings.DEBUG and not opts["force"]:
            raise CommandError("DEBUG=False: demo parollarni productionda yaratmang. Kerak bo'lsa --force ishlating.")

        users = {}
        for username, password, first, last, role in ACCOUNTS:
            u, created = User.objects.get_or_create(username=username, defaults={"first_name": first, "last_name": last, "role": role, "phone": "+998901234567"})
            if created:
                u.set_password(password)
                u.is_staff = role == "admin"
                u.is_superuser = role == "admin"
                u.save()
            users[username] = u

        svc = {}
        for name, desc, price, minutes in SERVICES:
            svc[name], _ = Service.objects.get_or_create(name=name, defaults={"description": desc, "price": Decimal(price), "estimated_minutes": minutes})
        parts = {}
        for name, sku, unit, buy, sell, stock in PARTS:
            parts[sku], _ = Part.objects.get_or_create(sku=sku, defaults={"name": name, "unit": unit, "purchase_price": Decimal(buy), "sale_price": Decimal(sell), "stock": stock, "min_stock": 3})

        if not Order.objects.exists():
            client, mech, mgr = users["client"], users["mechanic"], users["manager"]
            v1 = Vehicle.objects.create(owner=client, make="Chevrolet", model="Gentra", year=2019, plate_number="01A123BC", color="Oq")
            v2 = Vehicle.objects.create(owner=client, make="Chevrolet", model="Cobalt", year=2021, plate_number="01B456CD", color="Qora")

            o1 = Order.objects.create(vehicle=v1, created_by=client, complaint="Dvigatel ovozi g'alati", status="new")
            o2 = Order.objects.create(vehicle=v2, created_by=mgr, mechanic=mech, complaint="Moy almashtirish va tormoz tekshiruvi",
                                      diagnosis="Tormoz kolodkalari eskirgan", status="in_progress", spent_minutes=40)
            o3 = Order.objects.create(vehicle=v1, created_by=mgr, mechanic=mech, complaint="Rejali texnik xizmat", diagnosis="Hammasi joyida",
                                      status="completed", spent_minutes=60, labor_cost=Decimal("50000"))
            for o, st in ((o2, "in_progress"), (o3, "completed")):
                OrderHistory.objects.create(order=o, actor=mgr, from_status="new", to_status=st, note="Demo ma'lumot")
            OrderService.objects.create(order=o2, service=svc["Moy almashtirish"], price=svc["Moy almashtirish"].price)
            OrderPart.objects.create(order=o2, part=parts["OIL-5W30"], quantity=4, unit_price=parts["OIL-5W30"].sale_price)
            OrderService.objects.create(order=o3, service=svc["Kompyuter diagnostikasi"], price=svc["Kompyuter diagnostikasi"].price)
            OrderPart.objects.create(order=o3, part=parts["FLT-AIR-001"], quantity=1, unit_price=parts["FLT-AIR-001"].sale_price)
            for o in (o2, o3):
                o.recalculate()
            from django.utils import timezone
            o3.completed_at = timezone.now()
            o3.save(update_fields=["completed_at"])
            Payment.objects.create(order=o3, amount=o3.total_amount, method="cash", note="To'liq to'landi")
            Review.objects.create(order=o3, author=client, rating=5, comment="Tez va sifatli xizmat!")
            PartRequest.objects.create(order=o2, part=parts["BRK-PAD-001"], quantity=1, requested_by=mech, note="Old tormoz kolodkasi kerak")

        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar tayyor.\n"))
        self.stdout.write("ROL       | LOGIN      | PAROL")
        for username, password, _, _, role in ACCOUNTS:
            self.stdout.write(f"{role:9} | {username:10} | {password}")
        self.stdout.write(self.style.WARNING("\nBu parollar FAQAT lokal sinov uchun. Productionda almashtiring yoki ishlatmang."))
