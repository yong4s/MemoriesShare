# apps/shared/storage/s3_storage.py
import logging
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from apps.shared.storage.base import AbstractStorageService
from apps.shared.storage.s3_utils import S3Service

logger = logging.getLogger(__name__)


class S3StorageService(AbstractStorageService):
    """
    S3 storage service adapter that implements AbstractStorageService.
    Обгортка навколо існуючого S3Service для сумісності з новою архітектурою.
    """

    def __init__(self):
        self.s3_service = S3Service()

    @property
    def provider_name(self) -> str:
        return 's3'

    @property
    def supports_resumable_upload(self) -> bool:
        return True  # S3 підтримує multipart uploads

    @property
    def max_file_size(self) -> int:
        return 5 * 1024 * 1024 * 1024 * 1024  # 5TB для S3

    def generate_upload_url(
        self,
        key: str,
        content_type: str = 'application/octet-stream',
        expires_in: int = 3600,
        **kwargs,
    ) -> str:
        """Генерує presigned URL для завантаження файлу в S3."""
        return self.s3_service.generate_upload_url(key, content_type, expires_in)

    def generate_download_url(self, key: str, filename: str | None = None, expires_in: int = 3600, **kwargs) -> str:
        """Генерує presigned URL для скачування файлу з S3."""
        return self.s3_service.generate_download_url(key, filename, expires_in)

    def generate_delete_url(self, key: str, expires_in: int = 300, **kwargs) -> str:
        """Генерує presigned URL для видалення файлу з S3."""
        return self.s3_service.generate_delete_url(key, expires_in)

    def file_exists(self, key: str) -> bool:
        """Перевіряє чи існує файл в S3."""
        return self.s3_service.object_exists(key)

    def get_file_metadata(self, key: str) -> dict | None:
        """Отримує метадані файлу з S3."""
        return self.s3_service.get_object_metadata(key)

    def delete_file(self, key: str) -> bool:
        """Видаляє файл з S3."""
        try:
            return self.s3_service.delete_s3_object(key)
        except Exception as e:
            logger.exception(f'Error deleting S3 file {key}: {e}')
            return False

    def list_files(self, prefix: str, limit: int = 100) -> list[dict]:
        """Отримує список файлів з S3."""
        return self.s3_service.list_objects(prefix, limit)

    def bulk_delete_files(self, keys: list[str]) -> tuple[list[str], list[str]]:
        """Bulk видалення файлів з S3."""
        return self.s3_service.bulk_delete_objects(keys)

    def get_storage_stats(self, prefix: str) -> dict:
        """Отримує статистику використання S3."""
        return self.s3_service.get_bucket_statistics(prefix)
