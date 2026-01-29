"""
Cron-based scheduling for agent workflows.

Schedules are tracked via workflow definitions and executed via run_definition.

Note: For production use, consider integrating with an external scheduler
like cron, systemd timers, or a task queue (Celery, APScheduler, etc.).
This module provides the interface for reading schedule configurations.
"""

from __future__ import annotations

import logging
from typing import Any

from .registry import list_definitions

logger = logging.getLogger(__name__)


def get_scheduled_workflows() -> list[dict[str, Any]]:
    """
    Get list of scheduled workflows with their configuration.

    Returns:
        List of dicts with name, cron, enabled, timezone info
    """
    result = []
    for definition in list_definitions():
        if definition.schedule:
            result.append(
                {
                    "name": definition.name,
                    "title": definition.title,
                    "cron": definition.schedule.cron,
                    "timezone": definition.schedule.timezone,
                    "enabled": definition.schedule.enabled,
                }
            )
    return result


