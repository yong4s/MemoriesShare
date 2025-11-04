# apps/shared/storage/factory.py
import logging
from typing import Optional

from apps.shared.exceptions.exception import S3ServiceError

from .base import AbstractStorageService
from .s3_storage import S3StorageService

logger = logging.getLogger(__name__)


class StorageFactory:
    """
    Factory для створення storage сервісів.
    Реалізує Strategy pattern для роботи з різними storage providers.
    """

    _providers = {
        's3': S3StorageService,
    }

    @classmethod
    def create_storage_service(cls, provider: str, **kwargs) -> AbstractStorageService:
        """
        Створює storage service для вказаного provider.

        Args:
            provider: Назва storage provider ('s3')
            **kwargs: Додаткові параметри для конкретного provider

        Returns:
            AbstractStorageService: Інстанс storage service

        Raises:
            S3ServiceError: Якщо provider не підтримується
        """
        if provider not in cls._providers:
            supported = ', '.join(cls._providers.keys())
            raise S3ServiceError(f'Unsupported storage provider: {provider}. ' f'Supported providers: {supported}')

        try:
            service_class = cls._providers[provider]
            return service_class()

        except Exception as e:
            logger.error(f'Failed to create {provider} storage service: {e}')
            raise S3ServiceError(f'Failed to initialize {provider} storage: {e}')

    @classmethod
    def get_supported_providers(cls) -> list:
        """Повертає список підтримуваних storage providers."""
        return list(cls._providers.keys())

    @classmethod
    def register_provider(cls, name: str, service_class):
        """
        Реєструє новий storage provider.

        Args:
            name: Назва provider
            service_class: Клас що реалізує AbstractStorageService
        """
        if not issubclass(service_class, AbstractStorageService):
            raise ValueError('Service class must inherit from AbstractStorageService')

        cls._providers[name] = service_class
        logger.info(f'Registered storage provider: {name}')


def get_storage_service(provider: str, **kwargs) -> AbstractStorageService:
    """
    Зручна функція для отримання storage service.

    Args:
        provider: Назва storage provider
        **kwargs: Додаткові параметри

    Returns:
        AbstractStorageService: Storage service instance
    """
    return StorageFactory.create_storage_service(provider, **kwargs)
