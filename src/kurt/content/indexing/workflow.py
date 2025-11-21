"""DBOS workflows for document indexing with fine-grained checkpointing.

This module provides two main workflows:

1. **complete_indexing_workflow** - Complete end-to-end indexing (Stage 1-4)
   - Stage 1: Extract metadata + entities from documents
   - Stage 2: Link existing entities to documents
   - Stage 3: Resolve new entities (clustering + LLM deduplication)
   - Stage 4: Create entities and relationships

2. **complete_entity_resolution_workflow** - Just entity resolution (Stages 2-4)
   - Used when you already have extraction results
   - Called by complete_indexing_workflow

Pattern:
- Business logic in content/indexing/ files (extract.py, entity_resolution.py)
- Database operations in db/graph_resolution.py
- Workflow orchestration here (just calls those functions)

Benefits:
- Granular checkpointing saves progress at each step
- Clear transaction boundaries with ACID guarantees
- Automatic workflow recovery on failure
- Easy to test (business logic separate from workflow)
"""

import asyncio
import logging

from dbos import DBOS

from kurt.db.database import get_session
from kurt.db.graph_resolution import (
    build_entity_docs_mapping,
    cleanup_old_entities,
    create_entities,
    create_relationships,
    group_by_canonical_entity,
    link_existing_entities,
    resolve_merge_chains,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Async Orchestration Helpers
# ============================================================================


async def _resolve_all_groups_async(groups: dict[int, list[dict]]) -> list[dict]:
    """Orchestrate parallel resolution of all entity groups.

    Steps:
    1. Fetch similar entities from DB for each group (parallel async)
    2. Resolve each group with LLM (parallel async)
    3. Validate MERGE_WITH decisions

    Args:
        groups: Dict mapping group_id -> list of entities in that group

    Returns:
        List of resolution decisions
    """
    from kurt.config import load_config
    from kurt.content.indexing.llm_resolution import resolve_single_group
    from kurt.db.database import async_session_scope
    from kurt.db.graph_similarity import search_similar_entities
    from kurt.utils.async_helpers import gather_with_semaphore

    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING

    # Step 2a: Fetch similar entities from DB (parallel async)
    async def fetch_group_similarities(group_item):
        """Fetch similar entities for one group."""
        group_id, group_entities = group_item

        async with async_session_scope() as session:
            similar = await search_similar_entities(
                entity_name=group_entities[0]["name"],
                entity_type=group_entities[0]["type"],
                limit=10,
                session=session,
            )
            return {
                "group_id": group_id,
                "group_entities": group_entities,
                "similar_existing": similar,
            }

    group_tasks = await gather_with_semaphore(
        tasks=[fetch_group_similarities(item) for item in groups.items()],
        max_concurrent=max_concurrent,
        task_description="similarity search",
    )

    # Step 2b: Resolve groups with LLM (parallel async)
    async def resolve_group_task(task_data):
        """Resolve a single group using LLM."""
        return await resolve_single_group(
            group_entities=task_data["group_entities"],
            existing_candidates=task_data["similar_existing"],
        )

    all_group_resolutions = await gather_with_semaphore(
        tasks=[resolve_group_task(task) for task in group_tasks],
        max_concurrent=max_concurrent,
        task_description="group resolution",
    )

    # Flatten list of lists into single list
    resolutions = [
        resolution
        for group_resolutions in all_group_resolutions
        for resolution in group_resolutions
    ]

    # Step 3: Validate MERGE_WITH decisions
    all_entity_names = {r["entity_name"] for r in resolutions}
    validated_resolutions = []

    for resolution in resolutions:
        decision = resolution["decision"]
        entity_name = resolution["entity_name"]

        if decision.startswith("MERGE_WITH:"):
            merge_target = decision.replace("MERGE_WITH:", "").strip()

            if merge_target not in all_entity_names:
                logger.warning(
                    f"Invalid MERGE_WITH target '{merge_target}' for entity '{entity_name}'. "
                    f"Target not found in group. Converting to CREATE_NEW."
                )
                resolution["decision"] = "CREATE_NEW"

        validated_resolutions.append(resolution)

    create_new_count = sum(1 for r in validated_resolutions if r["decision"] == "CREATE_NEW")
    merge_count = sum(1 for r in validated_resolutions if r["decision"].startswith("MERGE_WITH:"))
    link_count = len(validated_resolutions) - create_new_count - merge_count

    logger.info(
        f"Stage 3: Resolved {len(validated_resolutions)} entities across {len(groups)} clusters "
        f"({create_new_count} CREATE_NEW, {merge_count} MERGE, {link_count} LINK)"
    )

    return validated_resolutions


# ============================================================================
# Steps - Lightweight compute operations (checkpointed)
# ============================================================================


@DBOS.step()
def resolve_entity_groups_step(new_entities_batch: list[dict]) -> list[dict]:
    """Step: Resolve new entities using clustering + LLM (Stage 3).

    Orchestration logic:
    1. Cluster similar entities using DBSCAN
    2. For each cluster, fetch similar existing entities from DB
    3. Use LLM to resolve each group (parallel processing)
    4. Validate MERGE_WITH decisions

    Checkpointed - won't re-run if workflow restarts.
    """
    if not new_entities_batch:
        return []

    # Step 1: Cluster similar entities
    from kurt.db.graph_entities import cluster_entities_by_similarity

    groups = cluster_entities_by_similarity(new_entities_batch, eps=0.25, min_samples=1)

    logger.info(
        f"Stage 3: Grouped {len(new_entities_batch)} NEW entities into {len(groups)} groups"
    )

    # Step 2-3: Resolve each group with orchestration + parallel processing
    return asyncio.run(_resolve_all_groups_async(groups))


@DBOS.step()
def build_entity_docs_mapping_step(doc_to_kg_data: dict) -> dict[str, list[dict]]:
    """Step 1: Build mapping of which documents mention which entity names.

    Checkpointed - won't re-run if workflow restarts.
    """
    return build_entity_docs_mapping(doc_to_kg_data)


@DBOS.step()
def resolve_merge_chains_step(resolutions: list[dict]) -> dict[str, str]:
    """Step 2: Resolve merge chains and detect cycles.

    Checkpointed - won't re-run if workflow restarts.
    """
    return resolve_merge_chains(resolutions)


@DBOS.step()
def group_by_canonical_step(
    resolutions: list[dict], merge_map: dict[str, str]
) -> dict[str, list[dict]]:
    """Step 3: Group resolutions by canonical entity.

    Checkpointed - won't re-run if workflow restarts.
    """
    return group_by_canonical_entity(resolutions, merge_map)


# ============================================================================
# Transactions - Database operations with ACID guarantees (checkpointed)
# ============================================================================


@DBOS.transaction()
def link_existing_entities_txn(doc_to_kg_data: dict) -> int:
    """Transaction: Link existing entities to documents (Stage 2).

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all links created or all roll back.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data with 'existing_entities'

    Returns:
        Total number of entities linked across all documents
    """
    session = get_session()
    try:
        total_linked = 0
        for doc_id, kg_data in doc_to_kg_data.items():
            if kg_data.get("existing_entities"):
                linked_count = link_existing_entities(session, doc_id, kg_data["existing_entities"])
                total_linked += linked_count
        session.commit()
        return total_linked
    except Exception as e:
        logger.error(f"Error linking existing entities: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def cleanup_old_entities_txn(doc_to_kg_data: dict) -> int:
    """Transaction: Clean up old document-entity links when re-indexing.

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all deletes succeed or all roll back.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data

    Returns:
        Number of orphaned entities cleaned up
    """
    session = get_session()
    try:
        orphaned_count = cleanup_old_entities(session, doc_to_kg_data)
        session.commit()
        return orphaned_count
    except Exception as e:
        logger.error(f"Error cleaning up old entities: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def create_entities_txn(
    canonical_groups: dict[str, list[dict]],
    entity_name_to_docs: dict[str, list[dict]],
) -> dict[str, str]:
    """Transaction 2: Create or link all entities atomically.

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all entities created/linked or none.

    Args:
        canonical_groups: Dict mapping canonical_name -> list of resolutions
        entity_name_to_docs: Dict mapping entity_name -> list of doc mentions

    Returns:
        Dict mapping entity_name -> entity_id (as strings for serialization)
    """
    session = get_session()
    try:
        entity_name_to_id = create_entities(session, canonical_groups, entity_name_to_docs)
        session.commit()
        # Convert UUIDs to strings for DBOS serialization
        return {name: str(uuid) for name, uuid in entity_name_to_id.items()}
    except Exception as e:
        logger.error(f"Error creating entities: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def create_relationships_txn(
    doc_to_kg_data: dict,
    entity_name_to_id_str: dict[str, str],
) -> int:
    """Transaction 3: Create all entity relationships atomically.

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all relationships created or none.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data with 'relationships'
        entity_name_to_id_str: Dict mapping entity_name -> entity_id (strings)

    Returns:
        Number of relationships created
    """
    from uuid import UUID

    session = get_session()
    try:
        # Convert string IDs back to UUIDs
        entity_name_to_id = {name: UUID(id_str) for name, id_str in entity_name_to_id_str.items()}
        relationships_created = create_relationships(session, doc_to_kg_data, entity_name_to_id)
        session.commit()
        return relationships_created
    except Exception as e:
        logger.error(f"Error creating relationships: {e}")
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================================
# Workflow - Orchestrates steps with automatic checkpointing
# ============================================================================


@DBOS.workflow()
def complete_entity_resolution_workflow(index_results: list[dict]) -> dict:
    """Complete entity resolution workflow orchestrating Stages 2-4.

    This is the MAIN workflow that should be called from indexing.py.

    If this workflow crashes, DBOS automatically resumes from last completed step.

    Stages (each checkpointed):
    - Stage 2: Link existing entities to documents (transaction)
    - Stage 3: Resolve new entities with LLM (step)
    - Stage 4: Create entities and relationships (transactions)

    Args:
        index_results: List of results from extract_document_metadata()
                      Each should have 'kg_data' with entities/relationships

    Returns:
        dict with:
            - document_ids: list of document IDs processed
            - entities_created: number of new entities created
            - entities_linked_existing: number of existing entities linked
            - entities_merged: number of entities merged
            - relationships_created: number of relationships created
            - orphaned_entities_cleaned: number of orphaned entities removed
            - workflow_id: DBOS workflow ID (for tracking/debugging)
    """
    # Filter out skipped results and aggregate data
    valid_results = [r for r in index_results if not r.get("skipped") and "kg_data" in r]

    if not valid_results:
        logger.info("No documents with KG data to process")
        return {
            "document_ids": [],
            "entities_created": 0,
            "entities_linked_existing": 0,
            "entities_merged": 0,
            "relationships_created": 0,
            "orphaned_entities_cleaned": 0,
            "workflow_id": DBOS.workflow_id,
        }

    # Build doc_to_kg_data mapping
    doc_to_kg_data = {}
    all_new_entities = []

    for result in valid_results:
        from uuid import UUID

        doc_id = UUID(str(result["document_id"]).strip())
        kg_data = result["kg_data"]
        doc_to_kg_data[doc_id] = kg_data
        all_new_entities.extend(kg_data["new_entities"])

    all_document_ids = list(doc_to_kg_data.keys())

    # STAGE 2: Link existing entities (transaction - checkpointed)
    entities_linked_existing = link_existing_entities_txn(doc_to_kg_data)

    # STAGE 3: Resolve new entities with LLM (step - checkpointed)
    resolutions = []
    entities_created = 0
    entities_merged = 0

    if all_new_entities:
        resolutions = resolve_entity_groups_step(all_new_entities)
        entities_created = sum(1 for r in resolutions if r["decision"] == "CREATE_NEW")
        entities_merged = len(resolutions) - entities_created

    # STAGE 4: Create entities and relationships (multiple steps - checkpointed)
    orphaned_count = 0
    relationships_created = 0

    if resolutions:
        # Step 4a: Clean up old entities
        orphaned_count = cleanup_old_entities_txn(doc_to_kg_data)

        # Step 4b: Build entity->docs mapping
        entity_name_to_docs = build_entity_docs_mapping_step(doc_to_kg_data)

        # Step 4c: Resolve merge chains
        merge_map = resolve_merge_chains_step(resolutions)

        # Step 4d: Group by canonical entity
        canonical_groups = group_by_canonical_step(resolutions, merge_map)

        # Step 4e: Create/link all entities
        entity_name_to_id_str = create_entities_txn(canonical_groups, entity_name_to_docs)

        # Step 4f: Create relationships
        relationships_created = create_relationships_txn(doc_to_kg_data, entity_name_to_id_str)

    logger.info(
        f"Complete entity resolution workflow finished: "
        f"Created {entities_created} new entities, "
        f"merged {entities_merged} entities, "
        f"linked {entities_linked_existing} existing entities, "
        f"{relationships_created} relationships, "
        f"cleaned {orphaned_count} orphaned entities "
        f"for {len(all_document_ids)} documents"
    )

    return {
        "document_ids": [str(d) for d in all_document_ids],
        "entities_created": entities_created,
        "entities_linked_existing": entities_linked_existing,
        "entities_merged": entities_merged,
        "relationships_created": relationships_created,
        "orphaned_entities_cleaned": orphaned_count,
        "workflow_id": DBOS.workflow_id,
    }


# ============================================================================
# Complete Indexing Workflow (Stage 1-4)
# ============================================================================


@DBOS.step()
def extract_documents_step(document_ids: list[str], force: bool = False) -> dict:
    """Step: Extract metadata + entities from documents (Stage 1).

    This calls the async batch extraction business logic.
    Checkpointed - won't re-run if workflow restarts.

    Args:
        document_ids: List of document UUIDs to extract
        force: If True, re-extract even if content unchanged

    Returns:
        dict with keys:
            - results: list of extraction results
            - total: number of documents
            - succeeded: number of successful extractions
            - failed: number of failed extractions
            - skipped: number of skipped documents
    """
    from kurt.content.indexing.extract import batch_extract_document_metadata

    # Run the async batch extraction
    return asyncio.run(
        batch_extract_document_metadata(
            document_ids, max_concurrent=5, force=force, progress_callback=None
        )
    )


@DBOS.workflow()
def complete_indexing_workflow(
    document_ids: list[str], force: bool = False, enable_kg: bool = True
) -> dict:
    """Complete end-to-end indexing workflow (Stage 1-4).

    This is the MAIN workflow for full document indexing.
    Combines extraction + entity resolution into a single durable workflow.

    If this workflow crashes, DBOS automatically resumes from last completed step:
    - If crash during Stage 1: Resumes extraction from last checkpoint
    - If crash after Stage 1: Skips extraction, goes to entity resolution
    - If crash during Stages 2-4: Resumes entity resolution from last step

    Stages (each checkpointed):
    - Stage 1: Extract metadata + entities from documents (step)
    - Stage 2: Link existing entities to documents (transaction)
    - Stage 3: Resolve new entities with LLM (step)
    - Stage 4: Create entities and relationships (transactions)

    Args:
        document_ids: List of document UUIDs to index
        force: If True, re-index even if content unchanged
        enable_kg: If True, run knowledge graph finalization (Stages 2-4)

    Returns:
        dict with:
            - extract_results: dict with extraction stats
            - kg_stats: dict with KG stats (if enable_kg=True)
            - workflow_id: DBOS workflow ID
    """
    logger.info(f"Starting complete indexing workflow for {len(document_ids)} documents")

    # STAGE 1: Extract metadata + entities (checkpointed)
    extract_results = extract_documents_step(document_ids, force=force)

    logger.info(
        f"Stage 1 complete: {extract_results['succeeded']} succeeded, "
        f"{extract_results['failed']} failed, {extract_results['skipped']} skipped"
    )

    # STAGES 2-4: Finalize knowledge graph (checkpointed)
    kg_stats = None
    if enable_kg and extract_results["results"]:
        logger.info("Stages 2-4: Finalizing knowledge graph...")
        kg_stats = complete_entity_resolution_workflow(extract_results["results"])
        logger.info(
            f"Knowledge graph complete: {kg_stats.get('entities_created', 0)} created, "
            f"{kg_stats.get('entities_merged', 0)} merged, "
            f"{kg_stats.get('entities_linked_existing', 0)} linked"
        )

    return {
        "extract_results": extract_results,
        "kg_stats": kg_stats,
        "workflow_id": DBOS.workflow_id,
    }
