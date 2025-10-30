"""Telemetry module for Kurt CLI.

This module provides anonymous usage analytics to help improve Kurt.
All telemetry is:
- Anonymous (no PII collected)
- Transparent (clearly documented)
- Optional (easy opt-out via DO_NOT_TRACK or config)
- Non-blocking (never slows down CLI commands)
"""

from kurt.telemetry.config import is_telemetry_enabled, set_telemetry_enabled
from kurt.telemetry.tracker import track_event

__all__ = ["is_telemetry_enabled", "set_telemetry_enabled", "track_event"]
