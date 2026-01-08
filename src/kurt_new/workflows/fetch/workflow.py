from __future__ import annotations

import time
from typing import Any

from dbos import DBOS

from kurt_new.core import track_step

from .config import FetchConfig
from .steps import fetch_step


@DBOS.workflow()
def fetch_workflow(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch content from discovered documents.
    """
    config = FetchConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    with track_step("fetch_documents"):
        result = fetch_step(config.model_dump())

    DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {"workflow_id": workflow_id, **result}


def run_fetch(config: FetchConfig | dict[str, Any]) -> dict[str, Any]:
    """
    Run the fetch workflow and return the result.
    """
    payload = config.model_dump() if isinstance(config, FetchConfig) else config
    handle = DBOS.start_workflow(fetch_workflow, payload)
    return handle.get_result()
