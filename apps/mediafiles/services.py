"""
MediaFiles Services Package

Для зворотної сумісності всі сервіси доступні через цей файл.
Нова архітектура розділяє сервіси на окремі модулі:
- MediafileService: apps.mediafiles.services.mediafile_service

Цей файл тепер слугує тільки для зворотної сумісності.
Всі класи перенесено в окремі модулі в папці services/
Для нового коду використовуйте прямі імпорти з відповідних модулів.
"""

# Імпорти для зворотної сумісності
from .services.mediafile_service import MediafileService

# Експортуємо для зручності
__all__ = [
    "MediafileService",
]
