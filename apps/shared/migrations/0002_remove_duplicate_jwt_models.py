from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('shared', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BlacklistedToken',
        ),
        migrations.DeleteModel(
            name='UserSession',
        ),
    ]
