from django.contrib import admin
from .models import Driver, Truck, DeliveryOrder, Container, Trip

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
