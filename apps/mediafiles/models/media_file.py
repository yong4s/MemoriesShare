import uuid

from django.db import models

from apps.albums.models import Album
from apps.shared.base.models import BaseModel
from settings.main import AUTH_USER_MODEL


class MediaFile(BaseModel):
    mediafilePK = models.AutoField(primary_key=True)
    file_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    album_id = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='mediafiles', db_column='album_id')
    user_id = models.ForeignKey(
        AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mediafiles',
        db_column='user_id',
    )
    file_name = models.CharField(max_length=500, blank=True, default='')
    file_type = models.CharField(max_length=255)
    file_size = models.BigIntegerField(
        default=0,
        help_text='Size in bytes, populated from S3 ContentLength after upload confirmation.',
    )
    S3_bucket_name = models.CharField(max_length=255)
    S3_object_key = models.CharField(max_length=500)


class Download(BaseModel):
    mediafile = models.ForeignKey(MediaFile, on_delete=models.CASCADE, related_name='downloads')
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='downloads')
