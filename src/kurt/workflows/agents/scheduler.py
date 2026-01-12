"""
DBOS-native scheduling for agent workflows.

Scheduled workflows use DBOS @DBOS.scheduled decorator which provides:
- Exactly-once execution guarantees
- Automatic deduplication via idempotency keys
- Survives restarts (missed schedules can be recovered)
- No external scheduler needed
"""

from __future__ import annotations

import logging
from datetime import datetime

from dbos import DBOS

from .executor import execute_agent_workflow
from .registry import get_definition, list_definitions

logger = logging.getLogger(__name__)


def register_scheduled_workflows() -> int:
    """
    Register scheduled workflows with DBOS at startup.

    Scans .kurt/workflows/ for definitions with schedules and
    creates @DBOS.scheduled decorated functions for each.

    Returns:
        Number of workflows registered
    """
    count = 0
    for definition in list_definitions():
        if definition.schedule and definition.schedule.enabled:
            _register_scheduled_workflow(definition.name, definition.schedule.cron)
            count += 1
    return count


def _register_scheduled_workflow(name: str, cron: str) -> None:
    """Register a single scheduled workflow with DBOS."""

    @DBOS.scheduled(cron)
    @DBOS.workflow()
    def scheduled_agent_workflow(scheduled_time: datetime, actual_time: datetime):
        """Auto-generated scheduled workflow."""
        logger.info(f"Running scheduled workflow: {name} (scheduled: {scheduled_time})")

        definition = get_definition(name)
        if not definition:
            logger.error(f"Scheduled workflow definition not found: {name}")
            return {"error": f"Definition not found: {name}"}

        # Execute the agent workflow with default inputs
        result = execute_agent_workflow(
            definition_dict=definition.model_dump(),
            inputs=dict(definition.inputs),
            trigger="scheduled",
        )

        logger.info(f"Scheduled workflow '{name}' completed: {result.get('status')}")
        return result

    # Register with unique name for DBOS
    scheduled_agent_workflow.__name__ = f"scheduled_{name}"
    scheduled_agent_workflow.__qualname__ = f"scheduled_{name}"

    logger.info(f"Registered scheduled workflow: {name} with cron: {cron}")


def get_scheduled_workflows() -> list[dict]:
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
