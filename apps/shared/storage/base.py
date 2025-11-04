# apps/shared/storage/base.py
from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple


class AbstractStorageService(ABC):
    """
    Абстрактний клас для storage сервісів.
    Визначає інтерфейс для роботи з різними storage providers.
    """

    @abstractmethod
    def generate_upload_url(
        self, key: str, content_type: str = 'application/octet-stream', expires_in: int = 3600, **kwargs
    ) -> str:
        """
        Генерує presigned URL для завантаження файлу.

        Args:
            key: Шлях до файлу в storage
            content_type: MIME тип файлу
            expires_in: Час життя URL в секундах
            **kwargs: Додаткові параметри для конкретного provider

        Returns:
            str: Presigned URL для завантаження
        """

    @abstractmethod
    def generate_download_url(self, key: str, filename: str | None = None, expires_in: int = 3600, **kwargs) -> str:
        """
        Генерує presigned URL для скачування файлу.

        Args:
            key: Шлях до файлу в storage
            filename: Кастомна назва файлу для скачування
            expires_in: Час життя URL в секундах
            **kwargs: Додаткові параметри

        Returns:
            str: Presigned URL для скачування
        """

    @abstractmethod
    def generate_delete_url(self, key: str, expires_in: int = 300, **kwargs) -> str:
        """
        Генерує presigned URL для видалення файлу.

        Args:
            key: Шлях до файлу в storage
            expires_in: Час життя URL в секундах
            **kwargs: Додаткові параметри

        Returns:
            str: Presigned URL для видалення
        """

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """
        Перевіряє чи існує файл в storage.

        Args:
            key: Шлях до файлу

        Returns:
            bool: True якщо файл існує
        """

    @abstractmethod
    def get_file_metadata(self, key: str) -> dict | None:
        """
        Отримує метадані файлу.

        Args:
            key: Шлях до файлу

        Returns:
            Dict: Метадані файлу або None якщо файл не існує
        """

    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """
        Видаляє файл з storage.

        Args:
            key: Шлях до файлу

        Returns:
            bool: True якщо файл успішно видалено
        """

    @abstractmethod
    def list_files(self, prefix: str, limit: int = 100) -> list[dict]:
        """
        Отримує список файлів з префіксом.

        Args:
            prefix: Префікс для пошуку
            limit: Максимальна кількість файлів

        Returns:
            List[Dict]: Список файлів з метаданими
        """

    @abstractmethod
    def bulk_delete_files(self, keys: list[str]) -> tuple[list[str], list[str]]:
        """
        Bulk видалення файлів.

        Args:
            keys: Список шляхів до файлів

        Returns:
            Tuple[List[str], List[str]]: (успішно видалені, помилки)
        """

    @abstractmethod
    def get_storage_stats(self, prefix: str) -> dict:
        """
        Отримує статистику використання storage.

        Args:
            prefix: Префікс для підрахунку

        Returns:
            Dict: Статистика (кількість файлів, розмір, тощо)
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Назва storage provider."""

    @property
    @abstractmethod
    def supports_resumable_upload(self) -> bool:
        """Чи підтримує resumable upload."""

    @property
    @abstractmethod
    def max_file_size(self) -> int:
        """Максимальний розмір файлу в байтах."""
