import uuid

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from apps.shared.base.models import BaseModel


class AlbumQuerySet(models.QuerySet):
    """Кастомний QuerySet для альбомів з додатковою функціональністю"""

    def for_event(self, event_id):
        """Повертає альбоми для конкретної події"""
        return self.filter(event_id=event_id)

    def with_file_counts(self):
        """Додає кількість файлів до кожного альбому"""
        return self.annotate(file_count=Count("mediafiles", distinct=True))

    def public(self):
        """Повертає тільки публічні альбоми"""
        return self.filter(is_public=True)

    def private(self):
        """Повертає тільки приватні альбоми"""
        return self.filter(is_public=False)

    def with_recent_activity(self):
        """Додає оптимізовані prefetch запити"""
        return self.select_related("event", "event__user").prefetch_related(
            "mediafiles"
        )

    def for_user(self, user_id):
        """Повертає альбоми користувача (власні події)"""
        return self.filter(event__user_id=user_id)


class Album(BaseModel):
    """
    Модель для зберігання інформації про альбоми в рамках події.
    Використовує Amazon S3 для зберігання файлів з hierarchical структурою.
    """

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="albums",
        verbose_name=_("Подія"),
        help_text=_("Подія, до якої належить альбом"),
        db_index=True,  # Критично для performance
    )
    name = models.CharField(
        _("Назва альбому"),
        max_length=255,
        help_text=_("Введіть назву альбому (не більше 255 символів)"),
        db_index=True,  # Індекс для пошуку за назвою
    )
    description = models.TextField(
        _("Опис альбому"),
        max_length=500,
        blank=True,
        help_text=_("Додайте опис альбому (не більше 500 символів)"),
    )
    album_uuid = models.UUIDField(
        _("UUID альбому"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,  # Індекс для API calls
    )
    album_s3_prefix = models.CharField(
        _("S3 Prefix"),
        max_length=500,
        unique=True,
        help_text=_("S3 шлях для зберігання файлів альбому"),
    )
    is_public = models.BooleanField(
        _("Публічний альбом"),
        default=False,
        help_text=_("Чи є альбом публічним для перегляду"),
    )
    cover_image_s3_key = models.CharField(
        _("Обкладинка альбому"),
        max_length=500,
        blank=True,
        help_text=_("S3 ключ для обкладинки альбому"),
    )
    sort_order = models.PositiveIntegerField(
        _("Порядок сортування"),
        default=0,
        help_text=_("Порядок відображення альбому в списку"),
    )

    objects = AlbumQuerySet.as_manager()

    class Meta:
        verbose_name = _("Альбом")
        verbose_name_plural = _("Альбоми")
        ordering = ["sort_order", "-created_at", "name"]
        unique_together = [["event", "name"]]  # Унікальність назви в рамках події
        indexes = [
            models.Index(fields=["event", "created_at"]),
            models.Index(fields=["event", "is_public"]),
            models.Index(fields=["event", "sort_order"]),
            models.Index(fields=["album_uuid"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.event.event_name})"

    def clean(self):
        """Валідація моделі"""
        super().clean()

        errors = {}

        # Валідація назви альбому
        if not self.name or len(self.name.strip()) < 2:
            errors["name"] = _("Назва альбому має бути не менше 2 символів")
        elif len(self.name.strip()) > 255:
            errors["name"] = _("Назва альбому занадто довга (максимум 255 символів)")

        # Валідація опису
        if self.description and len(self.description.strip()) > 500:
            errors["description"] = _(
                "Опис альбому занадто довгий (максимум 500 символів)"
            )

        # Валідація порядку сортування
        if self.sort_order < 0:
            errors["sort_order"] = _("Порядок сортування не може бути від'ємним")

        # Перевірка унікальності назви в рамках події
        if self.name and self.event_id:
            qs = Album.objects.filter(
                event_id=self.event_id, name__iexact=self.name.strip()
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors["name"] = _("Альбом з такою назвою вже існує в цій події")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Перевизначений метод збереження"""
        # Очищуємо та валідуємо дані
        if self.name:
            self.name = self.name.strip()
        if self.description:
            self.description = self.description.strip()

        # Генеруємо S3 prefix якщо його немає
        if not self.album_s3_prefix and self.event_id:
            self.album_s3_prefix = f"user-bucket-{self.event.user_id}/{self.event.event_uuid}/album-{self.album_uuid}"

        self.clean()
        super().save(*args, **kwargs)

        # Очищуємо кеш після збереження
        self._clear_cache()

    def delete(self, *args, **kwargs):
        """Перевизначений метод видалення"""
        album_id = self.id
        event_id = self.event_id
        super().delete(*args, **kwargs)

        # Очищуємо кеш після видалення
        self._clear_cache(album_id, event_id)

    def _clear_cache(self, album_id=None, event_id=None):
        album_id = album_id or self.id
        event_id = event_id or self.event_id

        if album_id:
            cache_keys = [
                f"album_file_count:{album_id}",
                f"album_statistics:{album_id}",
                f"album_cover_image:{album_id}",
            ]
            cache.delete_many(cache_keys)

        # Очищуємо кеш події
        if event_id:
            cache.delete(f"event_albums_count:{event_id}")

    @property
    def file_count(self):
        """Повертає кількість файлів в альбомі"""
        cache_key = f"album_file_count:{self.id}"
        count = cache.get(cache_key)

        if count is None:
            count = self.mediafiles.count()
            cache.set(cache_key, count, 300)  # Кешуємо на 5 хвилин

        return count

    @property
    def total_file_size(self):
        """Returns file count instead of total size (file_size field not implemented in MediaFile)"""
        return self.file_count

    @property
    def has_cover_image(self):
        """Перевіряє чи має альбом обкладинку"""
        return bool(self.cover_image_s3_key)

    @property
    def is_empty(self):
        """Перевіряє чи альбом порожній"""
        return self.file_count == 0

    def can_be_accessed_by_user(self, user_id):
        """Перевіряє чи може користувач отримати доступ до альбому"""
        if self.is_public:
            return True

        # Власник події має доступ
        if self.event.user_id == user_id:
            return True

        # Гості події мають доступ
        return self.event.guests.filter(id=user_id).exists()

    def set_cover_image(self, s3_key):
        """Встановлює обкладинку альбому"""
        self.cover_image_s3_key = s3_key
        self.save(update_fields=["cover_image_s3_key"])

        # Очищуємо кеш обкладинки
        cache.delete(f"album_cover_image:{self.id}")

    def get_file_types_summary(self):
        """Повертає статистику типів файлів в альбомі"""
        cache_key = f"album_file_types:{self.id}"
        summary = cache.get(cache_key)

        if summary is None:
            from django.db.models import Count

            summary = dict(
                self.mediafiles.values("file_type")
                .annotate(count=Count("id"))
                .values_list("file_type", "count")
            )
            cache.set(cache_key, summary, 600)

        return summary


class DownloadQuerySet(models.QuerySet):
    """Кастомний QuerySet для завантажень"""

    def pending(self):
        """Повертає завантаження в очікуванні"""
        return self.filter(status="pending")

    def processing(self):
        """Повертає завантаження в процесі"""
        return self.filter(status="processing")

    def completed(self):
        """Повертає завершені завантаження"""
        return self.filter(status="completed")

    def failed(self):
        """Повертає невдалі завантаження"""
        return self.filter(status="failed")

    def expired(self):
        """Повертає завантаження з минулим терміном дії"""
        from django.utils import timezone

        return self.filter(expires_at__lt=timezone.now())

    def active(self):
        """Повертає активні завантаження"""
        from django.utils import timezone

        return self.filter(status="completed", expires_at__gt=timezone.now())


class DownloadManager(models.Manager):
    """Кастомний менеджер для завантажень"""

    def get_queryset(self):
        return DownloadQuerySet(self.model, using=self._db)

    def pending(self):
        return self.get_queryset().pending()

    def processing(self):
        return self.get_queryset().processing()

    def completed(self):
        return self.get_queryset().completed()

    def failed(self):
        return self.get_queryset().failed()

    def expired(self):
        return self.get_queryset().expired()

    def active(self):
        return self.get_queryset().active()


class Download(BaseModel):
    """
    Модель для зберігання інформації про завантаження альбомів.
    Дозволяє створювати тимчасові посилання для завантаження всього альбому.
    """

    DOWNLOAD_STATUSES = [
        ("pending", _("Очікується")),
        ("processing", _("Обробляється")),
        ("completed", _("Завершено")),
        ("failed", _("Помилка")),
        ("expired", _("Минув термін дії")),
    ]

    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name="downloads",
        verbose_name=_("Альбом"),
        help_text=_("Альбом для завантаження"),
        db_index=True,
    )
    download_uuid = models.UUIDField(
        _("UUID завантаження"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )
    status = models.CharField(
        _("Статус завантаження"),
        max_length=20,
        choices=DOWNLOAD_STATUSES,
        default="pending",
        help_text=_("Поточний статус завантаження"),
        db_index=True,
    )
    download_url = models.URLField(
        _("URL завантаження"),
        max_length=500,
        null=True,
        blank=True,
        help_text=_("Тимчасове посилання для завантаження"),
    )
    expires_at = models.DateTimeField(
        _("Дата закінчення"),
        null=True,
        blank=True,
        help_text=_("Дата та час закінчення дії посилання"),
        db_index=True,
    )
    file_count = models.PositiveIntegerField(
        _("Кількість файлів"), default=0, help_text=_("Кількість файлів в архіві")
    )
    archive_size = models.BigIntegerField(
        _("Розмір архіву"),
        null=True,
        blank=True,
        help_text=_("Розмір створеного архіву в байтах"),
    )
    error_message = models.TextField(
        _("Повідомлення про помилку"),
        blank=True,
        help_text=_("Деталі помилки якщо завантаження невдале"),
    )

    objects = DownloadManager()

    class Meta:
        verbose_name = _("Завантаження")
        verbose_name_plural = _("Завантаження")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["album", "status"]),
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["download_uuid"]),
        ]

    def __str__(self):
        return f"Download {self.album.name} - {self.get_status_display()}"

    def clean(self):
        """Валідація моделі"""
        super().clean()

        errors = {}

        # Валідація URL якщо статус completed
        if self.status == "completed" and not self.download_url:
            errors["download_url"] = _(
                "URL завантаження обов'язковий для завершених завантажень"
            )

        # Валідація expires_at якщо статус completed
        if self.status == "completed" and not self.expires_at:
            errors["expires_at"] = _(
                "Дата закінчення обов'язкова для завершених завантажень"
            )

        # Валідація file_count
        if self.file_count < 0:
            errors["file_count"] = _("Кількість файлів не може бути від'ємною")

        # Валідація archive_size
        if self.archive_size is not None and self.archive_size < 0:
            errors["archive_size"] = _("Розмір архіву не може бути від'ємним")

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Перевизначений метод збереження"""
        # Встановлюємо кількість файлів з альбому якщо не вказано
        if not self.file_count and self.album_id:
            self.file_count = self.album.file_count

        self.clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Перевіряє чи минув термін дії завантаження"""
        if not self.expires_at:
            return False
        from django.utils import timezone

        return timezone.now() > self.expires_at

    @property
    def is_active(self):
        """Перевіряє чи активне завантаження"""
        return self.status == "completed" and not self.is_expired

    @property
    def time_remaining(self):
        """Повертає час що залишився до закінчення"""
        if not self.expires_at:
            return None
        from django.utils import timezone

        remaining = self.expires_at - timezone.now()
        return remaining if remaining.total_seconds() > 0 else None

    def mark_as_processing(self):
        """Позначає завантаження як таке що обробляється"""
        self.status = "processing"
        self.save(update_fields=["status"])

    def mark_as_completed(self, download_url, expires_at, archive_size=None):
        """Позначає завантаження як завершене"""
        self.status = "completed"
        self.download_url = download_url
        self.expires_at = expires_at
        if archive_size is not None:
            self.archive_size = archive_size
        self.save(
            update_fields=["status", "download_url", "expires_at", "archive_size"]
        )

    def mark_as_failed(self, error_message=None):
        """Позначає завантаження як невдале"""
        self.status = "failed"
        if error_message:
            self.error_message = error_message
        self.save(update_fields=["status", "error_message"])

    def extend_expiry(self, hours=24):
        """Продовжує термін дії завантаження"""
        if self.expires_at:
            from datetime import timedelta

            from django.utils import timezone

            self.expires_at = timezone.now() + timedelta(hours=hours)
            self.save(update_fields=["expires_at"])
