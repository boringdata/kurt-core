"""Add Row Level Security policies for multi-tenant tables.

Revision ID: 006_rls
Revises: 005_add_tenant
Create Date: 2026-01-13

Note: This migration only runs on shared PostgreSQL mode.
Skipped on SQLite and Kurt Cloud (workspace schemas use schema isolation).
RLS policies ensure users can only see their own data based on user_id.
"""

from typing import Sequence, Union

from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "006_rls"
down_revision: Union[str, None] = "005_add_tenant"
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
        # Enable RLS on the table
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Create policy: users can see their own data OR data with NULL user_id (shared/public)
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            FOR ALL USING (user_id = auth.uid()::text OR user_id IS NULL)
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
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
