#!/usr/bin/env python3
"""
Migrate Document.primary_topics and Document.tools_technologies to Knowledge Graph entities.

This script backfills the knowledge graph from existing document metadata fields,
creating Entity records for topics and technologies that were previously stored as JSON arrays.

Issue: #16 - Data Model Simplification

Usage:
    python scripts/migrate_metadata_to_entities.py
    python scripts/migrate_metadata_to_entities.py --dry-run
    python scripts/migrate_metadata_to_entities.py --batch-size 50
"""

import argparse
import logging
from uuid import uuid4

from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, DocumentEntity, Entity

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def migrate_document_topics_and_tools(
    document: Document,
    dry_run: bool = False,
) -> dict:
    """
    Migrate topics and tools from document metadata to knowledge graph entities.

    Args:
        document: Document to migrate
        dry_run: If True, don't actually create entities (just report)

    Returns:
        Dictionary with migration stats:
            - topics_created: int
            - tools_created: int
            - topics_linked: int
            - tools_linked: int
            - topics_skipped: int (already exist as entities)
            - tools_skipped: int (already exist as entities)
    """
    session = get_session()
    stats = {
        "topics_created": 0,
        "tools_created": 0,
        "topics_linked": 0,
        "tools_linked": 0,
        "topics_skipped": 0,
        "tools_skipped": 0,
    }

    # Check if document already has entities linked
    existing_entity_ids = set()
    existing_links = session.exec(
        select(DocumentEntity).where(DocumentEntity.document_id == document.id)
    ).all()
    existing_entity_ids = {link.entity_id for link in existing_links}

    if existing_entity_ids:
        logger.debug(
            f"  Document {document.id} already has {len(existing_entity_ids)} entities linked"
        )

    # Migrate topics
    if document.primary_topics:
        for topic_name in document.primary_topics:
            # Check if topic entity already exists
            existing_topic = session.exec(
                select(Entity)
                .where(Entity.entity_type == "Topic")
                .where((Entity.name == topic_name) | (Entity.canonical_name == topic_name))
            ).first()

            if existing_topic:
                # Entity exists, check if already linked to this document
                if existing_topic.id in existing_entity_ids:
                    stats["topics_skipped"] += 1
                    logger.debug(f"  Topic '{topic_name}' already linked to document")
                else:
                    # Link existing entity to document
                    if not dry_run:
                        doc_entity = DocumentEntity(
                            document_id=document.id,
                            entity_id=existing_topic.id,
                            mention_count=1,
                            confidence=0.8,  # Moderate confidence for metadata-derived links
                            context=f"Migrated from document metadata: {document.title or document.source_url}",
                        )
                        session.add(doc_entity)
                    stats["topics_linked"] += 1
                    logger.debug(f"  Linked existing topic '{topic_name}' to document")
            else:
                # Create new topic entity
                if not dry_run:
                    new_topic = Entity(
                        id=uuid4(),
                        name=topic_name,
                        entity_type="Topic",
                        canonical_name=topic_name,
                        description="Topic migrated from document metadata",
                        confidence_score=0.8,
                        source_mentions=1,
                    )
                    session.add(new_topic)
                    session.flush()  # Get the ID

                    # Link to document
                    doc_entity = DocumentEntity(
                        document_id=document.id,
                        entity_id=new_topic.id,
                        mention_count=1,
                        confidence=0.8,
                        context=f"Migrated from document metadata: {document.title or document.source_url}",
                    )
                    session.add(doc_entity)

                stats["topics_created"] += 1
                stats["topics_linked"] += 1
                logger.debug(f"  Created and linked new topic '{topic_name}'")

    # Migrate tools/technologies
    if document.tools_technologies:
        for tool_name in document.tools_technologies:
            # Check if tool entity already exists (check multiple types)
            existing_tool = session.exec(
                select(Entity)
                .where(Entity.entity_type.in_(["Technology", "Tool", "Product"]))
                .where((Entity.name == tool_name) | (Entity.canonical_name == tool_name))
            ).first()

            if existing_tool:
                # Entity exists, check if already linked to this document
                if existing_tool.id in existing_entity_ids:
                    stats["tools_skipped"] += 1
                    logger.debug(f"  Tool '{tool_name}' already linked to document")
                else:
                    # Link existing entity to document
                    if not dry_run:
                        doc_entity = DocumentEntity(
                            document_id=document.id,
                            entity_id=existing_tool.id,
                            mention_count=1,
                            confidence=0.8,
                            context=f"Migrated from document metadata: {document.title or document.source_url}",
                        )
                        session.add(doc_entity)
                    stats["tools_linked"] += 1
                    logger.debug(f"  Linked existing tool '{tool_name}' to document")
            else:
                # Create new tool entity (default to "Technology" type)
                if not dry_run:
                    new_tool = Entity(
                        id=uuid4(),
                        name=tool_name,
                        entity_type="Technology",
                        canonical_name=tool_name,
                        description="Technology migrated from document metadata",
                        confidence_score=0.8,
                        source_mentions=1,
                    )
                    session.add(new_tool)
                    session.flush()

                    # Link to document
                    doc_entity = DocumentEntity(
                        document_id=document.id,
                        entity_id=new_tool.id,
                        mention_count=1,
                        confidence=0.8,
                        context=f"Migrated from document metadata: {document.title or document.source_url}",
                    )
                    session.add(doc_entity)

                stats["tools_created"] += 1
                stats["tools_linked"] += 1
                logger.debug(f"  Created and linked new tool '{tool_name}'")

    # Commit changes
    if not dry_run:
        session.commit()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Migrate document metadata (topics/tools) to knowledge graph entities"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually changing the database",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of documents to process in each batch (default: 100)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of documents to process (for testing)",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made to the database\n")

    session = get_session()

    # Get all documents with metadata (topics or tools)
    stmt = select(Document).where(
        (Document.primary_topics.is_not(None)) | (Document.tools_technologies.is_not(None))
    )

    if args.limit:
        stmt = stmt.limit(args.limit)

    documents = session.exec(stmt).all()

    if not documents:
        logger.info("✅ No documents with metadata found - nothing to migrate")
        return

    logger.info(f"Found {len(documents)} documents with topics or tools in metadata\n")

    # Process in batches
    total_stats = {
        "topics_created": 0,
        "tools_created": 0,
        "topics_linked": 0,
        "tools_linked": 0,
        "topics_skipped": 0,
        "tools_skipped": 0,
        "documents_processed": 0,
        "documents_with_topics": 0,
        "documents_with_tools": 0,
    }

    for i, doc in enumerate(documents):
        logger.info(
            f"Processing {i+1}/{len(documents)}: {doc.title or doc.source_url or doc.content_path} ({doc.id})"
        )

        # Migrate this document
        doc_stats = migrate_document_topics_and_tools(doc, dry_run=args.dry_run)

        # Accumulate stats
        for key in doc_stats:
            total_stats[key] += doc_stats[key]

        total_stats["documents_processed"] += 1
        if doc.primary_topics:
            total_stats["documents_with_topics"] += 1
        if doc.tools_technologies:
            total_stats["documents_with_tools"] += 1

        # Log batch progress
        if (i + 1) % args.batch_size == 0:
            logger.info(
                f"\n--- Batch {(i+1)//args.batch_size} complete ({i+1}/{len(documents)} docs) ---"
            )
            logger.info(f"  Topics created: {total_stats['topics_created']}")
            logger.info(f"  Tools created: {total_stats['tools_created']}")
            logger.info(f"  Topics linked: {total_stats['topics_linked']}")
            logger.info(f"  Tools linked: {total_stats['tools_linked']}\n")

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Documents processed: {total_stats['documents_processed']}")
    logger.info(f"  - With topics: {total_stats['documents_with_topics']}")
    logger.info(f"  - With tools: {total_stats['documents_with_tools']}")
    logger.info("")
    logger.info("Topics:")
    logger.info(f"  - Created: {total_stats['topics_created']}")
    logger.info(
        f"  - Linked (existing): {total_stats['topics_linked'] - total_stats['topics_created']}"
    )
    logger.info(f"  - Skipped (already linked): {total_stats['topics_skipped']}")
    logger.info(f"  - Total links: {total_stats['topics_linked']}")
    logger.info("")
    logger.info("Tools/Technologies:")
    logger.info(f"  - Created: {total_stats['tools_created']}")
    logger.info(
        f"  - Linked (existing): {total_stats['tools_linked'] - total_stats['tools_created']}"
    )
    logger.info(f"  - Skipped (already linked): {total_stats['tools_skipped']}")
    logger.info(f"  - Total links: {total_stats['tools_linked']}")
    logger.info("")

    if args.dry_run:
        logger.info("🔍 DRY RUN COMPLETE - No changes were made")
    else:
        logger.info("✅ MIGRATION COMPLETE")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Verify migration: python scripts/verify_metadata_migration.py")
        logger.info("  2. Test queries: kurt content list-topics, kurt content list-technologies")
        logger.info("  3. If everything looks good, you can drop the old fields with:")
        logger.info("     alembic revision -m 'drop_metadata_fields'")


if __name__ == "__main__":
    main()
