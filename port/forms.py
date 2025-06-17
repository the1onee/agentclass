from django import forms
from .models import Driver, Truck, DeliveryOrder, Container, Trip
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
        fields = ['order_number', 'issue_date', 'expiry_date', 'notes', 'status']
        widgets = {
            'order_number': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'issue_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'expiry_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize bulk_containers as empty if not provided
        if 'instance' in kwargs and kwargs['instance']:
            # This is an edit form, we don't need bulk_containers for editing
            self.fields.pop('bulk_containers', None)

    def clean_bulk_containers(self):
        bulk_containers = self.cleaned_data.get('bulk_containers', '')
        if bulk_containers:
            container_numbers = [num.strip() for num in bulk_containers.split('\n') if num.strip()]
            
            # التحقق من وجود تكرارات في نفس الإدخال
            duplicates = set([num for num in container_numbers if container_numbers.count(num) > 1])
            if duplicates:
                raise forms.ValidationError(
                    f'هنالك حاويات متكررة في نفس الإذن: {", ".join(duplicates)}'
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
            
            # إضافة الحاويات
            bulk_containers = self.cleaned_data.get('bulk_containers', '')
            if bulk_containers:
                container_numbers = [num.strip() for num in bulk_containers.split('\n') if num.strip()]
                
                # تحديث الحاويات الموجودة وإنشاء الجديدة
                for num in container_numbers:
                    Container.objects.update_or_create(
                        container_number=num,
                        defaults={
                            'user': order.user,
                            'container_type': '40DC',
                            'delivery_order': order,
                            'status': order.status, # تحديث حالة الحاويات المرتبطة
                            'weight': 40  # تعيين الوزن تلقائيًا إلى 40
                        }
                    )
            Container.objects.filter(delivery_order=order).update(status=order.status, weight=40)  # تحديث الوزن أيضًا
         
        
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
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['delivery_order'].queryset = DeliveryOrder.objects.filter(user=self.user)
            
            if self.instance and self.instance.pk:
                current_delivery_order = self.instance.delivery_order
                self.fields['delivery_order'].queryset = self.fields['delivery_order'].queryset | DeliveryOrder.objects.filter(pk=current_delivery_order.pk)

    def save(self, commit=True):
        trip = super().save(commit=False)
        if not trip.pk:  # إذا كانت رحلة جديدة
            trip.user = self.user
        
        # حفظ الرحلة بدون الحاويات أولاً
        trip.save()

        # إذا كان هناك إذن تسليم، نضيف الحاويات بعد حفظ الرحلة
        if trip.delivery_order:
            containers = Container.objects.filter(delivery_order=trip.delivery_order)
            # نستخدم clear() ثم add() بدلاً من set()
            trip.containers.clear()
            trip.containers.add(*containers)

        return trip

    def clean_delivery_order(self):
        delivery_order = self.cleaned_data.get('delivery_order')
        if delivery_order:
            # التحقق من عدم وجود رحلة نشطة تستخدم نفس إذن التسليم
            existing_trip = Trip.objects.filter(
                delivery_order=delivery_order,
                status__in=['pending', 'active']
            )
            if self.instance and self.instance.pk:
                existing_trip = existing_trip.exclude(pk=self.instance.pk)
            
            if existing_trip.exists():
                raise forms.ValidationError('هذا الإذن مستخدم بالفعل في رحلة نشطة')
        return delivery_order 