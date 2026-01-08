from __future__ import annotations

import time
from typing import Any

from dbos import DBOS

from kurt_new.core import track_step

from .config import MapConfig
from .steps import map_cms_step, map_folder_step, map_step, map_url_step


@DBOS.workflow()
def map_workflow(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Map/discover content sources and return discovered documents.
    """
    config = MapConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    with track_step("map_sources"):
        if config.source_url:
            result = map_url_step(config.model_dump())
        elif config.source_folder:
            result = map_folder_step(config.model_dump())
        elif config.cms_platform and config.cms_instance:
            result = map_cms_step(config.model_dump())
        else:
            result = map_step(config.model_dump())

    DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {"workflow_id": workflow_id, **result}


def run_map(config: MapConfig | dict[str, Any]) -> dict[str, Any]:
    """
    Run the map workflow and return the result.
    """
    payload = config.model_dump() if isinstance(config, MapConfig) else config
    handle = DBOS.start_workflow(map_workflow, payload)
    return handle.get_result()
