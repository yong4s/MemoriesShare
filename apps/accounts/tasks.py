import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from settings.celery import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True,
    retry_jitter=True,
)
def send_verification_code_task(self, email: str, code: str, expiry_minutes: int = 10):
    """
    Send verification code email with HTML template
    
    Args:
        email: Recipient email address
        code: 6-digit verification code
        expiry_minutes: Code expiration time in minutes
    """
    try:
        logger.info(f'Sending verification code email to {email}')

        context = {
            'code': code,
            'email': email,
            'expiry_minutes': expiry_minutes,
            'app_name': 'MediaFlow',
            'site_url': getattr(settings, 'SITE_URL', 'https://mediaflow.com'),
        }

        html_content = render_to_string('emails/verification_code.html', context)
        text_content = render_to_string('emails/verification_code.txt', context)

        subject = f'{getattr(settings, "EMAIL_SUBJECT_PREFIX", "[MediaFlow]")} Код входу'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mediaflow.com')

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[email],
        )

        email_message.attach_alternative(html_content, "text/html")

        result = email_message.send()
        
        if result == 1:
            logger.info(f'Verification code email sent successfully to {email}')
            return {'success': True, 'email': email, 'message': 'Email sent successfully'}
        else:
            logger.error(f'Failed to send verification code email to {email}')
            raise Exception(f'Email send failed for {email}')
            
    except Exception as e:
        logger.exception(f'Error sending verification code email to {email}: {e}')

        if self.request.retries >= self.max_retries:
            logger.error(f'Final retry failed for verification code email to {email}')
            
        raise  # Re-raise to trigger Celery retry mechanism
