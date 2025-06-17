from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomAuthenticationForm
from django.utils import timezone

def home(request):
    if request.user.is_authenticated:
        return redirect('port:home')
    
    return render(request, 'home.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'تم تسجيل الدخول بنجاح')
            return redirect('port:home')
        else:
            messages.error(request, 'اسم المستخدم أو كلمة المرور غير صحيحة')
            return render(request, 'home.html')
    else:
        # إذا كان المستخدم مسجل الدخول بالفعل، قم بتوجيهه إلى لوحة التحكم
        if request.user.is_authenticated:
            return redirect('port:home')
        return render(request, 'home.html')

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required
def home_view(request):
    return render(request, 'users/home.html')

def subscription_expired(request):
    return render(request, 'users/subscription_expired.html')

def disclaimer(request):
    return render(request, 'disclaimer.html', {'now': timezone.now()}) 