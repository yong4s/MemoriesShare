# Generated manually - Remove Guest model from events app

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0014_alter_event_description'),
        ('accounts', '0008_migrate_guest_data'),  # Ensure data is migrated first
    ]

    operations = [
        # Remove the Guest model completely from events app
        migrations.DeleteModel(
            name='Guest',
        ),
    ]
