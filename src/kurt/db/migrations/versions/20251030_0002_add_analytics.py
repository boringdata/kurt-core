"""Add analytics integration tables

Revision ID: 003_analytics
Revises: 003_cms_document_id
Create Date: 2025-10-30

This migration adds:
1. analytics_domains table for tracking domains with analytics configured
   - Credentials stored in .kurt/analytics-config.json (not in database)
   - Database only tracks: domain registration, platform type, sync metadata
2. document_analytics table for storing synced analytics metrics
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_analytics"
down_revision: Union[str, None] = "003_cms_document_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add analytics_domains and document_analytics tables."""

    # Create analytics_domains table
    # Note: Credentials (project_id, api_key) stored in .kurt/analytics-config.json
    # Database only tracks domain registration and sync metadata
    op.create_table(
        "analytics_domains",
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("has_data", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sync_period_days", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("domain"),
    )

    # Create document_analytics table
    op.create_table(
        "document_analytics",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        # Traffic metrics - 60-day total
        sa.Column("pageviews_60d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_visitors_60d", sa.Integer(), nullable=False, server_default="0"),
        # Traffic metrics - Last 30 days
        sa.Column("pageviews_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_visitors_30d", sa.Integer(), nullable=False, server_default="0"),
        # Traffic metrics - Previous 30 days (days 31-60)
        sa.Column("pageviews_previous_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_visitors_previous_30d", sa.Integer(), nullable=False, server_default="0"),
        # Engagement metrics
        sa.Column("avg_session_duration_seconds", sa.Float(), nullable=True),
        sa.Column("bounce_rate", sa.Float(), nullable=True),
        # Computed trends
        sa.Column("pageviews_trend", sa.String(), nullable=False, server_default="'stable'"),
        sa.Column("trend_percentage", sa.Float(), nullable=True),
        # Time window metadata
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        # Sync metadata
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
    )

    # Create indexes for document_analytics
    op.create_index(
        op.f("ix_document_analytics_document_id"),
        "document_analytics",
        ["document_id"],
        unique=True,  # One analytics record per document
    )
    op.create_index(
        op.f("ix_document_analytics_pageviews_30d"),
        "document_analytics",
        ["pageviews_30d"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_analytics_pageviews_trend"),
        "document_analytics",
        ["pageviews_trend"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_analytics_bounce_rate"),
        "document_analytics",
        ["bounce_rate"],
        unique=False,
    )


def downgrade() -> None:
    """Remove analytics tables."""

    # Drop indexes
    op.drop_index(op.f("ix_document_analytics_bounce_rate"), table_name="document_analytics")
    op.drop_index(op.f("ix_document_analytics_pageviews_trend"), table_name="document_analytics")
    op.drop_index(op.f("ix_document_analytics_pageviews_30d"), table_name="document_analytics")
    op.drop_index(op.f("ix_document_analytics_document_id"), table_name="document_analytics")

    # Drop tables
    op.drop_table("document_analytics")
    op.drop_table("analytics_domains")
