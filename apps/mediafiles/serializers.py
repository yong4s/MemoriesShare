from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from apps.mediafiles.models import Download
from apps.mediafiles.models import MediaFile
from apps.shared.storage.s3_utils import file_generate_name


class MediaFileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        write_only=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'jpg',
                    'png',
                    'jpeg',
                    'pdf',
                    'gif',
                    'mp3',
                    'mp4',
                    'mov',
                ]
            )
        ],
    )

    class Meta:
        model = MediaFile
        fields = (
            'mediafilePK',
            'album_id',
            'user_id',
            'file',
            'file_type',
            'S3_bucket_name',
            'S3_object_key',
        )
        read_only_fields = (
            'mediafilePK',
            'file_type',
            'S3_bucket_name',
            'S3_object_key',
            'user_id',
            'album_id',
        )


class DownloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Download
        fields = '__all__'
