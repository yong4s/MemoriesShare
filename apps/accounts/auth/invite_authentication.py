"""
Аутентифікація через QR-код токени запрошень
"""

from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.utils.translation import gettext as _
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.models import EventInvite
from apps.accounts.models import User


class InviteTokenAuthentication(BaseAuthentication):
    """
    Аутентифікація через токен запрошення

    Шукає токен в:
    1. Authorization: Bearer <token>
    2. X-Invite-Token: <token>
    3. invite_token в GET/POST параметрах
    """

    def authenticate(self, request):
        """Перевіряє токен запрошення та аутентифікує користувача"""

        token = self._get_token_from_request(request)
        if not token:
            return None

        # Знаходимо валідне запрошення
        invite = EventInvite.objects.get_valid_invite(token)
        if not invite:
            return None

        # Перевіряємо чи токен вже використаний користувачем
        if invite.guest_user:
            user = invite.guest_user
        else:
            # Створюємо анонімного користувача
            guest_name = request.data.get('guest_name') or invite.guest_name
            user = User.create_anonymous_guest(invite_token=token, guest_name=guest_name)

            # Зв'язуємо запрошення з користувачем
            invite.use_invite(user)

        return (user, invite)

    def _get_token_from_request(self, request):
        """Витягує токен з різних місць в запиті"""

        # 1. Authorization header: Bearer <token>
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]

        # 2. Custom header: X-Invite-Token
        token = request.META.get('HTTP_X_INVITE_TOKEN')
        if token:
            return token

        # 3. GET parameters
        token = request.GET.get('invite_token')
        if token:
            return token

        # 4. POST parameters
        if hasattr(request, 'data') and request.data:
            token = request.data.get('invite_token')
            if token:
                return token

        return None

    def authenticate_header(self, request):
        """Повертає header для WWW-Authenticate"""
        return 'Bearer realm="api"'


class InviteTokenMiddleware:
    """
    Middleware для автоматичної аутентифікації через токени запрошень
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Перевіряємо чи є токен запрошення
        token = self._get_invite_token(request)

        if token and isinstance(request.user, AnonymousUser):
            # Спробуємо аутентифікувати через токен
            auth = InviteTokenAuthentication()
            try:
                auth_result = auth.authenticate(request)
                if auth_result:
                    user, invite = auth_result
                    request.user = user
                    request.invite = invite

                    # Додаємо інформацію про подію до запиту
                    request.event = invite.event

            except Exception as e:
                # Логуємо помилку але не ламаємо запит
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f'Помилка аутентифікації через токен: {e}')

        response = self.get_response(request)
        return response

    def _get_invite_token(self, request):
        """Витягує токен запрошення з запиту"""
        # Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]

        # Custom header
        token = request.META.get('HTTP_X_INVITE_TOKEN')
        if token:
            return token

        # URL parameters
        token = request.GET.get('invite_token')
        if token:
            return token

        return None


def require_valid_invite(view_func):
    """
    Декоратор для перевірки валідного запрошення

    Використання:
    @require_valid_invite
    def my_view(request):
        # request.user буде анонімним гостем
        # request.invite буде EventInvite об'єктом
        # request.event буде Event об'єктом
        pass
    """
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Перевіряємо чи користувач аутентифікований через запрошення
        if not hasattr(request, 'invite'):
            return JsonResponse(
                {'error': _('Необхідний валідний токен запрошення'), 'code': 'invalid_invite_token'}, status=401
            )

        if not request.invite.is_valid:
            return JsonResponse({'error': _('Запрошення більше не дійсне'), 'code': 'expired_invite_token'}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper


class InvitePermission:
    """
    Permission клас для перевірки доступу через запрошення
    """

    def has_permission(self, request, view):
        """Перевіряє чи користувач має доступ через запрошення"""

        # Якщо користувач вже аутентифікований - дозволяємо
        if request.user.is_authenticated and not request.user.is_anonymous_guest:
            return True

        # Перевіряємо наявність валідного запрошення
        if hasattr(request, 'invite') and request.invite.is_valid:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        """Перевіряє доступ до конкретного об'єкта"""

        # Для власників завжди дозволяємо
        if hasattr(obj, 'user') and obj.user == request.user:
            return True

        # Для гостей перевіряємо чи об'єкт належить до події з запрошення
        if hasattr(request, 'invite') and hasattr(obj, 'event'):
            return obj.event == request.invite.event

        return False


# Utility функції
def get_user_from_invite_token(token: str):
    """
    Отримує користувача за токеном запрошення

    Args:
        token: Токен запрошення

    Returns:
        User об'єкт або None
    """
    try:
        invite = EventInvite.objects.get_valid_invite(token)
        if invite and invite.guest_user:
            return invite.guest_user
    except Exception:
        pass
    return None


def create_guest_from_invite(token: str, guest_name: str = None):
    """
    Створює анонімного гостя з токена запрошення

    Args:
        token: Токен запрошення
        guest_name: Ім'я гостя

    Returns:
        Tuple (User, EventInvite) або (None, None)
    """
    try:
        invite = EventInvite.objects.get_valid_invite(token)
        if not invite:
            return None, None

        # Якщо запрошення вже використано
        if invite.guest_user:
            return invite.guest_user, invite

        # Створюємо нового анонімного користувача
        user = User.create_anonymous_guest(invite_token=token, guest_name=guest_name or invite.guest_name)

        # Позначаємо запрошення як використане
        invite.use_invite(user)

        return user, invite

    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f'Помилка створення гостя з запрошення: {e}')
        return None, None


def validate_invite_token(token: str):
    """
    Валідує токен запрошення

    Args:
        token: Токен для перевірки

    Returns:
        Dict з інформацією про валідність
    """
    try:
        invite = EventInvite.objects.get_valid_invite(token)

        if not invite:
            return {'valid': False, 'error': 'Невалідний або прострочений токен запрошення', 'code': 'invalid_token'}

        return {
            'valid': True,
            'invite_id': invite.id,
            'event_name': invite.event.event_name,
            'event_uuid': str(invite.event.event_uuid),
            'guest_name': invite.guest_name,
            'remaining_uses': invite.remaining_uses,
            'expires_at': invite.expires_at.isoformat() if invite.expires_at else None,
        }

    except Exception as e:
        return {'valid': False, 'error': f'Помилка перевірки токена: {e!s}', 'code': 'validation_error'}
