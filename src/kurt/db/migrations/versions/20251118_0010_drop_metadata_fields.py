"""Drop deprecated metadata fields from documents table

Revision ID: 010_drop_metadata_fields
Revises: 009_add_page_analytics
Create Date: 2025-11-18

This migration:
1. Migrates data from primary_topics/tools_technologies to knowledge graph entities
2. Drops the deprecated Document.primary_topics and Document.tools_technologies fields

The data migration creates Entity records for topics and technologies, and links them
to documents via DocumentEntity relationships.

NOTE: Embedding fields are KEPT as they are used for vector search in entity_embeddings table.

Related Issue: #16 - Data Model Simplification
"""

import json
from datetime import datetime
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON, text

# revision identifiers, used by Alembic.
revision: str = "010_drop_metadata_fields"
down_revision: Union[str, None] = "009_add_page_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def migrate_metadata_to_entities(conn) -> dict:
    """
    Migrate primary_topics and tools_technologies from documents to entities.

    Returns:
        Dictionary with migration statistics
    """
    stats = {
        "topics_created": 0,
        "tools_created": 0,
        "topics_linked": 0,
        "tools_linked": 0,
    }

    # Get documents with metadata using raw SQL
    result = conn.execute(
        text("""
        SELECT id, title, source_url, primary_topics, tools_technologies
        FROM documents
        WHERE primary_topics IS NOT NULL OR tools_technologies IS NOT NULL
    """)
    )

    for doc_id, title, source_url, topics_json, tools_json in result:
        # Parse JSON fields - ensure we always get a list even if JSON contains null
        try:
            topics = json.loads(topics_json) if topics_json else []
            if not isinstance(topics, list):
                topics = []
        except (json.JSONDecodeError, TypeError):
            topics = []

        try:
            tools = json.loads(tools_json) if tools_json else []
            if not isinstance(tools, list):
                tools = []
        except (json.JSONDecodeError, TypeError):
            tools = []

        # Get existing entity links for this document
        existing_entity_ids = {
            row[0]
            for row in conn.execute(
                text("SELECT entity_id FROM document_entities WHERE document_id = :doc_id"),
                {"doc_id": doc_id},
            )
        }

        # Migrate topics
        for topic_name in topics:
            # Check if topic entity already exists
            existing = conn.execute(
                text("""
                SELECT id FROM entities
                WHERE entity_type = 'Topic'
                AND (name = :name OR canonical_name = :name)
            """),
                {"name": topic_name},
            ).fetchone()

            if existing:
                topic_id = existing[0]
                if topic_id not in existing_entity_ids:
                    # Link existing entity
                    conn.execute(
                        text("""
                        INSERT INTO document_entities (
                            id, document_id, entity_id, mention_count, confidence,
                            context, created_at, updated_at
                        ) VALUES (
                            :id, :doc_id, :entity_id, :mentions, :confidence,
                            :context, :created_at, :updated_at
                        )
                    """),
                        {
                            "id": uuid4().hex,
                            "doc_id": doc_id,
                            "entity_id": topic_id,
                            "mentions": 1,
                            "confidence": 0.8,
                            "context": f"Migrated from document metadata: {title or source_url}",
                            "created_at": datetime.now(),
                            "updated_at": datetime.now(),
                        },
                    )
                    stats["topics_linked"] += 1
            else:
                # Create new topic entity
                topic_id = uuid4().hex
                conn.execute(
                    text("""
                    INSERT INTO entities (
                        id, name, entity_type, canonical_name, description,
                        confidence_score, source_mentions, created_at, updated_at
                    ) VALUES (
                        :id, :name, :type, :canonical, :desc,
                        :confidence, :mentions, :created_at, :updated_at
                    )
                """),
                    {
                        "id": topic_id,
                        "name": topic_name,
                        "type": "Topic",
                        "canonical": topic_name,
                        "desc": "Topic migrated from document metadata",
                        "confidence": 0.8,
                        "mentions": 1,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    },
                )

                # Link to document
                conn.execute(
                    text("""
                    INSERT INTO document_entities (
                        id, document_id, entity_id, mention_count, confidence,
                        context, created_at, updated_at
                    ) VALUES (
                        :id, :doc_id, :entity_id, :mentions, :confidence,
                        :context, :created_at, :updated_at
                    )
                """),
                    {
                        "id": uuid4().hex,
                        "doc_id": doc_id,
                        "entity_id": topic_id,
                        "mentions": 1,
                        "confidence": 0.8,
                        "context": f"Migrated from document metadata: {title or source_url}",
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    },
                )

                stats["topics_created"] += 1
                stats["topics_linked"] += 1

        # Migrate tools/technologies (similar logic)
        for tool_name in tools:
            existing = conn.execute(
                text("""
                SELECT id FROM entities
                WHERE entity_type IN ('Technology', 'Tool', 'Product')
                AND (name = :name OR canonical_name = :name)
            """),
                {"name": tool_name},
            ).fetchone()

            if existing:
                tool_id = existing[0]
                if tool_id not in existing_entity_ids:
                    conn.execute(
                        text("""
                        INSERT INTO document_entities (
                            id, document_id, entity_id, mention_count, confidence,
                            context, created_at, updated_at
                        ) VALUES (
                            :id, :doc_id, :entity_id, :mentions, :confidence,
                            :context, :created_at, :updated_at
                        )
                    """),
                        {
                            "id": uuid4().hex,
                            "doc_id": doc_id,
                            "entity_id": tool_id,
                            "mentions": 1,
                            "confidence": 0.8,
                            "context": f"Migrated from document metadata: {title or source_url}",
                            "created_at": datetime.now(),
                            "updated_at": datetime.now(),
                        },
                    )
                    stats["tools_linked"] += 1
            else:
                tool_id = uuid4().hex
                conn.execute(
                    text("""
                    INSERT INTO entities (
                        id, name, entity_type, canonical_name, description,
                        confidence_score, source_mentions, created_at, updated_at
                    ) VALUES (
                        :id, :name, :type, :canonical, :desc,
                        :confidence, :mentions, :created_at, :updated_at
                    )
                """),
                    {
                        "id": tool_id,
                        "name": tool_name,
                        "type": "Technology",
                        "canonical": tool_name,
                        "desc": "Technology migrated from document metadata",
                        "confidence": 0.8,
                        "mentions": 1,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    },
                )

                conn.execute(
                    text("""
                    INSERT INTO document_entities (
                        id, document_id, entity_id, mention_count, confidence,
                        context, created_at, updated_at
                    ) VALUES (
                        :id, :doc_id, :entity_id, :mentions, :confidence,
                        :context, :created_at, :updated_at
                    )
                """),
                    {
                        "id": uuid4().hex,
                        "doc_id": doc_id,
                        "entity_id": tool_id,
                        "mentions": 1,
                        "confidence": 0.8,
                        "context": f"Migrated from document metadata: {title or source_url}",
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    },
                )

                stats["tools_created"] += 1
                stats["tools_linked"] += 1

    return stats


