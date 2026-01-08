"""Signals workflow orchestration."""

from __future__ import annotations

import time
from typing import Any

from dbos import DBOS

from kurt_new.core import run_workflow, track_step

from .config import SignalsConfig
from .steps import fetch_signals_step, persist_signals


@DBOS.workflow()
def signals_workflow(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch signals from a source (Reddit, HN, RSS feeds).

    The workflow:
    1. Fetches signals from the configured source
    2. Optionally persists signals to database

    Args:
        config_dict: SignalsConfig as dict

    Returns:
        Dict with workflow_id, signals, persistence info
    """
    config = SignalsConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    with track_step("fetch_signals"):
        step_result = fetch_signals_step(config.model_dump())

    signals = step_result["signals"]

    # Persist if not dry run
    persistence_info = {}
    if not step_result.get("dry_run") and signals:
        persistence = persist_signals(signals, config.source)
        persistence_info = persistence

    DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {
        "workflow_id": workflow_id,
        "source": config.source,
        "total_signals": step_result["total"],
        "signals": signals,
        "dry_run": config.dry_run,
        **persistence_info,
    }


def run_signals(
    config: SignalsConfig | dict[str, Any],
    *,
    background: bool = False,
    priority: int = 10,
) -> dict[str, Any] | str | None:
    """
    Run the signals workflow and return the result.

    Args:
        config: SignalsConfig instance or dict
        background: Run in background (returns workflow_id)
        priority: Workflow priority (default 10)

    Returns:
        Workflow result dict, or workflow_id if background=True
    """
    payload = config.model_dump() if isinstance(config, SignalsConfig) else config
    return run_workflow(
        signals_workflow,
        payload,
        background=background,
        priority=priority,
    )
