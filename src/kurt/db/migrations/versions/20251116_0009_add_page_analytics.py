"""Add page_analytics table

Revision ID: 009_add_page_analytics
Revises: 008_add_document_links
Create Date: 2025-11-16

This migration adds URL-based analytics tracking:
- Creates page_analytics table to store analytics independently of documents
- Stores analytics by URL (no foreign key to documents)
- Allows syncing analytics without requiring documents to exist first
- Documents can optionally join with analytics when both exist
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_add_page_analytics"
down_revision: Union[str, None] = "008_add_document_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create page_analytics table."""
    op.create_table(
        "page_analytics",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
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
        sa.Column("pageviews_trend", sa.String(), nullable=False, server_default="stable"),
        sa.Column("trend_percentage", sa.Float(), nullable=True),
        # Time window metadata
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        # Sync metadata
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_page_analytics_url",
        "page_analytics",
        ["url"],
        unique=True,
    )
    op.create_index(
        "ix_page_analytics_domain",
        "page_analytics",
        ["domain"],
        unique=False,
    )


def downgrade() -> None:
    """Drop page_analytics table."""
    op.drop_index("ix_page_analytics_domain", table_name="page_analytics")
    op.drop_index("ix_page_analytics_url", table_name="page_analytics")
    op.drop_table("page_analytics")
