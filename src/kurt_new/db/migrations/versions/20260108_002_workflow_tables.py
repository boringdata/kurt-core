"""Add workflow tables - map, fetch, research, signals, analytics

Revision ID: 002_workflow_tables
Revises: 001_initial
Create Date: 2026-01-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_workflow_tables"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========================================================================
    # map_documents - Document discovery/mapping
    # ========================================================================
    op.create_table(
        "map_documents",
        # Primary key
        sa.Column("document_id", sa.String(), nullable=False),
        # Core fields
        sa.Column("source_url", sa.String(), nullable=False, server_default=""),
        sa.Column("source_type", sa.String(), nullable=False, server_default="url"),
        sa.Column("discovery_method", sa.String(), nullable=False, server_default=""),
        sa.Column("discovery_url", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="DISCOVERED"),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # TenantMixin
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index("ix_map_documents_content_hash", "map_documents", ["content_hash"])
    op.create_index("ix_map_documents_user_id", "map_documents", ["user_id"])
    op.create_index("ix_map_documents_workspace_id", "map_documents", ["workspace_id"])

    # ========================================================================
    # fetch_documents - Document content fetching
    # ========================================================================
    op.create_table(
        "fetch_documents",
        # Primary key
        sa.Column("document_id", sa.String(), nullable=False),
        # Status
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        # Content info
        sa.Column("content_length", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(), nullable=True),
        sa.Column("content_path", sa.String(), nullable=True),
        # Fetch info
        sa.Column("fetch_engine", sa.String(), nullable=True),
        sa.Column("public_url", sa.String(), nullable=True),
        # Error tracking
        sa.Column("error", sa.Text(), nullable=True),
        # Metadata
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        # EmbeddingMixin
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # TenantMixin
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index("ix_fetch_documents_user_id", "fetch_documents", ["user_id"])
    op.create_index("ix_fetch_documents_workspace_id", "fetch_documents", ["workspace_id"])

    # ========================================================================
    # research_documents - Perplexity research results
    # ========================================================================
    op.create_table(
        "research_documents",
        # Primary key
        sa.Column("id", sa.String(), nullable=False),
        # Core fields
        sa.Column("query", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer", sa.Text(), nullable=False, server_default=""),
        # Source info
        sa.Column("source", sa.String(), nullable=False, server_default="perplexity"),
        sa.Column("model", sa.String(), nullable=True),
        # Metadata
        sa.Column("citations_json", sa.JSON(), nullable=True),
        sa.Column("response_time_seconds", sa.Float(), nullable=True),
        # Status
        sa.Column("status", sa.String(), nullable=False, server_default="COMPLETED"),
        sa.Column("error", sa.Text(), nullable=True),
        # File storage
        sa.Column("content_path", sa.String(), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ========================================================================
    # monitoring_signals - Reddit/HN/Feeds signals
    # ========================================================================
    op.create_table(
        "monitoring_signals",
        # Primary key
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        # Core fields
        sa.Column("signal_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default=""),
        sa.Column("title", sa.String(), nullable=False, server_default=""),
        sa.Column("url", sa.String(), nullable=False, server_default=""),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("author", sa.String(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subreddit", sa.String(), nullable=True),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("keywords_json", sa.JSON(), nullable=True),
        sa.Column("signal_timestamp", sa.String(), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_id"),
    )
    op.create_index("ix_monitoring_signals_signal_id", "monitoring_signals", ["signal_id"])

    # ========================================================================
    # analytics_domains - Domain analytics sync tracking
    # ========================================================================
    op.create_table(
        "analytics_domains",
        # Primary key
        sa.Column("domain", sa.String(), nullable=False),
        # Core fields
        sa.Column("platform", sa.String(), nullable=False, server_default="posthog"),
        sa.Column("has_data", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sync_period_days", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("error", sa.Text(), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # TenantMixin
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("domain"),
    )
    op.create_index("ix_analytics_domains_user_id", "analytics_domains", ["user_id"])
    op.create_index("ix_analytics_domains_workspace_id", "analytics_domains", ["workspace_id"])

    # ========================================================================
    # page_analytics - Per-page traffic metrics
    # ========================================================================
    op.create_table(
        "page_analytics",
        # Primary key
        sa.Column("id", sa.String(), nullable=False),
        # Core fields
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        # Traffic metrics (60-day window)
        sa.Column("pageviews_60d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_visitors_60d", sa.Integer(), nullable=False, server_default="0"),
        # Traffic metrics (30-day windows)
        sa.Column("pageviews_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_visitors_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pageviews_previous_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_visitors_previous_30d", sa.Integer(), nullable=False, server_default="0"),
        # Engagement metrics
        sa.Column("avg_session_duration_seconds", sa.Float(), nullable=True),
        sa.Column("bounce_rate", sa.Float(), nullable=True),
        # Trend analysis
        sa.Column("pageviews_trend", sa.String(), nullable=False, server_default="stable"),
        sa.Column("trend_percentage", sa.Float(), nullable=True),
        # Time window
        sa.Column("period_start", sa.DateTime(), nullable=True),
        sa.Column("period_end", sa.DateTime(), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        # TimestampMixin
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # TenantMixin
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("workspace_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_page_analytics_url", "page_analytics", ["url"])
    op.create_index("ix_page_analytics_domain", "page_analytics", ["domain"])
    op.create_index("ix_page_analytics_user_id", "page_analytics", ["user_id"])
    op.create_index("ix_page_analytics_workspace_id", "page_analytics", ["workspace_id"])


def downgrade() -> None:
    # Drop in reverse order
    op.drop_index("ix_page_analytics_workspace_id", "page_analytics")
    op.drop_index("ix_page_analytics_user_id", "page_analytics")
    op.drop_index("ix_page_analytics_domain", "page_analytics")
    op.drop_index("ix_page_analytics_url", "page_analytics")
    op.drop_table("page_analytics")

    op.drop_index("ix_analytics_domains_workspace_id", "analytics_domains")
    op.drop_index("ix_analytics_domains_user_id", "analytics_domains")
    op.drop_table("analytics_domains")

    op.drop_index("ix_monitoring_signals_signal_id", "monitoring_signals")
    op.drop_table("monitoring_signals")

    op.drop_table("research_documents")

    op.drop_index("ix_fetch_documents_workspace_id", "fetch_documents")
    op.drop_index("ix_fetch_documents_user_id", "fetch_documents")
    op.drop_table("fetch_documents")

    op.drop_index("ix_map_documents_workspace_id", "map_documents")
    op.drop_index("ix_map_documents_user_id", "map_documents")
    op.drop_index("ix_map_documents_content_hash", "map_documents")
    op.drop_table("map_documents")
