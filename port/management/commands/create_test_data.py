from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from port.models import DeliveryOrder, Container, Driver, Truck
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'إنشاء بيانات تجريبية للاختبار'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            default=1,
            help='معرف المستخدم لإنشاء البيانات له'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'المستخدم برقم {user_id} غير موجود')
            )
            return

        # إنشاء أذونات تسليم تجريبية
        delivery_orders = []
        for i in range(1, 6):
            order, created = DeliveryOrder.objects.get_or_create(
                order_number=f'DO-{2024}{i:03d}',
                user=user,
                defaults={
                    'issue_date': timezone.now() - timedelta(days=i),
                    'expiry_date': timezone.now() + timedelta(days=30-i),
                    'status': 'LOADING',
                    'notes': f'إذن تسليم تجريبي رقم {i}'
                }
            )
            delivery_orders.append(order)
            if created:
                self.stdout.write(f'تم إنشاء إذن التسليم: {order.order_number}')

        # إنشاء سائقين تجريبيين
        drivers = []
        driver_names = ['أحمد محمد', 'علي حسن', 'محمود عبدالله']
        for i, name in enumerate(driver_names, 1):
            driver, created = Driver.objects.get_or_create(
                phone_number=f'0790123456{i}',
                user=user,
                defaults={
                    'name': name,
                    'mother_name': 'فاطمة',
                    'governorate': 'BGD',
                    'license_number': f'LIC{2024}{i:03d}',
                    'id_number': f'ID{2024}{i:06d}'
                }
            )
            drivers.append(driver)
            if created:
                self.stdout.write(f'تم إنشاء السائق: {driver.name}')

        # إنشاء شاحنات تجريبية
        trucks = []
        plate_numbers = ['12345', '23456', '34567']
        for i, plate in enumerate(plate_numbers, 1):
            truck, created = Truck.objects.get_or_create(
                plate_number=plate,
                user=user,
                defaults={
                    'governorate': 'BGD',
                    'truck_type': 'CONT'
                }
            )
            trucks.append(truck)
            if created:
                self.stdout.write(f'تم إنشاء الشاحنة: {truck.plate_number}')

        # إنشاء حاويات تجريبية لكل إذن
        container_types = ['20DC', '40DC', '20RF', '40RF']
        for order in delivery_orders:
            for i, container_type in enumerate(container_types[:2], 1):
                container_number = f'{order.order_number}-C{i:02d}'
                container, created = Container.objects.get_or_create(
                    container_number=container_number,
                    user=user,
                    defaults={
                        'container_type': container_type,
                        'delivery_order': order,
                        'status': order.status,
                        'weight': 40,  # تعيين الوزن إلى 40 لجميع أنواع الحاويات
                        'content_description': f'بضائع تجريبية للحاوية {container_number}'
                    }
                )
                if created:
                    self.stdout.write(f'تم إنشاء الحاوية: {container.container_number}')

        self.stdout.write(
            self.style.SUCCESS(f'تم إنشاء البيانات التجريبية بنجاح للمستخدم: {user.username}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'أذونات التسليم: {len(delivery_orders)}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'السائقين: {len(drivers)}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'الشاحنات: {len(trucks)}')
        )
        
        # عرض عدد الحاويات المرتبطة بكل إذن
        for order in delivery_orders:
            container_count = order.containers.count()
            self.stdout.write(
                self.style.SUCCESS(f'إذن {order.order_number}: {container_count} حاوية')
            ) 