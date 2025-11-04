"""Simplify feedback system

Revision ID: 004_simplify_feedback
Revises: 003_cms_document_id
Create Date: 2025-11-03

This migration simplifies the feedback system by:
1. Dropping unused tables (improvements, workflow_retrospectives, workflow_phase_ratings, feedback_loops)
2. Simplifying feedback_events table to only essential content feedback fields
3. Removing workflow-related and automation tracking columns

Changes to feedback_events:
- Removed: feedback_type (always content_quality now)
- Removed: workflow_id, skill_name, operation (not needed for patterns)
- Removed: issue_identified (implicit from issue_category presence)
- Removed: execution_count, prompted (automation overhead)
- Removed: telemetry_sent, telemetry_event_id (handled by telemetry system)
- Kept: id, created_at, rating, comment, issue_category, asset_path, project_id

Note: This migration preserves existing feedback data while removing workflow/automation tracking.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision: str = "004_simplify_feedback"
down_revision: Union[str, None] = "003_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = reflection.Inspector.from_engine(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Simplify feedback system tables."""

    # Drop unused tables (if they exist)
    tables_to_drop = [
        "feedback_loops",
        "workflow_phase_ratings",
        "workflow_retrospectives",
        "improvements",
    ]

    for table_name in tables_to_drop:
        if table_exists(table_name):
            op.drop_table(table_name)

    # Handle feedback_events table
    if table_exists("feedback_events"):
        # Table exists with old schema - need to recreate it
        # First, create new simplified table
        op.create_table(
            "feedback_events_new",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.String(), nullable=True),
            sa.Column("issue_category", sa.String(), nullable=True),
            sa.Column("asset_path", sa.String(), nullable=True),
            sa.Column("project_id", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating_range"),
            sa.CheckConstraint(
                "issue_category IN ('tone', 'structure', 'info', 'comprehension', 'length', 'examples', 'other') OR issue_category IS NULL",
                name="ck_issue_category",
            ),
        )

        # Copy data from old table (only the columns we want to keep)
        op.execute(
            """
            INSERT INTO feedback_events_new (id, created_at, rating, comment, issue_category, asset_path, project_id)
            SELECT id, created_at, rating, comment, issue_category, asset_path, project_id
            FROM feedback_events
            """
        )

        # Drop old table and rename new one
        op.drop_table("feedback_events")
        op.rename_table("feedback_events_new", "feedback_events")

    else:
        # Table doesn't exist - create it with the new simplified schema
        op.create_table(
            "feedback_events",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("created_at", sa.String(), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.String(), nullable=True),
            sa.Column("issue_category", sa.String(), nullable=True),
            sa.Column("asset_path", sa.String(), nullable=True),
            sa.Column("project_id", sa.String(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating_range"),
            sa.CheckConstraint(
                "issue_category IN ('tone', 'structure', 'info', 'comprehension', 'length', 'examples', 'other') OR issue_category IS NULL",
                name="ck_issue_category",
            ),
        )

    # Create indexes for the simplified feedback_events table
    op.create_index("idx_feedback_created", "feedback_events", ["created_at"], unique=False)
    op.create_index("idx_feedback_category", "feedback_events", ["issue_category"], unique=False)
    op.create_index("idx_feedback_rating", "feedback_events", ["rating"], unique=False)


def downgrade() -> None:
    """Revert to complex feedback system (not supported)."""
    # Downgrade is not supported for this migration because it would require
    # recreating all the complex tables and restoring deleted data.
    # If downgrade is needed, restore from database backup.
    raise NotImplementedError(
        "Downgrade not supported for feedback simplification. "
        "Restore from database backup if needed."
    )
