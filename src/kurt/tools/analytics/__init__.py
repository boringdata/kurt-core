"""
AnalyticsTool - Domain analytics syncing tool for Kurt workflows.

Fetches page-level analytics metrics from analytics platforms (PostHog, GA4, Plausible).
Thin wrapper around kurt.integrations.domains_analytics.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from kurt.tools.core import ProgressCallback, Tool, ToolContext, ToolResult, register_tool

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class AnalyticsInput(BaseModel):
    """Input parameters for the Analytics tool."""

    domain: str = Field(
        ...,
        description="Domain to sync analytics for (e.g., 'example.com')",
    )

    platform: Literal["posthog", "ga4", "plausible"] = Field(
        default="posthog",
        description="Analytics platform to use",
    )

    period_days: int = Field(
        default=60,
        ge=1,
        le=365,
        description="Days of data to fetch",
    )

    dry_run: bool = Field(
        default=False,
        description="Preview mode - fetch but don't persist",
    )


class PageMetricsOutput(BaseModel):
    """Analytics metrics for a single page/URL."""

    id: str = Field(..., description="Unique metrics record ID")
    url: str = Field(..., description="Page URL (normalized)")
    domain: str = Field(..., description="Domain")

    # Pageview metrics
    pageviews_60d: int = Field(default=0, description="Pageviews in last 60 days")
    pageviews_30d: int = Field(default=0, description="Pageviews in last 30 days")
    pageviews_previous_30d: int = Field(
        default=0,
        description="Pageviews in 30 days before that",
    )

    # Visitor metrics
    unique_visitors_60d: int = Field(default=0, description="Unique visitors in 60 days")
    unique_visitors_30d: int = Field(default=0, description="Unique visitors in 30 days")
    unique_visitors_previous_30d: int = Field(
        default=0,
        description="Unique visitors in previous 30 days",
    )

    # Engagement metrics
    avg_session_duration_seconds: float | None = Field(
        default=None,
        description="Average session duration in seconds",
    )
    bounce_rate: float | None = Field(
        default=None,
        description="Bounce rate (0.0 - 1.0)",
    )

    # Trend analysis
    pageviews_trend: Literal["up", "down", "flat"] | None = Field(
        default=None,
        description="Pageview trend direction",
    )
    trend_percentage: float | None = Field(
        default=None,
        description="Percentage change in pageviews",
    )

    # Time range
    period_start: str | None = Field(default=None, description="Period start date (ISO)")
    period_end: str | None = Field(default=None, description="Period end date (ISO)")
    synced_at: str | None = Field(default=None, description="Sync timestamp (ISO)")


class AnalyticsOutput(BaseModel):
    """Summary output from analytics sync."""

    domain: str = Field(..., description="Domain synced")
    platform: str = Field(..., description="Analytics platform used")
    period_days: int = Field(..., description="Days of data fetched")
    total_urls: int = Field(default=0, description="Number of URLs with data")
    total_pageviews: int = Field(default=0, description="Total pageviews across all URLs")
    pages: list[PageMetricsOutput] = Field(
        default_factory=list,
        description="Per-page metrics",
    )


# ============================================================================
# AnalyticsTool Implementation
# ============================================================================


@register_tool
class AnalyticsTool(Tool[AnalyticsInput, AnalyticsOutput]):
    """
    Sync domain analytics from analytics platforms.

    Substeps:
    - sync_analytics: Fetch metrics from platform API

    Platforms:
    - posthog: PostHog analytics
    - ga4: Google Analytics 4 (coming soon)
    - plausible: Plausible Analytics (coming soon)
    """

    name = "analytics"
    description = "Sync page-level analytics from PostHog, GA4, or Plausible"
    InputModel = AnalyticsInput
    OutputModel = AnalyticsOutput

    async def run(
        self,
        params: AnalyticsInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the analytics sync tool.

        Args:
            params: Analytics parameters (domain, platform, period)
            context: Execution context
            on_progress: Optional progress callback

        Returns:
            ToolResult with page-level analytics metrics
        """
        from kurt.integrations.domains_analytics import sync_domain_metrics
        from kurt.integrations.domains_analytics.utils import normalize_url_for_analytics

        # ----------------------------------------------------------------
        # Substep: sync_analytics
        # ----------------------------------------------------------------
        self.emit_progress(
            on_progress,
            substep="sync_analytics",
            status="running",
            message=f"Syncing analytics for {params.domain} from {params.platform}",
        )

        try:
            # Fetch metrics from integration
            metrics_map = sync_domain_metrics(
                platform=params.platform,
                domain=params.domain,
                period_days=params.period_days,
            )

        except NotImplementedError as e:
            logger.error(f"Platform not implemented: {e}")
            self.emit_progress(
                on_progress,
                substep="sync_analytics",
                status="failed",
                message=str(e),
            )
            tool_result = ToolResult(success=False)
            tool_result.add_error(
                error_type="platform_not_implemented",
                message=str(e),
            )
            return tool_result

        except Exception as e:
            logger.error(f"Failed to sync analytics: {e}")
            self.emit_progress(
                on_progress,
                substep="sync_analytics",
                status="failed",
                message=str(e),
            )
            tool_result = ToolResult(success=False)
            tool_result.add_error(
                error_type="sync_failed",
                message=str(e),
            )
            return tool_result

        if not metrics_map:
            self.emit_progress(
                on_progress,
                substep="sync_analytics",
                status="completed",
                current=0,
                total=0,
                message="No analytics data found",
            )

            tool_result = ToolResult(
                success=True,
                data=[{
                    "domain": params.domain,
                    "platform": params.platform,
                    "period_days": params.period_days,
                    "total_urls": 0,
                    "total_pageviews": 0,
                    "pages": [],
                }],
            )
            tool_result.add_substep(
                name="sync_analytics",
                status="completed",
                current=0,
                total=0,
            )
            return tool_result

        # Build page metrics rows
        pages = []
        total_pageviews = 0
        now = datetime.utcnow()

        for url, metrics in metrics_map.items():
            normalized_url = normalize_url_for_analytics(url)

            # Convert datetime fields to ISO strings
            period_start = None
            period_end = None
            if hasattr(metrics, "period_start") and metrics.period_start:
                if isinstance(metrics.period_start, datetime):
                    period_start = metrics.period_start.isoformat()
                else:
                    period_start = str(metrics.period_start)
            if hasattr(metrics, "period_end") and metrics.period_end:
                if isinstance(metrics.period_end, datetime):
                    period_end = metrics.period_end.isoformat()
                else:
                    period_end = str(metrics.period_end)

            page_data = {
                "id": str(uuid4()),
                "url": normalized_url,
                "domain": params.domain,
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
                "period_start": period_start,
                "period_end": period_end,
                "synced_at": now.isoformat(),
            }
            pages.append(page_data)
            total_pageviews += metrics.pageviews_60d

        # Emit progress for each page
        total = len(pages)
        for idx, page in enumerate(pages):
            self.emit_progress(
                on_progress,
                substep="sync_analytics",
                status="progress",
                current=idx + 1,
                total=total,
                message=f"Processed {idx + 1}/{total} URLs",
                metadata={
                    "url": page["url"],
                    "pageviews": page["pageviews_60d"],
                },
            )

        self.emit_progress(
            on_progress,
            substep="sync_analytics",
            status="completed",
            current=total,
            total=total,
            message=f"Synced {total} URL(s), {total_pageviews} total pageviews",
        )

        # Build output data
        output_data = {
            "domain": params.domain,
            "platform": params.platform,
            "period_days": params.period_days,
            "total_urls": len(pages),
            "total_pageviews": total_pageviews,
            "pages": pages,
        }

        # Build result
        tool_result = ToolResult(
            success=True,
            data=[output_data],
        )

        tool_result.add_substep(
            name="sync_analytics",
            status="completed",
            current=total,
            total=total,
        )

        return tool_result


__all__ = [
    "AnalyticsTool",
    "AnalyticsInput",
    "AnalyticsOutput",
    "PageMetricsOutput",
]
