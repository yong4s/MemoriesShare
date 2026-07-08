"""Celery tasks for the events domain.

Anything that does heavy I/O (S3 delete, mail, analytics recompute) should run
here, not on the request thread. Tasks are dispatched from services via
``transaction.on_commit(lambda: <task>.delay(...))`` so they fire only after
the originating DB transaction commits — never on rollback.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.events.dal.event_participant_dal import EventParticipantDAL
from apps.shared.storage.optimized_s3_service import get_optimized_s3_service
from settings.celery import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5, 'countdown': 30},
    retry_backoff=True,
    retry_jitter=True,
)
def cleanup_event_s3_prefix_task(self, s3_prefix: str, event_uuid: str) -> None:
    """Delete an event's S3 folder asynchronously.

    Dispatched after a successful event-deletion commit. Idempotent: if the
    folder is already gone, the underlying delete is a no-op.
    """
    if not s3_prefix:
        logger.debug('No s3_prefix supplied for event %s, skipping cleanup', event_uuid)
        return

    s3_service = get_optimized_s3_service()
    try:
        s3_service.delete_folder(s3_prefix)
        logger.info('Cleaned up S3 folder for event %s (prefix=%s)', event_uuid, s3_prefix)
    except Exception:
        logger.exception('Failed to clean up S3 folder for event %s', event_uuid)
        raise  # let Celery retry per the decorator policy


def _build_event_url(event_uuid: str) -> str | None:
    """Build a frontend link to the event detail page, or None if not configured."""
    base = getattr(settings, 'FRONTEND_URL', None)
    if not base:
        return None
    return f'{base.rstrip('/')}/events/{event_uuid}'


def _resolve_organizer_name(event) -> str:
    """Best-effort organizer display name from the OWNER participant."""
    owner = next(
        (p for p in event.participants_through.all() if p.role == 'OWNER'),
        None,
    )
    if not owner:
        return ''
    if owner.user and getattr(owner.user, 'display_name', None):
        return owner.user.display_name
    return owner.guest_name or ''


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_jitter=True,
)
def send_event_invitation_task(self, participant_id: int) -> None:
    """Render and send the event-invitation email to a participant."""
    dal = EventParticipantDAL()
    participant = dal.get_participant_for_invitation(participant_id)
    if participant is None:
        logger.warning('send_event_invitation: participant %s no longer exists', participant_id)
        return

    recipient_email = participant.guest_email or getattr(participant.user, 'email', '') or ''
    recipient_email = recipient_email.strip()
    if not recipient_email:
        logger.info(
            'send_event_invitation: participant %s has no email, skipping',
            participant_id,
        )
        return

    event = participant.event
    recipient_name = (participant.guest_name or getattr(participant.user, 'display_name', '') or '').strip()

    event_date_human = event.date.strftime('%A, %d %b %Y') if event.date else ''
    event_time_human = '' if event.all_day or not event.time else event.time.strftime('%H:%M')

    context = {
        'app_name': 'MediaFlow',
        'site_url': getattr(settings, 'SITE_URL', ''),
        'event_url': _build_event_url(str(event.event_uuid)),
        'event_name': event.event_name,
        'event_date_human': event_date_human,
        'event_time_human': event_time_human,
        'all_day': event.all_day,
        'location': event.location or '',
        'address': event.address or '',
        'description': event.description or '',
        'organizer_name': _resolve_organizer_name(event),
        'recipient_name': recipient_name,
        'recipient_email': recipient_email,
    }

    html_body = render_to_string('emails/event_invitation.html', context)
    text_body = render_to_string('emails/event_invitation.txt', context)

    subject_prefix = getattr(settings, 'EMAIL_SUBJECT_PREFIX', '[MediaFlow]')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mediaflow.com')
    subject = f"{subject_prefix} You're invited to {event.event_name}"

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[recipient_email],
    )
    message.attach_alternative(html_body, 'text/html')
    sent = message.send()

    if sent != 1:
        logger.error(
            'send_event_invitation: send() returned %s for participant %s',
            sent,
            participant_id,
        )
        # Force a Celery retry — the decorator's autoretry_for catches Exception.
        msg = f'Email backend reported send=={sent} for participant {participant_id}'
        raise RuntimeError(msg)

    dal.mark_invitation_sent(participant_id)
    logger.info(
        'Sent event invitation to %s for event %s (participant %s)',
        recipient_email,
        event.event_uuid,
        participant_id,
    )
