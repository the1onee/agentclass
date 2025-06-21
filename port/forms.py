from django import forms
from .models import Driver, Truck, DeliveryOrder, Container, Trip, Company, DriverTransaction, CompanyTransaction, DriverFinancialAccount
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
import json
from django.db import IntegrityError

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = ['name', 'phone_number']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        driver = super().save(commit=False)
        if self.user:
            driver.user = self.user
        if commit:
            driver.save()
        return driver

class TruckForm(forms.ModelForm):
    class Meta:
        model = Truck
        fields = ['plate_number', 'governorate', 'truck_type', 'is_active']
        widgets = {
            'plate_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل رقم اللوحة',
                'dir': 'rtl'
            }),
            'governorate': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'truck_type': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
                'checked': 'checked'  # تعيين القيمة الافتراضية إلى نشط
            })
        }

    def clean_plate_number(self):
        plate_number = self.cleaned_data.get('plate_number')
        instance = getattr(self, 'instance', None)
        
        # التحقق من تكرار رقم اللوحة
        if instance and instance.pk:
            # في حالة التعديل، نستثني الشاحنة الحالية من الفحص
            if Truck.objects.filter(plate_number=plate_number).exclude(pk=instance.pk).exists():
                raise forms.ValidationError('رقم اللوحة موجود مسبقاً. الرجاء إدخال رقم لوحة آخر.')
        else:
            # في حالة الإضافة
            if Truck.objects.filter(plate_number=plate_number).exists():
                raise forms.ValidationError('رقم اللوحة موجود مسبقاً. الرجاء إدخال رقم لوحة آخر.')
        
        return plate_number

    def save(self, commit=True):
        truck = super().save(commit=False)
        if commit:
            try:
                truck.save()
            except IntegrityError:
                # إذا حدث خطأ في قاعدة البيانات، نرفع خطأ تحقق
                raise forms.ValidationError('حدث خطأ أثناء حفظ البيانات. رقم اللوحة موجود مسبقاً.')
        return truck

