"""Domain analytics workflow orchestration."""

from __future__ import annotations

import time
from typing import Any

from dbos import DBOS

from kurt.core import run_workflow, track_step, with_parent_workflow_id

from .config import DomainAnalyticsConfig
from .steps import domain_analytics_sync_step, persist_domain_analytics


@DBOS.workflow()
@with_parent_workflow_id
def domain_analytics_workflow(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Sync analytics metrics for a domain.

    The workflow:
    1. Fetches URLs and metrics from analytics platform
    2. Persists PageAnalytics records (if not dry_run)

    Args:
        config_dict: DomainAnalyticsConfig as dict

    Returns:
        Dict with workflow_id, domain, platform, totals, etc.
    """
    config = DomainAnalyticsConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    with track_step("domain_analytics_sync"):
        result = domain_analytics_sync_step(config.model_dump())

    # Persist if not dry run and we have data
    if not result.get("dry_run") and result.get("rows"):
        persistence = persist_domain_analytics(
            domain=result["domain"],
            platform=result["platform"],
            rows=result["rows"],
            period_days=result.get("period_days", 60),
        )
        result["rows_written"] = persistence["rows_written"]
        result["rows_updated"] = persistence["rows_updated"]
    else:
        result["rows_written"] = 0
        result["rows_updated"] = 0

    DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {"workflow_id": workflow_id, **result}


def run_domain_analytics(
    config: DomainAnalyticsConfig | dict[str, Any],
    *,
    background: bool = False,
    priority: int = 10,
) -> dict[str, Any] | str | None:
    """
    Run the domain analytics workflow and return the result.

    Args:
        config: DomainAnalyticsConfig instance or dict

    Returns:
        Workflow result dict
    """
    payload = config.model_dump() if isinstance(config, DomainAnalyticsConfig) else config
    return run_workflow(
        domain_analytics_workflow,
        payload,
        background=background,
        priority=priority,
    )
