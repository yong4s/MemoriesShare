from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from apps.mediafiles.models import MediaFile

from .models import Album
from .models import Download


class MediaFileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(
        write_only=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'png', 'jpeg', 'pdf', 'gif', 'mp3', 'mp4', 'mov'])
        ],
    )
    album_id = serializers.PrimaryKeyRelatedField(source='album_id', queryset=Album.objects.all())
    user_id = serializers.PrimaryKeyRelatedField(source='user_id', read_only=True)

    class Meta:
        model = MediaFile
        fields = ('mediafilePK', 'album_id', 'user_id', 'file', 'file_type', 'S3_bucket_name', 'S3_object_key')
        read_only_fields = ('mediafilePK', 'file_type', 'S3_bucket_name', 'S3_object_key', 'user_id')


class AlbumListSerializer(serializers.ModelSerializer):
    mediafiles_count = serializers.SerializerMethodField()
    event_name = serializers.CharField(source='event.event_name', read_only=True)

    class Meta:
        model = Album
        fields = ('album_uuid', 'event_name', 'name', 'description', 'is_public', 'created_at', 'mediafiles_count')
        read_only_fields = ('album_uuid', 'event_name', 'created_at')

    def get_mediafiles_count(self, obj):
        return obj.mediafiles.count()


class AlbumDetailSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.event_name', read_only=True)
    event_uuid = serializers.UUIDField(source='event.event_uuid', read_only=True)
    file_count = serializers.IntegerField(read_only=True)
    total_file_size = serializers.IntegerField(read_only=True)

    class Meta:
        model = Album
        fields = (
            'album_uuid',
            'event_name',
            'event_uuid',
            'name',
            'description',
            'is_public',
            'file_count',
            'total_file_size',
            'has_cover_image',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'album_uuid',
            'event_name',
            'event_uuid',
            'file_count',
            'total_file_size',
            'has_cover_image',
            'created_at',
            'updated_at',
        )


class AlbumCreateSerializer(serializers.ModelSerializer):
    """Серіалізатор для створення альбому - без зайвих полів"""

    class Meta:
        model = Album
        fields = ('name', 'description', 'is_public')

    def validate_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError('Назва альбому має бути не менше 2 символів')
        return value.strip()

    def validate_description(self, value):
        if value and len(value.strip()) > 500:
            raise serializers.ValidationError('Опис альбому занадто довгий (максимум 500 символів)')
        return value.strip() if value else ''


class DownloadSerializer(serializers.ModelSerializer):
    album_name = serializers.CharField(source='album.name', read_only=True)
    album_uuid = serializers.UUIDField(source='album.album_uuid', read_only=True)
    time_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Download
        fields = (
            'download_uuid',
            'album_name',
            'album_uuid',
            'status',
            'download_url',
            'expires_at',
            'file_count',
            'archive_size',
            'time_remaining',
            'created_at',
        )
        read_only_fields = (
            'download_uuid',
            'album_name',
            'album_uuid',
            'status',
            'download_url',
            'expires_at',
            'time_remaining',
            'created_at',
        )

    def get_time_remaining(self, obj):
        """Повертає час що залишився до закінчення в секундах"""
        remaining = obj.time_remaining
        return remaining.total_seconds() if remaining else None
