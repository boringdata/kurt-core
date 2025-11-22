"""Add tenant_id for multi-tenancy support.

Revision ID: 20251120_0011
Revises: 20251118_0010
Create Date: 2025-11-20

This migration adds tenant_id columns to support multi-tenant cloud deployments.

In local SQLite mode, tenant_id defaults to '00000000-0000-0000-0000-000000000000'.
In cloud PostgreSQL mode, tenant_id is set to the user's workspace ID.

Row-Level Security (RLS) policies in PostgreSQL enforce workspace isolation.

Tables Updated:
- documents: Add tenant_id
- entities: Add tenant_id
- entity_relationships: Add tenant_id
- document_entities: Add tenant_id
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251120_0011"
down_revision = "20251118_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add tenant_id columns to multi-tenant tables."""

    # Default tenant ID for local mode
    default_tenant_id = "00000000-0000-0000-0000-000000000000"

    # Check if we're using SQLite or PostgreSQL
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Add tenant_id to documents table
    with op.batch_alter_table("documents", schema=None) as batch_op:
        if is_sqlite:
            batch_op.add_column(
                sa.Column(
                    "tenant_id", sa.String(36), nullable=False, server_default=default_tenant_id
                )
            )
        else:
            # PostgreSQL uses UUID type
            batch_op.add_column(
                sa.Column(
                    "tenant_id",
                    sa.dialects.postgresql.UUID(),
                    nullable=False,
                    server_default=default_tenant_id,
                )
            )
        batch_op.create_index("ix_documents_tenant_id", ["tenant_id"])

    # Add tenant_id to entities table
    with op.batch_alter_table("entities", schema=None) as batch_op:
        if is_sqlite:
            batch_op.add_column(
                sa.Column(
                    "tenant_id", sa.String(36), nullable=False, server_default=default_tenant_id
                )
            )
        else:
            batch_op.add_column(
                sa.Column(
                    "tenant_id",
                    sa.dialects.postgresql.UUID(),
                    nullable=False,
                    server_default=default_tenant_id,
                )
            )
        batch_op.create_index("ix_entities_tenant_id", ["tenant_id"])

    # Add tenant_id to entity_relationships table
    with op.batch_alter_table("entity_relationships", schema=None) as batch_op:
        if is_sqlite:
            batch_op.add_column(
                sa.Column(
                    "tenant_id", sa.String(36), nullable=False, server_default=default_tenant_id
                )
            )
        else:
            batch_op.add_column(
                sa.Column(
                    "tenant_id",
                    sa.dialects.postgresql.UUID(),
                    nullable=False,
                    server_default=default_tenant_id,
                )
            )
        batch_op.create_index("ix_entity_relationships_tenant_id", ["tenant_id"])

    # Add tenant_id to document_entities table
    with op.batch_alter_table("document_entities", schema=None) as batch_op:
        if is_sqlite:
            batch_op.add_column(
                sa.Column(
                    "tenant_id", sa.String(36), nullable=False, server_default=default_tenant_id
                )
            )
        else:
            batch_op.add_column(
                sa.Column(
                    "tenant_id",
                    sa.dialects.postgresql.UUID(),
                    nullable=False,
                    server_default=default_tenant_id,
                )
            )
        batch_op.create_index("ix_document_entities_tenant_id", ["tenant_id"])


def downgrade() -> None:
    """Remove tenant_id columns."""

    with op.batch_alter_table("document_entities", schema=None) as batch_op:
        batch_op.drop_index("ix_document_entities_tenant_id")
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("entity_relationships", schema=None) as batch_op:
        batch_op.drop_index("ix_entity_relationships_tenant_id")
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("entities", schema=None) as batch_op:
        batch_op.drop_index("ix_entities_tenant_id")
        batch_op.drop_column("tenant_id")

    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_index("ix_documents_tenant_id")
        batch_op.drop_column("tenant_id")
