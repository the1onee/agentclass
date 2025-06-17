from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import DriverForm, TruckForm, DeliveryOrderForm, ContainerForm, TripForm
from .models import Driver, Truck, DeliveryOrder, Container,  Trip
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.db.models import Q, Prefetch, Count
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
from django.utils import timezone
from datetime import timedelta
from django.db.utils import IntegrityError
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView
from django import forms
import logging
import pdb
import io
import csv
from django.utils.translation import gettext as _
import os
from django.conf import settings
from bidi.algorithm import get_display
import arabic_reshaper
import xlsxwriter
from django.core.cache import cache
import pprint
from django.views.decorators.http import require_GET
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Create your views here.

def calculate_stats(user):
    """Calculate dashboard statistics for a given user"""
    # إحصائيات أذونات التسليم
    delivery_orders_stats = DeliveryOrder.objects.filter(user=user).aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status__in=['UNLOADING', 'LOADING', 'GENERAL_CARGO', 'EMPTY'])),
        completed=Count('id', filter=Q(status='COMPLETED'))
    )
    
    # إحصائيات الحاويات
    containers_stats = Container.objects.filter(user=user).aggregate(
        total=Count('id'),
        assigned=Count('id', filter=Q(delivery_order__isnull=False)),
        unassigned=Count('id', filter=Q(delivery_order__isnull=True))
    )
    
    # إحصائيات الشاحنات
    trucks_stats = Truck.objects.filter(user=user).aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(is_active=True)),
        inactive=Count('id', filter=Q(is_active=False))
    )
    
    # إحصائيات الرحلات
    trips_stats = Trip.objects.filter(user=user).aggregate(
        total=Count('id'),
        active=Count('id', filter=Q(status='active')),
        completed=Count('id', filter=Q(status='completed')),
        pending=Count('id', filter=Q(status='pending'))
    )
    
    # جلب الرحلات الأخيرة
    recent_trips = Trip.objects.filter(user=user).select_related(
        'delivery_order'
    ).prefetch_related(
        'containers'
    ).order_by('-created_at')[:5]
    
    return {
        'total_orders': delivery_orders_stats['total'],
        'active_orders': delivery_orders_stats['active'],
        'completed_orders': delivery_orders_stats['completed'],
        'containers_report': containers_stats,
        'trucks_report': trucks_stats,
        'trips_report': trips_stats,
        'drivers_count': Driver.objects.filter(user=user, is_active=True).count(),
        'orders_count': delivery_orders_stats['active'],
        'containers_count': containers_stats['total'],
        'recent_trips': recent_trips,
    }

@login_required
def port_home(request):
    if not request.user.is_subscription_active:
        messages.warning(request, 'يرجى تجديد اشتراكك للوصول إلى هذه الخدمات')
        return redirect('subscription_expired')
    
    cache_key = f'dashboard_stats_{request.user.id}'
    stats = cache.get(cache_key)
    
    if not stats:
        stats = calculate_stats(request.user)
        # إضافة وقت آخر تحديث
        stats['last_update'] = timezone.now()
        cache.set(cache_key, stats, timeout=300)  # تخزين لمدة 5 دقائق
    
    # تمرير المتغيرات بشكل صحيح
    context = {
        'stats': stats,
        'total_orders': stats['total_orders'],
        'active_orders': stats['active_orders'],
        'completed_orders': stats['completed_orders'],
        'containers_report': stats['containers_report'],
        'trucks_report': stats['trucks_report'],
        'trips_report': stats['trips_report'],
        'drivers_count': stats['drivers_count'],
        'orders_count': stats['orders_count'],
        'containers_count': stats['containers_count'],
        'recent_trips': stats['recent_trips'],
    }
    
    return render(request, 'port/home.html', context)

@login_required
def add_item(request, item_type):
    if not request.user.is_subscription_active:
        messages.warning(request, 'يرجى تجديد اشتراكك للوصول إلى هذه الخدمات')
        return redirect('subscription_expired')

    forms = {
        'driver': DriverForm,
        'truck': TruckForm,
        'order': DeliveryOrderForm,
        'container': ContainerForm
    }
    
    if item_type not in forms:
        return redirect('port:home')

    form_class = forms[item_type]

    if item_type == 'truck':
        if request.method == 'POST':
            form = TruckForm(request.POST)
            if form.is_valid():
                truck = form.save(commit=False)
                truck.user = request.user
                truck.save()
                messages.success(request, 'تمت إضافة الشاحنة بنجاح')
                return redirect('port:trucks_list')
        else:
            form = TruckForm()
            
        context = {
            'form': form,
            'title': 'إضافة شاحنة',
            'item_type': 'truck'
        }
        return render(request, 'port/add_truck.html', context)

    if item_type == 'order':
        if request.method == 'POST':
            form = DeliveryOrderForm(request.POST)
            if form.is_valid():
                try:
                    # حفظ الإذن أولاً
                    order = form.save(commit=False)
                    order.user = request.user
                    order.save()

                    # إضافة الحاويات
                    bulk_containers = form.cleaned_data.get('bulk_containers', '')
                    if bulk_containers:
                        container_numbers = [num.strip() for num in bulk_containers.split('\n') if num.strip()]
                        
                        # إنشاء الحاويات
                        containers_to_create = [
                            Container(
                                user=request.user,  # استخدام request.user مباشرة
                                container_number=num,
                                container_type='20DC',
                                delivery_order=order
                            )
                            for num in container_numbers
                        ]
                        
                        # إنشاء الحاويات بشكل جماعي
                        if containers_to_create:
                            Container.objects.bulk_create(containers_to_create)
                            messages.success(
                                request, 
                                f'تم إنشاء إذن التسليم بنجاح وإضافة {len(containers_to_create)} حاوية'
                            )
                        else:
                            messages.success(request, 'تم إنشاء إذن التسليم بنجاح')
                    
                    return redirect('port:delivery_orders')
                
                except Exception as e:
                    messages.error(request, f'حدث خطأ أثناء حفظ البيانات: {str(e)}')
            else:
                messages.error(request, 'يرجى تصحيح الأخطاء أدناه')
        else:
            form = DeliveryOrderForm()
            
        context = {
            'form': form,
            'title': 'إضافة إذن تسليم',
            'item_type': 'order'
        }
        return render(request, 'port/add_item.html', context)

    if request.method == 'POST':
        # إذا كان النموذج للحاويات، نمرر المستخدم الحالي
        if item_type == 'container':
            form = form_class(request.POST, user=request.user)
        else:
            form = form_class(request.POST)
            
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, 'تمت الإضافة بنجاح')
            if item_type == 'order':
                return redirect('port:delivery_orders')
            return redirect(f'port:{item_type}s_list')
    else:
        # عند عرض النموذج لأول مرة
        if item_type == 'container':
            form = form_class(user=request.user)
        else:
            form = form_class()

    return render(request, 'port/add_item.html', {
        'form': form,
        'title': f'إضافة {item_type}',
        'item_type': item_type
    })

