"""
Сервіси для роботи з запрошеннями
"""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.accounts.models import EventInvite
from apps.accounts.models import User
from apps.accounts.utils.qr_utils import generate_invite_qr_code
from apps.events.models import Event


class InviteService:
    """Сервіс для роботи з запрошеннями"""

    @staticmethod
    def create_and_send_invite(
        event_uuid: str,
        invited_by_user: User,
        guest_name: str,
        guest_email: str,
        max_uses: int = 1,
        expires_in_days: int | None = None,
        send_email: bool = True,
        qr_style: str = 'default',
    ) -> dict[str, Any]:
        """
        Створює запрошення та надсилає його гостю

        Args:
            event_uuid: UUID події
            invited_by_user: Користувач який створює запрошення
            guest_name: Ім'я гостя
            guest_email: Email гостя
            max_uses: Максимальна кількість використань
            expires_in_days: Термін дії в днях
            send_email: Чи надсилати email
            qr_style: Стиль QR-коду

        Returns:
            Dict з результатом операції
        """
        try:
            # Отримуємо подію та перевіряємо права через EventParticipant
            event = Event.objects.get(event_uuid=event_uuid)
            
            # Перевіряємо, чи користувач є власником події
            from apps.events.models.event_participant import EventParticipant
            if not EventParticipant.objects.filter(
                event=event, 
                user=invited_by_user, 
                role=EventParticipant.Role.OWNER
            ).exists():
                raise Event.DoesNotExist("No permission to invite")

            # Створюємо запрошення
            invite = EventInvite.objects.create_invite(
                event=event,
                invited_by=invited_by_user,
                guest_name=guest_name,
                guest_email=guest_email,
                max_uses=max_uses,
            )

            # Встановлюємо термін дії
            if expires_in_days:
                invite.expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
                invite.save()

            # Генеруємо QR-код
            qr_data = generate_invite_qr_code(invite.invite_token, event_name=event.event_name, style=qr_style)

            result = {
                'success': True,
                'invite': {
                    'id': invite.id,
                    'token': invite.invite_token,
                    'url': invite.qr_code_data,
                    'guest_name': invite.guest_name,
                    'guest_email': invite.guest_email,
                    'expires_at': invite.expires_at.isoformat() if invite.expires_at else None,
                    'remaining_uses': invite.remaining_uses,
                },
                'event': {'name': event.event_name, 'date': event.date.isoformat(), 'uuid': str(event.event_uuid)},
                'qr_data': qr_data,
                'email_sent': False,
            }

            # Надсилаємо email якщо потрібно
            if send_email and guest_email:
                email_result = InviteService.send_invite_email(invite=invite, qr_data=qr_data)
                result['email_sent'] = email_result['success']
                result['email_error'] = email_result.get('error')

            return result

        except Event.DoesNotExist:
            return {'success': False, 'error': 'Подія не знайдена або у вас немає прав'}
        except Exception as e:
            return {'success': False, 'error': f'Помилка створення запрошення: {e!s}'}

    @staticmethod
    def send_invite_email(invite: EventInvite, qr_data: dict | None = None) -> dict[str, Any]:
        """
        Надсилає email з запрошенням

        Args:
            invite: Об'єкт запрошення
            qr_data: Дані QR-коду (опціонально)

        Returns:
            Dict з результатом надсилання
        """
        try:
            subject = f'Запрошення на подію: {invite.event.event_name}'

            # Контекст для шаблону email
            context = {
                'invite': invite,
                'event': invite.event,
                'guest_name': invite.guest_name,
                'invite_url': invite.qr_code_data,
                'qr_data': qr_data,
                'expires_at': invite.expires_at,
                'remaining_uses': invite.remaining_uses,
            }

            # Генеруємо HTML та текстову версію
            html_message = InviteService._generate_invite_email_html(context)
            text_message = InviteService._generate_invite_email_text(context)

            # Надсилаємо email
            send_mail(
                subject=subject,
                message=text_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=[invite.guest_email],
                html_message=html_message,
                fail_silently=False,
            )

            return {'success': True, 'message': f'Email надіслано на {invite.guest_email}'}

        except Exception as e:
            return {'success': False, 'error': f'Помилка надсилання email: {e!s}'}

    @staticmethod
    def _generate_invite_email_html(context: dict) -> str:
        """Генерує HTML версію email запрошення"""
        invite = context['invite']
        event = context['event']
        qr_data = context.get('qr_data')

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Запрошення на подію</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; color: #333; }}
                .invite-card {{ background: #f9f9f9; padding: 20px; border-radius: 10px; max-width: 600px; }}
                .event-name {{ color: #2196F3; font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
                .invite-url {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .qr-code {{ text-align: center; margin: 20px 0; }}
                .details {{ margin: 15px 0; }}
                .footer {{ color: #666; font-size: 12px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="invite-card">
                <h1>🎉 Запрошення на подію</h1>
                
                <div class="event-name">{event.event_name}</div>
                
                <div class="details">
                    <p><strong>Вітаємо, {invite.guest_name or 'Гість'}!</strong></p>
                    <p>Ви запрошені на подію <strong>{event.event_name}</strong></p>
                    <p><strong>Дата:</strong> {event.date.strftime('%d.%m.%Y')}</p>
                </div>
                
                <div class="invite-url">
                    <p><strong>Посилання для входу:</strong></p>
                    <a href="{invite.qr_code_data}">{invite.qr_code_data}</a>
                </div>
        """

        if qr_data and qr_data.get('qr_code_data_url'):
            html += f"""
                <div class="qr-code">
                    <p><strong>QR-код для швидкого доступу:</strong></p>
                    <img src="{qr_data['qr_code_data_url']}" alt="QR-код запрошення" style="max-width: 200px;">
                </div>
            """

        if invite.expires_at:
            html += f"""
                <div class="details">
                    <p><strong>⏰ Термін дії:</strong> до {invite.expires_at.strftime('%d.%m.%Y %H:%M')}</p>
                </div>
            """

        if invite.max_uses > 1:
            html += f"""
                <div class="details">
                    <p><strong>🔄 Використань:</strong> {invite.remaining_uses} з {invite.max_uses}</p>
                </div>
            """

        html += """
                <div class="footer">
                    <p>Це автоматичне повідомлення. Будь ласка, не відповідайте на нього.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    @staticmethod
    def _generate_invite_email_text(context: dict) -> str:
        """Генерує текстову версію email запрошення"""
        invite = context['invite']
        event = context['event']

        text = f"""
Запрошення на подію: {event.event_name}

Вітаємо, {invite.guest_name or 'Гість'}!

Ви запрошені на подію "{event.event_name}"
Дата: {event.date.strftime('%d.%m.%Y')}

Посилання для входу:
{invite.qr_code_data}
"""

        if invite.expires_at:
            text += f"\\nТермін дії: до {invite.expires_at.strftime('%d.%m.%Y %H:%M')}"

        if invite.max_uses > 1:
            text += f'\\nВикористань: {invite.remaining_uses} з {invite.max_uses}'

        text += '\\n\\n---\\nЦе автоматичне повідомлення. Будь ласка, не відповідайте на нього.'

        return text

    @staticmethod
    def bulk_create_invites(
        event_uuid: str,
        invited_by_user: User,
        guests: list[dict[str, str]],
        default_max_uses: int = 1,
        expires_in_days: int | None = None,
        send_emails: bool = True,
    ) -> dict[str, Any]:
        """
        Створює запрошення для багатьох гостей одночасно

        Args:
            event_uuid: UUID події
            invited_by_user: Користувач який створює запрошення
            guests: Список гостей [{'name': 'Ім'я', 'email': 'email@example.com'}, ...]
            default_max_uses: Стандартна кількість використань
            expires_in_days: Термін дії
            send_emails: Чи надсилати emails

        Returns:
            Dict з результатами для всіх гостей
        """
        results = {'success_count': 0, 'error_count': 0, 'results': []}

        for guest_data in guests:
            result = InviteService.create_and_send_invite(
                event_uuid=event_uuid,
                invited_by_user=invited_by_user,
                guest_name=guest_data.get('name', ''),
                guest_email=guest_data.get('email', ''),
                max_uses=guest_data.get('max_uses', default_max_uses),
                expires_in_days=expires_in_days,
                send_email=send_emails,
            )

            results['results'].append({'guest': guest_data, 'result': result})

            if result['success']:
                results['success_count'] += 1
            else:
                results['error_count'] += 1

        return results
