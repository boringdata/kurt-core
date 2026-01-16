"""Add foreign key and view for document lifecycle JOIN.

Revision ID: 84688a81b9ab
Revises: 007_rls_session
Create Date: 2026-01-15 14:19:32.172281+00:00

This migration adds:
1. Foreign key from fetch_documents.document_id to map_documents.document_id
2. View `document_lifecycle` that joins map_documents and fetch_documents

The view enables:
- PostgREST to query the joined data efficiently
- Database-level JOIN instead of Python-side JOIN
- Existing code to work in cloud mode without changes
"""

from typing import Sequence, Union

from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "84688a81b9ab"
down_revision: Union[str, None] = "007_rls_session"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Skip on SQLite - foreign keys and views work differently
    if context.get_context().dialect.name != "postgresql":
        return

    # Clean up orphaned fetch_documents (no matching map_document)
    op.execute("""
        DELETE FROM fetch_documents
        WHERE document_id NOT IN (SELECT document_id FROM map_documents)
    """)

    # Add foreign key constraint
    op.execute("""
        ALTER TABLE fetch_documents
        ADD CONSTRAINT fk_fetch_documents_map_documents
        FOREIGN KEY (document_id)
        REFERENCES map_documents(document_id)
        ON DELETE CASCADE
    """)

    # Create view for document lifecycle (map + fetch)
    # This view combines data from both tables with a LEFT OUTER JOIN
    # Prefix fetch columns to avoid conflicts with map columns
    op.execute("""
        CREATE VIEW document_lifecycle AS
        SELECT
            m.*,
            f.status as fetch_status,
            f.content_length as fetch_content_length,
            f.content_hash as fetch_content_hash,
            f.content_path,
            f.fetch_engine,
            f.public_url,
            f.error as fetch_error,
            f.metadata_json as fetch_metadata_json,
            f.embedding,
            f.created_at as fetch_created_at,
            f.updated_at as fetch_updated_at
        FROM map_documents m
        LEFT OUTER JOIN fetch_documents f
        ON m.document_id = f.document_id
    """)


def downgrade() -> None:
    # Skip on SQLite
    if context.get_context().dialect.name != "postgresql":
        return

    # Drop view first
    op.execute("DROP VIEW IF EXISTS document_lifecycle")

    # Drop foreign key
    op.execute("""
        ALTER TABLE fetch_documents
        DROP CONSTRAINT IF EXISTS fk_fetch_documents_map_documents
    """)
