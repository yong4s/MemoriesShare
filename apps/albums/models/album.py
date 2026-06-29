import uuid

from django.db import models
from django.db.models import Count
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from apps.shared.base.models import BaseModel


class AlbumQuerySet(models.QuerySet):
    """Custom QuerySet for albums."""

    def for_event(self, event_id):
        """Return albums for specific event"""
        return self.filter(event_id=event_id)

    def with_file_counts(self):
        """Add file count annotation to each album"""
        return self.annotate(file_count=Count('mediafiles', distinct=True))


class Album(BaseModel):
    """
    Model for storing album information within events.
    Uses Amazon S3 for file storage with hierarchical structure.
    """

    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='albums',
        verbose_name=_('Подія'),
        help_text=_('Подія, до якої належить альбом'),
        db_index=True,
    )
    name = models.CharField(
        _('Назва альбому'),
        max_length=255,
        help_text=_('Введіть назву альбому (не більше 255 символів)'),
        db_index=True,
    )
    description = models.TextField(
        _('Опис альбому'),
        max_length=500,
        blank=True,
        help_text=_('Додайте опис альбому (не більше 500 символів)'),
    )
    album_uuid = models.UUIDField(
        _('Album UUID'),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    album_s3_prefix = models.CharField(
        _('S3 Prefix'),
        max_length=500,
        unique=True,
        help_text=_('S3 шлях для зберігання файлів альбому'),
    )
    is_public = models.BooleanField(
        _('Публічний альбом'),
        default=False,
        help_text=_('Чи є альбом публічним для перегляду'),
    )
    cover_image_s3_key = models.CharField(
        _('Обкладинка альбому'),
        max_length=500,
        blank=True,
        help_text=_('S3 ключ для обкладинки альбому'),
    )
    sort_order = models.PositiveIntegerField(
        _('Порядок сортування'),
        default=0,
        help_text=_('Порядок відображення альбому в списку'),
    )

    objects = AlbumQuerySet.as_manager()

    class Meta:
        app_label = 'albums'
        verbose_name = _('Альбом')
        verbose_name_plural = _('Альбоми')
        ordering = ['sort_order', '-created_at', 'name']
        unique_together = [['event', 'name']]
        indexes = [
            models.Index(fields=['event', 'created_at']),
            models.Index(fields=['event', 'is_public']),
            models.Index(fields=['event', 'sort_order']),
            models.Index(fields=['album_uuid']),
        ]

    def __str__(self):
        return f'{self.name} ({self.event.event_name})'

    @property
    def total_file_size(self):
        """Total size in bytes of all media files in this album.

        Sums ``MediaFile.file_size``, populated from the S3 ``ContentLength``
        header on upload confirmation. Files uploaded before the field existed
        read 0 until the ``backfill_media_file_sizes`` command is run.
        """
        return self.mediafiles.aggregate(total=Sum('file_size'))['total'] or 0

    @property
    def has_cover_image(self):
        return bool(self.cover_image_s3_key)
