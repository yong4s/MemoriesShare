"""Celery tasks for the albums domain.

S3 cleanup runs here, not on the request thread. Dispatched from services via
``transaction.on_commit(lambda: cleanup_album_s3_prefix_task.delay(...))`` so
the task fires only after the originating DB transaction commits.
"""

import logging

from settings.celery import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5, 'countdown': 30},
    retry_backoff=True,
    retry_jitter=True,
)
def cleanup_album_s3_prefix_task(self, s3_prefix: str, album_uuid: str) -> None:
    """Delete an album's S3 folder asynchronously.

    Idempotent: if the folder is already gone, the underlying delete is a no-op.
    """
    # In-function import avoids Django app-registry boot ordering issues
    # when this module is imported eagerly at Celery worker startup.
    from apps.shared.container import get_s3_service  # noqa: PLC0415

    if not s3_prefix:
        logger.debug('No s3_prefix supplied for album %s, skipping cleanup', album_uuid)
        return

    s3_service = get_s3_service()
    try:
        s3_service.delete_folder(s3_prefix)
        logger.info('Cleaned up S3 folder for album %s (prefix=%s)', album_uuid, s3_prefix)
    except Exception:
        logger.exception('Failed to clean up S3 folder for album %s', album_uuid)
        raise
