"""
API views для роботи з QR-код запрошеннями
"""

from django.http import JsonResponse
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.auth.invite_authentication import create_guest_from_invite
from apps.accounts.auth.invite_authentication import InviteTokenAuthentication
from apps.accounts.auth.invite_authentication import validate_invite_token
from apps.accounts.models import EventInvite
from apps.accounts.utils.qr_utils import generate_invite_qr_code
from apps.events.models import Event
from apps.shared.auth.permissions import HasJWTAuth


@extend_schema(
    summary='Створити запрошення на подію',
    description='Створює QR-код запрошення для конкретної події',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'event_uuid': {'type': 'string', 'description': 'UUID події'},
                'guest_name': {'type': 'string', 'description': "Ім'я гостя (опціонально)"},
                'guest_email': {'type': 'string', 'description': 'Email гостя (опціонально)'},
                'max_uses': {
                    'type': 'integer',
                    'description': 'Максимальна кількість використань (за замовчуванням 1)',
                },
                'expires_in_days': {'type': 'integer', 'description': 'Термін дії в днях (опціонально)'},
                'qr_style': {'type': 'string', 'description': 'Стиль QR-коду: default, rounded, gradient'},
            },
            'required': ['event_uuid'],
        }
    },
)
@api_view(['POST'])
@permission_classes([HasJWTAuth])
def create_invite(request):
    """Створює нове запрошення на подію"""

    event_uuid = request.data.get('event_uuid')
    if not event_uuid:
        return Response({'error': _("event_uuid є обов'язковим параметром")}, status=status.HTTP_400_BAD_REQUEST)

    try:
        event = Event.objects.get(event_uuid=event_uuid)
    except Event.DoesNotExist:
        return Response({'error': _('Подія не знайдена')}, status=status.HTTP_404_NOT_FOUND)

    # Перевіряємо права доступу
    if event.user != request.user:
        return Response(
            {'error': _('У вас немає прав на створення запрошень для цієї події')}, status=status.HTTP_403_FORBIDDEN
        )

    # Отримуємо параметри запрошення
    guest_name = request.data.get('guest_name')
    guest_email = request.data.get('guest_email')
    max_uses = request.data.get('max_uses', 1)
    expires_in_days = request.data.get('expires_in_days')
    qr_style = request.data.get('qr_style', 'default')

    try:
        # Створюємо запрошення
        invite = EventInvite.objects.create_invite(
            event=event, invited_by=request.user, guest_name=guest_name, guest_email=guest_email, max_uses=max_uses
        )

        # Встановлюємо термін дії якщо вказано
        if expires_in_days:
            from django.utils import timezone

            invite.expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
            invite.save()

        # Генеруємо QR-код
        qr_data = generate_invite_qr_code(invite.invite_token, event_name=event.event_name, style=qr_style)

        return Response(
            {
                'invite_id': invite.id,
                'invite_token': invite.invite_token,
                'invite_url': invite.qr_code_data,
                'qr_code': qr_data,
                'event': {'uuid': str(event.event_uuid), 'name': event.event_name, 'date': event.date.isoformat()},
                'guest_name': invite.guest_name,
                'guest_email': invite.guest_email,
                'max_uses': invite.max_uses,
                'expires_at': invite.expires_at.isoformat() if invite.expires_at else None,
                'created_at': invite.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({'error': f'Помилка створення запрошення: {e!s}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary='Перевірити токен запрошення', description='Валідує токен запрошення та повертає інформацію про нього'
)
@api_view(['GET', 'POST'])
@permission_classes([])  # Дозволяємо анонімний доступ
def validate_invite(request, token=None):
    """Перевіряє валідність токена запрошення"""

    # Отримуємо токен з URL або з body
    if not token:
        token = request.data.get('token') or request.GET.get('token')

    if not token:
        return Response({'error': _('Токен запрошення не вказано')}, status=status.HTTP_400_BAD_REQUEST)

    # Валідуємо токен
    validation_result = validate_invite_token(token)

    if validation_result['valid']:
        return Response({'valid': True, 'invite': validation_result})
    else:
        return Response(
            {'valid': False, 'error': validation_result['error'], 'code': validation_result['code']},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(summary='Використати запрошення', description='Активує запрошення та створює анонімного користувача')
@api_view(['POST'])
@permission_classes([])  # Дозволяємо анонімний доступ
def use_invite(request, token=None):
    """Використовує запрошення та створює анонімного користувача"""

    if not token:
        token = request.data.get('token')

    if not token:
        return Response({'error': _('Токен запрошення не вказано')}, status=status.HTTP_400_BAD_REQUEST)

    guest_name = request.data.get('guest_name', '')

    # Створюємо гостя з запрошення
    user, invite = create_guest_from_invite(token, guest_name)

    if not user or not invite:
        return Response(
            {'error': _('Неможливо використати запрошення. Токен може бути невалідним або прострочений.')},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'display_name': user.display_name,
                'is_anonymous_guest': user.is_anonymous_guest,
            },
            'invite': {
                'id': invite.id,
                'token': invite.invite_token,
                'used_count': invite.used_count,
                'remaining_uses': invite.remaining_uses,
            },
            'event': {
                'uuid': str(invite.event.event_uuid),
                'name': invite.event.event_name,
                'date': invite.event.date.isoformat(),
            },
            'auth_token': token,  # Повертаємо токен для подальшої аутентифікації
        }
    )


@extend_schema(
    summary='Отримати інформацію про запрошення події', description='Повертає всі запрошення для конкретної події'
)
@api_view(['GET'])
@permission_classes([HasJWTAuth])
def list_event_invites(request, event_uuid):
    """Повертає список запрошень для події"""

    try:
        event = Event.objects.get(event_uuid=event_uuid)
    except Event.DoesNotExist:
        return Response({'error': _('Подія не знайдена')}, status=status.HTTP_404_NOT_FOUND)

    # Перевіряємо права доступу
    if event.user != request.user:
        return Response(
            {'error': _('У вас немає прав на перегляд запрошень цієї події')}, status=status.HTTP_403_FORBIDDEN
        )

    invites = event.invites.all().order_by('-created_at')

    invites_data = []
    for invite in invites:
        invites_data.append(
            {
                'id': invite.id,
                'token': invite.invite_token,
                'guest_name': invite.guest_name,
                'guest_email': invite.guest_email,
                'is_active': invite.is_active,
                'max_uses': invite.max_uses,
                'used_count': invite.used_count,
                'remaining_uses': invite.remaining_uses,
                'expires_at': invite.expires_at.isoformat() if invite.expires_at else None,
                'last_used_at': invite.last_used_at.isoformat() if invite.last_used_at else None,
                'created_at': invite.created_at.isoformat(),
                'qr_code_url': invite.qr_code_data,
                'guest_user': {'id': invite.guest_user.id, 'display_name': invite.guest_user.display_name}
                if invite.guest_user
                else None,
            }
        )

    return Response(
        {
            'event': {'uuid': str(event.event_uuid), 'name': event.event_name},
            'invites': invites_data,
            'total_count': len(invites_data),
        }
    )


@extend_schema(summary='Деактивувати запрошення', description='Деактивує конкретне запрошення')
@api_view(['DELETE'])
@permission_classes([HasJWTAuth])
def deactivate_invite(request, invite_id):
    """Деактивує запрошення"""

    try:
        invite = EventInvite.objects.get(id=invite_id)
    except EventInvite.DoesNotExist:
        return Response({'error': _('Запрошення не знайдено')}, status=status.HTTP_404_NOT_FOUND)

    # Перевіряємо права доступу
    if invite.invited_by != request.user:
        return Response(
            {'error': _('У вас немає прав на деактивацію цього запрошення')}, status=status.HTTP_403_FORBIDDEN
        )

    invite.deactivate()

    return Response({'success': True, 'message': _('Запрошення успішно деактивовано')})


@extend_schema(
    summary='Генерувати QR-код для існуючого запрошення', description='Повертає QR-код для існуючого запрошення'
)
@api_view(['GET'])
@permission_classes([HasJWTAuth])
def generate_qr_for_invite(request, invite_id):
    """Генерує QR-код для існуючого запрошення"""

    try:
        invite = EventInvite.objects.get(id=invite_id)
    except EventInvite.DoesNotExist:
        return Response({'error': _('Запрошення не знайдено')}, status=status.HTTP_404_NOT_FOUND)

    # Перевіряємо права доступу
    if invite.invited_by != request.user:
        return Response({'error': _('У вас немає прав на це запрошення')}, status=status.HTTP_403_FORBIDDEN)

    style = request.GET.get('style', 'default')
    size = int(request.GET.get('size', 10))

    # Генеруємо QR-код
    qr_data = generate_invite_qr_code(invite.invite_token, event_name=invite.event.event_name, style=style, size=size)

    if not qr_data:
        return Response({'error': _('Помилка генерації QR-коду')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'invite_id': invite.id, 'qr_code': qr_data})


# Utility view для отримання поточного користувача через токен
@extend_schema(
    summary='Отримати інформацію про поточного користувача',
    description='Повертає інформацію про користувача аутентифікованого через токен запрошення',
)
@api_view(['GET'])
@permission_classes([])  # Дозволяємо анонімний доступ
def current_user_info(request):
    """Повертає інформацію про поточного користувача"""

    # Спробуємо аутентифікувати через токен запрошення
    auth = InviteTokenAuthentication()
    auth_result = auth.authenticate(request)

    if auth_result:
        user, invite = auth_result
        return Response(
            {
                'authenticated': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'display_name': user.display_name,
                    'is_anonymous_guest': user.is_anonymous_guest,
                },
                'invite': {'token': invite.invite_token, 'remaining_uses': invite.remaining_uses},
                'event': {
                    'uuid': str(invite.event.event_uuid),
                    'name': invite.event.event_name,
                    'date': invite.event.date.isoformat(),
                },
            }
        )

    return Response({'authenticated': False, 'error': _('Не аутентифіковано')}, status=status.HTTP_401_UNAUTHORIZED)
