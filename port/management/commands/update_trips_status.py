from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from port.models import Trip

class Command(BaseCommand):
    help = 'تحديث حالة الرحلات التي مر عليها أكثر من ثلاثة أيام إلى مكتملة'

    def handle(self, *args, **options):
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
        
        self.stdout.write(
            self.style.SUCCESS(f'تم تحديث {updated_count} رحلة إلى حالة "مكتملة"')
        ) 