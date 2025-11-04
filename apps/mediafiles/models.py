from django.db import models

from apps.albums.models import Album
from apps.shared.base.models import BaseModel
from settings.main import AUTH_USER_MODEL


class MediaFile(BaseModel):
    mediafilePK = models.AutoField(primary_key=True)
    album_id = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='mediafiles', db_column='album_id')
    user_id = models.ForeignKey(
        AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mediafiles', db_column='user_id'
    )
    file_type = models.CharField(max_length=255)
    S3_bucket_name = models.CharField(max_length=255)
    S3_object_key = models.CharField(max_length=255)


class Download(BaseModel):
    mediafile = models.ForeignKey(MediaFile, on_delete=models.CASCADE, related_name='downloads')
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='downloads')
