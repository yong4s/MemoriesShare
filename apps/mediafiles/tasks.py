import logging

from apps.mediafiles.utils.thumbnail import derive_thumbnail_key
from apps.mediafiles.utils.thumbnail import generate_thumbnail_bytes
from apps.mediafiles.utils.thumbnail import is_image_mime_type
from settings.celery import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_jitter=True,
)
def generate_thumbnail_task(self, media_file_uuid: str):
    """Generate a JPEG thumbnail for an uploaded image and store it in S3.

    This task is idempotent — if the thumbnail already exists, it returns early.
    Dispatched after upload confirmation for image MIME types.
    """
    from apps.mediafiles.models.media_file import MediaFile
    from apps.shared.container import get_s3_service

    try:
        media_file = MediaFile.objects.get(file_uuid=media_file_uuid)
    except MediaFile.DoesNotExist:
        logger.warning('MediaFile %s not found, skipping thumbnail generation', media_file_uuid)
        return

    if not is_image_mime_type(media_file.file_type):
        logger.debug('MediaFile %s is not an image (%s), skipping', media_file_uuid, media_file.file_type)
        return

    thumbnail_key = derive_thumbnail_key(media_file.S3_object_key)
    s3_service = get_s3_service()

    # Idempotent: skip if thumbnail already exists
    if s3_service.object_exists(thumbnail_key):
        logger.debug('Thumbnail already exists for %s, skipping', media_file_uuid)
        return

    original_bytes = s3_service.download_object(media_file.S3_object_key)
    logger.info('Generating thumbnail for %s (%d bytes original)', media_file_uuid, len(original_bytes))

    thumbnail_bytes = generate_thumbnail_bytes(original_bytes)
    s3_service.upload_object(thumbnail_key, thumbnail_bytes, content_type='image/jpeg')

    logger.info(
        'Thumbnail generated for %s: %s (%d bytes)',
        media_file_uuid,
        thumbnail_key,
        len(thumbnail_bytes),
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5, 'countdown': 30},
    retry_backoff=True,
    retry_jitter=True,
)
def cleanup_media_file_s3_task(self, object_key: str, thumbnail_key: str | None = None) -> None:
    """Delete a media file's S3 objects after its DB row was deleted.

    Dispatched via ``transaction.on_commit`` so it only runs once the delete has
    committed — a rolled-back delete never destroys the object. Idempotent:
    deleting an already-absent key is a no-op.
    """
    from apps.shared.container import get_s3_service

    s3_service = get_s3_service()
    s3_service.delete_object(object_key)
    if thumbnail_key:
        s3_service.delete_object(thumbnail_key)
    logger.info('Cleaned up S3 objects for deleted media file (key=%s)', object_key)
