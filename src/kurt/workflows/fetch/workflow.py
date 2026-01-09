from __future__ import annotations

import os
import time
from typing import Any

from dbos import DBOS

from kurt.core import run_workflow, track_step

from .config import FetchConfig
from .steps import embedding_step, fetch_step, persist_fetch_documents, save_content_step


def _has_embedding_api_key() -> bool:
    """Check if an embedding API key is available."""
    # Check common embedding API keys
    return any(
        os.environ.get(key)
        for key in [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "COHERE_API_KEY",
            "VOYAGE_API_KEY",
        ]
    )


@DBOS.workflow()
def fetch_workflow(
    docs: list[dict[str, Any]], config_dict: dict[str, Any], cli_command: str | None = None
) -> dict[str, Any]:
    """
    Fetch content from discovered documents.
    """
    config = FetchConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("workflow_type", "fetch")
    DBOS.set_event("stage", "fetching")
    DBOS.set_event("started_at", time.time())
    if cli_command:
        DBOS.set_event("cli_command", cli_command)

    with track_step("fetch_documents"):
        result = fetch_step(docs, config.model_dump())

    # Save content to files and get content_path
    DBOS.set_event("stage", "saving")
    with track_step("save_content"):
        rows_with_paths = save_content_step(result["rows"], config.model_dump())
        result["rows"] = rows_with_paths

    # Generate embeddings (skip if no API key available)
    if _has_embedding_api_key():
        DBOS.set_event("stage", "embedding")
        with track_step("generate_embeddings"):
            rows_with_embeddings = embedding_step(result["rows"], config.model_dump())
            result["rows"] = rows_with_embeddings
    else:
        # Set embedding to None for all rows
        for row in result["rows"]:
            row["embedding"] = None

    # Persist rows via transaction (called from workflow, not step)
    DBOS.set_event("stage", "persisting")
    if not result.get("dry_run") and result.get("rows"):
        persistence = persist_fetch_documents(result["rows"])
        result["rows_written"] = persistence["rows_written"]
        result["rows_updated"] = persistence["rows_updated"]
    else:
        result["rows_written"] = 0
        result["rows_updated"] = 0

    # Set final status based on results
    failed_count = result.get("failed", 0)
    if failed_count > 0:
        DBOS.set_event("status", "completed_with_errors")
    else:
        DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {"workflow_id": workflow_id, **result}


def run_fetch(
    docs: list[dict[str, Any]],
    config: FetchConfig | dict[str, Any],
    *,
    background: bool = False,
    priority: int = 10,
    cli_command: str | None = None,
) -> dict[str, Any] | str | None:
    """
    Run the fetch workflow and return the result.
    """
    config_dict = config.model_dump() if isinstance(config, FetchConfig) else config
    return run_workflow(
        fetch_workflow,
        docs,
        config_dict,
        cli_command,
        background=background,
        priority=priority,
    )