def upgrade() -> None:
    """
    Migrate metadata to entities, then drop deprecated fields.

    This is done in one migration to ensure atomicity.
    """
    conn = op.get_bind()

    # Step 1: Migrate data from metadata fields to knowledge graph
    print("Migrating metadata to entities...")
    stats = migrate_metadata_to_entities(conn)

    if stats["topics_created"] > 0 or stats["tools_created"] > 0:
        print(f"  Created {stats['topics_created']} topics, {stats['tools_created']} tools")
        print(
            f"  Linked {stats['topics_linked']} topic relationships, {stats['tools_linked']} tool relationships"
        )
    else:
        print("  No metadata to migrate")

    # Step 2: Drop the deprecated columns
    dialect = conn.dialect.name

    if dialect == "sqlite":
        # SQLite: Recreate table without deprecated columns
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.drop_column("primary_topics")
            batch_op.drop_column("tools_technologies")
    elif dialect == "postgresql":
        # PostgreSQL: Direct column drop
        op.drop_column("documents", "primary_topics")
        op.drop_column("documents", "tools_technologies")
    else:
        # For other databases, try direct drop
        op.drop_column("documents", "primary_topics")
        op.drop_column("documents", "tools_technologies")


def downgrade() -> None:
    """
    Restore deprecated metadata fields.

    NOTE: This only recreates the columns - it does NOT restore the data!
    You would need to manually backfill from the knowledge graph if needed.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "sqlite":
        # SQLite: Add columns back
        with op.batch_alter_table("documents", schema=None) as batch_op:
            batch_op.add_column(sa.Column("primary_topics", JSON, nullable=True))
            batch_op.add_column(sa.Column("tools_technologies", JSON, nullable=True))

    elif dialect == "postgresql":
        # PostgreSQL: Direct column add
        op.add_column("documents", sa.Column("primary_topics", JSON, nullable=True))
        op.add_column("documents", sa.Column("tools_technologies", JSON, nullable=True))

    else:
        # For other databases
        op.add_column("documents", sa.Column("primary_topics", JSON, nullable=True))
        op.add_column("documents", sa.Column("tools_technologies", JSON, nullable=True))
