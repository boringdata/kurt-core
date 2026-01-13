from __future__ import annotations

import os
import time
from typing import Any

from dbos import DBOS

from kurt.core import run_workflow, with_parent_workflow_id
from kurt.core.tracking import track_batch_step

from .config import FetchConfig
from .models import FetchStatus
from .steps import (
    embedding_step,
    fetch_step,
    fetch_urls_parallel,
    persist_fetch_documents,
    save_content_step,
)


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
@with_parent_workflow_id
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

    # Separate web docs from non-web docs
    web_docs = [d for d in docs if d.get("source_type", "url") == "url"]
    non_web_docs = [d for d in docs if d.get("source_type", "url") != "url"]

    # Fetch documents - QueueStepTracker handles its own progress tracking
    # All web docs use parallel queue (handles batching for tavily/firecrawl internally)
    if web_docs:
        web_rows = fetch_urls_parallel(web_docs, config)
    else:
        web_rows = []

    # Non-web docs (file, cms) go through fetch_step
    if non_web_docs:
        non_web_result = fetch_step(non_web_docs, config.model_dump())
        non_web_rows = non_web_result.get("rows", [])
    else:
        non_web_rows = []

    # Combine results
    all_rows = web_rows + non_web_rows
    fetched = sum(1 for r in all_rows if r.get("status") in ("SUCCESS", FetchStatus.SUCCESS))
    failed = sum(1 for r in all_rows if r.get("status") in ("ERROR", FetchStatus.ERROR))
    result = {
        "total": len(docs),
        "documents_fetched": fetched,
        "documents_failed": failed,
        "rows": all_rows,
        "dry_run": config.dry_run,
    }

    # Save content to files - batch step (no per-item progress)
    rows = result["rows"]
    success_count = sum(1 for r in rows if r.get("status") in ("SUCCESS", FetchStatus.SUCCESS))

    DBOS.set_event("stage", "saving")
    with track_batch_step("save_content", total=success_count):
        rows_with_paths = save_content_step(rows, config.model_dump())
        result["rows"] = rows_with_paths

    # Generate embeddings - batch step (no per-item progress)
    if _has_embedding_api_key():
        DBOS.set_event("stage", "embedding")
        with track_batch_step("generate_embeddings", total=success_count):
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
