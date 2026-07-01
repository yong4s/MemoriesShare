"""Best-effort secret redaction for log messages and outbound error strings.

Defense-in-depth only: never rely on this for authorization decisions. The goal
is to keep invite tokens, signed-token blobs, and similar sensitive substrings
out of log aggregators and 4xx response bodies when an internal exception is
echoed.
"""

import re

_UUID_RE = re.compile(
    r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b',
)
_TOKEN_KV_RE = re.compile(
    r'(?P<key>(?:invite_token|invite_token_used|signed_token|token))'
    r'(?P<sep>\s*[:=]\s*[\'"]?)'
    r'(?P<value>[A-Za-z0-9._\-:]+)',
    flags=re.IGNORECASE,
)
_REDACTED = '<redacted>'


def redact_secrets(text: str) -> str:
    """Strip token-shaped substrings from ``text``.

    Catches: ``invite_token=...``, ``token: '...'``, ``signed_token = ...``, and
    any standalone UUID. Errors and odd inputs return the original text — this
    helper must never raise.
    """
    if not text:
        return text
    try:
        cleaned = _TOKEN_KV_RE.sub(lambda m: f'{m.group('key')}{m.group('sep')}{_REDACTED}', text)
        return _UUID_RE.sub(_REDACTED, cleaned)
    except (TypeError, ValueError):
        return text
