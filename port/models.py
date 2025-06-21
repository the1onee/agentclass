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
    container_size = models.CharField(
        max_length=4,
        choices=[
            ('20DC', '20 قدم عادي'),
            ('40DC', '40 قدم عادي'),
            ('20RF', '20 قدم مبرد'),
            ('40RF', '40 قدم مبرد'),
            ('TANK', 'صهريج'),
        ],
        default='40DC',
        verbose_name="حجم الحاويات",
        help_text="حجم الحاويات الافتراضي لهذا الإذن"
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
        return f'رحلة {self.delivery_order.order_number} - {self.get_status_display()}'
    
    def check_auto_complete(self):
        """تحقق من إمكانية إنجاز الرحلة تلقائياً"""
        # إذا كانت جميع الحاويات مكتملة
        if self.containers.filter(status__in=['LOADING', 'GENERAL_CARGO']).count() == 0:
            self.status = 'completed'
            self.end_time = timezone.now()
            self.save()
            return True
        return False

    def save(self, *args, **kwargs):
        # التحقق من وجود المستخدم
        if not self.user_id:
            raise ValueError('يجب تحديد المستخدم للرحلة')
        
        # التحقق من وجود إذن التسليم
        if not self.delivery_order_id:
            raise ValueError('يجب تحديد إذن التسليم للرحلة')
        
        # التحقق من أن إذن التسليم ينتمي لنفس المستخدم
        if self.delivery_order and self.delivery_order.user_id != self.user_id:
            raise ValueError('إذن التسليم لا ينتمي لنفس المستخدم')
        
        # تعيين قيم افتراضية
        if not self.start_time:
            self.start_time = timezone.now()
        
        # إذا كانت حالة الرحلة "مكتملة" ولا يوجد وقت انتهاء
        if self.status == 'completed' and not self.end_time:
            self.end_time = timezone.now()
        
        # حفظ الرحلة
        super().save(*args, **kwargs)
        
        # التحقق من إكمال الرحلة تلقائياً إذا تم تسليم جميع الحاويات
        if self.status == 'active':
            self.check_auto_complete()

    class Meta:
        verbose_name = 'رحلة'
        verbose_name_plural = 'رحلات'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['delivery_order'],
                condition=models.Q(status__in=['pending', 'active']),
                name='unique_active_trip_per_order'
            )
        ]


# ===== نماذج إدارة الشركات =====
class Company(models.Model):
    COMPANY_TYPES = [
        ('shipping', 'شحن'),
        ('transport', 'نقل'),
        ('logistics', 'لوجستية'),
        ('commercial', 'تجارية'),
        ('clearance', 'تخليص'),
        ('other', 'أخرى'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('inactive', 'غير نشط'),
        ('suspended', 'معلق'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='companies',
        verbose_name='المستخدم'
    )
    name = models.CharField(max_length=200, verbose_name='اسم الشركة')
    company_type = models.CharField(
        max_length=20,
        choices=COMPANY_TYPES,
        verbose_name='نوع الشركة'
    )
    registration_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='رقم التسجيل'
    )
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='الرقم الضريبي'
    )
    contact_person = models.CharField(max_length=100, verbose_name='الشخص المسؤول')
    phone_number = models.CharField(max_length=15, verbose_name='رقم الهاتف')
    email = models.EmailField(blank=True, null=True, verbose_name='البريد الإلكتروني')
    address = models.TextField(verbose_name='العنوان')
    city = models.CharField(max_length=100, verbose_name='المدينة')
    country = models.CharField(max_length=100, default='العراق', verbose_name='البلد')
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='الحد الائتماني (دينار)'
    )
    contract_start_date = models.DateField(verbose_name='تاريخ بداية التعاقد')
    contract_end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='تاريخ انتهاء التعاقد'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='حالة الشركة'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'شركة'
        verbose_name_plural = 'شركات'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.registration_number}"

    def current_balance(self):
        """حساب الرصيد الحالي للشركة"""
        transactions = self.company_transactions.all()
        total_income = sum(t.amount for t in transactions if t.transaction_type in ['income', 'commission', 'service_fee'])
        total_payments = sum(t.amount for t in transactions if t.transaction_type in ['payment', 'fine', 'advance'])
        return total_income - total_payments


# ===== نماذج إدارة الأموال =====

