"""Add tenant columns to research_documents and monitoring_signals.

Revision ID: 005_add_tenant
Revises: 004_unique_source_url
Create Date: 2026-01-13

These tables were missing user_id and workspace_id columns for multi-tenant support.
Also ensures WORKSPACE_ID exists in kurt.config for data tagging.
"""

import re
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_tenant"
down_revision: Union[str, None] = "004_unique_source_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_workspace_id_in_config() -> None:
    """Generate and save WORKSPACE_ID to kurt.config if missing.

    This ensures existing users get a workspace identifier for data tagging,
    which is required for future migration to cloud/shared databases.
    """
    try:
        from kurt.config import get_config_file_path

        config_path = get_config_file_path()
        if not config_path.exists():
            return

        content = config_path.read_text()

        # Check if already has WORKSPACE_ID
        if re.search(r"^WORKSPACE_ID\s*=", content, re.MULTILINE):
            return  # Already exists

        # Generate new workspace ID
        workspace_id = str(uuid.uuid4())

        # Append to config file
        content += f'\n# Auto-generated workspace identifier for multi-tenant support\nWORKSPACE_ID="{workspace_id}"\n'
        config_path.write_text(content)
    except Exception:
        # Don't fail migration if config can't be updated
        pass


def upgrade() -> None:
    # Ensure WORKSPACE_ID exists in kurt.config for data tagging
    _ensure_workspace_id_in_config()
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
