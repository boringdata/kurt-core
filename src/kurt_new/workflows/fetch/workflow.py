from __future__ import annotations

import time
from typing import Any

from dbos import DBOS

from kurt_new.core import run_workflow, track_step

from .config import FetchConfig
from .steps import embedding_step, fetch_step, persist_fetch_documents


@DBOS.workflow()
def fetch_workflow(docs: list[dict[str, Any]], config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch content from discovered documents.
    """
    config = FetchConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    with track_step("fetch_documents"):
        result = fetch_step(docs, config.model_dump())

    # Generate embeddings in a separate step (can't start workflows from within a step)
    with track_step("generate_embeddings"):
        rows_with_embeddings = embedding_step(result["rows"], config.model_dump())
        result["rows"] = rows_with_embeddings

    # Persist rows via transaction (called from workflow, not step)
    if not result.get("dry_run") and result.get("rows"):
        persistence = persist_fetch_documents(result["rows"])
        result["rows_written"] = persistence["rows_written"]
        result["rows_updated"] = persistence["rows_updated"]
    else:
        result["rows_written"] = 0
        result["rows_updated"] = 0

    DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {"workflow_id": workflow_id, **result}


def run_fetch(
    docs: list[dict[str, Any]],
    config: FetchConfig | dict[str, Any],
    *,
    background: bool = False,
    priority: int = 10,
) -> dict[str, Any] | str | None:
    """
    Run the fetch workflow and return the result.
    """
    config_dict = config.model_dump() if isinstance(config, FetchConfig) else config
    return run_workflow(
        fetch_workflow,
        docs,
        config_dict,
        background=background,
        priority=priority,
    )
