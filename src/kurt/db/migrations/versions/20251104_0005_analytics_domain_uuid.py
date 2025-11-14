"""Add UUID primary key to analytics_domains

Revision ID: 005_analytics_domain_uuid
Revises: 004_simplify_feedback
Create Date: 2025-11-04

This migration changes analytics_domains table:
- Adds UUID id field as primary key
- Changes domain from primary key to unique indexed field
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_analytics_domain_uuid"
down_revision: Union[str, None] = "004_simplify_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add UUID id field to analytics_domains."""

    # SQLite doesn't support ALTER TABLE for complex changes
    # We need to recreate the table with the new schema

    # 1. Rename old table
    op.rename_table("analytics_domains", "analytics_domains_old")

    # 2. Create new table with UUID id
    op.create_table(
        "analytics_domains",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("has_data", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sync_period_days", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create unique index on domain
    op.create_index(
        op.f("ix_analytics_domains_domain"),
        "analytics_domains",
        ["domain"],
        unique=True,
    )

    # 4. Copy data from old table (generate UUIDs for existing rows)
    op.execute("""
        INSERT INTO analytics_domains (id, domain, platform, has_data, last_synced_at, sync_period_days, created_at, updated_at)
        SELECT
            lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(6))) as id,
            domain,
            platform,
            has_data,
            last_synced_at,
            sync_period_days,
            created_at,
            updated_at
        FROM analytics_domains_old
    """)

    # 5. Drop old table
    op.drop_table("analytics_domains_old")


def downgrade() -> None:
    """Revert to domain as primary key."""

    # 1. Rename current table
    op.rename_table("analytics_domains", "analytics_domains_new")

    # 2. Recreate old table structure (domain as primary key)
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

    # 3. Copy data (drop id column)
    op.execute("""
        INSERT INTO analytics_domains (domain, platform, has_data, last_synced_at, sync_period_days, created_at, updated_at)
        SELECT domain, platform, has_data, last_synced_at, sync_period_days, created_at, updated_at
        FROM analytics_domains_new
    """)

    # 4. Drop new table
    op.drop_table("analytics_domains_new")
