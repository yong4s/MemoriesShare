from rest_framework import serializers

from apps.albums.models import Album


class AlbumListSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source='event.event_name', read_only=True)
    file_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Album
        fields = (
            'album_uuid',
            'event_name',
            'name',
            'description',
            'is_public',
            'created_at',
            'file_count',
        )
        read_only_fields = ('album_uuid', 'event_name', 'created_at', 'file_count')


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
    """Serializer for creating album"""

    class Meta:
        model = Album
        fields = ('name', 'description', 'is_public')

    def validate_name(self, value):
        if not value or len(value.strip()) < 2:
            msg = 'Album name must be at least 2 characters'
            raise serializers.ValidationError(msg)
        return value.strip()

    def validate_description(self, value):
        if value and len(value.strip()) > 500:
            msg = 'Album description too long (maximum 500 characters)'
            raise serializers.ValidationError(msg)
        return value.strip() if value else ''


class AlbumUpdateSerializer(serializers.Serializer):
    """Serializer for updating album — all fields optional"""

    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    is_public = serializers.BooleanField(required=False)

    def validate_name(self, value):
        if value and len(value.strip()) < 2:
            msg = 'Album name must be at least 2 characters'
            raise serializers.ValidationError(msg)
        return value.strip() if value else value
