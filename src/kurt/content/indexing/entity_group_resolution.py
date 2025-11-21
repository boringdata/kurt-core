"""DEPRECATED: Entity group resolution - orchestration logic moved to workflow.py

This module is kept for backward compatibility with fallback functions.

NEW ARCHITECTURE:
- Pure LLM logic → llm_resolution.py (DSPy signature + single group resolution)
- Orchestration → workflow.py (clustering + DB queries + parallel processing)
- Database operations → db/graph_resolution.py

Pattern:
- llm_resolution.py: DSPy signature + LLM calls (pure business logic)
- workflow.py: Orchestration (clustering, DB queries, parallel processing, validation)
- db/graph_resolution.py: Database operations (CRUD)
"""

import asyncio
import logging
from uuid import UUID

# Re-export DSPy signature from new location for backward compatibility
from kurt.content.indexing.llm_resolution import ResolveEntityGroup  # noqa: F401
from kurt.db.database import get_session

logger = logging.getLogger(__name__)


async def resolve_entity_groups(
    new_entities_batch: list[dict], activity_callback: callable = None
) -> list[dict]:
    """DEPRECATED: Use workflow.resolve_entity_groups_step() instead.

    This function now delegates to the workflow orchestration.
    Kept for backward compatibility with fallback functions.

    Args:
        new_entities_batch: NEW entity dicts from extraction
        activity_callback: Optional progress callback (ignored in new implementation)

    Returns:
        Resolution decisions with: entity_name, decision, canonical_name, aliases, reasoning
    """
    if not new_entities_batch:
        return []

    # Delegate to workflow orchestration (async version)
    from kurt.content.indexing.workflow import _resolve_all_groups_async
    from kurt.db.graph_entities import cluster_entities_by_similarity

    groups = cluster_entities_by_similarity(new_entities_batch, eps=0.25, min_samples=1)
    return await _resolve_all_groups_async(groups)


def _resolve_entity_groups(
    new_entities_batch: list[dict], activity_callback: callable = None
) -> list[dict]:
    """Sync wrapper for resolve_entity_groups (fallback for sync contexts)."""
    return asyncio.run(resolve_entity_groups(new_entities_batch, activity_callback))


# ============================================================================
# Fallback Implementations (for non-DBOS environments like tests)
# ============================================================================
# NOTE: These functions orchestrate Stages 2-4 when DBOS is not available.
# In production, the workflow.py file handles orchestration with DBOS decorators.


