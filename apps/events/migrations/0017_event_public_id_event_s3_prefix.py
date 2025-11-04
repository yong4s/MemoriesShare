# Generated manually for Event optimization fields

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0016_eventcategory_event_address_event_all_day_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='public_id',
            field=models.CharField(
                max_length=12,
                unique=True,
                editable=False,
                db_index=True,
                null=True,
                blank=True,
                help_text='Короткий публічний ID для gallery URLs',
                verbose_name='Публічний ID',
            ),
        ),
        migrations.AddField(
            model_name='event',
            name='s3_prefix',
            field=models.CharField(
                max_length=255,
                editable=False,
                null=True,
                blank=True,
                help_text='S3 префікс: users/{user_uuid}/events/{event_uuid}/',
                verbose_name='S3 префікс',
            ),
        ),
        migrations.AlterField(
            model_name='event',
            name='event_gallery_url',
            field=models.CharField(
                unique=True,
                editable=False,
                max_length=10,
                db_index=True,
                null=True,
                blank=True,
                help_text='Застаріле поле, використовуйте public_id',
                verbose_name='URL галереї (застаріле)',
            ),
        ),
    ]
