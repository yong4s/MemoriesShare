"""
Albums Services Package

Цей пакет містить всі сервіси для роботи з альбомами:
- AlbumService: Основний сервіс для CRUD операцій з альбомами
"""

# Імпорти для зворотної сумісності
from .album_service import AlbumService

# Експортуємо для зручності
__all__ = [
    "AlbumService",
]
