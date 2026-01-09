"""Research workflow orchestration."""

from __future__ import annotations

import time
from typing import Any

from dbos import DBOS

from kurt_new.core import run_workflow, track_step

from .config import ResearchConfig
from .steps import persist_research_result, research_search_step


@DBOS.workflow()
def research_workflow(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a research query via Perplexity.

    The workflow:
    1. Executes research query via adapter
    2. Optionally persists result to DB and filesystem

    Args:
        config_dict: ResearchConfig as dict

    Returns:
        Dict with workflow_id, result, persistence info
    """
    config = ResearchConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    with track_step("research_search"):
        step_result = research_search_step(config.model_dump())

    result = step_result["result"]

    # Persist if not dry run
    persistence_info = {}
    if not step_result.get("dry_run"):
        save_to_file = step_result.get("save", False)
        output_dir = config.output_dir
        persistence = persist_research_result(
            result, save_to_file=save_to_file, output_dir=output_dir
        )
        persistence_info = persistence

    DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {
        "workflow_id": workflow_id,
        "query": config.query,
        "source": config.source,
        "citations_count": len(result.get("citations", [])),
        "response_time_seconds": result.get("response_time_seconds"),
        "result": result,
        "dry_run": config.dry_run,
        **persistence_info,
    }


def run_research(
    config: ResearchConfig | dict[str, Any],
    *,
    background: bool = False,
    priority: int = 10,
) -> dict[str, Any] | str | None:
    """
    Run the research workflow and return the result.

    Args:
        config: ResearchConfig instance or dict
        background: Run in background (returns workflow_id)
        priority: Workflow priority (default 10)

    Returns:
        Workflow result dict, or workflow_id if background=True
    """
    payload = config.model_dump() if isinstance(config, ResearchConfig) else config
    return run_workflow(
        research_workflow,
        payload,
        background=background,
        priority=priority,
    )
