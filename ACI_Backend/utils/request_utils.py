"""
HTTP client utility with built-in timeout and retry logic for AI backend calls.
Provides resilience against transient failures and connection drops.
"""

import requests
import aiohttp
import asyncio
import logging
from typing import Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


# Configurable timeout and retry settings (in seconds)
# Get from Django settings or use sensible defaults
AI_BACKEND_CONNECT_TIMEOUT = getattr(settings, "AI_BACKEND_CONNECT_TIMEOUT", 15)
AI_BACKEND_MAX_RETRIES = getattr(settings, "AI_BACKEND_MAX_RETRIES", 3)
AI_BACKEND_RETRY_BACKOFF_FACTOR = getattr(settings, "AI_BACKEND_RETRY_BACKOFF_FACTOR", 2)
AI_BACKEND_RETRY_ON_STATUS_CODES = getattr(settings, "AI_BACKEND_RETRY_ON_STATUS_CODES", [408, 429, 500, 502, 503, 504])

# Tuple of (connect_timeout, read_timeout). read_timeout=None disables read timeout.
TIMEOUT = (AI_BACKEND_CONNECT_TIMEOUT, None)


def post_with_retry(
    url: str,
    headers: Dict[str, str],
    data: Dict[str, Any],
    max_retries: int = AI_BACKEND_MAX_RETRIES,
) -> requests.Response:
    """
    Make a POST request to the AI backend with automatic retry on transient failures.

    Args:
        url: Target URL
        headers: Request headers
        data: Request data
        max_retries: Maximum number of retries

    Returns:
        Response object

    Raises:
        requests.exceptions.RequestException: If all retries exhausted or permanent error
    """
    last_exception = None
    retry_delay = 1  # Start with 1 second

    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                timeout=TIMEOUT,
            )

            # Retry on specific HTTP error codes
            if response.status_code in AI_BACKEND_RETRY_ON_STATUS_CODES:
                if attempt < max_retries:
                    logger.warning(
                        f"AI backend returned {response.status_code}, retrying... (attempt {attempt + 1}/{max_retries})"
                    )
                    asyncio.sleep(retry_delay)
                    retry_delay *= AI_BACKEND_RETRY_BACKOFF_FACTOR
                    continue
                else:
                    # Last attempt and still getting retryable error
                    logger.error(
                        f"AI backend returned {response.status_code} after {max_retries} retries"
                    )
                    response.raise_for_status()  # Raise HTTPError

            # Successful response on acceptable status code
            return response

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        ) as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"AI backend connection failed: {type(e).__name__}, retrying... (attempt {attempt + 1}/{max_retries})"
                )
                asyncio.sleep(retry_delay)
                retry_delay *= AI_BACKEND_RETRY_BACKOFF_FACTOR
            else:
                logger.error(
                    f"AI backend connection failed after {max_retries} retries: {type(e).__name__}: {e}"
                )
                raise

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected state in post_with_retry")


async def async_post_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    headers: Dict[str, str],
    data: Dict[str, Any],
    max_retries: int = AI_BACKEND_MAX_RETRIES,
) -> Dict[str, Any]:
    """
    Make an async POST request to the AI backend with automatic retry on transient failures.

    Args:
        session: aiohttp ClientSession
        url: Target URL
        headers: Request headers
        data: Request data
        max_retries: Maximum number of retries

    Returns:
        JSON response dict

    Raises:
        aiohttp.ClientError: If all retries exhausted or permanent error
    """
    last_exception = None
    retry_delay = 1  # Start with 1 second
    timeout = aiohttp.ClientTimeout(
        connect=AI_BACKEND_CONNECT_TIMEOUT,
    )

    for attempt in range(max_retries + 1):
        try:
            async with session.post(
                url,
                headers=headers,
                data=data,
                timeout=timeout,
            ) as response:
                # Check for retryable status codes
                if response.status in AI_BACKEND_RETRY_ON_STATUS_CODES:
                    if attempt < max_retries:
                        logger.warning(
                            f"AI backend returned {response.status}, retrying... (attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(retry_delay)
                        retry_delay *= AI_BACKEND_RETRY_BACKOFF_FACTOR
                        continue
                    else:
                        logger.error(
                            f"AI backend returned {response.status} after {max_retries} retries"
                        )
                        response.raise_for_status()

                # Success
                return await response.json()

        except (
            aiohttp.ClientConnectionError,
            aiohttp.ClientSSLError,
            aiohttp.ClientOSError,
            asyncio.TimeoutError,
        ) as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"AI backend async connection failed: {type(e).__name__}, retrying... (attempt {attempt + 1}/{max_retries})"
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= AI_BACKEND_RETRY_BACKOFF_FACTOR
            else:
                logger.error(
                    f"AI backend async connection failed after {max_retries} retries: {type(e).__name__}: {e}"
                )
                raise

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected state in async_post_with_retry")
