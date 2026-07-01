from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('albums', '0002_alter_album_options_alter_download_options_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Download',
        ),
    ]
