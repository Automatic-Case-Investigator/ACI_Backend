from __future__ import annotations

from datetime import datetime, timezone

from django.utils import timezone as django_timezone

MAX_NOTE_LENGTH = 4000


def now_iso() -> str:
    return django_timezone.now().isoformat().replace("+00:00", "Z")


def to_int(value):
    try:
        if isinstance(value, bool):
            return None
        return int(str(value))
    except (TypeError, ValueError):
        return None


def trim_text(value: str | None, limit: int = MAX_NOTE_LENGTH) -> str:
    if value is None:
        return ""
    return str(value).strip()[:limit]


def parse_iso_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_webhook_timestamp(timestamp_header: str) -> int | None:
    value = to_int(timestamp_header)
    if value is None:
        return None
    return value // 1000 if value > 10_000_000_000 else value
