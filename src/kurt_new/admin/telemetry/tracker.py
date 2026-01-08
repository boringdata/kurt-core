"""PostHog event tracking for Kurt CLI telemetry."""

from __future__ import annotations

import atexit
import logging
import os
import platform
import sys
import threading
from typing import Any

from .config import (
    POSTHOG_API_KEY,
    POSTHOG_HOST,
    get_machine_id,
    is_ci_environment,
    is_telemetry_enabled,
)

logger = logging.getLogger(__name__)

# Global PostHog client (lazy initialized)
_posthog_client: Any | None = None
_client_lock = threading.Lock()


def _get_posthog_client():
    """Get or create PostHog client (lazy initialization).

    Returns:
        PostHog client instance or None if disabled/error
    """
    global _posthog_client

    if not is_telemetry_enabled():
        return None

    if _posthog_client is not None:
        return _posthog_client

    with _client_lock:
        if _posthog_client is not None:
            return _posthog_client

        try:
            from posthog import Posthog

            client = Posthog(
                project_api_key=POSTHOG_API_KEY,
                host=POSTHOG_HOST,
                debug=os.getenv("KURT_TELEMETRY_DEBUG", "").lower() == "true",
                sync_mode=False,
            )

            def _shutdown():
                try:
                    client.shutdown()
                except Exception as e:
                    logger.debug(f"Error in PostHog shutdown: {e}")

            atexit.register(_shutdown)

            _posthog_client = client
            return _posthog_client

        except Exception as e:
            logger.debug(f"Failed to initialize PostHog: {e}")
            return None


def _get_kurt_version() -> str:
    """Get Kurt version string."""
    try:
        from kurt_new import __version__

        return __version__
    except Exception:
        return "unknown"


def _get_system_properties() -> dict:
    """Get system properties for telemetry events.

    Returns:
        Dictionary of system properties
    """
    return {
        "os": platform.system(),
        "os_version": platform.release(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "kurt_version": _get_kurt_version(),
        "is_ci": is_ci_environment(),
    }


def track_event(
    event_name: str,
    properties: dict | None = None,
    blocking: bool = False,
) -> None:
    """Track an analytics event.

    This is non-blocking by default and will never raise exceptions
    to ensure telemetry doesn't impact CLI performance.

    Args:
        event_name: Name of the event (e.g., "command_started")
        properties: Optional event properties
        blocking: If True, wait for event to be sent (default: False)
    """
    if not is_telemetry_enabled():
        return

    try:
        client = _get_posthog_client()
        if client is None:
            return

        event_properties = _get_system_properties()
        if properties:
            event_properties.update(properties)

        distinct_id = get_machine_id()

        def _track():
            try:
                client.capture(
                    distinct_id=distinct_id,
                    event=event_name,
                    properties=event_properties,
                )
            except Exception as e:
                logger.debug(f"Failed to track event {event_name}: {e}")

        if blocking:
            _track()
        else:
            thread = threading.Thread(target=_track, daemon=True)
            thread.start()

    except Exception as e:
        logger.debug(f"Error in track_event: {e}")


def flush_events(timeout: float = 2.0) -> None:
    """Flush pending telemetry events.

    Args:
        timeout: Maximum time to wait for flush (seconds)
    """
    try:
        client = _get_posthog_client()
        if client is not None:
            client.shutdown()
    except Exception as e:
        logger.debug(f"Error flushing events: {e}")
