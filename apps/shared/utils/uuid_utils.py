import secrets
import uuid
from typing import Protocol

import base62
from django.db import models


class UUIDMixin(models.Model):
    """Base mixin для генерації UUID з різними стратегіями"""

    class Meta:
        abstract = True

    @classmethod
    def generate_uuid(cls) -> str:
        """Генерує UUID4 для максимальної випадковості та S3 розподілу"""
        return str(uuid.uuid4())

    @classmethod
    def generate_short_uuid(cls) -> str:
        """Генерує коротший UUID для URLs (base62 encoded)"""
        # Використовуємо secrets для кращої безпеки
        random_bytes = secrets.token_bytes(6)  # 6 байт = 48 біт
        return base62.encode(int.from_bytes(random_bytes, "big"))

    @classmethod
    def generate_prefixed_uuid(cls, prefix: str = "") -> str:
        """Генерує UUID з префіксом для конкретних цілей"""
        short_uuid = cls.generate_short_uuid()
        return f"{prefix}-{short_uuid}" if prefix else short_uuid


class S3KeyGenerator:
    """Утиліта для генерації S3 ключів з оптимальним розподілом"""

    @staticmethod
    def generate_user_prefix(user_uuid: str) -> str:
        """Генерує префікс для користувача"""
        return f"users/{user_uuid}"

    @staticmethod
    def generate_event_prefix(user_uuid: str, event_uuid: str) -> str:
        """Генерує префікс для події"""
        return f"users/{user_uuid}/events/{event_uuid}"

    @staticmethod
    def generate_album_prefix(user_uuid: str, event_uuid: str, album_uuid: str) -> str:
        """Генерує префікс для альбому"""
        return f"users/{user_uuid}/events/{event_uuid}/albums/{album_uuid}"

    @staticmethod
    def generate_file_key(
        user_uuid: str,
        event_uuid: str,
        album_uuid: str,
        file_uuid: str,
        file_extension: str,
        file_type: str = "originals",
    ) -> str:
        """
        Генерує повний S3 ключ для файлу

        Args:
            user_uuid: UUID користувача
            event_uuid: UUID події
            album_uuid: UUID альбому
            file_uuid: UUID файлу
            file_extension: Розширення файлу (.jpg, .mp4, тощо)
            file_type: Тип файлу (originals, thumbnails, compressed)
        """
        album_prefix = S3KeyGenerator.generate_album_prefix(
            user_uuid, event_uuid, album_uuid
        )
        return f"{album_prefix}/{file_type}/{file_uuid}{file_extension}"

    @staticmethod
    def parse_s3_key(s3_key: str) -> dict:
        """
        Парсить S3 ключ та витягує компоненти

        Returns:
            dict: Словник з компонентами ключа
        """
        parts = s3_key.split("/")

        try:
            if len(parts) >= 4 and parts[0] == "users" and parts[2] == "events":
                result = {
                    "user_uuid": parts[1],
                    "event_uuid": parts[3],
                    "type": "event",
                }

                if len(parts) >= 6 and parts[4] == "albums":
                    result.update({"album_uuid": parts[5], "type": "album"})

                    if len(parts) >= 8:
                        result.update(
                            {
                                "file_type": parts[
                                    6
                                ],  # originals, thumbnails, compressed
                                "filename": parts[7],
                                "type": "file",
                            }
                        )

                elif len(parts) >= 6 and parts[4] == "metadata":
                    result.update(
                        {
                            "metadata_type": parts[5].replace(".json", ""),
                            "type": "metadata",
                        }
                    )

                return result

        except (IndexError, ValueError):
            pass

        return {"type": "unknown", "raw_key": s3_key}


class UUIDValidator:
    """Валідатор для UUID полів"""

    @staticmethod
    def is_valid_uuid(uuid_string: str) -> bool:
        """Перевіряє чи є рядок валідним UUID"""
        try:
            uuid.UUID(uuid_string)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_short_uuid(short_uuid: str) -> bool:
        """Перевіряє чи є рядок валідним коротким UUID"""
        try:
            # Перевіряємо що це валідний base62
            base62.decode(short_uuid)
            return len(short_uuid) >= 6  # Мінімальна довжина
        except (ValueError, TypeError):
            return False

    @staticmethod
    def validate_s3_key_structure(s3_key: str) -> bool:
        """Валідує структуру S3 ключа"""
        parsed = S3KeyGenerator.parse_s3_key(s3_key)
        return parsed["type"] != "unknown"


# Utility функції для зручності
def generate_file_uuid() -> str:
    """Генерує UUID для файлу"""
    return str(uuid.uuid4())


def generate_public_id() -> str:
    """Генерує публічний ID для URL"""
    return UUIDMixin.generate_short_uuid()


def generate_s3_structure(user_uuid: str, event_uuid: str) -> dict:
    """Генерує повну S3 структуру для події"""
    return {
        "user_prefix": S3KeyGenerator.generate_user_prefix(user_uuid),
        "event_prefix": S3KeyGenerator.generate_event_prefix(user_uuid, event_uuid),
    }
