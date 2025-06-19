from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.account, name='account'),
    path('subscription-expired/', views.subscription_expired, name='subscription_expired'),
    path('disclaimer/', views.disclaimer, name='disclaimer'),
]