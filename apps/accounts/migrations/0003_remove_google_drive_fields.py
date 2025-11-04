# Generated manually to remove Google Drive fields

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_user_google_access_token_encrypted_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='google_access_token_encrypted',
        ),
        migrations.RemoveField(
            model_name='user',
            name='google_refresh_token_encrypted',
        ),
        migrations.RemoveField(
            model_name='user',
            name='google_token_expires_at',
        ),
        migrations.RemoveField(
            model_name='user',
            name='google_drive_connected',
        ),
    ]