@login_required
def delivery_orders_list(request):
    if not request.user.is_subscription_active:
        messages.warning(request, 'يرجى تجديد اشتراكك للوصول إلى هذه الخدمات')
        return redirect('subscription_expired')
    
    # جلب الأذونات التي لم ترتبط برحلة
    orders = DeliveryOrder.objects.filter(
        user=request.user,
        trips__isnull=True  # استخدام الحقل الصحيح 'trips'
    ).order_by('-issue_date')
    
    context = {
        'orders': orders,
        'orders_count': orders.count(),
        'container_types': [
            {'value': code, 'label': label} 
            for code, label in Container.CONTAINER_TYPES
        ],
    }
    return render(request, 'port/delivery_orders_list.html', context)

@login_required
def delivery_order_detail(request, order_id):
    if not request.user.is_subscription_active:
        return JsonResponse({'error': 'Subscription required'}, status=403)
    
    order = get_object_or_404(DeliveryOrder, id=order_id, user=request.user)
    containers = order.containers.filter(user=request.user)
    
    containers_data = list(containers.values('id', 'container_number', 'weight', 'container_type'))
    for container in containers_data:
        container['container_type'] = dict(Container.CONTAINER_TYPES)[container['container_type']]
    
    return JsonResponse({
        'order_number': order.order_number,
        'containers': containers_data
    })

@login_required
def add_container_to_order(request, order_id):
    order = get_object_or_404(DeliveryOrder, id=order_id, user=request.user)
    
    if request.method == 'POST':
        form = ContainerForm(request.POST)
        if form.is_valid():
            try:
                container = form.save(commit=False)
                container.delivery_order = order
                container.user = request.user
                container.save()
                messages.success(request, 'تم إضافة الحاوية بنجاح')
                return redirect('port:edit_item', item_type='order', item_id=order.id)
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء حفظ الحاوية: {str(e)}')
        else:
            messages.error(request, 'يرجى التحقق من البيانات المدخلة')
    else:
        form = ContainerForm()
    
    return render(request, 'port/add_container.html', {
        'form': form,
        'order': order,
        'title': 'إضافة حاوية جديدة'
    })

@login_required
def delivery_orders(request):
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    # جلب الأذونات التي لم ترتبط برحلة
    orders = DeliveryOrder.objects.filter(
        user=request.user,
        
    )
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
        
    orders = orders.order_by('-issue_date')
    
    # إضافة إحصائيات حسب الحالة
    unloading_count = DeliveryOrder.objects.filter(user=request.user, status='UNLOADING').count()
    loading_count = DeliveryOrder.objects.filter(user=request.user, status='LOADING').count()
    general_count = DeliveryOrder.objects.filter(user=request.user, status='GENERAL_CARGO').count()
    empty_count = DeliveryOrder.objects.filter(user=request.user, status='EMPTY').count()
    
    context = {
        'orders': orders,
        'status_choices': DeliveryOrder.STATUS_CHOICES,
        'search_query': search_query,
        'status_filter': status_filter,
        # إضافة المتغيرات الجديدة للإحصائيات
        'unloading_count': unloading_count,
        'loading_count': loading_count,
        'general_count': general_count,
        'empty_count': empty_count,
    }
    
    return render(request, 'port/delivery_orders.html', context)

@login_required
def containers_list(request):
    if not request.user.is_subscription_active:
        messages.warning(request, 'يرجى تجديد اشتراكك للوصول إلى هذه الخدمات')
        return redirect('subscription_expired')
    
    # معالجة معاملات البحث والفلترة
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    
    # الحصول على جميع الحاويات مع الفلترة
    containers = Container.objects.filter(user=request.user)
    
    if search_query:
        containers = containers.filter(
            Q(container_number__icontains=search_query) |
            Q(delivery_order__order_number__icontains=search_query)
        )
    
    if status_filter:
        containers = containers.filter(status=status_filter)
    
    if type_filter:
        containers = containers.filter(container_type=type_filter)
    
    # التصنيف حسب تاريخ الإنشاء
    containers = containers.order_by('-created_at')
    
    # إنشاء Paginator لعرض 10 حاويات لكل صفحة
    paginator = Paginator(containers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'status_choices': Container.STATUS_CHOICES,
        'container_types': Container.CONTAINER_TYPES,
    }
    
    return render(request, 'port/containers_list.html', context)

@login_required
def drivers_list(request):
    """عرض قائمة السائقين مع تحسين الأداء"""
    # استخدام select_related لتقليل عدد الاستعلامات
    drivers_queryset = Driver.objects.filter(user=request.user).select_related('user')
    
    # تطبيق الفلترة
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        drivers_queryset = drivers_queryset.filter(is_active=True)
    elif status_filter == 'inactive':
        drivers_queryset = drivers_queryset.filter(is_active=False)
    
    # تطبيق البحث
    search_query = request.GET.get('q')
    if search_query:
        drivers_queryset = drivers_queryset.filter(
            Q(name__icontains=search_query) | 
            Q(phone_number__icontains=search_query) |
            Q(id_number__icontains=search_query)
        )
    
    # ترتيب النتائج
    drivers_queryset = drivers_queryset.order_by('-created_at')
    
    # تقسيم الصفحات
    paginator = Paginator(drivers_queryset, 10)  # 10 سائقين في كل صفحة
    page = request.GET.get('page')
    drivers = paginator.get_page(page)
    
    context = {
        'drivers': drivers,
        'active_count': Driver.objects.filter(user=request.user, is_active=True).count(),
        'inactive_count': Driver.objects.filter(user=request.user, is_active=False).count(),
        'total_count': Driver.objects.filter(user=request.user).count(),
    }
    
    return render(request, 'port/drivers_list.html', context)

