from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta

class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, email, password=None, **extra_fields):
        if not phone_number:
            raise ValueError('رقم الهاتف مطلوب')
        email = self.normalize_email(email)
        user = self.model(phone_number=phone_number, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(phone_number, email, password, **extra_fields)

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('DELIVERY', 'مندوب'),
        ('SUPERVISOR', 'مشرف'),
        ('MANAGER', 'مدير'),
    )
    
    phone_number = models.CharField(max_length=15, unique=True, verbose_name="رقم الهاتف")
    email = models.EmailField(unique=True)
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPE_CHOICES,
        verbose_name="نوع المستخدم"
    )
    is_subscription_active = models.BooleanField(default=False, verbose_name="الاشتراك مفعل")
    subscription_end_date = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ انتهاء الاشتراك")
    username = None
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['email', 'user_type']

    objects = CustomUserManager()

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمين"

    def __str__(self):
        return self.phone_number

    def activate_subscription(self, months=1):
        """تفعيل الاشتراك لعدد محدد من الشهور"""
        if self.subscription_end_date and self.subscription_end_date > timezone.now():
            # إذا كان الاشتراك ما زال فعالاً، أضف الشهور إلى تاريخ الانتهاء الحالي
            self.subscription_end_date += timedelta(days=30 * months)
        else:
            # إذا كان الاشتراك منتهياً، ابدأ من اليوم
            self.subscription_end_date = timezone.now() + timedelta(days=30 * months)
        
        self.is_subscription_active = True
        self.save()

class Subscription(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="المستخدم")
    start_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ بداية الاشتراك")
    end_date = models.DateTimeField(verbose_name="تاريخ نهاية الاشتراك")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ المدفوع")
    
    class Meta:
        verbose_name = "اشتراك"
        verbose_name_plural = "الاشتراكات"

    def __str__(self):
        return f"اشتراك {self.user.phone_number} - ينتهي في {self.end_date.date()}"

class SubscriptionPlan(models.Model):
    """خطط الاشتراك المختلفة"""
    PLAN_TYPES = [
        ('trial', 'تجريبي - 7 أيام'),
        ('basic', 'أساسي'),
        ('premium', 'مميز'),
        ('enterprise', 'مؤسسي'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='اسم الخطة')
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True, verbose_name='نوع الخطة')
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='السعر الشهري (دينار)')
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='السعر السنوي (دينار)')
    
    # الحدود والميزات
    max_containers = models.IntegerField(verbose_name='الحد الأقصى للحاويات')
    max_trucks = models.IntegerField(verbose_name='الحد الأقصى للشاحنات')
    max_drivers = models.IntegerField(verbose_name='الحد الأقصى للسائقين')
    max_trips_per_month = models.IntegerField(verbose_name='الحد الأقصى للرحلات شهرياً')
    
    # الميزات
    has_financial_reports = models.BooleanField(default=False, verbose_name='التقارير المالية')
    has_advanced_analytics = models.BooleanField(default=False, verbose_name='التحليلات المتقدمة')
    has_api_access = models.BooleanField(default=False, verbose_name='الوصول للـ API')
    has_export_features = models.BooleanField(default=False, verbose_name='ميزات التصدير')
    has_priority_support = models.BooleanField(default=False, verbose_name='الدعم الفني المتقدم')
    
    description = models.TextField(verbose_name='وصف الخطة')
    features_list = models.JSONField(default=list, verbose_name='قائمة الميزات')
    is_active = models.BooleanField(default=True, verbose_name='خطة نشطة')
    is_popular = models.BooleanField(default=False, verbose_name='خطة شائعة')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'خطة اشتراك'
        verbose_name_plural = 'خطط الاشتراك'
        ordering = ['price_monthly']
    
    def __str__(self):
        return f"{self.name} - {self.price_monthly} دينار/شهر"
    
    def get_yearly_discount_percentage(self):
        if self.price_monthly > 0:
            monthly_total = self.price_monthly * 12
            if monthly_total > self.price_yearly:
                return round(((monthly_total - self.price_yearly) / monthly_total) * 100)
        return 0

class UserSubscription(models.Model):
    """اشتراك المستخدم الحالي"""
    BILLING_CYCLES = [
        ('monthly', 'شهري'),
        ('yearly', 'سنوي'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('expired', 'منتهي'),
        ('cancelled', 'ملغي'),
        ('suspended', 'معلق'),
        ('trial', 'تجريبي'),
    ]
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='subscription_info')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, verbose_name='خطة الاشتراك')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLES, verbose_name='دورة الفوترة')
    
    start_date = models.DateTimeField(verbose_name='تاريخ البداية')
    end_date = models.DateTimeField(verbose_name='تاريخ النهاية')
    auto_renew = models.BooleanField(default=True, verbose_name='التجديد التلقائي')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial', verbose_name='حالة الاشتراك')
    
    # معلومات الدفع
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ المدفوع')
    payment_method = models.CharField(max_length=50, blank=True, verbose_name='طريقة الدفع')
    
    # إحصائيات الاستخدام
    containers_used = models.IntegerField(default=0, verbose_name='الحاويات المستخدمة')
    trucks_used = models.IntegerField(default=0, verbose_name='الشاحنات المستخدمة')
    drivers_used = models.IntegerField(default=0, verbose_name='السائقين المستخدمين')
    trips_this_month = models.IntegerField(default=0, verbose_name='الرحلات هذا الشهر')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'اشتراك المستخدم'
        verbose_name_plural = 'اشتراكات المستخدمين'
    
    def __str__(self):
        return f"{self.user.phone_number} - {self.plan.name}"
    
    def save(self, *args, **kwargs):
        # تحديث حالة المستخدم
        self.user.is_subscription_active = (self.status == 'active' and not self.is_expired())
        self.user.subscription_end_date = self.end_date
        self.user.save()
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.end_date
    
    def days_remaining(self):
        if self.is_expired():
            return 0
        return (self.end_date - timezone.now()).days
    
    def usage_percentage(self):
        """نسبة الاستخدام من الحدود المسموحة"""
        usage_data = {
            'containers': (self.containers_used / self.plan.max_containers * 100) if self.plan.max_containers > 0 else 0,
            'trucks': (self.trucks_used / self.plan.max_trucks * 100) if self.plan.max_trucks > 0 else 0,
            'drivers': (self.drivers_used / self.plan.max_drivers * 100) if self.plan.max_drivers > 0 else 0,
            'trips': (self.trips_this_month / self.plan.max_trips_per_month * 100) if self.plan.max_trips_per_month > 0 else 0,
        }
        return usage_data
    
    def can_add_container(self):
        """التحقق من إمكانية إضافة حاوية جديدة"""
        return self.containers_used < self.plan.max_containers
    
    def can_add_truck(self):
        """التحقق من إمكانية إضافة شاحنة جديدة"""
        return self.trucks_used < self.plan.max_trucks
    
    def can_add_driver(self):
        """التحقق من إمكانية إضافة سائق جديد"""
        return self.drivers_used < self.plan.max_drivers
    
    def can_create_trip(self):
        """التحقق من إمكانية إنشاء رحلة جديدة هذا الشهر"""
        return self.trips_this_month < self.plan.max_trips_per_month 