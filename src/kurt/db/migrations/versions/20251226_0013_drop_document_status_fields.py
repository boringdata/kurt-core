"""Drop status and metadata fields from documents table

Revision ID: 013_drop_document_status_fields
Revises: 012_add_section_tracking
Create Date: 2025-12-26

This migration removes duplicated fields from the documents table that are now
derived from staging tables:

Fields being removed:
- ingestion_status: Now derived from landing_fetch, staging_section_extractions
- discovery_method: Now stored in landing_discovery table
- discovery_url: Now stored in landing_discovery table
- is_chronological: No longer used
- indexed_with_git_commit: No longer used
- content_type: Now stored in staging_topic_clustering table
- has_code_examples: Now stored in staging_section_extractions.metadata_json
- has_step_by_step_procedures: Now stored in staging_section_extractions.metadata_json
- has_narrative_structure: Now stored in staging_section_extractions.metadata_json

The design principle is:
- documents table = minimal identity (id, title, source_url, content_path, etc.)
- Staging tables = source of truth for step-specific data
- Status/metadata derived on the fly via get_document_status() and get_document_with_metadata()

Related Issue: Document table refactoring
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013_drop_document_status_fields"
down_revision: Union[str, None] = "012_add_section_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Drop deprecated status and metadata fields from documents table.

    Data is preserved in staging tables:
    - Status: landing_discovery, landing_fetch, staging_section_extractions
    - Metadata: staging_topic_clustering, staging_section_extractions

    Note: For fresh databases, these columns don't exist (removed from initial schema).
    This migration only drops columns from existing databases that were created before
    the schema was updated.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Step 1: Recreate the metadata_sync_trigger without removed columns
    # The old trigger may reference content_type which is being dropped
    print("  Recreating metadata_sync_trigger without removed columns...")
    op.execute("DROP TRIGGER IF EXISTS documents_metadata_sync_trigger")
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_metadata_sync_trigger
        AFTER UPDATE ON documents
        WHEN (
            NEW.title != OLD.title OR
            NEW.description != OLD.description OR
            NEW.author != OLD.author OR
            NEW.published_date != OLD.published_date OR
            NEW.indexed_with_hash != OLD.indexed_with_hash
        )
        BEGIN
            INSERT INTO metadata_sync_queue (document_id, created_at)
            VALUES (NEW.id, datetime('now'));
        END;
    """)

    # Step 2: Check which columns actually exist
    if dialect == "sqlite":
        result = conn.execute(sa.text("PRAGMA table_info(documents)"))
        existing_columns = {row[1] for row in result}
    else:
        # PostgreSQL
        result = conn.execute(
            sa.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'documents'
        """)
        )
        existing_columns = {row[0] for row in result}

    # List of columns to drop
    columns_to_drop = [
        "ingestion_status",
        "discovery_method",
        "discovery_url",
        "is_chronological",
        "indexed_with_git_commit",
        "content_type",
        "has_code_examples",
        "has_step_by_step_procedures",
        "has_narrative_structure",
    ]

    # Only drop columns that exist
    columns_to_drop = [col for col in columns_to_drop if col in existing_columns]

    if not columns_to_drop:
        print("  No deprecated columns to drop (fresh database)")
        return

    if dialect == "sqlite":
        # SQLite: Use batch mode for column drops
        with op.batch_alter_table("documents", schema=None) as batch_op:
            for col in columns_to_drop:
                try:
                    batch_op.drop_column(col)
                    print(f"  Dropped column: {col}")
                except Exception as e:
                    print(f"  Skipping column {col}: {e}")
    else:
        # PostgreSQL and others: Direct column drop
        for col in columns_to_drop:
            try:
                op.drop_column("documents", col)
                print(f"  Dropped column: {col}")
            except Exception as e:
                print(f"  Skipping column {col}: {e}")


def downgrade() -> None:
    """
    Restore status and metadata fields to documents table.

    NOTE: This only recreates the columns with NULL values.
    Data would need to be backfilled from staging tables if needed.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("ingestion_status", sa.String(), nullable=True, default="NOT_FETCHED")
            )
            batch_op.add_column(sa.Column("discovery_method", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("discovery_url", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("is_chronological", sa.Boolean(), nullable=True))
            batch_op.add_column(sa.Column("indexed_with_git_commit", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("content_type", sa.String(), nullable=True))
            batch_op.add_column(sa.Column("has_code_examples", sa.Boolean(), nullable=True))
            batch_op.add_column(
                sa.Column("has_step_by_step_procedures", sa.Boolean(), nullable=True)
            )
            batch_op.add_column(sa.Column("has_narrative_structure", sa.Boolean(), nullable=True))
    else:
        op.add_column(
            "documents",
            sa.Column("ingestion_status", sa.String(), nullable=True, server_default="NOT_FETCHED"),
        )
        op.add_column("documents", sa.Column("discovery_method", sa.String(), nullable=True))
        op.add_column("documents", sa.Column("discovery_url", sa.String(), nullable=True))
        op.add_column("documents", sa.Column("is_chronological", sa.Boolean(), nullable=True))
        op.add_column("documents", sa.Column("indexed_with_git_commit", sa.String(), nullable=True))
        op.add_column("documents", sa.Column("content_type", sa.String(), nullable=True))
        op.add_column("documents", sa.Column("has_code_examples", sa.Boolean(), nullable=True))
        op.add_column(
            "documents", sa.Column("has_step_by_step_procedures", sa.Boolean(), nullable=True)
        )
        op.add_column(
            "documents", sa.Column("has_narrative_structure", sa.Boolean(), nullable=True)
        )
