from django.core.management.base import BaseCommand
from users.models import CustomUser
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Creates initial users'

    def handle(self, *args, **kwargs):
        # إنشاء حساب المدير
        manager_data = {
            'phone_number': '07739601770',
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'Super',
            'user_type': 'MANAGER',
            'is_staff': True,
            'is_superuser': True,
            'is_subscription_active': True,
            'subscription_end_date': timezone.now() + timedelta(days=365)
        }

        try:
            manager = CustomUser.objects.create_superuser(
                **manager_data,
                password='1111'
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created superuser: {manager.phone_number}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}')) 