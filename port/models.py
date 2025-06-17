from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Driver(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='drivers',
        #add the new fild mothername

        verbose_name='المستخدم'
    )
    GOVERNORATE_CHOICES = [
        ('BGD', 'بغداد'),
        ('BSR', 'البصرة'),
        ('NBL', 'بابل'),
        ('KRB', 'كربلاء'),
        ('NJF', 'النجف'),
        
        # يمكن إضافة المزيد من المحافظات
    ]

    name = models.CharField(max_length=100, verbose_name="اسم السائق")
    phone_regex = RegexValidator(
        regex=r'^\d{11}$',
        message="رقم الهاتف يجب أن يكون 11 رقم"
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=11,
        unique=True,
        verbose_name="رقم الهاتف"
    )
    mother_name = models.CharField(max_length=100, verbose_name="اسم الأم")
    governorate = models.CharField(
        max_length=3,
        choices=GOVERNORATE_CHOICES,
        verbose_name="المحافظة"
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    license_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="رقم الرخصة")
    id_number = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "السائق"
        verbose_name_plural = "السائقين"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

class Truck(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="المستخدم"
    )
    TRUCK_TYPES = [
        ('FLAT', 'مسطحة'),
        ('CONT', 'حاويات'),
        ('TANK', 'صهريج'),
    ]

    GOVERNORATE_CHOICES = [
        ('BGD', 'بغداد'),
        ('NNW', 'نينوى'),
        ('BSR', 'البصرة'),
        ('SLY', 'السليمانية'),
        ('ARB', 'أربيل'),
        ('THQ', 'ذي قار'),
        ('NBL', 'بابل'),
        ('ANB', 'الأنبار'),
        ('DIY', 'ديالى'),
        ('KRK', 'كركوك'),
        ('NJF', 'النجف'),
        ('WST', 'واسط'),
        ('QDS', 'القادسية'),
        ('SLH', 'صلاح الدين'),
        ('KRB', 'كربلاء'),
        ('MSN', 'ميسان'),
        ('DHK', 'دهوك'),
        ('MTH', 'المثنى'),
    ]

    id = models.CharField(
        primary_key=True,
        max_length=50,
        verbose_name="المعرف"
    )
    plate_number = models.CharField(max_length=20, unique=True, verbose_name="رقم اللوحة")
    governorate = models.CharField(max_length=50, choices=GOVERNORATE_CHOICES, verbose_name="المحافظة")
    truck_type = models.CharField(max_length=50, choices=TRUCK_TYPES, verbose_name="نوع الشاحنة")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # إنشاء ID من المحافظة ورقم اللوحة
        self.id = f"{self.governorate}_{self.plate_number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plate_number} - {self.get_governorate_display()}"

    class Meta:
        verbose_name = "شاحنة"
        verbose_name_plural = "الشاحنات"
        ordering = ['-created_at']

class DeliveryOrder(models.Model):
    STATUS_CHOICES = [
        ('LOADING', 'تحميل'),
        ('EMPTY', 'فارغ'),
        ('GENERAL_CARGO', 'بضائع عامة'),
        ('UNLOADING', 'تجزئة')
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_orders',
        verbose_name='المستخدم'
    )
    order_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="رقم الإذن"
    )
    issue_date = models.DateTimeField(
        verbose_name="تاريخ الإصدار"
    )
    expiry_date = models.DateTimeField(
        verbose_name="تاريخ الانتهاء",
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='LOADING',
        verbose_name="الحالة"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # التحقق إذا كان الإذن جديداً
        super().save(*args, **kwargs)
        
        # إذا كان الإذن جديداً وكانت هناك حاويات محددة
        if is_new and hasattr(self, 'bulk_containers'):
            container_numbers = [num.strip() for num in self.bulk_containers.split('\n') if num.strip()]
            
            # تحديث الحاويات المحددة
            Container.objects.filter(
                container_number__in=container_numbers,
                user=self.user
            ).update(
                delivery_order=self,
                status=self.status
            )

    class Meta:
        verbose_name = "إذن التسليم"
        verbose_name_plural = "أذونات التسليم"
        ordering = ['-issue_date']

    def __str__(self):
        return f"إذن رقم {self.order_number}"

class Container(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='containers',
        verbose_name='المستخدم'
    )
    container_number = models.CharField(max_length=50)
    CONTAINER_TYPES = [
        ('20DC', '20 قدم عادي'),
        ('40DC', '40 قدم عادي'),
        ('20RF', '20 قدم مبرد'),
        ('40RF', '40 قدم مبرد'),
        ('TANK', 'صهريج'),
    ]
    container_type = models.CharField(
        max_length=4,
        choices=CONTAINER_TYPES,
        verbose_name="نوع الحاوية"
    )
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="الوزن (طن)",
        null=True,
        blank=True
    )
    delivery_order = models.ForeignKey(
        DeliveryOrder,
        on_delete=models.SET_NULL,
        related_name='containers',
        verbose_name="إذن التسليم",
        null=True,
        blank=True
    )
    driver = models.ForeignKey(
        'Driver',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="السائق"
    )
    truck = models.ForeignKey(
        'Truck',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="الشاحنة"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    content_description = models.TextField(
        blank=True,
        verbose_name="وصف المحتويات"
    )
    STATUS_CHOICES = [
        ('LOADING', 'تحميل'),
        ('EMPTY', 'فارغ'),
        ('GENERAL_CARGO', 'بضائع عامة'),
        ('UNLOADING', 'تجزئة')
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='LOADING',
        verbose_name="الحالة"
    )
    size = models.CharField(max_length=50, blank=True, null=True, verbose_name="الحجم")

    def save(self, *args, **kwargs):
        # إذا كان هناك إذن تسليم مرتبط، نأخذ حالته
        if self.delivery_order:
            self.status = self.delivery_order.status
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "الحاوية"
        verbose_name_plural = "الحاويات"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.container_number} - {self.get_container_type_display()}"


class Trip(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('active', 'نشط'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]
    
    delivery_order = models.ForeignKey(
        'DeliveryOrder', 
        on_delete=models.CASCADE, 
        verbose_name='إذن التسليم',
        related_name='trips'
    )
    
    containers = models.ManyToManyField(Container, related_name='trips', blank=True)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    
    start_time = models.DateTimeField(
        verbose_name='تاريخ البداية',
        default=timezone.now
    )
    
    end_time = models.DateTimeField(
        verbose_name='تاريخ النهاية',
        null=True,
        blank=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='الحالة'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    driver_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="اسم السائق")
    truck_plate = models.CharField(max_length=50, blank=True, null=True, verbose_name="رقم لوحة الشاحنة")

    def __str__(self):
        return f"رحلة {self.delivery_order.order_number}"

    def check_auto_complete(self):
        """التحقق مما إذا كان يجب تحديث حالة الرحلة تلقائياً"""
        if self.status == 'active' and self.created_at:
            three_days_ago = timezone.now() - timedelta(days=3)
            if self.created_at <= three_days_ago:
                self.status = 'completed'
                self.end_time = timezone.now()
                self.save(update_fields=['status', 'end_time'])
                return True
        return False

    def save(self, *args, **kwargs):
        if not self.end_time:
            self.end_time = self.start_time + timedelta(days=2)
             
        # إذا كانت الرحلة جديدة، تعيين وقت الإنشاء
        if not self.id:
            self.created_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'رحلة'
        verbose_name_plural = 'رحلات'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['delivery_order'],
                name='unique_delivery_order_trip'
            )
        ] 

    #قم بعمل يوزر ل مخول طباعه واريده يعمل علي الموديل السابق
   