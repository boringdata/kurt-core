"""Domain analytics workflow steps."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any
from uuid import uuid4

from dbos import DBOS

from kurt_new.db import ensure_tables, managed_session
from kurt_new.integrations.domains_analytics import sync_domain_metrics
from kurt_new.integrations.domains_analytics.utils import normalize_url_for_analytics

from .config import DomainAnalyticsConfig
from .models import AnalyticsDomain, AnalyticsStatus, PageAnalytics


def build_analytics_rows(
    domain: str,
    metrics_map: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build PageAnalytics rows from metrics map.

    Args:
        domain: Domain being synced
        metrics_map: Dict mapping URL -> AnalyticsMetrics

    Returns:
        List of row dicts ready for persistence
    """
    rows = []
    for url, metrics in metrics_map.items():
        normalized_url = normalize_url_for_analytics(url)
        rows.append(
            {
                "id": str(uuid4()),
                "url": normalized_url,
                "domain": domain,
                "pageviews_60d": metrics.pageviews_60d,
                "pageviews_30d": metrics.pageviews_30d,
                "pageviews_previous_30d": metrics.pageviews_previous_30d,
                "unique_visitors_60d": metrics.unique_visitors_60d,
                "unique_visitors_30d": metrics.unique_visitors_30d,
                "unique_visitors_previous_30d": metrics.unique_visitors_previous_30d,
                "avg_session_duration_seconds": metrics.avg_session_duration_seconds,
                "bounce_rate": metrics.bounce_rate,
                "pageviews_trend": metrics.pageviews_trend,
                "trend_percentage": metrics.trend_percentage,
                "period_start": metrics.period_start,
                "period_end": metrics.period_end,
                "synced_at": datetime.utcnow(),
            }
        )
    return rows


def serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize rows for DBOS step return (convert datetimes to ISO strings)."""
    serialized = []
    for row in rows:
        serialized_row = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                serialized_row[key] = value.isoformat()
            else:
                serialized_row[key] = value
        serialized.append(serialized_row)
    return serialized


def deserialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deserialize rows from DBOS step (convert ISO strings back to datetimes)."""
    datetime_fields = {"period_start", "period_end", "synced_at"}
    deserialized = []
    for row in rows:
        deserialized_row = {}
        for key, value in row.items():
            if key in datetime_fields and value is not None:
                deserialized_row[key] = datetime.fromisoformat(value)
            else:
                deserialized_row[key] = value
        deserialized.append(deserialized_row)
    return deserialized


@DBOS.step(name="domain_analytics_sync")
def domain_analytics_sync_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch analytics from platform (pure, no persistence).

    Args:
        config_dict: DomainAnalyticsConfig as dict

    Returns:
        Dict with domain, platform, urls, rows, etc.
    """
    config = DomainAnalyticsConfig.model_validate(config_dict)

    # Fetch metrics using integration
    metrics_map = sync_domain_metrics(
        platform=config.platform,
        domain=config.domain,
        period_days=config.period_days,
    )

    if not metrics_map:
        return {
            "domain": config.domain,
            "platform": config.platform,
            "total_urls": 0,
            "total_pageviews": 0,
            "rows": [],
            "dry_run": config.dry_run,
        }

    # Build rows for persistence
    rows = build_analytics_rows(config.domain, metrics_map)

    # Calculate totals
    total_pageviews = sum(m.pageviews_60d for m in metrics_map.values())

    # Stream progress
    total = len(rows)
    DBOS.set_event("stage_total", total)
    for idx, row in enumerate(rows):
        DBOS.set_event("stage_current", idx + 1)
        DBOS.write_stream(
            "progress",
            {
                "step": "domain_analytics_sync",
                "idx": idx,
                "total": total,
                "url": row["url"],
                "pageviews": row["pageviews_60d"],
                "timestamp": time.time(),
            },
        )

    return {
        "domain": config.domain,
        "platform": config.platform,
        "period_days": config.period_days,
        "total_urls": len(metrics_map),
        "total_pageviews": total_pageviews,
        "rows": serialize_rows(rows),
        "dry_run": config.dry_run,
    }


@DBOS.transaction()
def persist_domain_analytics(
    domain: str,
    platform: str,
    rows: list[dict[str, Any]],
    period_days: int = 60,
) -> dict[str, int]:
    """
    Persist analytics results in a durable transaction.

    Args:
        domain: Domain being synced
        platform: Analytics platform
        rows: List of PageAnalytics row dicts
        period_days: Days of data synced

    Returns:
        Dict with rows_written, rows_updated counts
    """
    # Deserialize datetime fields
    rows = deserialize_rows(rows)

    with managed_session() as session:
        ensure_tables([AnalyticsDomain, PageAnalytics], session=session)

        # Upsert AnalyticsDomain
        existing_domain = session.get(AnalyticsDomain, domain)
        if existing_domain:
            existing_domain.platform = platform
            existing_domain.last_synced_at = datetime.utcnow()
            existing_domain.sync_period_days = period_days
            existing_domain.has_data = len(rows) > 0
            existing_domain.status = AnalyticsStatus.SUCCESS
            existing_domain.error = None
        else:
            session.add(
                AnalyticsDomain(
                    domain=domain,
                    platform=platform,
                    has_data=len(rows) > 0,
                    last_synced_at=datetime.utcnow(),
                    sync_period_days=period_days,
                    status=AnalyticsStatus.SUCCESS,
                )
            )

        # Upsert PageAnalytics rows
        inserted = 0
        updated = 0

        for row in rows:
            # Check by normalized URL
            existing = session.query(PageAnalytics).filter(PageAnalytics.url == row["url"]).first()

            if existing:
                # Update existing record
                for key, value in row.items():
                    if key != "id":  # Don't update primary key
                        setattr(existing, key, value)
                updated += 1
            else:
                # Insert new record
                session.add(PageAnalytics(**row))
                inserted += 1

        return {"rows_written": inserted, "rows_updated": updated}
