from django.contrib import admin
from django.urls import path, include  # إضافة include هنا
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('port.urls')),  # الصفحة الرئيسية تتوجه لتطبيق المندوب
    path('port/', RedirectView.as_view(url='/', permanent=True)),  # إعادة توجيه /port/ إلى /
    path('users/', include('users.urls')),  # نقل مسارات المستخدمين إلى /users/
]