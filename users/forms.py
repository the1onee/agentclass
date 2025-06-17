from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='رقم الهاتف',
        widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'})
    )
    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    error_messages = {
        'invalid_login': 'رقم الهاتف أو كلمة المرور غير صحيحة',
        'inactive': 'هذا الحساب غير مفعل'
    } 