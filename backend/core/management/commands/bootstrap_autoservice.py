import secrets
import string
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Part, Service

User = get_user_model()

class Command(BaseCommand):
    help = "Create initial admin/staff accounts and starter service/parts catalog. Passwords are generated and printed once."

    def handle(self, *args, **options):
        created_credentials = []
        accounts = [
            ("admin", "Administrator", True, True),
            ("manager", "Servis menejeri", False, False),
            ("mechanic", "Bosh mexanik", False, False),
        ]
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        for role, full_name, is_staff, is_superuser in accounts:
            username = f"{role}_main"
            user = User.objects.filter(username=username).first()
            if user:
                self.stdout.write(self.style.WARNING(f"Mavjud: {username} (parol o'zgartirilmadi)"))
                continue
            password = ''.join(secrets.choice(alphabet) for _ in range(16))
            user = User.objects.create_user(
                username=username, password=password,
                first_name=full_name, role=role,
                is_staff=is_staff, is_superuser=is_superuser,
            )
            created_credentials.append((username, password, role))

        services = [
            ("Kompyuter diagnostikasi", "Elektron tizimlarni diagnostika qilish", "150000", 45),
            ("Moy almashtirish", "Dvigatel moyi va filtrni almashtirish", "80000", 30),
            ("Tormoz tizimi tekshiruvi", "Kolodka va disklarni tekshirish", "120000", 45),
            ("G'ildirak balansirovkasi", "G'ildiraklarni balanslash", "100000", 40),
            ("Konditsioner xizmati", "Konditsioner diagnostikasi va to'ldirish", "180000", 60),
            ("Dvigatel ta'miri", "Dvigatel bo'yicha boshlang'ich ish haqi", "500000", 240),
        ]
        for name, description, price, minutes in services:
            Service.objects.get_or_create(name=name, defaults={"description": description, "price": Decimal(price), "estimated_minutes": minutes})

        parts = [
            ("Motor moyi 5W-30", "OIL-5W30", "litr", "65000", "85000", 20),
            ("Moy filtri", "FLT-OIL-001", "dona", "35000", "50000", 15),
            ("Havo filtri", "FLT-AIR-001", "dona", "45000", "65000", 10),
            ("Tormoz kolodkasi", "BRK-PAD-001", "komplekt", "180000", "240000", 8),
            ("Sham (svecha)", "SPK-001", "dona", "30000", "45000", 20),
            ("Antifriz", "CLT-001", "litr", "40000", "55000", 12),
            ("Salon filtri", "FLT-CAB-001", "dona", "40000", "60000", 10),
            ("Akkumulyator 60Ah", "BAT-60AH", "dona", "850000", "980000", 4),
        ]
        for name, sku, unit, purchase, sale, stock in parts:
            Part.objects.get_or_create(sku=sku, defaults={
                "name": name, "unit": unit, "purchase_price": Decimal(purchase),
                "sale_price": Decimal(sale), "stock": stock, "min_stock": 2,
            })

        self.stdout.write(self.style.SUCCESS("Boshlang'ich katalog tayyor: xizmatlar va ehtiyot qismlar yaratildi (mavjudlari saqlandi)."))
        if created_credentials:
            self.stdout.write(self.style.SUCCESS("\nYANGI HISOBLAR — parollarni hozir xavfsiz joyga yozib oling:"))
            for username, password, role in created_credentials:
                self.stdout.write(f"{role.upper():9} | login: {username} | parol: {password}")
            self.stdout.write(self.style.WARNING("Bu parollar bir marta ko'rsatiladi. Birinchi kirishda almashtiring."))
        else:
            self.stdout.write(self.style.WARNING("Hisoblar avvaldan mavjud. Parollar qayta chiqarilmadi yoki almashtirilmadi."))
