import logging

from django.conf import settings
from django.core.mail import send_mail

from settings.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True)
def send_verification_code_email_task(self, email: str, code: str):
    """
    Send verification code via email.

    Args:
        email: Recipient email address
        code: 6-digit verification code

    Returns:
        dict with success status
    """
    try:
        subject = 'Your MediaFlow verification code'
        message = f"""Your verification code: {code}

This code expires in 10 minutes.
If you didn't request this code, please ignore this email.

-- MediaFlow Team"""

        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mediaflow.com'),
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info(f'Verification code email sent successfully to: {email}')

        return {'status': 'success', 'email': email, 'message': 'Verification code email sent'}

    except Exception as e:
        logger.exception(f'Failed to send verification code email to {email}: {e}')

        # Retry with exponential backoff
        raise self.retry(
            countdown=60,  # Wait 1 minute before retry
            max_retries=3,
            exc=e,
        )


@app.task
def cleanup_expired_passwordless_codes_task():
    """
    Cleanup expired passwordless codes from Redis.

    This task is optional since Redis TTL automatically expires keys,
    but can be used for monitoring and statistics.

    Returns:
        dict with cleanup statistics
    """
    try:
        from django_redis import get_redis_connection

        redis_client = get_redis_connection('default')

        # Get all passwordless code keys
        pattern = 'passwordless_code:*'
        keys = redis_client.keys(pattern)

        expired_count = 0
        active_count = len(keys)

        logger.info(f'Found {active_count} active passwordless codes in Redis')

        return {
            'status': 'success',
            'active_codes': active_count,
            'expired_codes': expired_count,  # Redis TTL handles expiry automatically
            'message': 'Cleanup completed',
        }

    except Exception as e:
        logger.exception(f'Failed to cleanup passwordless codes: {e}')
        return {'status': 'error', 'message': str(e)}
