"""Telemetry module for anonymous usage analytics."""

from .config import (
    get_machine_id,
    get_telemetry_status,
    is_ci_environment,
    is_telemetry_enabled,
    set_telemetry_enabled,
)
from .decorators import track_command
from .tracker import flush_events, track_event

__all__ = [
    "get_machine_id",
    "get_telemetry_status",
    "is_ci_environment",
    "is_telemetry_enabled",
    "set_telemetry_enabled",
    "flush_events",
    "track_command",
    "track_event",
]
