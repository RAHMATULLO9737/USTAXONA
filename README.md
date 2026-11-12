# AutoService Manager

React + Vite frontend va Django REST Framework backend asosidagi avtoservis boshqaruv tizimi.

## Yangilangan imkoniyatlar

- Admin: manager va mexanik hisoblarini yaratish, xodim ma'lumotlarini tahrirlash/o'chirish.
- Manager: mexanik hisoblarini yaratish, tahrirlash/o'chirish va jamoani boshqarish.
- Mijoz: login sahifasidan mustaqil ro'yxatdan o'tish; ro'yxatdan o'tgan foydalanuvchi avtomatik `client` rolini oladi.
- Mahsulotlar: CRUD, SKU, xarid/sotuv narxi, qoldiq, minimal qoldiq va rasm yuklash.
- Ombor: kirim, chiqim va qoldiqni belgilash; buyurtmaga ehtiyot qism sarflanganda chiqim harakati yoziladi.
- Har bir rol uchun alohida dashboard va ruxsatlar.
- Admin/manager uchun moliyaviy hisobotlar va oylik tushum.
- Ustaga ehtiyot qism so'rash (menejer tasdiqlaydi → ombordan avtomatik chiqim), qo'shimcha nosozlik, izoh va sarflangan vaqtni kiritish.
- Mijoz: avtomobil qo'shish, ta'mirlash so'rovi, holatni kuzatish, hisob-faktura, baho va fikr.
- Admin/Manager: mijozlar bo'limi, buyurtma filtrlari (sana, status, mijoz, usta), hisob-faktura, to'lov holati.
- Admin: barcha foydalanuvchilar, bloklash/faollashtirish, rol o'zgartirish, jarayonlar tarixi, eng yaxshi ustalar.

## Backendni ishga tushirish (Windows)

```cmd
cd backend
py -m venv env
env\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

`bootstrap_autoservice` birinchi ishga tushishda quyidagi haqiqiy rollar uchun noyob, tasodifiy parollar yaratadi: `admin_main`, `manager_main`, `mechanic_main`. Buyruq parollarni terminalda faqat bir marta ko'rsatadi — xavfsiz joyga yozib oling. Buyruqni qayta ishlatish mavjud parollarni o'zgartirmaydi. Keyinchalik qo'shimcha superuser kerak bo'lsa `python manage.py createsuperuser` dan foydalaning.

Backend API: `http://127.0.0.1:8000/api/`

## Frontendni ishga tushirish

Yangi terminalda:

```cmd
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173/`

Agar backend manzili boshqacha bo'lsa, `frontend/.env` yarating va quyidagini yozing:

```env
VITE_API_URL=http://127.0.0.1:8000/api
```

## Rollar

- `admin`: to'liq boshqaruv, manager va mexanik yaratish.
- `manager`: mexanik yaratish/boshqarish, mahsulotlar, xizmatlar, ombor va hisobotlar.
- `mechanic`: o'ziga biriktirilgan buyurtmalar, status yangilash va mahsulot katalogini ko'rish.
- `client`: o'z avtomobillari va buyurtmalarini ko'rish/yaratish.

## Dastlabki katalog

`python manage.py bootstrap_autoservice` xizmatlar va ehtiyot qismlarning boshlang'ich katalogini ham yaratadi. SKU bo'yicha mavjud mahsulotlar qayta nusxalanmaydi. Narx va qoldiqlarni tizimdagi Mahsulotlar bo'limidan yangilang.

## Muhim eslatmalar

- Yangi model maydonlari qo'shilgani uchun `makemigrations` va `migrate` majburiy.
- Mahsulot rasmlari lokal rejimda `backend/media/parts/` ichida saqlanadi. Production serverda persistent media storage sozlang.
- Production uchun `.env` ichida kuchli `SECRET_KEY`, `DEBUG=False`, to'g'ri `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` va PostgreSQL sozlang. Dastlabki parollarni serverga chiqarishdan oldin almashtiring.
- Hisobotlar, xodimlar ro'yxati va ombor harakatlari backendda faqat admin/manager uchun cheklangan. Mexanik va mijoz ularga kira olmaydi. SQLite production uchun tavsiya etilmaydi.
- Frontenddagi ro'yxatdan o'tish faqat mijoz hisobini yaratadi; xodim hisoblari faqat ruxsatli Admin/Manager panelidan yaratiladi.


## Demo hisoblar (faqat lokal sinov uchun)

`python manage.py seed_demo` quyidagi hisoblarni, 9 ta xizmatni, 20 ta mahsulotni, 2 ta avtomobil va 3 ta namunaviy buyurtmani yaratadi (DEBUG=False bo'lsa ishlamaydi):

| Rol | Login | Parol |
|---|---|---|
| Admin | `admin` | `Admin@12345` |
| Manager | `manager` | `Manager@12345` |
| Mechanic | `mechanic` (va `mechanic2`) | `Mechanic@12345` |
| Client | `client` | `Client@12345` |

Bu parollar ochiq yozilgan — productionda ishlatmang. Productionda `bootstrap_autoservice` (tasodifiy parollar) dan foydalaning.

## Testlar

```cmd
python manage.py test core
```

## Bildirishnomalar va hisobotlar

- Tizim ichida qo'ng'iroqcha (yuqori o'ng burchak): buyurtma holati, usta biriktirilishi, to'lov, ehtiyot qism so'rovi va uning natijasi haqida xabarlar keladi. Foydalanuvchida email bo'lsa, xabar emailga ham yuboriladi.
- Email standart holatda terminalga chiqadi. Haqiqiy yuborish uchun `backend/.env` ga `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` ni yozing.
- SMS qo'shilmagan: u uchun Eskiz yoki Playmobile kabi provayder akkaunti kerak.
- Hisobotlar sahifasi barcha rollarda bor va sana oralig'i bilan filtrlanadi: admin/manager — butun servis, usta — faqat o'z ishlari (pulsiz), mijoz — faqat o'z buyurtmalari.

## Statuslar va dizayn

- Statuslar: Yangi → Diagnostika → Ehtiyot qism kutilmoqda → Ta'mirlanmoqda → Yakunlandi (yoki Bekor qilindi).
- Ko'rinishi: buyurtmalar sahifasida status tugmalari (sonlari bilan), buyurtma ichida bosqichma-bosqich chiziq, dashboardda status kartalari, "Taxta" sahifasida Kanban ko'rinishi.
