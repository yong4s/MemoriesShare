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
from django.utils import timezone

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
    # In-function imports avoid Django app-registry boot ordering issues
    # when this module is imported eagerly at Celery worker startup.
    from apps.shared.container import get_s3_service  # noqa: PLC0415

    if not s3_prefix:
        logger.debug('No s3_prefix supplied for event %s, skipping cleanup', event_uuid)
        return

    s3_service = get_s3_service()
    try:
        s3_service.delete_folder(s3_prefix)
        logger.info('Cleaned up S3 folder for event %s (prefix=%s)', event_uuid, s3_prefix)
    except Exception:
        logger.exception('Failed to clean up S3 folder for event %s', event_uuid)
        raise  # let Celery retry per the decorator policy


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 30},
    retry_backoff=True,
    retry_jitter=True,
)
def recompute_event_statistics_task(self, event_uuid: str) -> None:
    """Re-warm the cached event statistics for ``event_uuid``.

    Dispatched after participant CUD operations to keep the cache hot for
    popular events. Cheap idempotent operation — safe to fire multiple times.
    """
    from apps.shared.container import get_analytics_service  # noqa: PLC0415

    service = get_analytics_service()
    service.warm_event_analytics_cache(event_uuid)
    logger.debug('Warmed analytics cache for event %s', event_uuid)


def _build_event_url(event_uuid: str) -> str | None:
    """Build a frontend link to the event detail page, or None if not configured."""
    base = getattr(settings, 'FRONTEND_URL', None)
    if not base:
        return None
    return f'{base.rstrip("/")}/events/{event_uuid}'


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
    """Render and send the event-invitation email to a participant.

    Idempotent re-runs are safe: re-sending updates ``invitation_sent_at``
    again, but the recipient just gets one extra email per retry. The dispatch
    site (`EventService.add_participant_to_event`) only enqueues once per
    participant creation.
    """
    # In-function imports keep Celery worker boot order safe even if the
    # events app hasn't fully populated when tasks.py is loaded.
    from apps.events.models.event_participant import EventParticipant  # noqa: PLC0415

    try:
        participant = (
            EventParticipant.objects
            .select_related('event', 'user')
            .prefetch_related('event__participants_through__user')
            .get(pk=participant_id)
        )
    except EventParticipant.DoesNotExist:
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
    recipient_name = (
        participant.guest_name
        or getattr(participant.user, 'display_name', '')
        or ''
    ).strip()

    event_date_human = event.date.strftime('%A, %d %b %Y') if event.date else ''
    event_time_human = (
        '' if event.all_day or not event.time else event.time.strftime('%H:%M')
    )

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

    EventParticipant.objects.filter(pk=participant_id).update(
        invitation_sent_at=timezone.now(),
    )
    logger.info(
        'Sent event invitation to %s for event %s (participant %s)',
        recipient_email,
        event.event_uuid,
        participant_id,
    )
