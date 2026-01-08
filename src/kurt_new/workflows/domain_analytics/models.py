"""Database models for domain analytics workflow."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from kurt_new.db.models import TenantMixin, TimestampMixin


class AnalyticsStatus(str, Enum):
    """Status for analytics sync operations."""

    PENDING = "PENDING"
    SYNCED = "SYNCED"
    ERROR = "ERROR"


class AnalyticsDomain(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Tracks domains registered for analytics sync."""

    __tablename__ = "analytics_domains"

    domain: str = Field(primary_key=True)
    platform: str = Field(default="posthog")
    has_data: bool = Field(default=False)
    last_synced_at: Optional[datetime] = Field(default=None)
    sync_period_days: int = Field(default=60)
    status: AnalyticsStatus = Field(default=AnalyticsStatus.PENDING)
    error: Optional[str] = Field(default=None)


class PageAnalytics(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Analytics metrics for individual pages/URLs.

    Independent of documents - stores metrics directly from analytics platform.
    Uses normalized URLs for consistent matching with documents.
    """

    __tablename__ = "page_analytics"

    id: str = Field(primary_key=True)
    url: str = Field(index=True, unique=True)
    domain: str = Field(index=True)

    # Traffic metrics (60-day window)
    pageviews_60d: int = Field(default=0)
    unique_visitors_60d: int = Field(default=0)

    # Traffic metrics (30-day windows for trend calculation)
    pageviews_30d: int = Field(default=0)
    unique_visitors_30d: int = Field(default=0)
    pageviews_previous_30d: int = Field(default=0)
    unique_visitors_previous_30d: int = Field(default=0)

    # Engagement metrics
    avg_session_duration_seconds: Optional[float] = Field(default=None)
    bounce_rate: Optional[float] = Field(default=None)

    # Trend analysis
    pageviews_trend: str = Field(default="stable")
    trend_percentage: Optional[float] = Field(default=None)

    # Time window
    period_start: Optional[datetime] = Field(default=None)
    period_end: Optional[datetime] = Field(default=None)
    synced_at: Optional[datetime] = Field(default=None)
