# نظام مراقبة أحواض الترسيب الثانوي الذكي — Django + PostgreSQL

مشروع كامل ومُختبَر: قاعدة بيانات **PostgreSQL**، محرّك ذكي (حساب + تشخيص + فهارس + إنذارات)،
وواجهة عصرية **بيضاء بتأثير زجاجي (Glassmorphism)** مع تسجيل دخول.

> تم اختبار كل شيء فعلياً: التهجير على PostgreSQL، خط المعالجة، وكل الصفحات (HTTP 200).

---

## ما الجديد في هذه المرحلة

- قاعدة البيانات على **PostgreSQL** (تُقرأ من `.env`).
- **طبقة الخدمات** `analytics/services/`: تحسب المؤشرات وتشخّص وتولّد الإنذارات والفهارس تلقائياً عند حفظ أي قراءة (عبر Signal).
- **Views + Templates**: تسجيل دخول · لوحة مراقبة · إدخال يومي · سجلّ قراءات.
- **تصميم زجاجي أبيض** في `static/css/app.css` (RTL عربي، خطوط Cairo + Oxanium).

---

## خطوات التشغيل

### 1) إنشاء قاعدة البيانات في PostgreSQL
```sql
CREATE USER clarifier WITH PASSWORD 'clarifier123';
CREATE DATABASE clarifier OWNER clarifier;
ALTER USER clarifier CREATEDB;
```

### 2) البيئة والمتطلّبات
```bash
cd clarifier_system
python -m venv .venv && source .venv/bin/activate    # ويندوز: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # عدّل DB_* إن لزم
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"  # ضع الناتج في .env
```

### 3) التهجير وتحميل الحدود
```bash
python manage.py migrate
python manage.py loaddata references      # الحدود السبعة من الملف
python manage.py createsuperuser
```

### 4) التشغيل
```bash
python manage.py runserver
```
- الواجهة: `http://127.0.0.1:8000/`  (تُحوّل لتسجيل الدخول)
- الإدارة: `http://127.0.0.1:8000/admin/`

---

## بنية المشروع

```
clarifier_system/
├── config/settings.py              # PostgreSQL + AUTH_USER_MODEL + i18n
├── accounts/                       # User (مشغّل/مشرف/مدير)
├── monitoring/                     # Plant · Clarifier · DailyReading + forms + views
├── references/                     # ParameterReference + fixtures
├── analytics/
│   ├── models.py                   # Metric · Diagnosis · IndexScore · Alarm
│   ├── signals.py                  # يشغّل المعالجة عند الحفظ
│   └── services/                   # ← المحرّك الذكي
│       ├── calculator.py           #   SLR · SOR · HRT · SVI · نسب الإزالة
│       ├── diagnosis.py            #   حالة+سبب+إجراء لكل مؤشر
│       ├── indices.py              #   CHI · CSI · CRI + تقييم المشغّل
│       ├── alarms.py               #   توليد الإنذارات
│       └── pipeline.py             #   يربط الكل في معاملة واحدة
├── dashboard/                      # لوحة المراقبة
├── templates/                      # base · login · dashboard · forms (زجاجي أبيض)
└── static/css/app.css              # نظام التصميم الزجاجي
```

## المسارات

| المسار | الصفحة |
|--------|--------|
| `/login/` | تسجيل الدخول |
| `/` | لوحة المراقبة |
| `/monitoring/readings/new/` | إدخال قراءة يومية |
| `/monitoring/readings/` | سجلّ القراءات |
| `/admin/` | لوحة الإدارة |

## كيف يعمل المحرّك الذكي

عند حفظ `DailyReading` تشغّل إشارة `post_save` الدالة `process_reading()` ضمن معاملة واحدة:
1. **calculator** → SLR, SOR, HRT, SVI, نسب الإزالة.
2. **diagnosis** → يقارن كل مؤشر بحدوده ويولّد الحالة والسبب والإجراء.
3. **alarms** → إنذار لكل حالة تحذير/حرج.
4. **indices** → CHI و CSI (تباين 7 أيام) و CRI وتقييم المشغّل.

## الخطوة التالية (المرحلة 4)

**التنبؤ المبكّر**: `analytics/services/prediction.py` يفحص اتجاه كل مؤشر بالانحدار الخطّي
ويولّد إنذارات استباقية قبل تجاوز الحدود، مع تشغيلها في مهمة Celery يومية.
