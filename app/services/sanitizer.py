import re
from typing import Optional


_SQL_META_PATTERN = re.compile(r"(--|;|/\*|\*/|xp_|execute\s|exec\s|drop\s|insert\s|delete\s|update\s)", re.IGNORECASE)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]\s*")


def sanitize_text(value: Optional[str], max_length: Optional[int] = None) -> str:
    """Sanitize user supplied text to reduce risk of SQL injection payloads.

    The function removes control characters, trims leading/trailing whitespace,
    and strips common SQL meta tokens. It also optionally enforces a maximum
    length to avoid oversized payloads that could be used for DoS attempts.
    """
    if not value:
        return ""

    cleaned = _CONTROL_CHARS.sub(" ", value)
    cleaned = cleaned.strip()
    cleaned = _SQL_META_PATTERN.sub("", cleaned)

    if max_length is not None:
        cleaned = cleaned[:max_length]

    return cleaned
