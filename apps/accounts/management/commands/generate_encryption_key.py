import os

from cryptography.fernet import Fernet
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a new encryption key for Google Drive tokens"

    def handle(self, *args, **options):
        key = Fernet.generate_key()
        key_str = key.decode("utf-8")

        self.stdout.write(self.style.SUCCESS(f"Generated encryption key: {key_str}"))

        self.stdout.write(self.style.WARNING("Add this key to your .env file as:"))

        self.stdout.write(f"GOOGLE_DRIVE_ENCRYPTION_KEY={key_str}")

        self.stdout.write(
            self.style.WARNING(
                "IMPORTANT: Keep this key secure and don't lose it! "
                "If you lose the key, all encrypted tokens will become unrecoverable."
            )
        )
