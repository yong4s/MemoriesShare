"""
Utility для генерації QR-кодів для запрошень
"""

import base64
import io
from typing import Any
from typing import Dict
from typing import Optional

try:
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.colorfills import SquareGradientColorFill
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer

    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

from django.conf import settings


class QRCodeGenerator:
    """Генератор QR-кодів для запрошень на події"""

    def __init__(self):
        if not QR_AVAILABLE:
            raise ImportError('QR код бібліотеки не встановлені. ' 'Встановіть: pip install qrcode[pil] pillow')

    def generate_invite_qr(
        self, invite_token: str, event_name: str = None, style: str = 'default', size: int = 10
    ) -> dict[str, Any]:
        """
        Генерує QR-код для запрошення

        Args:
            invite_token: Токен запрошення
            event_name: Назва події (для відображення)
            style: Стиль QR-коду ("default", "rounded", "gradient")
            size: Розмір QR-коду (1-40)

        Returns:
            Dict з даними QR-коду (base64 image, URL, etc.)
        """
        # Формуємо URL для запрошення
        base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        invite_url = f'{base_url}/invite/{invite_token}'

        # Створюємо QR-код
        qr = qrcode.QRCode(
            version=1,  # Автоматично підбирає розмір
            error_correction=qrcode.constants.ERROR_CORRECT_M,  # 15% помилок
            box_size=size,
            border=4,
        )

        qr.add_data(invite_url)
        qr.make(fit=True)

        # Генеруємо зображення в залежності від стилю
        if style == 'rounded':
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                fill_color='black',
                back_color='white',
            )
        elif style == 'gradient':
            img = qr.make_image(image_factory=StyledPilImage, color_mask=SquareGradientColorFill(), back_color='white')
        else:
            # Звичайний стиль
            img = qr.make_image(fill_color='black', back_color='white')

        # Конвертуємо в base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return {
            'qr_code_base64': img_base64,
            'qr_code_data_url': f'data:image/png;base64,{img_base64}',
            'invite_url': invite_url,
            'invite_token': invite_token,
            'event_name': event_name,
            'style': style,
            'size': size,
        }

    def generate_event_qr(self, event_uuid: str, event_name: str = None, style: str = 'default') -> dict[str, Any]:
        """
        Генерує QR-код для події (загальний доступ)

        Args:
            event_uuid: UUID події
            event_name: Назва події
            style: Стиль QR-коду

        Returns:
            Dict з даними QR-коду
        """
        base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        event_url = f'{base_url}/event/{event_uuid}'

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )

        qr.add_data(event_url)
        qr.make(fit=True)

        if style == 'rounded':
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                fill_color='black',
                back_color='white',
            )
        else:
            img = qr.make_image(fill_color='black', back_color='white')

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return {
            'qr_code_base64': img_base64,
            'qr_code_data_url': f'data:image/png;base64,{img_base64}',
            'event_url': event_url,
            'event_uuid': event_uuid,
            'event_name': event_name,
            'style': style,
        }


def generate_invite_qr_code(invite_token: str, **kwargs) -> dict[str, Any] | None:
    """
    Зручна функція для генерації QR-коду запрошення

    Args:
        invite_token: Токен запрошення
        **kwargs: Додаткові параметри для QRCodeGenerator.generate_invite_qr

    Returns:
        Dict з даними QR-коду або None якщо помилка
    """
    try:
        generator = QRCodeGenerator()
        return generator.generate_invite_qr(invite_token, **kwargs)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f'Помилка генерації QR-коду: {e}')
        return None


def generate_event_qr_code(event_uuid: str, **kwargs) -> dict[str, Any] | None:
    """
    Зручна функція для генерації QR-коду події

    Args:
        event_uuid: UUID події
        **kwargs: Додаткові параметри для QRCodeGenerator.generate_event_qr

    Returns:
        Dict з даними QR-коду або None якщо помилка
    """
    try:
        generator = QRCodeGenerator()
        return generator.generate_event_qr(event_uuid, **kwargs)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f'Помилка генерації QR-коду події: {e}')
        return None


# Простий fallback для випадків коли qrcode не встановлений
class FallbackQRGenerator:
    """Fallback генератор QR-кодів без зображень"""

    @staticmethod
    def generate_invite_data(invite_token: str, event_name: str = None) -> dict[str, Any]:
        """Генерує дані запрошення без QR-коду"""
        base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        invite_url = f'{base_url}/invite/{invite_token}'

        return {
            'qr_code_base64': None,
            'qr_code_data_url': None,
            'invite_url': invite_url,
            'invite_token': invite_token,
            'event_name': event_name,
            'fallback': True,
            'message': 'QR-код недоступний. Використовуйте URL для запрошення.',
        }


# Автоматичний вибір генератора
if QR_AVAILABLE:
    default_generator = QRCodeGenerator()
else:
    default_generator = FallbackQRGenerator()
