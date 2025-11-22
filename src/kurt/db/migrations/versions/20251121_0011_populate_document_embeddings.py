"""Populate document_embeddings vector table

Revision ID: 011_populate_document_embeddings
Revises: 010_drop_metadata_fields
Create Date: 2025-11-21

This migration populates the document_embeddings virtual table for vector search:
- Ensures document_embeddings vec0 virtual table exists
- Populates it with existing document embeddings from documents table
- Enables semantic search on documents
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_populate_document_embeddings"
down_revision: Union[str, None] = "010_drop_metadata_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create and populate document_embeddings virtual table."""
    conn = op.get_bind()

    # Create document_embeddings virtual table (vec0 extension)
    # Note: This will silently fail if sqlite-vec extension is not available,
    # which is OK - vector search features just won't work in that case
    try:
        conn.execute(
            sa.text(
                """
            CREATE VIRTUAL TABLE IF NOT EXISTS document_embeddings
            USING vec0(
                document_id TEXT PRIMARY KEY,
                embedding float[512]
            )
            """
            )
        )
        conn.commit()
    except Exception as e:
        print(
            f"Warning: Could not create document_embeddings table (sqlite-vec not available): {e}"
        )
        return

    # Populate document_embeddings from existing documents.embedding
    # Only insert documents that have embeddings
    try:
        conn.execute(
            sa.text(
                """
            INSERT INTO document_embeddings (document_id, embedding)
            SELECT id, embedding
            FROM documents
            WHERE embedding IS NOT NULL AND embedding != ''
            """
            )
        )
        conn.commit()
        print("Successfully populated document_embeddings vector table")
    except Exception as e:
        print(f"Warning: Could not populate document_embeddings: {e}")


def downgrade() -> None:
    """Drop document_embeddings virtual table."""
    conn = op.get_bind()

    try:
        conn.execute(sa.text("DROP TABLE IF EXISTS document_embeddings"))
        conn.commit()
    except Exception:
        # Silently fail - table might not exist
        pass