class DeliveryOrderForm(forms.ModelForm):
    bulk_containers = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'dir': 'ltr',
            'placeholder': 'أدخل أرقام الحاويات (حاوية واحدة في كل سطر)'
        }),
        required=False,
        label='إضافة حاويات متعددة'
    )
    


    class Meta:
        model = DeliveryOrder
        fields = ['order_number', 'issue_date', 'expiry_date', 'notes', 'status', 'container_size']
        widgets = {
            'order_number': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'issue_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'expiry_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'container_size': forms.Select(attrs={'class': 'form-control', 'dir': 'rtl'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize bulk_containers as empty if not provided
        if 'instance' in kwargs and kwargs['instance']:
            # This is an edit form, we don't need bulk_containers for editing
            self.fields.pop('bulk_containers', None)
        
        # إعداد تسميات الحقول باللغة العربية
        self.fields['container_size'].label = 'حجم الحاويات'
        if hasattr(self.fields['container_size'], 'help_text'):
            self.fields['container_size'].help_text = 'سيتم تطبيق هذا الحجم على جميع الحاويات المرتبطة بهذا الإذن'

    def clean_bulk_containers(self):
        bulk_containers = self.cleaned_data.get('bulk_containers', '')
        if bulk_containers:
            container_numbers = [str(num).strip() for num in bulk_containers.split('\n') if str(num).strip()]
            
            # التحقق من وجود تكرارات في نفس الإدخال
            duplicates = set([num for num in container_numbers if container_numbers.count(num) > 1])
            if duplicates:
                raise forms.ValidationError(
                    f'هنالك حاويات متكررة في نفس الإذن: {", ".join([str(d) for d in duplicates])}'
                )
            
            # التحقق من الحاويات المرتبطة بأذونات أخرى
            existing_containers = Container.objects.filter(
                container_number__in=container_numbers,
                delivery_order__isnull=False
            ).values_list('container_number', flat=True)
            
        return bulk_containers

    def save(self, commit=True):
        order = super().save(commit=False)
        if commit:
            order.save()
            
            # إضافة الحاويات الجديدة (إذا وُجدت)
            bulk_containers = self.cleaned_data.get('bulk_containers', '')
            container_size = order.container_size  # استخدام الحجم المحفوظ في إذن التسليم
            
            if bulk_containers:
                container_numbers = [num.strip() for num in bulk_containers.split('\n') if num.strip()]
                
                # تحديث الحاويات الموجودة وإنشاء الجديدة
                for num in container_numbers:
                    Container.objects.update_or_create(
                        container_number=num,
                        defaults={
                            'user': order.user,
                            'container_type': container_size,  # استخدام الحجم المحفوظ
                            'delivery_order': order,
                            'status': order.status, # تحديث حالة الحاويات المرتبطة
                            'weight': 40  # تعيين الوزن تلقائيًا إلى 40
                        }
                    )
            
            # تحديث جميع حاويات الإذن بالحجم والحالة الجديدة (سواء كانت موجودة من قبل أم جديدة)
            Container.objects.filter(delivery_order=order).update(
                status=order.status, 
                weight=40,
                container_type=container_size  # تحديث الحجم لجميع الحاويات
            )
            
            # طباعة رسالة للتأكد من التحديث (للتصحيح)
            print(f"✅ تم تحديث جميع حاويات إذن التسليم {order.order_number} إلى الحجم: {container_size}")
         
        
        return order

class ContainerForm(forms.ModelForm):
    class Meta:
        model = Container
        fields = ['container_number', 'container_type', 'weight', 'delivery_order']
        widgets = {
            'container_number': forms.TextInput(attrs={'class': 'form-control'}),
            'container_type': forms.Select(attrs={'class': 'form-select'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'delivery_order': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['delivery_order'].queryset = DeliveryOrder.objects.filter(user=user)

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = ['delivery_order', 'start_time']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'delivery_order': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # إعداد التسميات باللغة العربية
        self.fields['delivery_order'].label = 'إذن التسليم'
        self.fields['start_time'].label = 'تاريخ ووقت البداية'
        
        if self.user:
            # فلترة أذونات التسليم حسب المستخدم
            self.fields['delivery_order'].queryset = DeliveryOrder.objects.filter(
                user=self.user
            ).exclude(
                trips__status__in=['pending', 'active']
            ).order_by('-issue_date')
            
            # إضافة خيار فارغ
            self.fields['delivery_order'].empty_label = "-- اختر إذن التسليم --"
            
            # إذا كان التعديل، نشمل إذن التسليم الحالي
            if self.instance and self.instance.pk and self.instance.delivery_order:
                current_delivery_order = self.instance.delivery_order
                # التأكد من أن إذن التسليم الحالي موجود في الخيارات
                all_orders = list(self.fields['delivery_order'].queryset)
                if current_delivery_order not in all_orders:
                    all_orders.append(current_delivery_order)
                    self.fields['delivery_order'].queryset = DeliveryOrder.objects.filter(
                        id__in=[order.id for order in all_orders]
                    ).order_by('-issue_date')

    def clean_delivery_order(self):
        """التحقق من صحة إذن التسليم"""
        delivery_order = self.cleaned_data.get('delivery_order')
        
        if not delivery_order:
            raise forms.ValidationError('يجب اختيار إذن تسليم')
        
        # التحقق من أن إذن التسليم ينتمي للمستخدم الحالي
        if self.user and delivery_order.user != self.user:
            raise forms.ValidationError('إذن التسليم غير صالح أو غير مصرح لك بالوصول إليه')
        
        # التحقق من عدم وجود رحلة نشطة لنفس إذن التسليم (في حالة الإضافة)
        if not self.instance.pk:  # رحلة جديدة
            existing_trips = Trip.objects.filter(
                delivery_order=delivery_order,
                status__in=['pending', 'active']
            )
            if existing_trips.exists():
                raise forms.ValidationError(
                    f'يوجد بالفعل رحلة نشطة أو قيد الانتظار لإذن التسليم {delivery_order.order_number}'
                )
        
        return delivery_order
    
    def clean_start_time(self):
        """التحقق من صحة تاريخ البداية"""
        start_time = self.cleaned_data.get('start_time')
        
        if not start_time:
            # إذا لم يتم تحديد وقت، نستخدم الوقت الحالي
            start_time = timezone.now()
        
        # يمكن إضافة المزيد من التحققات هنا حسب الحاجة
        # مثل التأكد من أن الوقت ليس في الماضي البعيد
        
        return start_time

    def save(self, commit=True):
        trip = super().save(commit=False)
        
        # تعيين المستخدم إذا لم يكن موجوداً
        if not trip.pk and self.user:  # رحلة جديدة
            trip.user = self.user
        
        # تعيين الحالة الافتراضية
        if not trip.pk:
            trip.status = 'pending'
        
        if commit:
            trip.save()
            
            # إضافة حاويات إذن التسليم إلى الرحلة إذا كانت رحلة جديدة
            if not self.instance.pk and trip.delivery_order:
                containers = Container.objects.filter(delivery_order=trip.delivery_order)
                if containers.exists():
                    trip.containers.set(containers)
        
        return trip


# ===== نماذج إدارة الشركات =====
class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'name', 'company_type', 'registration_number', 'tax_number',
            'contact_person', 'phone_number', 'email', 'address', 'city',
            'country', 'credit_limit', 'contract_start_date', 'contract_end_date',
            'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل اسم الشركة',
                'dir': 'rtl'
            }),
            'company_type': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم التسجيل',
                'dir': 'ltr'
            }),
            'tax_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الرقم الضريبي (اختياري)',
                'dir': 'ltr'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الشخص المسؤول',
                'dir': 'rtl'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الهاتف',
                'dir': 'ltr'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'البريد الإلكتروني (اختياري)',
                'dir': 'ltr'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'العنوان الكامل',
                'dir': 'rtl'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'المدينة',
                'dir': 'rtl'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'credit_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'contract_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'contract_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
        }

    def clean_registration_number(self):
        registration_number = self.cleaned_data.get('registration_number')
        instance = getattr(self, 'instance', None)
        
        # التحقق من تكرار رقم التسجيل
        if instance and instance.pk:
            if Company.objects.filter(registration_number=registration_number).exclude(pk=instance.pk).exists():
                raise forms.ValidationError('رقم التسجيل موجود مسبقاً. الرجاء إدخال رقم تسجيل آخر.')
        else:
            if Company.objects.filter(registration_number=registration_number).exists():
                raise forms.ValidationError('رقم التسجيل موجود مسبقاً. الرجاء إدخال رقم تسجيل آخر.')
        
        return registration_number

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('contract_start_date')
        end_date = cleaned_data.get('contract_end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError('تاريخ انتهاء التعاقد يجب أن يكون بعد تاريخ البداية.')
        
        return cleaned_data


# ===== نماذج المعاملات المالية =====
class DriverTransactionForm(forms.ModelForm):
    class Meta:
        model = DriverTransaction
        fields = [
            'driver_account', 'transaction_type', 'amount', 'description',
            'payment_method', 'reference_number', 'transaction_date',
            'due_date', 'trip', 'status'
        ]
        widgets = {
            'driver_account': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف المعاملة',
                'dir': 'rtl'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم المرجع (اختياري)',
                'dir': 'ltr'
            }),
            'transaction_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'trip': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # فلترة حسابات السائقين للمستخدم الحالي
            self.fields['driver_account'].queryset = DriverFinancialAccount.objects.filter(user=user)
            # فلترة الرحلات للمستخدم الحالي
            self.fields['trip'].queryset = Trip.objects.filter(user=user)
        
        # جعل الحقول الاختيارية غير مطلوبة
        self.fields['reference_number'].required = False
        self.fields['due_date'].required = False
        self.fields['trip'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من الصفر.')
        return amount


class CompanyTransactionForm(forms.ModelForm):
    class Meta:
        model = CompanyTransaction
        fields = [
            'company', 'transaction_type', 'amount', 'description',
            'payment_method', 'reference_number', 'invoice_number',
            'transaction_date', 'due_date', 'delivery_order', 'trip', 'status'
        ]
        widgets = {
            'company': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف المعاملة',
                'dir': 'rtl'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم المرجع (اختياري)',
                'dir': 'ltr'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الفاتورة (اختياري)',
                'dir': 'ltr'
            }),
            'transaction_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'delivery_order': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'trip': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'dir': 'rtl'
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # فلترة البيانات للمستخدم الحالي
            self.fields['company'].queryset = Company.objects.filter(user=user)
            self.fields['delivery_order'].queryset = DeliveryOrder.objects.filter(user=user)
            self.fields['trip'].queryset = Trip.objects.filter(user=user)
        
        # جعل الحقول الاختيارية غير مطلوبة
        self.fields['reference_number'].required = False
        self.fields['invoice_number'].required = False
        self.fields['due_date'].required = False
        self.fields['delivery_order'].required = False
        self.fields['trip'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise forms.ValidationError('المبلغ يجب أن يكون أكبر من الصفر.')
        return amount


# نموذج البحث المتقدم للشركات
class CompanySearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث بالاسم أو رقم التسجيل...',
            'dir': 'rtl'
        }),
        label='البحث'
    )
    company_type = forms.ChoiceField(
        choices=[('', 'جميع الأنواع')] + Company.COMPANY_TYPES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'dir': 'rtl'
        }),
        label='نوع الشركة'
    )
    status = forms.ChoiceField(
        choices=[('', 'جميع الحالات')] + Company.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'dir': 'rtl'
        }),
        label='الحالة'
    )


# نموذج البحث في المعاملات المالية
class TransactionSearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث في الوصف أو رقم المرجع...',
            'dir': 'rtl'
        }),
        label='البحث'
    )
    transaction_type = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'dir': 'rtl'
        }),
        label='نوع المعاملة'
    )
    status = forms.ChoiceField(
        choices=[('', 'جميع الحالات')] + DriverTransaction.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'dir': 'rtl'
        }),
        label='الحالة'
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='من تاريخ'
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='إلى تاريخ'
    ) 