def _create_entities_and_relationships(doc_to_kg_data: dict, resolutions: list[dict]):
    """Create new entities and relationships (fallback for non-DBOS environments).

    Orchestrates Stage 4 database operations without DBOS decorators.
    Called by finalize_knowledge_graph_from_index_results_fallback().

    Args:
        doc_to_kg_data: Dict mapping document_id to kg_data with entities/relationships
        resolutions: Resolution decisions from Stage 3

    Returns:
        dict with entities_created, entities_linked, relationships_created
    """
    from kurt.db.database import get_session
    from kurt.db.graph_resolution import (
        build_entity_docs_mapping,
        cleanup_old_entities,
        create_entities,
        create_relationships,
        group_by_canonical_entity,
        resolve_merge_chains,
    )

    session = get_session()
    try:
        cleanup_old_entities(session, doc_to_kg_data)
        entity_name_to_docs = build_entity_docs_mapping(doc_to_kg_data)
        merge_map = resolve_merge_chains(resolutions)
        canonical_groups = group_by_canonical_entity(resolutions, merge_map)
        entity_name_to_id = create_entities(session, canonical_groups, entity_name_to_docs)
        relationships_created = create_relationships(session, doc_to_kg_data, entity_name_to_id)
        session.commit()

        entities_created = len(
            [
                g
                for g, resols in canonical_groups.items()
                if any(r["decision"] == "CREATE_NEW" for r in resols)
            ]
        )
        entities_linked = len(canonical_groups) - entities_created

        logger.info(
            f"Stage 4: Created {entities_created} new entities, "
            f"linked {entities_linked} to existing for {len(doc_to_kg_data)} documents"
        )
        return {
            "entities_created": entities_created,
            "entities_linked": entities_linked,
            "relationships_created": relationships_created,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def finalize_knowledge_graph_from_index_results_fallback(
    index_results: list[dict], activity_callback: callable = None
) -> dict:
    """Complete knowledge graph finalization (fallback for non-DBOS environments).

    Orchestrates Stages 2-4 without DBOS decorators:
    - Stage 2: Link existing entities to documents (DB operations)
    - Stage 3: Resolve new entities with clustering + LLM (calls resolve_entity_groups)
    - Stage 4: Create new entities and relationships (DB operations)

    NOTE: Production code uses complete_entity_resolution_workflow() from workflow.py
    This fallback is for tests and scripts where DBOS is not initialized.

    Args:
        index_results: Results from extract_document_metadata() with kg_data
        activity_callback: Optional progress callback

    Returns:
        dict with entities_created, entities_merged, entities_linked, relationships_created
    """
    logger.info(f"Finalizing knowledge graph for {len(index_results)} documents")

    if activity_callback:
        activity_callback("Aggregating knowledge graph data...")

    valid_results = [r for r in index_results if not r.get("skipped") and "kg_data" in r]

    if not valid_results:
        logger.info("No documents with KG data to process")
        return {
            "entities_created": 0,
            "entities_merged": 0,
            "entities_linked": 0,
            "relationships_created": 0,
        }

    all_existing_entity_ids = []
    all_new_entities = []
    all_relationships = []
    doc_to_kg_data = {}

    for result in valid_results:
        try:
            doc_id_str = str(result["document_id"]).strip()
            doc_id = UUID(doc_id_str)
        except (ValueError, TypeError) as e:
            logger.error(
                f"Malformed document_id in result: {result.get('document_id', 'MISSING')!r} "
                f"(type: {type(result.get('document_id')).__name__}), title: {result.get('title', 'MISSING')}"
            )
            raise ValueError(
                f"Malformed document_id: {result.get('document_id', 'MISSING')!r}"
            ) from e

        kg_data = result["kg_data"]
        doc_to_kg_data[doc_id] = kg_data

        all_existing_entity_ids.extend(kg_data["existing_entities"])
        all_new_entities.extend(kg_data["new_entities"])
        all_relationships.extend(kg_data["relationships"])

    logger.info(
        f"Aggregated: {len(all_existing_entity_ids)} existing, "
        f"{len(all_new_entities)} new entities, {len(all_relationships)} relationships"
    )

    # Stage 2: Link existing entities
    if activity_callback:
        activity_callback(f"Linking {len(all_existing_entity_ids)} existing entities...")
    logger.info(f"Stage 2: Linking {len(all_existing_entity_ids)} existing entities...")

    from kurt.db.graph_resolution import link_existing_entities

    session = get_session()
    try:
        for doc_id, kg_data in doc_to_kg_data.items():
            if kg_data["existing_entities"]:
                link_existing_entities(session, doc_id, kg_data["existing_entities"])
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    # Stage 3: Resolve new entities
    entities_created = 0
    entities_merged = 0

    if all_new_entities:
        if activity_callback:
            activity_callback(f"Resolving {len(all_new_entities)} new entities...")
        logger.info(f"Stage 3: Resolving {len(all_new_entities)} new entities...")
        resolutions = _resolve_entity_groups(all_new_entities, activity_callback=activity_callback)

        # Stage 4: Create entities and relationships
        if activity_callback:
            activity_callback("Creating entities and relationships...")
        logger.info("Stage 4: Creating entities and relationships...")
        _create_entities_and_relationships(doc_to_kg_data, resolutions)

        entities_created = sum(1 for r in resolutions if r["decision"] == "CREATE_NEW")
        entities_merged = len(resolutions) - entities_created

        if activity_callback:
            activity_callback(
                f"Resolved: {entities_created} new entities, {entities_merged} merged with existing"
            )

    logger.info(
        f"Knowledge graph finalized: "
        f"{entities_created} created, {entities_merged} merged, "
        f"{len(set(all_existing_entity_ids))} linked"
    )

    return {
        "entities_created": entities_created,
        "entities_merged": entities_merged,
        "entities_linked": len(set(all_existing_entity_ids)),
        "relationships_created": len(all_relationships),
    }
