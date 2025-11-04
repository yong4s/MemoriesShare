"""
Shared models for the application
"""

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """Base model with created_at and updated_at fields"""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BlacklistedToken(BaseModel):
    """
    Model to store blacklisted JWT tokens
    Used for logout functionality and token invalidation
    """

    jti = models.CharField(max_length=255, unique=True, help_text='JWT ID (jti claim)')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, help_text='User who owns this token')
    token_type = models.CharField(
        max_length=20,
        choices=[
            ('access', 'Access Token'),
            ('refresh', 'Refresh Token'),
        ],
        default='access',
    )
    expires_at = models.DateTimeField(help_text='When this token expires')
    blacklisted_at = models.DateTimeField(auto_now_add=True, help_text='When this token was blacklisted')
    reason = models.CharField(
        max_length=100, default='logout', help_text='Reason for blacklisting (logout, security, etc.)'
    )

    class Meta:
        db_table = 'shared_blacklisted_tokens'
        indexes = [
            models.Index(fields=['jti']),
            models.Index(fields=['user', 'token_type']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'Blacklisted {self.token_type} token for {self.user.email}'

    @classmethod
    def is_blacklisted(cls, jti):
        """Check if a token is blacklisted by JTI"""
        return cls.objects.filter(jti=jti).exists()

    @classmethod
    def cleanup_expired(cls):
        """Remove expired blacklisted tokens from database"""
        from django.utils import timezone

        expired_tokens = cls.objects.filter(expires_at__lt=timezone.now())
        count = expired_tokens.count()
        expired_tokens.delete()
        return count


class UserSession(BaseModel):
    """
    Track user sessions for JWT tokens
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    refresh_token_jti = models.CharField(max_length=255, unique=True)
    device_info = models.TextField(blank=True, help_text='User agent, IP, etc.')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'shared_user_sessions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['refresh_token_jti']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f'Session for {self.user.email} from {self.ip_address}'

    def invalidate(self):
        """Invalidate this session"""
        self.is_active = False
        self.save()

    @classmethod
    def cleanup_expired(cls):
        """Remove expired sessions"""
        from django.utils import timezone

        expired_sessions = cls.objects.filter(expires_at__lt=timezone.now())
        count = expired_sessions.count()
        expired_sessions.delete()
        return count
