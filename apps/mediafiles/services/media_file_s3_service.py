import logging
from typing import Any

from botocore.exceptions import BotoCoreError
from botocore.exceptions import ClientError

from apps.mediafiles.exceptions import MediaFileStorageError
from apps.shared.storage.optimized_s3_service import OptimizedS3Service

logger = logging.getLogger(__name__)

# Hard cap on a single uploaded object; enforced by the presigned POST policy.
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


class MediaFileS3Service:
    def __init__(self, s3_service: OptimizedS3Service):
        self.s3_service = s3_service

    @property
    def bucket_name(self) -> str:
        return self.s3_service.bucket_name

    def generate_upload_url(self, s3_key: str, content_type: str, expires_in: int = 3600) -> dict[str, Any]:
        """Generate a presigned POST (``url`` + ``fields``) with an enforced max object size.

        Presigned POST is used over PUT because only POST policy conditions can
        cap the uploaded object size (``content-length-range``).
        """
        presigned_post = self.s3_service.generate_presigned_upload_url(
            s3_key=s3_key,
            content_type=content_type,
            expires_in=expires_in,
            content_length_range=(1, MAX_UPLOAD_BYTES),
        )
        logger.info('Generated upload POST for key: %s', s3_key)
        return presigned_post

    def generate_download_url(self, s3_key: str, filename: str | None = None) -> str:
        try:
            url = self.s3_service.generate_presigned_download_url(
                s3_key=s3_key,
                filename=filename,
            )
            logger.info('Generated download URL for key: %s', s3_key)
            return url
        except (ClientError, BotoCoreError) as e:
            logger.exception('AWS error generating download URL for %s: %s', s3_key, e)
            raise MediaFileStorageError(operation='download_url') from e

    def delete_object(self, s3_key: str) -> int:
        try:
            deleted = self.s3_service.delete_object(s3_key)
            logger.info('Deleted S3 object %s', s3_key)
            return deleted
        except (ClientError, BotoCoreError) as e:
            logger.exception('AWS error deleting %s: %s', s3_key, e)
            raise MediaFileStorageError(operation='delete') from e

    def generate_thumbnail_url(self, s3_key: str, expires_in: int = 3600) -> str:
        try:
            url = self.s3_service.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except (ClientError, BotoCoreError) as e:
            logger.exception('AWS error generating thumbnail URL for %s: %s', s3_key, e)
            raise MediaFileStorageError(operation='thumbnail_url') from e

    def get_metadata(self, s3_key: str) -> dict:
        try:
            metadata = self.s3_service.get_object_metadata(s3_key)
            logger.info('Retrieved metadata for key: %s', s3_key)
            return metadata
        except (ClientError, BotoCoreError) as e:
            logger.exception('AWS error getting metadata for %s: %s', s3_key, e)
            raise MediaFileStorageError(operation='get_metadata') from e