class DriverFinancialAccount(models.Model):
    """الحساب المالي لكل سائق"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    driver = models.OneToOneField(
        Driver,
        on_delete=models.CASCADE,
        related_name='financial_account',
        verbose_name='السائق'
    )
    current_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='الرصيد الحالي (دينار)'
    )
    total_earned = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='إجمالي المكاسب (دينار)'
    )
    total_deducted = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='إجمالي المستقطعات (دينار)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'حساب مالي للسائق'
        verbose_name_plural = 'حسابات مالية للسائقين'

    def __str__(self):
        return f"حساب {self.driver.name} - الرصيد: {self.current_balance} دينار"

    def update_balance(self):
        """تحديث الرصيد بناءً على المعاملات"""
        transactions = self.driver_transactions.all()
        income = sum(t.amount for t in transactions if t.transaction_type in ['payment', 'bonus', 'fuel_allowance'])
        deductions = sum(t.amount for t in transactions if t.transaction_type in ['deduction', 'fine', 'advance', 'maintenance'])
        
        self.total_earned = income
        self.total_deducted = deductions
        self.current_balance = income - deductions
        self.save()


class DriverTransaction(models.Model):
    """المعاملات المالية مع السائقين"""
    TRANSACTION_TYPES = [
        ('payment', 'دفع للسائق'),
        ('deduction', 'خصم من السائق'),
        ('bonus', 'مكافأة'),
        ('fine', 'غرامة'),
        ('advance', 'سلفة'),
        ('fuel_allowance', 'بدل وقود'),
        ('maintenance', 'صيانة'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('bank_transfer', 'تحويل بنكي'),
        ('check', 'شيك'),
        ('mobile', 'موبايل'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    driver_account = models.ForeignKey(
        DriverFinancialAccount,
        on_delete=models.CASCADE,
        related_name='driver_transactions',
        verbose_name='حساب السائق'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name='نوع المعاملة'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='المبلغ (دينار)'
    )
    description = models.TextField(verbose_name='الوصف')
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        verbose_name='طريقة الدفع'
    )
    reference_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='رقم المرجع'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='حالة المعاملة'
    )
    transaction_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='تاريخ المعاملة'
    )
    due_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الاستحقاق'
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driver_transactions',
        verbose_name='الرحلة المرتبطة'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'معاملة مالية مع السائق'
        verbose_name_plural = 'معاملات مالية مع السائقين'
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.driver_account.driver.name} - {self.amount} دينار"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # تحديث رصيد السائق عند حفظ المعاملة
        if self.status == 'completed':
            self.driver_account.update_balance()


class CompanyTransaction(models.Model):
    """المعاملات المالية مع الشركات"""
    TRANSACTION_TYPES = [
        ('income', 'دخل من الشركة'),
        ('payment', 'دفع للشركة'),
        ('commission', 'عمولة'),
        ('service_fee', 'رسوم خدمة'),
        ('fine', 'غرامة'),
        ('refund', 'استرداد'),
        ('advance', 'سلفة'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'نقدي'),
        ('bank_transfer', 'تحويل بنكي'),
        ('check', 'شيك'),
        ('mobile', 'موبايل'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'معلق'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='company_transactions',
        verbose_name='الشركة'
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name='نوع المعاملة'
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='المبلغ (دينار)'
    )
    description = models.TextField(verbose_name='الوصف')
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        verbose_name='طريقة الدفع'
    )
    reference_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='رقم المرجع'
    )
    invoice_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='رقم الفاتورة'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='حالة المعاملة'
    )
    transaction_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='تاريخ المعاملة'
    )
    due_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الاستحقاق'
    )
    delivery_order = models.ForeignKey(
        DeliveryOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='company_transactions',
        verbose_name='إذن التسليم المرتبط'
    )
    trip = models.ForeignKey(
        Trip,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='company_transactions',
        verbose_name='الرحلة المرتبطة'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        verbose_name = 'معاملة مالية مع الشركة'
        verbose_name_plural = 'معاملات مالية مع الشركات'
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.company.name} - {self.amount} دينار"


class FinancialReport(models.Model):
    """التقارير المالية"""
    REPORT_TYPES = [
        ('drivers_summary', 'ملخص السائقين'),
        ('companies_summary', 'ملخص الشركات'),
        ('monthly', 'تقرير شهري'),
        ('yearly', 'تقرير سنوي'),
        ('profit_loss', 'الأرباح والخسائر'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='المستخدم'
    )
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPES,
        verbose_name='نوع التقرير'
    )
    title = models.CharField(max_length=200, verbose_name='عنوان التقرير')
    start_date = models.DateField(verbose_name='تاريخ البداية')
    end_date = models.DateField(verbose_name='تاريخ النهاية')
    total_income = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='إجمالي الدخل (دينار)'
    )
    total_expenses = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='إجمالي المصروفات (دينار)'
    )
    net_profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='صافي الربح (دينار)'
    )
    report_data = models.JSONField(
        default=dict,
        verbose_name='بيانات التقرير'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')

    class Meta:
        verbose_name = 'تقرير مالي'
        verbose_name_plural = 'تقارير مالية'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.start_date} إلى {self.end_date}"
   