@login_required
def trucks_list(request):
    if not request.user.is_subscription_active:
        messages.warning(request, 'يرجى تجديد اشتراكك للوصول إلى هذه الخدمات')
        return redirect('subscription_expired')
    
    # استخراج معلمات الفلترة من الطلب
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    # فلترة الشاحنات بناءً على الحالة
    if status_filter == 'active':
        trucks = Truck.objects.filter(is_active=True)
    elif status_filter == 'inactive':
        trucks = Truck.objects.filter(is_active=False)
    else:
        # الحالة الافتراضية: جلب جميع الشاحنات
        trucks = Truck.objects.all()
    
    # فلترة إضافية بناءً على البحث إذا كان متوفراً
    if search_query:
        trucks = trucks.filter(Q(plate_number__icontains=search_query) | 
                               Q(governorate__icontains=search_query))
    
    # ترتيب النتائج
    trucks = trucks.order_by('-created_at')
    
    # حساب إحصائيات الشاحنات
    active_trucks = Truck.objects.filter(is_active=True).count()
    inactive_trucks = Truck.objects.filter(is_active=False).count()
    
    context = {
        'trucks': trucks,
        'active_trucks': active_trucks,
        'inactive_trucks': inactive_trucks,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'port/trucks_list.html', context)

@login_required
@csrf_exempt
def delete_item(request, item_type, item_id):
    if not request.user.is_subscription_active:
        messages.error(request, 'الاشتراك مطلوب لاستخدام هذه الميزة')
        return redirect('subscription_expired')
    
    if request.method != 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        else:
            messages.error(request, 'طريقة الطلب غير مسموح بها')
            return redirect('port:home')
    
    models_map = {
        'driver': Driver,
        'truck': Truck,
        'container': Container,
        'order': DeliveryOrder
    }
    
    redirect_map = {
        'driver': 'port:drivers_list',
        'truck': 'port:trucks_list',
        'container': 'port:containers_list',
        'order': 'port:delivery_orders'
    }
    
    if item_type not in models_map:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Invalid item type'}, status=400)
        else:
            messages.error(request, 'نوع العنصر غير صالح')
            return redirect('port:home')
    
    model = models_map[item_type]
    item = get_object_or_404(model, id=item_id, user=request.user)
    
    try:
        item.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        else:
            messages.success(request, f'تم حذف العنصر بنجاح')
            return redirect(redirect_map[item_type])
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=400)
        else:
            messages.error(request, f'حدث خطأ أثناء الحذف: {str(e)}')
            return redirect(redirect_map[item_type])

@login_required
def edit_item(request, item_type, item_id):
    if not request.user.is_subscription_active:
        messages.warning(request, 'يرجى تجديد اشتراكك للوصول إلى هذه الخدمات')
        return redirect('subscription_expired')

    forms = {
        'driver': DriverForm,
        'truck': TruckForm,
        'order': DeliveryOrderForm,
        'container': ContainerForm
    }
    
    if item_type not in forms:
        return redirect('port:home')

    form_class = forms[item_type]
    models_map = {
        'driver': Driver,
        'truck': Truck,
        'container': Container,
        'order': DeliveryOrder
    }
    
    model = models_map[item_type]
    item = get_object_or_404(model, id=item_id, user=request.user)

    if request.method == 'POST':
        if item_type == 'container':
            form = form_class(request.POST, instance=item, user=request.user)
        else:
            form = form_class(request.POST, instance=item)
            
        if form.is_valid():
            form.save()
            messages.success(request, 'تم التعديل بنجاح')
            urls_map = {
                'driver': 'drivers_list',
                'truck': 'trucks_list',
                'container': 'containers_list',
                'order': 'delivery_orders'
            }
            return redirect(f'port:{urls_map[item_type]}')
    else:
        if item_type == 'container':
            form = form_class(instance=item, user=request.user)
        else:
            form = form_class(instance=item)

    context = {
        'form': form,
        'title': f'تعديل {item}',
        'item_type': item_type,
        'item': item,
        'order_id': item_id if item_type == 'order' else None
    }
    return render(request, 'port/edit_item.html', context)

@login_required
def data_entry(request):
    if not request.user.is_subscription_active:
        messages.warning(request, 'يرجى تجديد اشتراكك للوصول إلى هذه الخدمات')
        return redirect('subscription_expired')
    
    return render(request, 'port/data_entry.html')

@login_required
@csrf_exempt
def update_containers(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    data = json.loads(request.body)
    containers = data.get('containers', [])
    
    try:
        with transaction.atomic():
            for container_data in containers:
                container = Container.objects.get(id=container_data['id'], user=request.user)
                container.container_number = container_data['container_number']
                container.container_type = container_data['container_type']
                container.weight = container_data['weight']
                container.delivery_order_id = container_data['delivery_order']
                container.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def search_container(request):
    container_number = request.GET.get('container_number')
    delivery_order_id = request.GET.get('delivery_order_id')
    
    try:
        container = Container.objects.get(
            container_number=container_number,
            delivery_order_id=delivery_order_id,
            user=request.user
        )
        
        return JsonResponse({
            'found': True,
            'id': container.id,
            'container_type': container.get_container_type_display(),
            'weight': str(container.weight)
        })
    except Container.DoesNotExist:
        return JsonResponse({
            'found': False
        })

@login_required
def containers_api(request):
    # جلب الحاويات المتاحة للمستخدم
    containers = Container.objects.filter(
        user=request.user,
        delivery_order__status='PENDING'
    ).values('id', 'container_number')
    
    return JsonResponse([{
        'id': container['id'],
        'display_name': container['container_number']
    } for container in containers], safe=False)

@login_required
def get_permit_containers(request, permit_id):
    try:
        # التحقق من وجود الإذن
        delivery_order = get_object_or_404(DeliveryOrder, id=permit_id, user=request.user)
        
        # جلب الحاويات المرتبطة بالإذن
        containers = delivery_order.containers.all()
        
        # تحضير البيانات للاستجابة
        data = {
            'success': True,
            'delivery_order': {
                'id': delivery_order.id,
                'number': delivery_order.order_number,
                'date': delivery_order.created_at.strftime('%Y-%m-%d %H:%M')
            },
            'containers': [
                {
                    'id': container.id,
                    'number': container.container_number,
                    'type': container.container_type,
                    'weight': container.weight
                }
                for container in containers
            ]
        }
        return JsonResponse(data)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'details': 'حدث خطأ أثناء جلب بيانات الإذن والحاويات'
        }, status=500)

