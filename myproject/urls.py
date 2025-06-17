from django.contrib import admin
from django.urls import path, include  # إضافة include هنا

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('port/', include('port.urls')),
    
]