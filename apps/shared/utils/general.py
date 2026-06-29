from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound

from apps.shared.exceptions.exception import UserNotFoundError


def get_client_ip(request) -> str | None:
    """Resolve the client IP, trusting only ``TRUSTED_PROXY_COUNT`` proxies.

    Each proxy appends to ``X-Forwarded-For``, so the rightmost entries are the
    trustworthy ones. With N proxies in front of the app the real client is the
    Nth entry from the right; anything further left is client-supplied and must
    be ignored — otherwise an attacker spoofs the header to dodge IP rate limits.
    Falls back to ``REMOTE_ADDR`` when XFF is absent or shorter than expected.
    """
    num_proxies = getattr(settings, 'TRUSTED_PROXY_COUNT', 1)
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded and num_proxies > 0:
        parts = [part.strip() for part in forwarded.split(',') if part.strip()]
        if len(parts) >= num_proxies:
            return parts[-num_proxies]
    return request.META.get('REMOTE_ADDR')


def get_user_by_id(user_id: int):
    user_model = get_user_model()

    try:
        return user_model.objects.get(pk=user_id)
    except user_model.DoesNotExist:
        raise UserNotFoundError