class TripCreateView(CreateView):
    model = Trip
    form_class = TripForm
    template_name = 'port/trip_form.html'
    success_url = '/port/trips/'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'إضافة رحلة جديدة'
        context['drivers'] = Driver.objects.filter(user=self.request.user, is_active=True)
        context['trucks'] = Truck.objects.filter(user=self.request.user, is_active=True)
        
        # جلب الأذونات غير المرتبطة برحلة
        context['delivery_orders'] = DeliveryOrder.objects.filter(
            user=self.request.user,
            trips__isnull=True  # استخدام الحقل الصحيح 'trips'
        ).order_by('-issue_date')
        
        return context
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                # طباعة البيانات المستلمة للتصحيح
                print("البيانات المستلمة:", self.request.POST)
                
                # تعيين المستخدم للرحلة
                form.instance.user = self.request.user
                
                # الحصول على معرف إذن التسليم
                delivery_order_id = self.request.POST.get('delivery_order_id') or self.request.POST.get('delivery_order')
                if not delivery_order_id:
                    raise ValueError('لم يتم تحديد إذن التسليم')
                
                # الحصول على إذن التسليم
                delivery_order = get_object_or_404(DeliveryOrder, id=delivery_order_id, user=self.request.user)
                
                # حفظ الرحلة
                trip = form.save(commit=False)
                trip.delivery_order = delivery_order  # تعيين إذن التسليم للرحلة
                trip.save()
                form.save_m2m()
                
                # معالجة بيانات الحاويات
                containers_data = []
                if 'containers' in self.request.POST:
                    try:
                        containers_data = json.loads(self.request.POST['containers'])
                    except json.JSONDecodeError:
                        print("خطأ في تحليل بيانات الحاويات:", self.request.POST['containers'])
                        raise ValueError('تنسيق بيانات الحاويات غير صالح')
                
                # طباعة بيانات الحاويات للتصحيح
                print("بيانات الحاويات:", containers_data)
                
                # التحقق من وجود حاويات
                if not containers_data:
                    raise ValueError('لا توجد حاويات لإضافتها إلى الرحلة')
                
                # معالجة كل حاوية
                container_ids = []
                for container_data in containers_data:
                    container_id = container_data.get('id')
                    if not container_id:
                        continue
                    
                    # الحصول على الحاوية
                    try:
                        container = Container.objects.get(id=container_id, user=self.request.user)
                    except Container.DoesNotExist:
                        print(f"الحاوية غير موجودة: {container_id}")
                        continue
                    
                    # تعيين السائق والشاحنة تلقائياً إذا كانت القيمة "auto"
                    if container_data.get('driver') == "auto":
                        # تعيين أول سائق متاح
                        driver = Driver.objects.filter(user=self.request.user, is_active=True).first()
                        if driver:
                            container.driver = driver
                    else:
                        driver_id = container_data.get('driver')
                        if driver_id and driver_id != "null":
                            try:
                                container.driver = Driver.objects.get(id=driver_id, user=self.request.user)
                            except Driver.DoesNotExist:
                                print(f"السائق غير موجود: {driver_id}")
                    
                    if container_data.get('truck') == "auto":
                        # تعيين أول شاحنة متاحة
                        truck = Truck.objects.filter(user=self.request.user, is_active=True).first()
                        if truck:
                            container.truck = truck
                    else:
                        truck_id = container_data.get('truck')
                        if truck_id and truck_id != "null":
                            try:
                                container.truck = Truck.objects.get(id=truck_id, user=self.request.user)
                            except Truck.DoesNotExist:
                                print(f"الشاحنة غير موجودة: {truck_id}")
                    
                    # حفظ الحاوية
                    container.save()
                    container_ids.append(container.id)
                
                # ربط الحاويات بالرحلة
                if container_ids:
                    trip.containers.set(container_ids)
                else:
                    raise ValueError('لم يتم العثور على أي حاويات صالحة')
                
             
                
                self.object = trip
                
                # إعادة استجابة JSON للطلبات AJAX
                if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'تم إنشاء الرحلة بنجاح',
                        'redirect': self.get_success_url()
                    })
                
                # إعادة استجابة عادية للطلبات غير AJAX
                messages.success(self.request, f'تم إنشاء الرحلة {self.object} بنجاح')
                return HttpResponseRedirect(self.get_success_url())
                
        except Exception as e:
            print(f"خطأ في إنشاء الرحلة: {str(e)}")
            
            # إعادة استجابة JSON للطلبات AJAX
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': f'حدث خطأ أثناء حفظ الرحلة',
                    'details': str(e)
                }, status=400)
            
            # إعادة استجابة عادية للطلبات غير AJAX
            messages.error(self.request, f'حدث خطأ أثناء حفظ الرحلة: {e}')
            return self.form_invalid(form)

