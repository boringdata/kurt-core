"""Update RLS policies to enforce workspace isolation.

Revision ID: 008_rls_workspace
Revises: 007_rls_session
Create Date: 2026-01-16

This migration switches tenant isolation from user_id to workspace_id so
members of the same workspace can see shared data.
"""

from typing import Sequence, Union

from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "008_rls_workspace"
down_revision: Union[str, None] = "007_rls_session"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES_WITH_TENANT = [
    "llm_traces",
    "map_documents",
    "fetch_documents",
    "research_documents",
    "monitoring_signals",
    "analytics_domains",
    "page_analytics",
]


def upgrade() -> None:
    # Skip on SQLite - RLS is a PostgreSQL-only feature
    if context.get_context().dialect.name != "postgresql":
        return

    for table in TABLES_WITH_TENANT:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            FOR ALL USING (
                workspace_id = COALESCE(
                    current_setting('app.workspace_id', true),
                    auth.uid()::text
                )
                OR workspace_id IS NULL
            )
        """)


def downgrade() -> None:
    # Skip on SQLite
    if context.get_context().dialect.name != "postgresql":
        return

    for table in TABLES_WITH_TENANT:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            FOR ALL USING (
                user_id = COALESCE(
                    auth.uid()::text,
                    current_setting('app.user_id', true)
                )
                OR user_id IS NULL
            )
        """)
