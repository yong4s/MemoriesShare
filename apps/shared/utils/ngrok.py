"""Ngrok tunnel URL resolver for development environment."""

import json
import logging
import time
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

_cached_ngrok_url: str | None = None
_cache_timestamp: float = 0.0
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_ngrok_public_url() -> str | None:
    """Fetch the public ngrok URL from the ngrok agent API.

    Returns the HTTPS public URL if available, or None if ngrok is not running.
    Results are cached for 5 minutes to avoid excessive API calls.
    """
    global _cached_ngrok_url, _cache_timestamp

    if _cached_ngrok_url and (time.time() - _cache_timestamp) < CACHE_TTL_SECONDS:
        return _cached_ngrok_url

    ngrok_api_url = getattr(settings, 'NGROK_API_URL', 'http://ngrok:4040')
    try:
        req = urllib.request.Request(f'{ngrok_api_url}/api/tunnels', method='GET')
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            tunnels = data.get('tunnels', [])

        for tunnel in tunnels:
            if tunnel.get('proto') == 'https':
                _cached_ngrok_url = tunnel['public_url']
                _cache_timestamp = time.time()
                logger.info('Resolved ngrok public URL: %s', _cached_ngrok_url)
                return _cached_ngrok_url

        if tunnels:
            _cached_ngrok_url = tunnels[0].get('public_url')
            _cache_timestamp = time.time()
            logger.info('Resolved ngrok public URL (fallback): %s', _cached_ngrok_url)
            return _cached_ngrok_url

    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError, IndexError):
        logger.debug('Ngrok API not available at %s', ngrok_api_url)

    return None
