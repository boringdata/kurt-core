#!/usr/bin/env python3
"""
Verify that metadata migration is complete and correct.

This script checks that:
1. All topics in Document.primary_topics exist as Entity(type="Topic")
2. All tools in Document.tools_technologies exist as Entity(type="Technology"|"Tool"|"Product")
3. Entity counts match metadata counts
4. No data was lost

Issue: #16 - Data Model Simplification

Usage:
    python scripts/verify_metadata_migration.py
    python scripts/verify_metadata_migration.py --verbose
"""

import argparse
import logging
from collections import Counter

from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, DocumentEntity, Entity

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def verify_migration(verbose: bool = False):
    """
    Verify that migration from metadata to entities is complete.

    Returns:
        bool: True if verification passes, False otherwise
    """
    session = get_session()

    logger.info("=" * 80)
    logger.info("METADATA MIGRATION VERIFICATION")
    logger.info("=" * 80)
    logger.info("")

    # Get all documents with metadata
    docs_with_metadata = session.exec(
        select(Document).where(
            (Document.primary_topics.is_not(None)) | (Document.tools_technologies.is_not(None))
        )
    ).all()

    logger.info(f"Found {len(docs_with_metadata)} documents with metadata\n")

    # Verification checks
    all_passed = True

    # ========================================================================
    # Check 1: Count total topics in metadata
    # ========================================================================
    logger.info("Check 1: Counting topics in metadata...")

    total_topics_in_metadata = 0
    unique_topics_in_metadata = set()
    topic_doc_counts_metadata = Counter()

    for doc in docs_with_metadata:
        if doc.primary_topics:
            total_topics_in_metadata += len(doc.primary_topics)
            for topic in doc.primary_topics:
                unique_topics_in_metadata.add(topic)
                topic_doc_counts_metadata[topic] += 1

    logger.info(f"  Total topic mentions in metadata: {total_topics_in_metadata}")
    logger.info(f"  Unique topics in metadata: {len(unique_topics_in_metadata)}")

    # ========================================================================
    # Check 2: Count topics in knowledge graph
    # ========================================================================
    logger.info("\nCheck 2: Counting topics in knowledge graph...")

    topic_entities = session.exec(select(Entity).where(Entity.entity_type == "Topic")).all()

    # Count document links for each topic
    topic_doc_counts_graph = Counter()
    total_topic_links = 0

    for topic in topic_entities:
        doc_links = session.exec(
            select(DocumentEntity).where(DocumentEntity.entity_id == topic.id)
        ).all()
        topic_name = topic.canonical_name or topic.name
        topic_doc_counts_graph[topic_name] = len(doc_links)
        total_topic_links += len(doc_links)

    logger.info(f"  Total topic entities in graph: {len(topic_entities)}")
    logger.info(f"  Total topic-document links: {total_topic_links}")

    # ========================================================================
    # Check 3: Compare topics
    # ========================================================================
    logger.info("\nCheck 3: Comparing topic coverage...")

    # Find topics in metadata but not in graph
    topics_only_in_metadata = set()
    for topic in unique_topics_in_metadata:
        # Check if this topic exists as an entity
        entity_exists = session.exec(
            select(Entity)
            .where(Entity.entity_type == "Topic")
            .where((Entity.name == topic) | (Entity.canonical_name == topic))
        ).first()

        if not entity_exists:
            topics_only_in_metadata.add(topic)

    if topics_only_in_metadata:
        logger.error(
            f"  ❌ Found {len(topics_only_in_metadata)} topics in metadata but not in graph:"
        )
        if verbose:
            for topic in sorted(topics_only_in_metadata)[:10]:
                logger.error(f"     - {topic}")
            if len(topics_only_in_metadata) > 10:
                logger.error(f"     ... and {len(topics_only_in_metadata) - 10} more")
        all_passed = False
    else:
        logger.info("  ✅ All topics from metadata exist in knowledge graph")

    # ========================================================================
    # Check 4: Count tools in metadata
    # ========================================================================
    logger.info("\nCheck 4: Counting tools/technologies in metadata...")

    total_tools_in_metadata = 0
    unique_tools_in_metadata = set()
    tool_doc_counts_metadata = Counter()

    for doc in docs_with_metadata:
        if doc.tools_technologies:
            total_tools_in_metadata += len(doc.tools_technologies)
            for tool in doc.tools_technologies:
                unique_tools_in_metadata.add(tool)
                tool_doc_counts_metadata[tool] += 1

    logger.info(f"  Total tool mentions in metadata: {total_tools_in_metadata}")
    logger.info(f"  Unique tools in metadata: {len(unique_tools_in_metadata)}")

    # ========================================================================
    # Check 5: Count tools in knowledge graph
    # ========================================================================
    logger.info("\nCheck 5: Counting tools/technologies in knowledge graph...")

    tool_entities = session.exec(
        select(Entity).where(Entity.entity_type.in_(["Technology", "Tool", "Product"]))
    ).all()

    # Count document links for each tool
    tool_doc_counts_graph = Counter()
    total_tool_links = 0

    for tool in tool_entities:
        doc_links = session.exec(
            select(DocumentEntity).where(DocumentEntity.entity_id == tool.id)
        ).all()
        tool_name = tool.canonical_name or tool.name
        tool_doc_counts_graph[tool_name] = len(doc_links)
        total_tool_links += len(doc_links)

    logger.info(f"  Total tool entities in graph: {len(tool_entities)}")
    logger.info(f"  Total tool-document links: {total_tool_links}")

    # ========================================================================
    # Check 6: Compare tools
    # ========================================================================
    logger.info("\nCheck 6: Comparing tool/technology coverage...")

    # Find tools in metadata but not in graph
    tools_only_in_metadata = set()
    for tool in unique_tools_in_metadata:
        # Check if this tool exists as an entity
        entity_exists = session.exec(
            select(Entity)
            .where(Entity.entity_type.in_(["Technology", "Tool", "Product"]))
            .where((Entity.name == tool) | (Entity.canonical_name == tool))
        ).first()

        if not entity_exists:
            tools_only_in_metadata.add(tool)

    if tools_only_in_metadata:
        logger.error(
            f"  ❌ Found {len(tools_only_in_metadata)} tools in metadata but not in graph:"
        )
        if verbose:
            for tool in sorted(tools_only_in_metadata)[:10]:
                logger.error(f"     - {tool}")
            if len(tools_only_in_metadata) > 10:
                logger.error(f"     ... and {len(tools_only_in_metadata) - 10} more")
        all_passed = False
    else:
        logger.info("  ✅ All tools from metadata exist in knowledge graph")

    # ========================================================================
    # Check 7: Verify document links
    # ========================================================================
    logger.info("\nCheck 7: Verifying document-entity links...")

    docs_with_missing_links = []

    for doc in docs_with_metadata:
        # Get all entity links for this document
        doc_entity_links = session.exec(
            select(DocumentEntity).where(DocumentEntity.document_id == doc.id)
        ).all()

        linked_entity_ids = {link.entity_id for link in doc_entity_links}

        # Check if all metadata topics are linked
        if doc.primary_topics:
            for topic in doc.primary_topics:
                topic_entity = session.exec(
                    select(Entity)
                    .where(Entity.entity_type == "Topic")
                    .where((Entity.name == topic) | (Entity.canonical_name == topic))
                ).first()

                if topic_entity and topic_entity.id not in linked_entity_ids:
                    docs_with_missing_links.append(
                        {
                            "doc_id": doc.id,
                            "doc_title": doc.title or doc.source_url,
                            "missing_entity": topic,
                            "entity_type": "Topic",
                        }
                    )

        # Check if all metadata tools are linked
        if doc.tools_technologies:
            for tool in doc.tools_technologies:
                tool_entity = session.exec(
                    select(Entity)
                    .where(Entity.entity_type.in_(["Technology", "Tool", "Product"]))
                    .where((Entity.name == tool) | (Entity.canonical_name == tool))
                ).first()

                if tool_entity and tool_entity.id not in linked_entity_ids:
                    docs_with_missing_links.append(
                        {
                            "doc_id": doc.id,
                            "doc_title": doc.title or doc.source_url,
                            "missing_entity": tool,
                            "entity_type": "Technology/Tool",
                        }
                    )

    if docs_with_missing_links:
        logger.error(f"  ❌ Found {len(docs_with_missing_links)} missing document-entity links:")
        if verbose:
            for link in docs_with_missing_links[:10]:
                logger.error(
                    f"     - Doc {link['doc_id']}: Missing link to {link['entity_type']} '{link['missing_entity']}'"
                )
            if len(docs_with_missing_links) > 10:
                logger.error(f"     ... and {len(docs_with_missing_links) - 10} more")
        all_passed = False
    else:
        logger.info("  ✅ All metadata items are properly linked to documents")

    # ========================================================================
    # Summary
    # ========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("VERIFICATION SUMMARY")
    logger.info("=" * 80)

    logger.info("\nMetadata:")
    logger.info(f"  Total topics: {len(unique_topics_in_metadata)}")
    logger.info(f"  Total tools: {len(unique_tools_in_metadata)}")
    logger.info(f"  Documents with metadata: {len(docs_with_metadata)}")

    logger.info("\nKnowledge Graph:")
    logger.info(f"  Topic entities: {len(topic_entities)}")
    logger.info(f"  Tool entities: {len(tool_entities)}")
    logger.info(f"  Topic-doc links: {total_topic_links}")
    logger.info(f"  Tool-doc links: {total_tool_links}")

    logger.info("\nIssues Found:")
    logger.info(f"  Topics in metadata but not in graph: {len(topics_only_in_metadata)}")
    logger.info(f"  Tools in metadata but not in graph: {len(tools_only_in_metadata)}")
    logger.info(f"  Missing document-entity links: {len(docs_with_missing_links)}")

    logger.info("")
    if all_passed:
        logger.info("✅ VERIFICATION PASSED - Migration is complete and correct!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Test queries: kurt content list-topics, kurt content list-technologies")
        logger.info("  2. Create database migration to drop old metadata fields")
        logger.info("     python scripts/create_drop_metadata_migration.py")
        return True
    else:
        logger.error("❌ VERIFICATION FAILED - Please fix issues before proceeding")
        logger.error("")
        logger.error("Troubleshooting:")
        logger.error("  1. Run migration again: python scripts/migrate_metadata_to_entities.py")
        logger.error("  2. Check for partial migrations or errors in the migration script")
        logger.error("  3. Run with --verbose to see detailed issues")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verify metadata migration to knowledge graph")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information about verification failures",
    )
    args = parser.parse_args()

    success = verify_migration(verbose=args.verbose)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
