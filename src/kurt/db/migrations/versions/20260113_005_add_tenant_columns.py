"""Add tenant columns to research_documents and monitoring_signals.

Revision ID: 005_add_tenant
Revises: 004_unique_source_url
Create Date: 2026-01-13

These tables were missing user_id and workspace_id columns for multi-tenant support.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_tenant"
down_revision: Union[str, None] = "004_unique_source_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tenant columns to research_documents
    op.add_column("research_documents", sa.Column("user_id", sa.String(), nullable=True))
    op.add_column("research_documents", sa.Column("workspace_id", sa.String(), nullable=True))
    op.create_index("ix_research_documents_user_id", "research_documents", ["user_id"])
    op.create_index("ix_research_documents_workspace_id", "research_documents", ["workspace_id"])

    # Add tenant columns to monitoring_signals
    op.add_column("monitoring_signals", sa.Column("user_id", sa.String(), nullable=True))
    op.add_column("monitoring_signals", sa.Column("workspace_id", sa.String(), nullable=True))
    op.create_index("ix_monitoring_signals_user_id", "monitoring_signals", ["user_id"])
    op.create_index("ix_monitoring_signals_workspace_id", "monitoring_signals", ["workspace_id"])


def downgrade() -> None:
    # Drop indexes and columns from monitoring_signals
    op.drop_index("ix_monitoring_signals_workspace_id", "monitoring_signals")
    op.drop_index("ix_monitoring_signals_user_id", "monitoring_signals")
    op.drop_column("monitoring_signals", "workspace_id")
    op.drop_column("monitoring_signals", "user_id")

    # Drop indexes and columns from research_documents
    op.drop_index("ix_research_documents_workspace_id", "research_documents")
    op.drop_index("ix_research_documents_user_id", "research_documents")
    op.drop_column("research_documents", "workspace_id")
    op.drop_column("research_documents", "user_id")