@login_required
def edit_trip(request, trip_id):
    if not request.user.is_subscription_active:
        messages.warning(request, 'يرجى تجديد اشتراكك للوصول إلى هذه الخدمات')
        return redirect('subscription_expired')
    
    # جلب الرحلة مع البيانات المرتبطة
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    
    # جلب السائقين والشاحنات المتاحة
    drivers = Driver.objects.filter(user=request.user, is_active=True)
    trucks = Truck.objects.filter(user=request.user, is_active=True)
    
    # جلب الحاويات المرتبطة بالرحلة
    containers = trip.containers.all().prefetch_related('driver', 'truck')
    
    # جلب أذونات التسليم المرتبطة بالرحلة من خلال الحاويات
    delivery_order_ids = containers.values_list('delivery_order_id', flat=True).distinct()
    delivery_orders = DeliveryOrder.objects.filter(id__in=delivery_order_ids)
    
    # طباعة معلومات للتصحيح
    print(f"Trip ID: {trip.id}")
    print(f"Trip Status: {trip.status}")
    print(f"Trip Start Time: {trip.start_time}")
    print(f"Trip End Time: {trip.end_time}")
    print(f"Containers Count: {containers.count()}")
    
    # طباعة معلومات عن أذونات التسليم
    print(f"Delivery Orders: {delivery_orders}")
    if delivery_orders:
        for order in delivery_orders:
            print(f"Order ID: {order.id}, Order Number: {order.order_number}")
    
    # طباعة معلومات عن الحاويات وأذونات التسليم المرتبطة بها
    for container in containers:
        print(f"Container ID: {container.id}, Container Number: {container.container_number}")
        if hasattr(container, 'delivery_order') and container.delivery_order:
            print(f"  - Linked to Order: {container.delivery_order.id}, {container.delivery_order.order_number}")
    
    if request.method == 'POST':
        form = TripForm(request.POST, instance=trip, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # حفظ الرحلة
                    trip = form.save(commit=False)
                    trip.user = request.user
                    trip.save()
                    form.save_m2m()  # حفظ العلاقات

                    # حفظ الحاويات المرتبطة
                    if 'containers' in request.POST:
                        containers_data = json.loads(request.POST['containers'])
                        
                        for container_data in containers_data:
                            try:
                                container = Container.objects.get(
                                    id=container_data['id'],
                                    user=request.user
                                )
                                
                                # تحديث السائق والشاحنة
                                container.driver_id = container_data.get('driver') or None
                                container.truck_id = container_data.get('truck') or None
                                container.save()
                            
                            except Container.DoesNotExist:
                                continue

                    messages.success(request, 'تم تعديل الرحلة بنجاح')
                    return redirect('port:trip_list')

            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء حفظ البيانات: {str(e)}')
    else:
        form = TripForm(instance=trip, user=request.user)
    
    context = {
        'form': form,
        'trip': trip,
        'drivers': drivers,
        'trucks': trucks,
        'containers': containers,
        'delivery_orders': delivery_orders,
        'title': 'تعديل الرحلة'
    }
    
    return render(request, 'port/edit_trip.html', context)

@login_required
def trip_list(request):
    # تحديث حالة الرحلات القديمة
    update_trips_status()
    
    # الحصول على جميع الرحلات أولاً
    trips = Trip.objects.filter(user=request.user).select_related(
        'user', 'delivery_order'
    ).prefetch_related('containers').order_by('-start_time')
    
    # الحصول على جميع أذونات التسليم لقائمة الفلترة
    delivery_orders = DeliveryOrder.objects.filter(user=request.user)
    
    # فلترة حسب البحث
    query = request.GET.get('q')
    if query:
        trips = trips.filter(
            Q(id__icontains=query) |
            Q(delivery_order__order_number__icontains=query) |
            Q(containers__container_number__icontains=query)
        ).distinct()
    
    # فلترة حسب الحالة
    status = request.GET.get('status')
    if status:
        trips = trips.filter(status=status)
    
    # فلترة حسب إذن التسليم
    delivery_order_id = request.GET.get('delivery_order')
    if delivery_order_id:
        trips = trips.filter(delivery_order_id=delivery_order_id)
    
    # فلترة حسب نوع الإذن (استخدام حقل status في DeliveryOrder بدلاً من order_type)
    order_type = request.GET.get('order_type')
    if order_type:
        # تحويل قيم order_type من الواجهة إلى قيم status في النموذج
        order_type_mapping = {
            'unloading': 'UNLOADING',
            'loading': 'LOADING',
            'partial': 'EMPTY',  # تعديل هذا حسب القيم الفعلية في نموذجك
            'general': 'GENERAL_CARGO'
        }
        mapped_status = order_type_mapping.get(order_type)
        if mapped_status:
            trips = trips.filter(delivery_order__status=mapped_status)
    
    # فلترة حسب التاريخ
    date_from = request.GET.get('date_from')
    if date_from:
        trips = trips.filter(start_time__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        trips = trips.filter(start_time__lte=date_to)
    
    # إحصائيات الرحلات
    total_count = Trip.objects.filter(user=request.user).count()
    completed_count = Trip.objects.filter(user=request.user, status='completed').count()
    active_count = Trip.objects.filter(user=request.user, status='active').count()
    pending_count = Trip.objects.filter(user=request.user, status='pending').count()
    
    # التحقق مما إذا كان الطلب يريد جميع البيانات (للتصدير أو الطباعة)
    all_data = request.GET.get('all') == 'true'
    
    if all_data:
        # إذا كان الطلب يريد جميع البيانات، لا نقوم بالتقسيم إلى صفحات
        page_obj = trips
    else:
        # التقسيم إلى صفحات للعرض العادي
        paginator = Paginator(trips, 10)  # 10 رحلات في كل صفحة
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
    
    context = {
        'trips': page_obj,
        'total_count': total_count,
        'completed_count': completed_count,
        'active_count': active_count,
        'pending_count': pending_count,
        'delivery_orders': delivery_orders,  # إضافة أذونات التسليم للقائمة المنسدلة
    }
    
    return render(request, 'port/trip_list.html', context)

@login_required
def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    
    # التحقق من الحالة وتحديثها إذا لزم الأمر
    trip.check_auto_complete()
    
    context = {
        'trip': trip,
    }
    return render(request, 'port/trip_detail.html', context)

@login_required
def update_trip(request, trip_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            trip = Trip.objects.get(id=trip_id, user=request.user)
            
            # تحديث بيانات الرحلة
            trip.status = data['status']
            if 'start_time' in data and data['start_time']:
                trip.start_time = data['start_time']
            if 'end_time' in data and data['end_time']:
                trip.end_time = data['end_time']
            trip.save()
            
            # تحديث الحاويات
            for container_data in data['containers']:
                container = Container.objects.get(id=container_data['id'], user=request.user)
                if 'driver' in container_data and container_data['driver']:
                    container.driver_id = container_data['driver']
                if 'truck' in container_data and container_data['truck']:
                    container.truck_id = container_data['truck']
                container.save()
            
            # إضافة رسالة نجاح
            return JsonResponse({'success': True, 'message': 'تم تحديث الرحلة بنجاح'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def trip_edit(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    
    # جلب السائقين والشاحنات المتاحة
    drivers = Driver.objects.filter(user=request.user, is_active=True)
    trucks = Truck.objects.filter(user=request.user, is_active=True)
    
    if request.method == 'POST':
        form = TripForm(request.POST, instance=trip, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تعديل الرحلة بنجاح')
            return redirect('port:trip_list')
    else:
        form = TripForm(instance=trip, user=request.user)
    
    return render(request, 'port/trip_form.html', {
        'form': form,
        'trip': trip,
        'drivers': drivers,
        'trucks': trucks,
        'title': 'تعديل الرحلة'
    })

@login_required
@csrf_exempt
def update_container_driver(request, container_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            container = Container.objects.get(id=container_id, user=request.user)
            container.driver_id = data.get('driver_id') or None
            container.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def update_container_truck(request, container_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            container = Container.objects.get(id=container_id, user=request.user)
            container.truck_id = data.get('truck_id') or None
            container.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def add_truck(request):
    if request.method == 'POST':
        form = TruckForm(request.POST)
        if form.is_valid():
            plate_number = form.cleaned_data['plate_number']
            if Truck.objects.filter(plate_number=plate_number).exists():
                messages.error(request, 'رقم اللوحة موجود مسبقًا. الرجاء إدخال رقم لوحة آخر.')
            else:
                truck = form.save(commit=False)
                truck.user = request.user
                truck.save()
                messages.success(request, 'تمت إضافة الشاحنة بنجاح.')
                return redirect('port:trucks_list')
    else:
        form = TruckForm()
    
    return render(request, 'port/add_truck.html', {'form': form})

@login_required
def edit_truck(request, plate_number):
    truck = get_object_or_404(Truck, plate_number=plate_number, user=request.user)
    
    if request.method == 'POST':
        form = TruckForm(request.POST, instance=truck)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'تم تحديث بيانات الشاحنة بنجاح.')
                return redirect('port:trucks_list')
            except forms.ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'حدث خطأ غير متوقع: {str(e)}')
    else:
        form = TruckForm(instance=truck)
    
    context = {
        'form': form,
        'truck': truck,
        'title': 'تعديل الشاحنة'
    }
    return render(request, 'port/edit_truck.html', context)

@login_required
def delete_truck(request, truck_id):
    truck = get_object_or_404(Truck, id=truck_id)
    
    if request.method == 'POST':
        truck.delete()
        messages.success(request, 'تم حذف الشاحنة بنجاح')
        return redirect('port:trucks_list')
    
    return render(request, 'port/delete_truck.html', {
        'truck': truck,
        'title': 'حذف الشاحنة'
    })

def home(request):
    # Your home view logic here
    return render(request, 'port/home.html')

@login_required
def edit_container(request, container_id):
    container = get_object_or_404(Container, id=container_id, user=request.user)
    
    if request.method == 'POST':
        form = ContainerForm(request.POST, instance=container)
        if form.is_valid():
            try:
                container = form.save(commit=False)
                container.user = request.user
                container.save()
                messages.success(request, 'تم تعديل الحاوية بنجاح')
                
                # التحقق من وجود delivery_order قبل محاولة الوصول إلى id
                if container.delivery_order:
                    return redirect('port:edit_item', item_type='order', item_id=container.delivery_order.id)
                else:
                    # إذا لم يكن هناك delivery_order، إعادة التوجيه إلى قائمة الحاويات
                    messages.info(request, 'تم تعديل الحاوية بنجاح. لاحظ أن الحاوية غير مرتبطة بأي إذن تسليم.')
                    return redirect('port:containers_list')
                    
            except Exception as e:
                messages.error(request, f'حدث خطأ أثناء تعديل الحاوية: {str(e)}')
    else:
        form = ContainerForm(instance=container)
    
    return render(request, 'port/edit_container.html', {
        'form': form,
        'container': container,
        'request': request
    })

@login_required
def delete_delivery_order(request, order_id):
    order = get_object_or_404(DeliveryOrder, id=order_id, user=request.user)
    
    if request.method == 'POST':
        order.delete()
        messages.success(request, 'تم حذف إذن التسليم بنجاح')
        return redirect('port:delivery_orders')
    
    return render(request, 'port/delete_delivery_order.html', {
        'order': order,
        'title': 'حذف إذن التسليم'
    })

@login_required
@require_POST
def delete_multiple_orders(request):
    try:
        # Check if the request contains form data or JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            order_ids = data.get('order_ids', [])
        else:
            # Handle form data
            order_ids_str = request.POST.get('order_ids', '[]')
            order_ids = json.loads(order_ids_str)
        
        # حذف الأذونات المحددة
        deleted_count = DeliveryOrder.objects.filter(
            id__in=order_ids,
            user=request.user
        ).delete()[0]
        
        if request.content_type == 'application/json':
            return JsonResponse({'success': True, 'deleted_count': deleted_count})
        else:
            messages.success(request, f'تم حذف {deleted_count} أمر بنجاح')
            return redirect('port:delivery_orders')
    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        else:
            messages.error(request, f'حدث خطأ أثناء الحذف: {str(e)}')
            return redirect('port:delivery_orders')

@login_required
def delete_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    if request.method == 'POST':
        trip.delete()
        messages.success(request, 'تم حذف الرحلة بنجاح')
        return redirect('port:trip_list')  # تأكد من استخدام اسم المسار الصحيح مع namespace
    return render(request, 'port/confirm_delete.html', {'trip': trip})

@login_required
def add_driver(request):
    if request.method == 'POST':
        form = DriverForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'تمت إضافة السائق بنجاح!')
                return redirect('port:drivers_list')
            except IntegrityError:
                messages.error(request, 'رقم الرخصة موجود مسبقاً.')
        else:
            messages.error(request, 'يرجى تصحيح الأخطاء أدناه.')
    else:
        form = DriverForm(user=request.user)
    
    return render(request, 'port/add_driver.html', {'form': form})

@login_required
@require_POST
def remove_container_from_trip(request, trip_id, container_id):
    try:
        # إزالة نقطة التوقف بعد التصحيح
        # import pdb; pdb.set_trace()
        logger.info(f"Attempting to remove container {container_id} from trip {trip_id}")
        
        # التحقق من وجود الرحلة والحاوية
        trip = get_object_or_404(Trip, id=trip_id, user=request.user)
        container = get_object_or_404(Container, id=container_id, user=request.user)
        
        # طباعة معلومات للتصحيح
        logger.info(f"Trip: {trip.id}, Container: {container.id}")
        logger.info(f"Container in trip: {trip.containers.filter(id=container_id).exists()}")
        
        # التحقق من أن الحاوية مرتبطة بالرحلة
        if not trip.containers.filter(id=container_id).exists():
            logger.warning(f"Container {container_id} is not associated with trip {trip_id}")
            return JsonResponse({
                'success': False,
                'error': 'الحاوية غير مرتبطة بهذه الرحلة'
            }, status=400)
        
        # إزالة الحاوية من الرحلة
        trip.containers.remove(container)
        logger.info(f"Successfully removed container {container_id} from trip {trip_id}")
        
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Error removing container {container_id} from trip {trip_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def export_trips_csv(request):
    # الحصول على الرحلات المفلترة (نفس منطق الفلترة في trip_list)
    trips_queryset = Trip.objects.filter(user=request.user).order_by('-created_at')
    
    # تطبيق الفلترة إذا كانت موجودة
    search_query = request.GET.get('search', '')
    order_type = request.GET.get('order_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if search_query:
        trips_queryset = trips_queryset.filter(
            Q(delivery_order__order_number__icontains=search_query) |
            Q(containers__container_number__icontains=search_query)
        ).distinct()
    
    if order_type:
        order_type_mapping = {
            'unloading': 'UNLOADING',
            'loading': 'LOADING',
            'retail': 'EMPTY',  # تعديل هذا حسب القيم الفعلية في نموذجك
            'general': 'GENERAL_CARGO'
        }
        mapped_status = order_type_mapping.get(order_type)
        if mapped_status:
            trips_queryset = trips_queryset.filter(delivery_order__status=mapped_status)
    
    if date_from:
        trips_queryset = trips_queryset.filter(start_time__gte=date_from)
    
    if date_to:
        trips_queryset = trips_queryset.filter(start_time__lte=date_to + ' 23:59:59')
    
    # إنشاء استجابة HTTP لملف CSV
    response = HttpResponse(content_type='text/csv')
    filename = f"تقرير_الرحلات_{timezone.now().strftime('%Y-%m-%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # إنشاء كاتب CSV
    writer = csv.writer(response)
    
    # كتابة العناوين
    writer.writerow([
        'رقم إذن التسليم',
        'نوع الإذن',
        'عدد الحاويات',
        'تاريخ البداية',
        'تاريخ النهاية',
        'الحالة'
    ])
    
    # كتابة البيانات
    for trip in trips_queryset:
        writer.writerow([
            trip.delivery_order.order_number,
            trip.delivery_order.get_status_display(),
            str(trip.containers.count()),
            trip.start_time.strftime('%Y-%m-%d %H:%M'),
            trip.end_time.strftime('%Y-%m-%d %H:%M') if trip.end_time else '',
            trip.get_status_display()
        ])
    
    return response

@login_required
def export_trip_pdf(request, trip_id):
    # الحصول على الرحلة
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    
    # إرسال رسالة تنبيه بأن الميزة غير متاحة حالياً
    messages.warning(request, "ميزة تصدير PDF غير متاحة حالياً. يرجى استخدام تصدير Excel بدلاً من ذلك.")
    
    # إعادة توجيه المستخدم إلى صفحة تفاصيل الرحلة
    return redirect('port:trip_detail', trip_id=trip_id)

@login_required
def export_trip_excel(request, trip_id):
    # الحصول على الرحلة
    trip = get_object_or_404(Trip, id=trip_id, user=request.user)
    
    # إنشاء استجابة HTTP لملف Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"تفاصيل_الرحلة_{trip.delivery_order.order_number}_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # إنشاء ملف Excel
    workbook = xlsxwriter.Workbook(response)
    worksheet = workbook.add_worksheet('تفاصيل الرحلة')
    
    # تنسيقات الخلايا
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#4472C4',
        'font_color': 'white',
        'border': 1
    })
    
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'align': 'right',
        'valign': 'vcenter',
        'font_color': '#4472C4'
    })
    
    cell_format = workbook.add_format({
        'align': 'right',
        'valign': 'vcenter',
        'border': 1
    })
    
    # تعيين اتجاه الورقة من اليمين إلى اليسار
    worksheet.right_to_left()
    
    # إضافة العنوان
    worksheet.merge_range('A1:H1', f"تفاصيل الرحلة - {trip.delivery_order.order_number}", title_format)
    worksheet.merge_range('A2:H2', f"تاريخ التقرير: {timezone.now().strftime('%Y-%m-%d')}", cell_format)
    
    # معلومات الرحلة
    row = 4
    worksheet.merge_range(f'A{row}:H{row}', "معلومات الرحلة:", title_format)
    row += 1
    
    trip_info = [
        ["رقم إذن التسليم:", trip.delivery_order.order_number],
        ["تاريخ البداية:", trip.start_time.strftime('%Y-%m-%d %H:%M')],
        ["تاريخ النهاية:", trip.end_time.strftime('%Y-%m-%d %H:%M') if trip.end_time else ""],
        ["الحالة:", trip.get_status_display()]
    ]
    
    for info in trip_info:
        worksheet.write(row, 0, info[0], cell_format)
        worksheet.write(row, 1, info[1], cell_format)
        row += 1
    
    # معلومات إذن التسليم
    row += 1
    worksheet.merge_range(f'A{row}:H{row}', "معلومات إذن التسليم:", title_format)
    row += 1
    
    order_info = [
        ["تاريخ الإصدار:", trip.delivery_order.issue_date.strftime('%Y-%m-%d')],
        ["الملاحظات:", trip.delivery_order.notes if trip.delivery_order.notes else "لا توجد ملاحظات"]
    ]
    
    for info in order_info:
        worksheet.write(row, 0, info[0], cell_format)
        worksheet.write(row, 1, info[1], cell_format)
        row += 1
    
    # الحاويات المرتبطة
    row += 1
    worksheet.merge_range(f'A{row}:H{row}', "الحاويات المرتبطة:", title_format)
    row += 1
    
    # عناوين جدول الحاويات
    headers = ['رقم الحاوية', 'النوع', 'الوزن', 'السائق', 'الشاحنة', 'الحالة']
    for col, header in enumerate(headers):
        worksheet.write(row, col, header, header_format)
    
    # بيانات الحاويات
    row += 1
    for container in trip.containers.all():
        worksheet.write(row, 0, container.container_number, cell_format)
        worksheet.write(row, 1, container.get_container_type_display(), cell_format)
        worksheet.write(row, 2, f"{container.weight} طن" if container.weight else "", cell_format)
        worksheet.write(row, 3, container.driver.name if container.driver else "غير محدد", cell_format)
        worksheet.write(row, 4, container.truck.plate_number if container.truck else "غير محدد", cell_format)
        worksheet.write(row, 5, container.get_status_display(), cell_format)
        row += 1
    
    # ضبط عرض الأعمدة
    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:B', 15)
    worksheet.set_column('C:C', 10)
    worksheet.set_column('D:D', 20)
    worksheet.set_column('E:E', 15)
    worksheet.set_column('F:F', 15)
    
    # إغلاق ملف Excel
    workbook.close()
    
    return response

@login_required
def export_trips_pdf(request):
    # الحصول على الرحلات المفلترة (نفس منطق الفلترة في trip_list)
    trips = Trip.objects.filter(user=request.user)
    
    # تطبيق الفلترة
    status = request.GET.get('status')
    if status:
        trips = trips.filter(status=status)
    
    date_from = request.GET.get('date_from')
    if date_from:
        trips = trips.filter(created_at__date__gte=date_from)
    
    date_to = request.GET.get('date_to')
    if date_to:
        trips = trips.filter(created_at__date__lte=date_to)
    
    # إرسال رسالة تنبيه بأن الميزة غير متاحة حالياً
    messages.warning(request, "ميزة تصدير PDF غير متاحة حالياً. يرجى استخدام تصدير Excel بدلاً من ذلك.")
    
    # إعادة توجيه المستخدم إلى صفحة قائمة الرحلات
    return redirect('port:trip_list')

@require_GET
@login_required
def dashboard_stats_api(request):
    """API لجلب إحصائيات لوحة التحكم بشكل غير متزامن"""
    cache_key = f'dashboard_stats_api_{request.user.id}'
    stats = cache.get(cache_key)
    
    if not stats:
        # استخدام نفس دالة حساب الإحصائيات
        raw_stats = calculate_stats(request.user)
        
        # تحويل البيانات إلى تنسيق مناسب للـ API
        stats = {
            'orders': {
                'total': raw_stats['total_orders'],
                'active': raw_stats['active_orders'],
                'completed': raw_stats['completed_orders']
            },
            'containers': {
                'total': raw_stats['containers_report']['total'],
                'assigned': raw_stats['containers_report']['assigned'],
                'unassigned': raw_stats['containers_report']['unassigned']
            },
            'trucks': {
                'total': raw_stats['trucks_report']['total'],
                'active': raw_stats['trucks_report']['active'],
                'inactive': raw_stats['trucks_report']['inactive']
            },
            'trips': {
                'total': raw_stats['trips_report']['total'],
                'active': raw_stats['trips_report']['active'],
                'completed': raw_stats['trips_report']['completed'],
                'pending': raw_stats['trips_report']['pending']
            },
            'drivers_count': raw_stats['drivers_count'],
            'last_update': timezone.now().isoformat()
        }
        
        # تخزين البيانات في الذاكرة المؤقتة لمدة دقيقة واحدة
        cache.set(cache_key, stats, timeout=60)
    
    return JsonResponse(stats)

@login_required
def edit_driver(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id, user=request.user)
    
    if request.method == 'POST':
        form = DriverForm(request.POST, instance=driver)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث بيانات السائق بنجاح')
            return redirect('port:drivers_list')
    else:
        form = DriverForm(instance=driver)
    
    context = {
        'form': form,
        'driver': driver,
    }
    
    return render(request, 'port/edit_driver.html', context)

@login_required
def delete_driver(request, driver_id):
    driver = get_object_or_404(Driver, id=driver_id, user=request.user)
    try:
        driver.delete()
        messages.success(request, 'تم حذف السائق بنجاح')
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء محاولة حذف السائق: {str(e)}')
    return redirect('port:drivers_list')

def update_trips_status():
    """تحديث حالة الرحلات التي مر عليها أكثر من ثلاثة أيام إلى مكتملة"""
    # حساب التاريخ قبل ثلاثة أيام
    three_days_ago = timezone.now() - timedelta(days=3)
    
    # تحديث الرحلات النشطة التي تم إنشاؤها قبل ثلاثة أيام
    updated_count = Trip.objects.filter(
        status='active',
        created_at__lte=three_days_ago
    ).update(
        status='completed',
        end_time=timezone.now()  # تعيين وقت الانتهاء إلى الوقت الحالي
    )
    
    return updated_count

@login_required
@require_POST
def bulk_status_change(request):
    try:
        orders_ids = request.POST.get('orders', '').split(',')
        new_status = request.POST.get('status')
        
        if not orders_ids or not new_status:
            messages.error(request, 'بيانات غير كافية لتغيير الحالة')
            return redirect('port:delivery_orders')
        
        # تحديث حالة الأذونات المحددة
        updated_count = DeliveryOrder.objects.filter(
            id__in=orders_ids,
            user=request.user
        ).update(status=new_status)
        
        # تحديث حالة الحاويات المرتبطة بهذه الأذونات
        for order_id in orders_ids:
            try:
                order = DeliveryOrder.objects.get(id=order_id, user=request.user)
                # تحديث حالة الحاويات المرتبطة
                order.containers.all().update(status=new_status)
            except DeliveryOrder.DoesNotExist:
                continue
        
        messages.success(request, f'تم تحديث حالة {updated_count} أمر بنجاح')
        return redirect('port:delivery_orders')
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء تحديث الحالة: {str(e)}')
        return redirect('port:delivery_orders')

@login_required
@require_POST
def container_bulk_status_change(request):
    try:
        containers_ids = request.POST.get('containers', '').split(',')
        new_status = request.POST.get('status')
        
        if not containers_ids or not new_status:
            messages.error(request, 'بيانات غير كافية لتغيير الحالة')
            return redirect('port:containers_list')
        
        # تحديث حالة الحاويات المحددة
        updated_count = Container.objects.filter(
            id__in=containers_ids,
            user=request.user
        ).update(status=new_status)
        
        messages.success(request, f'تم تحديث حالة {updated_count} حاوية بنجاح')
        return redirect('port:containers_list')
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء تحديث الحالة: {str(e)}')
        return redirect('port:containers_list')

@login_required
@require_POST
def container_bulk_assign(request):
    try:
        containers_ids = request.POST.get('containers', '').split(',')
        delivery_order_id = request.POST.get('delivery_order')
        
        if not containers_ids or not delivery_order_id:
            messages.error(request, 'بيانات غير كافية لربط الحاويات')
            return redirect('port:containers_list')
        
        # التحقق من وجود إذن التسليم
        try:
            delivery_order = DeliveryOrder.objects.get(id=delivery_order_id, user=request.user)
        except DeliveryOrder.DoesNotExist:
            messages.error(request, 'إذن التسليم غير موجود')
            return redirect('port:containers_list')
        
        # ربط الحاويات بإذن التسليم
        updated_count = Container.objects.filter(
            id__in=containers_ids,
            user=request.user
        ).update(
            delivery_order=delivery_order,
            status=delivery_order.status  # تحديث حالة الحاويات لتتوافق مع حالة إذن التسليم
        )
        
        messages.success(request, f'تم ربط {updated_count} حاوية بإذن التسليم بنجاح')
        return redirect('port:containers_list')
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء ربط الحاويات: {str(e)}')
        return redirect('port:containers_list')

@login_required
@require_POST
def container_bulk_delete(request):
    try:
        containers_ids = request.POST.get('containers', '').split(',')
        
        if not containers_ids:
            messages.error(request, 'لم يتم تحديد أي حاويات للحذف')
            return redirect('port:containers_list')
        
        # حذف الحاويات المحددة
        deleted_count, _ = Container.objects.filter(
            id__in=containers_ids,
            user=request.user
        ).delete()
        
        messages.success(request, f'تم حذف {deleted_count} حاوية بنجاح')
        return redirect('port:containers_list')
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء حذف الحاويات: {str(e)}')
        return redirect('port:containers_list')

@login_required
@require_POST
def truck_bulk_status_change(request):
    try:
        trucks_ids = request.POST.get('trucks', '').split(',')
        new_status = request.POST.get('status')
        
        if not trucks_ids or not new_status:
            messages.error(request, 'بيانات غير كافية لتغيير الحالة')
            return redirect('port:trucks_list')
        
        # تحديث حالة الشاحنات المحددة
        is_active = new_status == 'active'
        updated_count = Truck.objects.filter(
            id__in=trucks_ids,
            user=request.user
        ).update(is_active=is_active)
        
        status_text = 'نشطة' if is_active else 'غير نشطة'
        messages.success(request, f'تم تحديث حالة {updated_count} شاحنة إلى {status_text} بنجاح')
        return redirect('port:trucks_list')
    except Exception as e:
        messages.error(request, f'حدث خطأ أثناء تحديث الحالة: {str(e)}')
        return redirect('port:trucks_list')



