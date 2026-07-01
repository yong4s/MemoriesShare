# Generated for adding file_size field to MediaFile.
#
# After applying, run `python manage.py backfill_media_file_sizes` to populate
# the size for files uploaded before this field existed (it head_objects each
# row from S3 and writes the actual ContentLength).

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ('mediafiles', '0002_mediafile_file_name_mediafile_file_uuid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='mediafile',
            name='file_size',
            field=models.BigIntegerField(
                default=0,
                help_text='Size in bytes, populated from S3 ContentLength after upload confirmation.',
            ),
        ),
    ]
