"""Update RLS policies to support session variables for CLI connections.

Revision ID: 007_rls_session
Revises: 006_rls
Create Date: 2026-01-15

Note: Only applies to shared PostgreSQL mode.
Skipped on SQLite and Kurt Cloud (workspace schemas use schema isolation).

The previous RLS policies only used auth.uid() which works for Supabase SDK
connections but not for direct PostgreSQL connections (CLI via pooler).

This migration updates policies to also check session variables:
- app.user_id: Set by CLI via SET LOCAL app.user_id = '...'
- auth.uid(): Set by Supabase SDK from JWT

Security model:
1. Supabase SDK: auth.uid() is automatically set from JWT
2. CLI via pooler: app.user_id is set via SET LOCAL at session start

Both methods are secure because:
- Supabase SDK validates JWT before setting auth.uid()
- CLI validates JWT against Supabase API before getting pooler connection
- Pooler connections require valid auth token
"""

from typing import Sequence, Union

from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "007_rls_session"
down_revision: Union[str, None] = "006_rls"
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
    conn = op.get_bind()
    result = conn.execute("SELECT current_schema()")
    current_schema = result.scalar()

    if current_schema and current_schema.startswith("ws_"):
        return

    # Apply RLS for shared PostgreSQL mode
    for table in TABLES_WITH_TENANT:
        # Drop old policy
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

        # Create new policy that checks both auth.uid() and session variable
        # - auth.uid()::text: Supabase SDK connections (JWT auth)
        # - current_setting('app.user_id', true): CLI pooler connections
        # - user_id IS NULL: Shared/public data
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
        # Revert to auth.uid()-only policy
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            FOR ALL USING (user_id = auth.uid()::text OR user_id IS NULL)
        """)
