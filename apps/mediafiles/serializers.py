from rest_framework import serializers


class MediaFileUploadRequestSerializer(serializers.Serializer):
    """POST /mediafiles/ — request presigned upload URL"""

    event_uuid = serializers.UUIDField()
    album_uuid = serializers.UUIDField()
    file_name = serializers.CharField(max_length=500)
    content_type = serializers.CharField(max_length=255)


class MediaFileUploadResponseSerializer(serializers.Serializer):
    """Response for presigned POST upload request"""

    url = serializers.URLField()
    fields = serializers.DictField(child=serializers.CharField())
    s3_key = serializers.CharField()
    file_uuid = serializers.CharField()
    event_uuid = serializers.CharField()
    album_uuid = serializers.CharField()
    expires_in = serializers.IntegerField()


class MediaFileListQuerySerializer(serializers.Serializer):
    """GET /mediafiles/ — query params validation"""

    event_uuid = serializers.UUIDField(required=False)
    album_uuid = serializers.UUIDField(required=False)


class MediaFileUpdateSerializer(serializers.Serializer):
    """PUT /mediafiles/{uuid}/ — update file metadata"""

    file_name = serializers.CharField(max_length=500, required=False)


class LegacyUploadedConfirmSerializer(serializers.Serializer):
    """POST /mediafiles/files/uploaded/ — confirm upload"""

    event_uuid = serializers.UUIDField()
    s3_key = serializers.CharField(max_length=500)
    file_type = serializers.CharField(max_length=255)
    file_uuid = serializers.CharField(required=False)
    album_uuid = serializers.UUIDField(required=False)
    file_name = serializers.CharField(max_length=500, required=False)
