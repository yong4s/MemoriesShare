import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ('mediafiles', '0003_remove_mediafile_file'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mediafile',
            old_name='user_pk',
            new_name='user_id',
        ),
    ]
