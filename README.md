# نظام إدارة المندوب - Port Management System

## نظرة سريعة
نظام شامل لإدارة عمليات الموانئ والشحن باللغة العربية، مطور باستخدام Django لإدارة الحاويات، أذونات التسليم، الشاحنات، السائقين، والرحلات.

## البدء السريع

### 1. تثبيت المتطلبات
```bash
pip install -r requirements.txt
```

### 2. إعداد قاعدة البيانات
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 3. تشغيل الخادم
```bash
python manage.py runserver
```

### 4. إنشاء بيانات تجريبية (اختياري)
```bash
python manage.py create_test_data
```

## الميزات الأساسية

- 🚢 **إدارة الحاويات**: تتبع أنواع وحالات الحاويات المختلفة
- 📋 **أذونات التسليم**: إدارة شاملة لأذونات التسليم والانتهاء
- 🚛 **إدارة الشاحنات**: تسجيل الشاحنات بالمحافظات العراقية  
- 👥 **إدارة السائقين**: معلومات كاملة للسائقين مع التحقق
- 🛣️ **نظام الرحلات**: ربط الحاويات بالشاحنات والسائقين
- 📊 **لوحة التحكم**: إحصائيات فورية وتقارير شاملة
- 📈 **التصدير**: تصدير البيانات بصيغ Excel و PDF
- 🔐 **نظام أذونات**: تحكم كامل في الصلاحيات والاشتراكات

## نماذج البيانات الرئيسية

```python
# نماذج أساسية
CustomUser - المستخدمون مع نظام اشتراكات
Driver - السائقون مع معلومات شاملة  
Truck - الشاحنات مع أنواع مختلفة
Container - الحاويات مع تتبع الحالة
DeliveryOrder - أذونات التسليم
Trip - الرحلات مع ربط شامل
```

## التقنيات المستخدمة

- **Backend**: Django 4.2.11, SQLite/PostgreSQL
- **Frontend**: Bootstrap, JavaScript, FontAwesome
- **Export**: XlsxWriter, ReportLab
- **Arabic Support**: arabic-reshaper, python-bidi

## بنية المشروع

```
agent-master/
├── myproject/      # إعدادات المشروع
├── users/          # إدارة المستخدمين والاشتراكات
├── port/           # الوظائف الأساسية للميناء
├── templates/      # قوالب HTML
├── static/         # ملفات CSS, JS, Images
└── requirements.txt
```

## الوصول للنظام

بعد التشغيل:
- **التطبيق**: http://localhost:8000
- **لوحة الإدارة**: http://localhost:8000/admin
- **تسجيل الدخول**: برقم الهاتف

## المتطلبات

- Python 3.8+
- Django 4.2+
- SQLite (افتراضي) أو PostgreSQL

## إعداد قاعدة البيانات

### SQLite (الحالي)
```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### PostgreSQL (للإنتاج)
```python
# قم بإلغاء التعليق في settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}
```

## أوامر مفيدة

```bash
# إنشاء بيانات تجريبية
python manage.py create_test_data

# تحديث حالة الرحلات
python manage.py update_trips_status

# جمع الملفات الثابتة
python manage.py collectstatic

# إنشاء نسخة احتياطية
python manage.py dumpdata > backup.json
```

## المساهمة

1. Fork المشروع
2. إنشاء فرع للميزة الجديدة
3. Commit التغييرات
4. Push للفرع
5. إنشاء Pull Request

## الترخيص

هذا المشروع مطور لبيئة العمل العراقية مع دعم كامل للغة العربية.

---

للمزيد من التفاصيل، راجع [الدليل الشامل](README_APPLICATION.md) 