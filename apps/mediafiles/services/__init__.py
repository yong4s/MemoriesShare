"""
MediaFiles Services Package

Цей пакет містить всі сервіси для роботи з медіафайлами:
- MediafileService: Основний сервіс для CRUD операцій з медіафайлами
"""

# Імпорти для зворотної сумісності
from .mediafile_service import MediafileService

# Експортуємо для зручності
__all__ = [
    'MediafileService',
]
