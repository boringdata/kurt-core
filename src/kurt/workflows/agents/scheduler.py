"""
Cron-based scheduling for agent workflows.

This module provides scheduling utilities for agent workflows without DBOS.
Schedules are tracked via workflow definitions and executed via run_definition.

Note: For production use, consider integrating with an external scheduler
like cron, systemd timers, or a task queue (Celery, APScheduler, etc.).
This module provides the interface for reading schedule configurations.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .registry import get_definition, list_definitions

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


def get_due_workflows(now: datetime | None = None) -> list[dict[str, Any]]:
    """
    Get workflows that are due to run based on their cron schedule.

    This is a simple check - for production use, integrate with
    a proper scheduler that tracks last run times.

    Args:
        now: Current datetime (defaults to utcnow)

    Returns:
        List of workflow configs that have enabled schedules
    """
    # For now, just return enabled scheduled workflows
    # A proper implementation would check cron expressions against last run time
    return [w for w in get_scheduled_workflows() if w.get("enabled")]


def run_scheduled_workflow(name: str) -> dict[str, Any]:
    """
    Run a scheduled workflow by name.

    Args:
        name: Workflow definition name

    Returns:
        Workflow result dict
    """
    from .executor import execute_agent_workflow

    definition = get_definition(name)
    if not definition:
        logger.error(f"Scheduled workflow definition not found: {name}")
        return {"error": f"Definition not found: {name}"}

    logger.info(f"Running scheduled workflow: {name}")

    # Execute the workflow with default inputs
    result = execute_agent_workflow(
        definition_dict=definition.model_dump(),
        inputs=dict(definition.inputs),
        trigger="scheduled",
    )

    logger.info(f"Scheduled workflow '{name}' completed: {result.get('status')}")
    return result


def register_scheduled_workflows() -> int:
    """
    Legacy function for DBOS compatibility.

    Without DBOS, scheduled workflows need to be triggered by an external
    scheduler (cron, systemd timer, task queue, etc.).

    Returns:
        Number of scheduled workflows found (not registered)
    """
    count = 0
    for definition in list_definitions():
        if definition.schedule and definition.schedule.enabled:
            logger.info(
                f"Found scheduled workflow: {definition.name} "
                f"(cron: {definition.schedule.cron})"
            )
            count += 1

    if count > 0:
        logger.info(
            f"Found {count} scheduled workflow(s). "
            "Use an external scheduler to trigger these workflows."
        )

    return count
