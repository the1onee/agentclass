from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from users.models import CustomUser, Subscription
from django.utils.translation import gettext_lazy as _

class CustomUserAdmin(UserAdmin):
    list_display = ('phone_number', 'email', 'first_name', 'last_name', 'user_type', 
                   'is_subscription_active', 'subscription_end_date')
    list_filter = ('is_subscription_active', 'user_type')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name')
    ordering = ('phone_number',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'user_type')}),
        (_('Subscription'), {'fields': ('is_subscription_active', 'subscription_end_date')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'email', 'password1', 'password2', 'user_type'),
        }),
    )

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'end_date', 'amount_paid')
    list_filter = ('start_date', 'end_date')
    search_fields = ('user__phone_number', 'user__email')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # تحديث حالة اشتراك المستخدم عند إضافة اشتراك جديد
        obj.user.subscription_end_date = obj.end_date
        obj.user.is_subscription_active = True
        obj.user.save()

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Subscription, SubscriptionAdmin) 