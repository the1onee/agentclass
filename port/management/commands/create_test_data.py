from django.core.management.base import BaseCommand
from django.utils import timezone
from port.models import DeliveryOrder, Container
import random

class Command(BaseCommand):
    help = 'Creates test delivery orders and containers'

    def handle(self, *args, **kwargs):
        # إنشاء 5 أوامر تسليم
        for i in range(5):
            order = DeliveryOrder.objects.create(
                order_number=f'DO-2024-{i+1:03d}',
                issue_date=timezone.now(),
                status='PENDING',
                notes=f'أمر تسليم تجريبي {i+1}'
            )
            
            # إنشاء 3 حاويات لكل أمر
            for j in range(3):
                Container.objects.create(
                    container_number=f'CONT-{i+1}-{j+1}',
                    weight=random.uniform(10.0, 30.0),
                    container_type=random.choice(['20DC', '40DC', '20RF']),
                    delivery_order=order
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created delivery order {order.order_number}')
            ) 