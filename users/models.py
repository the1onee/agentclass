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