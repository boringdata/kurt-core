"""Update RLS policies to enforce workspace isolation.

Revision ID: 008_rls_workspace
Revises: 007_rls_session
Create Date: 2026-01-16

This migration switches tenant isolation from user_id to workspace_id so
members of the same workspace can see shared data.

Behavior by mode:
- SQLite: Skipped (RLS not supported)
- Shared PostgreSQL: RLS policies applied to public schema tables
- Kurt Cloud: Skipped (workspace schemas use schema isolation, not RLS)

The migration detects workspace schemas (ws_*) and skips RLS policy creation
since schema-based isolation provides stronger security guarantees.
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

    # Skip in cloud mode (workspace schemas) - schema isolation handles multi-tenancy
    # Check if running in a workspace schema (ws_*)
    conn = op.get_bind()
    result = conn.execute("SELECT current_schema()")
    current_schema = result.scalar()

    if current_schema and current_schema.startswith("ws_"):
        # Cloud mode: schema-based isolation, no RLS needed
        return

    # Apply RLS for shared PostgreSQL mode (all workspaces share public schema)
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

    # Skip in cloud mode (workspace schemas)
    conn = op.get_bind()
    result = conn.execute("SELECT current_schema()")
    current_schema = result.scalar()

    if current_schema and current_schema.startswith("ws_"):
        return

    # Downgrade RLS for shared PostgreSQL mode
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
