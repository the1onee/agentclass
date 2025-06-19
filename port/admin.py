from django.contrib import admin
from .models import Driver, Truck, DeliveryOrder, Container, Trip, Company, DriverTransaction, CompanyTransaction, DriverFinancialAccount, FinancialReport

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'mother_name', 'governorate', 'is_active')
    list_filter = ('is_active', 'governorate')
    search_fields = ('name', 'phone_number')


# قم ب اضافه الشاحنات في الادمن 
@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ('plate_number', 'truck_type', 'is_active')
    list_filter = ('is_active', 'truck_type')
    search_fields = ('plate_number',)


@admin.register(DeliveryOrder)
class DeliveryOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'issue_date', 'status')
    list_filter = ('status', 'issue_date')
    search_fields = ('order_number',)
    date_hierarchy = 'issue_date'

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('container_number', 'container_type', 'status', 'driver', 'truck', 'delivery_order')
    list_filter = ('status', 'container_type')
    search_fields = ('container_number',)
    raw_id_fields = ('driver', 'truck', 'delivery_order')



@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['delivery_order', 'status', 'start_time', 'end_time', 'get_containers']
    list_filter = ['status', 'start_time']
    search_fields = ['delivery_order__order_number']
    date_hierarchy = 'start_time'
    filter_horizontal = ('containers',)
    
    def get_containers(self, obj):
        return ", ".join([c.container_number for c in obj.containers.all()])
    get_containers.short_description = 'الحاويات'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('delivery_order', 'user')

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'delivery_order':
            if not request.user.is_superuser:
                kwargs['queryset'] = db_field.related_model.objects.filter(user=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'containers':
            if not request.user.is_superuser:
                kwargs['queryset'] = Container.objects.filter(user=request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# ===== إدارة الشركات =====
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_type', 'registration_number', 'contact_person', 'phone_number', 'status', 'created_at')
    list_filter = ('company_type', 'status', 'created_at', 'city')
    search_fields = ('name', 'registration_number', 'contact_person', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('name', 'company_type', 'registration_number', 'tax_number', 'status')
        }),
        ('معلومات الاتصال', {
            'fields': ('contact_person', 'phone_number', 'email', 'address', 'city', 'country')
        }),
        ('معلومات مالية', {
            'fields': ('credit_limit', 'contract_start_date', 'contract_end_date')
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)


# ===== إدارة الحسابات المالية للسائقين =====
@admin.register(DriverFinancialAccount)
class DriverFinancialAccountAdmin(admin.ModelAdmin):
    list_display = ('driver', 'current_balance', 'total_earned', 'total_deducted', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('driver__name', 'driver__phone_number')
    readonly_fields = ('current_balance', 'total_earned', 'total_deducted', 'created_at', 'updated_at')
    
    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)


# ===== إدارة المعاملات المالية مع السائقين =====
@admin.register(DriverTransaction)
class DriverTransactionAdmin(admin.ModelAdmin):
    list_display = ('driver_account', 'transaction_type', 'amount', 'status', 'transaction_date', 'reference_number')
    list_filter = ('transaction_type', 'status', 'payment_method', 'transaction_date')
    search_fields = ('driver_account__driver__name', 'description', 'reference_number')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('معلومات المعاملة', {
            'fields': ('driver_account', 'transaction_type', 'amount', 'description', 'status')
        }),
        ('معلومات الدفع', {
            'fields': ('payment_method', 'reference_number', 'transaction_date', 'due_date')
        }),
        ('الربط', {
            'fields': ('trip',),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'driver_account':
            if not request.user.is_superuser:
                kwargs['queryset'] = DriverFinancialAccount.objects.filter(user=request.user)
        elif db_field.name == 'trip':
            if not request.user.is_superuser:
                kwargs['queryset'] = Trip.objects.filter(user=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ===== إدارة المعاملات المالية مع الشركات =====
@admin.register(CompanyTransaction)
class CompanyTransactionAdmin(admin.ModelAdmin):
    list_display = ('company', 'transaction_type', 'amount', 'status', 'transaction_date', 'invoice_number')
    list_filter = ('transaction_type', 'status', 'payment_method', 'transaction_date')
    search_fields = ('company__name', 'description', 'reference_number', 'invoice_number')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'transaction_date'
    
    fieldsets = (
        ('معلومات المعاملة', {
            'fields': ('company', 'transaction_type', 'amount', 'description', 'status')
        }),
        ('معلومات الدفع', {
            'fields': ('payment_method', 'reference_number', 'invoice_number', 'transaction_date', 'due_date')
        }),
        ('الربط', {
            'fields': ('delivery_order', 'trip'),
            'classes': ('collapse',)
        }),
        ('معلومات النظام', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'company':
            if not request.user.is_superuser:
                kwargs['queryset'] = Company.objects.filter(user=request.user)
        elif db_field.name == 'delivery_order':
            if not request.user.is_superuser:
                kwargs['queryset'] = DeliveryOrder.objects.filter(user=request.user)
        elif db_field.name == 'trip':
            if not request.user.is_superuser:
                kwargs['queryset'] = Trip.objects.filter(user=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ===== إدارة التقارير المالية =====
@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'start_date', 'end_date', 'total_income', 'total_expenses', 'net_profit', 'created_at')
    list_filter = ('report_type', 'created_at', 'start_date', 'end_date')
    search_fields = ('title', 'report_type')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return super().get_queryset(request).filter(user=request.user)

    def save_model(self, request, obj, form, change):
        if not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)
