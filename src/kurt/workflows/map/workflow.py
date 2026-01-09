from __future__ import annotations

import time
from typing import Any

from dbos import DBOS

from kurt.core import run_workflow, track_step

from .config import MapConfig
from .steps import map_step


@DBOS.workflow()
def map_workflow(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Map/discover content sources and return discovered documents.

    The workflow:
    1. Runs discovery step (returns rows without persisting)
    2. Persists rows via transaction (if not dry_run)
    """
    from .steps import persist_map_documents

    config = MapConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    with track_step("map_sources"):
        result = map_step(config.model_dump())

    # Persist rows via transaction (called from workflow, not step)
    if not result.get("dry_run") and result.get("rows"):
        persistence = persist_map_documents(result["rows"])
        result["rows_written"] = persistence["rows_written"]
        result["rows_updated"] = persistence["rows_updated"]

    DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {"workflow_id": workflow_id, **result}


def run_map(
    config: MapConfig | dict[str, Any],
    *,
    background: bool = False,
    priority: int = 10,
) -> dict[str, Any] | str | None:
    """
    Run the map workflow and return the result.
    """
    payload = config.model_dump() if isinstance(config, MapConfig) else config
    return run_workflow(
        map_workflow,
        payload,
        background=background,
        priority=priority,
    )
