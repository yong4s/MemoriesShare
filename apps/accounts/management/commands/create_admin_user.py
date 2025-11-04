from django.contrib.auth import get_user_model
from django.core.management import BaseCommand


class Command(BaseCommand):
    ADMIN_EMAIL = 'admin@mail.com'
    ADMIN_PASSWORD = 'adminpassword'  # nosec  # noqa: S105
    help = 'Check and create default development admin user'

    def handle(self, *args, **options):  # noqa: ARG002
        user_class = get_user_model()

        user, _ = user_class.objects.update_or_create(
            email=self.ADMIN_EMAIL,
            defaults={
                'is_staff': True,
                'is_active': True,
                'is_superuser': True,
            },
        )
        user.set_password(self.ADMIN_PASSWORD)
        user.save()
        self.stdout.write(self.style.SUCCESS('Development admin user has been created!'))
