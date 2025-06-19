from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # استثناء صفحات معينة من فحص الاشتراك
        excluded_paths = [
            reverse('users:subscription_expired'),
            reverse('users:login'),
            reverse('users:logout'),
            reverse('users:home'),
            reverse('users:disclaimer'),
        ]
        
        if request.user.is_authenticated and not request.path.startswith('/admin/'):
            if request.path not in excluded_paths:
                if not request.user.is_subscription_active:
                    messages.warning(request, 'انتهت صلاحية اشتراكك. يرجى التواصل مع المندوب عبر الواتساب لتجديد الاشتراك.')
                    return redirect('users:subscription_expired')
                elif request.user.subscription_end_date and request.user.subscription_end_date < timezone.now():
                    request.user.is_subscription_active = False
                    request.user.save()
                    messages.warning(request, 'انتهت صلاحية اشتراكك. يرجى التواصل مع المندوب عبر الواتساب لتجديد الاشتراك.')
                    return redirect('users:subscription_expired')
        
        return self.get_response(request) 