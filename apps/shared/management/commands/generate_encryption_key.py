# apps/shared/management/commands/generate_encryption_key.py
from cryptography.fernet import Fernet
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Django management command для генерації encryption key.

    Usage: python manage.py generate_encryption_key
    """

    help = 'Generate a new encryption key for token encryption'

    def handle(self, *args, **options):
        """Generate and display a new encryption key."""
        key = Fernet.generate_key()
        key_string = key.decode('utf-8')

        self.stdout.write(self.style.SUCCESS(f'Generated encryption key: {key_string}'))

        self.stdout.write(self.style.WARNING('IMPORTANT: Add this key to your environment variables as ENCRYPTION_KEY'))

        self.stdout.write(
            self.style.WARNING('Store this key securely - if you lose it, encrypted data cannot be recovered!')
        )
