"""PostHog event tracking for Kurt CLI telemetry."""

import atexit
import logging
import os
import platform
import sys
import threading
from typing import Any, Optional

from kurt import __version__
from kurt.admin.telemetry.config import (
    POSTHOG_API_KEY,
    POSTHOG_HOST,
    get_machine_id,
    is_ci_environment,
    is_telemetry_enabled,
)

# Configure logging
logger = logging.getLogger(__name__)

# Global PostHog client (lazy initialized)
_posthog_client: Optional[Any] = None
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
        # Double-check after acquiring lock
        if _posthog_client is not None:
            return _posthog_client

        try:
            from posthog import Posthog

            # Create PostHog client instance (not using module-level API)
            client = Posthog(
                project_api_key=POSTHOG_API_KEY,
                host=POSTHOG_HOST,
                debug=os.getenv("KURT_TELEMETRY_DEBUG", "").lower() == "true",
                sync_mode=False,
            )

            # Register shutdown hook to flush events
            def _shutdown():
                try:
                    client.shutdown()
                except Exception as e:
                    logger.debug(f"Error in PostHog shutdown: {e}")

            atexit.register(_shutdown)

            _posthog_client = client
            return _posthog_client

        except Exception as e:
            # Silently fail - telemetry should never break the CLI
            logger.debug(f"Failed to initialize PostHog: {e}")
            return None


def _get_system_properties() -> dict:
    """Get system properties for telemetry events.

    Returns:
        Dictionary of system properties
    """
    return {
        "os": platform.system(),
        "os_version": platform.release(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "kurt_version": __version__,
        "is_ci": is_ci_environment(),
    }


def track_event(
    event_name: str,
    properties: Optional[dict] = None,
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

        # Merge user properties with system properties
        event_properties = _get_system_properties()
        if properties:
            event_properties.update(properties)

        # Get distinct ID (machine ID)
        distinct_id = get_machine_id()

        # Track event in background thread
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
            # Run in background thread (non-blocking)
            thread = threading.Thread(target=_track, daemon=True)
            thread.start()

    except Exception as e:
        # Silently fail - telemetry should never break the CLI
        logger.debug(f"Error in track_event: {e}")


def flush_events(timeout: float = 2.0) -> None:
    """Flush pending telemetry events.

    This is automatically called on exit via atexit handler,
    but can be called manually if needed.

    Args:
        timeout: Maximum time to wait for flush (seconds)
    """
    try:
        client = _get_posthog_client()
        if client is not None:
            # PostHog's shutdown handles flushing
            client.shutdown()
    except Exception as e:
        logger.debug(f"Error flushing events: {e}")
