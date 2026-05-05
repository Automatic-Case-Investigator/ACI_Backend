import json
import logging
import time
from typing import Any

from django.conf import settings

from ACI_Backend.objects.redis_client.redis_client import redis_client


_CACHE_KEY_PREFIX = "siem_schema"
logger = logging.getLogger(__name__)


def _payload_key(siem_id: int) -> str:
    return f"{_CACHE_KEY_PREFIX}:{siem_id}:payload"


def _updated_at_key(siem_id: int) -> str:
    return f"{_CACHE_KEY_PREFIX}:{siem_id}:updated_at"


def _normalize_cached_counts(raw_counts: dict[str, Any]) -> dict[str, int]:
    normalized_counts: dict[str, int] = {}
    for field_name, count in raw_counts.items():
        if isinstance(count, int):
            normalized_counts[field_name] = count
            continue

        if isinstance(count, str) and count.isdigit():
            normalized_counts[field_name] = int(count)

    return normalized_counts


def _build_siem_schema_payload(siem_wrapper) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    base_field_map = siem_wrapper.get_available_fields()
    if not isinstance(base_field_map, dict):
        return {}, {}

    searchable_field_map: dict[str, dict[str, Any]] = {}
    field_count_map: dict[str, int] = {}
    
    for field_name, field_info in base_field_map.items():
        logger.info(f"Retrieving field: {field_name}")
        if not isinstance(field_info, dict):
            continue
        if not bool(field_info.get("searchable", False)):
            continue

        count_result = siem_wrapper.get_field_count(field=field_name)
        if not isinstance(count_result, int):
            continue
        if count_result <= 0:
            continue

        filtered_field_info = dict(field_info)
        filtered_field_info.pop("searchable", None)

        searchable_field_map[field_name] = filtered_field_info
        field_count_map[field_name] = count_result

    return searchable_field_map, field_count_map


def load_cached_siem_schema(
    siem_id: int,
) -> tuple[dict[str, dict[str, Any]] | None, dict[str, int] | None]:
    cached_payload = redis_client.get(_payload_key(siem_id))
    if not cached_payload:
        logger.debug("SIEM schema cache miss for siem_id=%s", siem_id)
        return None, None

    try:
        payload = json.loads(cached_payload)
    except json.JSONDecodeError:
        logger.warning("Invalid cached SIEM schema payload for siem_id=%s", siem_id)
        return None, None

    if not isinstance(payload, dict):
        return None, None

    fields = payload.get("fields")
    counts = payload.get("counts", {})

    if not isinstance(fields, dict):
        logger.warning("Cached SIEM schema fields are invalid for siem_id=%s", siem_id)
        return None, None
    if not isinstance(counts, dict):
        counts = {}

    logger.debug(
        "SIEM schema cache hit for siem_id=%s with %s fields",
        siem_id,
        len(fields),
    )

    return fields, _normalize_cached_counts(counts)


def refresh_siem_schema(
    siem_wrapper,
    siem_id: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    logger.info("Refreshing SIEM schema for siem_id=%s", siem_id)
    fields, counts = _build_siem_schema_payload(siem_wrapper=siem_wrapper)

    payload = {
        "fields": fields,
        "counts": counts,
        "updated_at": int(time.time()),
    }

    serialized_payload = json.dumps(payload)
    ttl_seconds = settings.SIEM_SCHEMA_RETRIEVAL_CACHE_TTL_SECONDS

    redis_client.set(_payload_key(siem_id), serialized_payload, ex=ttl_seconds)
    redis_client.set(_updated_at_key(siem_id), str(payload["updated_at"]), ex=ttl_seconds)

    logger.info(
        "Refreshed SIEM schema for siem_id=%s with %s fields",
        siem_id,
        len(fields),
    )

    return fields, counts


def get_siem_schema_cache(
    siem_wrapper,
    siem_id: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    cached_fields, cached_counts = load_cached_siem_schema(siem_id=siem_id)
    if cached_fields is not None and cached_counts is not None:
        return cached_fields, cached_counts

    logger.debug("SIEM schema cache fallback to refresh for siem_id=%s", siem_id)

    return refresh_siem_schema(siem_wrapper=siem_wrapper, siem_id=siem_id)
