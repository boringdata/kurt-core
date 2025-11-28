"""DBOS workflow for entity resolution (Stages 2-4).

Orchestrates entity resolution with checkpointed steps:
- Stage 2: Link existing entities
- Stage 3: Resolve new entities
- Stage 4: Create entities and relationships
"""

import asyncio
import logging

from dbos import DBOS

from kurt.db.database import get_session
from kurt.db.graph_claims import (
    build_claim_docs_mapping,
    cleanup_old_claims,
    cluster_claims_by_similarity,
    create_claim_entity_links,
    create_claims,
    group_claims_by_canonical,
    link_existing_claims,
    resolve_claim_merge_chains,
)
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
# Async Helper Functions (used by steps)
# ============================================================================


async def _fetch_similar_entities_for_groups(groups: dict[int, list[dict]]) -> list[dict]:
    """Fetch similar entities from DB for all groups."""
    from kurt.config import load_config
    from kurt.db.database import async_session_scope
    from kurt.db.graph_similarity import search_similar_entities
    from kurt.utils.async_helpers import gather_with_semaphore

    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING

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

    return await gather_with_semaphore(
        tasks=[fetch_group_similarities(item) for item in groups.items()],
        max_concurrent=max_concurrent,
        task_description="similarity search",
    )


async def _resolve_groups_with_llm(group_tasks: list[dict]) -> list[dict]:
    """Resolve all groups with LLM."""
    from kurt.config import load_config
    from kurt.content.indexing.resolution import resolve_single_group
    from kurt.utils.async_helpers import gather_with_semaphore

    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING

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
    return [
        resolution
        for group_resolutions in all_group_resolutions
        for resolution in group_resolutions
    ]


async def _fetch_similar_claims_for_groups(groups: dict[int, list[dict]]) -> list[dict]:
    """Fetch similar claims from DB for all groups."""
    from kurt.config import load_config
    from kurt.db.database import async_session_scope
    from kurt.db.graph_similarity import search_similar_claims
    from kurt.utils.async_helpers import gather_with_semaphore

    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING

    async def fetch_group_similarities(group_item):
        """Fetch similar claims for one group."""
        group_id, group_claims = group_item

        async with async_session_scope() as session:
            similar = await search_similar_claims(
                claim_text=group_claims[0]["claim_text"],
                claim_type=group_claims[0]["claim_type"],
                limit=10,
                session=session,
            )
            return {
                "group_id": group_id,
                "group_claims": group_claims,
                "similar_existing": similar,
            }

    return await gather_with_semaphore(
        tasks=[fetch_group_similarities(item) for item in groups.items()],
        max_concurrent=max_concurrent,
        task_description="claim similarity search",
    )


async def _resolve_claim_groups_with_llm(group_tasks: list[dict]) -> list[dict]:
    """Resolve all claim groups with LLM."""
    from kurt.config import load_config
    from kurt.content.indexing.resolution import resolve_single_claim_group
    from kurt.utils.async_helpers import gather_with_semaphore

    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING

    async def resolve_group_task(task_data):
        """Resolve a single claim group using LLM."""
        return await resolve_single_claim_group(
            group_claims=task_data["group_claims"],
            existing_candidates=task_data["similar_existing"],
        )

    all_group_resolutions = await gather_with_semaphore(
        tasks=[resolve_group_task(task) for task in group_tasks],
        max_concurrent=max_concurrent,
        task_description="claim group resolution",
    )

    # Flatten list of lists into single list
    return [
        resolution
        for group_resolutions in all_group_resolutions
        for resolution in group_resolutions
    ]


# ============================================================================
# Steps - Lightweight compute operations (checkpointed)
# ============================================================================


@DBOS.step()
def cluster_entities_step(new_entities_batch: list[dict]) -> dict[int, list[dict]]:
    """Cluster similar entities using DBSCAN."""
    from kurt.db.graph_entities import cluster_entities_by_similarity

    groups = cluster_entities_by_similarity(new_entities_batch, eps=0.25, min_samples=1)

    logger.info(
        f"Stage 3: Grouped {len(new_entities_batch)} NEW entities into {len(groups)} groups"
    )

    return groups


@DBOS.step()
def fetch_similar_entities_step(groups: dict[int, list[dict]]) -> list[dict]:
    """Fetch similar entities from DB for all groups."""
    return asyncio.run(_fetch_similar_entities_for_groups(groups))


@DBOS.step()
def resolve_with_llm_step(group_tasks: list[dict]) -> list[dict]:
    """Resolve all groups with LLM."""
    return asyncio.run(_resolve_groups_with_llm(group_tasks))


@DBOS.step()
def validate_resolutions_step(resolutions: list[dict]) -> list[dict]:
    """Validate MERGE_WITH decisions."""
    from kurt.content.indexing.resolution import validate_merge_decisions

    validated = validate_merge_decisions(resolutions)

    create_new_count = sum(1 for r in validated if r["decision"] == "CREATE_NEW")
    merge_count = sum(1 for r in validated if r["decision"].startswith("MERGE_WITH:"))
    link_count = len(validated) - create_new_count - merge_count

    logger.info(
        f"Stage 3 complete: Resolved {len(validated)} entities "
        f"({create_new_count} CREATE_NEW, {merge_count} MERGE, {link_count} LINK)"
    )

    return validated


@DBOS.step()
def build_entity_docs_mapping_step(doc_to_kg_data: dict) -> dict[str, list[dict]]:
    """Build mapping of entity names to documents."""
    return build_entity_docs_mapping(doc_to_kg_data)


@DBOS.step()
def resolve_merge_chains_step(resolutions: list[dict]) -> dict[str, str]:
    """Resolve merge chains and detect cycles."""
    return resolve_merge_chains(resolutions)


@DBOS.step()
def group_by_canonical_step(
    resolutions: list[dict], merge_map: dict[str, str]
) -> dict[str, list[dict]]:
    """Group resolutions by canonical entity."""
    return group_by_canonical_entity(resolutions, merge_map)


# ============================================================================
# Claim Steps - Lightweight compute operations (checkpointed)
# ============================================================================


@DBOS.step()
def cluster_claims_step(new_claims_batch: list[dict]) -> dict[int, list[dict]]:
    """Cluster similar claims using DBSCAN."""
    groups = cluster_claims_by_similarity(new_claims_batch, eps=0.25, min_samples=1)

    logger.info(
        f"Stage 5: Grouped {len(new_claims_batch)} NEW claims into {len(groups)} groups"
    )

    return groups


@DBOS.step()
def fetch_similar_claims_step(groups: dict[int, list[dict]]) -> list[dict]:
    """Fetch similar claims from DB for all groups."""
    return asyncio.run(_fetch_similar_claims_for_groups(groups))


@DBOS.step()
def resolve_claims_with_llm_step(group_tasks: list[dict]) -> list[dict]:
    """Resolve all claim groups with LLM."""
    return asyncio.run(_resolve_claim_groups_with_llm(group_tasks))


@DBOS.step()
def validate_claim_resolutions_step(resolutions: list[dict]) -> list[dict]:
    """Validate claim MERGE_WITH decisions."""
    from kurt.content.indexing.resolution import validate_claim_merge_decisions

    validated = validate_claim_merge_decisions(resolutions)

    create_new_count = sum(1 for r in validated if r["decision"] == "CREATE_NEW")
    merge_count = sum(1 for r in validated if r["decision"].startswith("MERGE_WITH:"))
    link_count = len(validated) - create_new_count - merge_count

    logger.info(
        f"Stage 5 complete: Resolved {len(validated)} claims "
        f"({create_new_count} CREATE_NEW, {merge_count} MERGE, {link_count} LINK)"
    )

    return validated


@DBOS.step()
def build_claim_docs_mapping_step(doc_to_kg_data: dict) -> dict[str, list[dict]]:
    """Build mapping of claim texts to documents."""
    return build_claim_docs_mapping(doc_to_kg_data)


@DBOS.step()
def resolve_claim_merge_chains_step(resolutions: list[dict]) -> dict[str, str]:
    """Resolve claim merge chains and detect cycles."""
    return resolve_claim_merge_chains(resolutions)


@DBOS.step()
def group_claims_by_canonical_step(
    resolutions: list[dict], merge_map: dict[str, str]
) -> dict[str, list[dict]]:
    """Group claim resolutions by canonical text."""
    return group_claims_by_canonical(resolutions, merge_map)


# ============================================================================
# Transactions - Database operations with ACID guarantees (checkpointed)
# ============================================================================


@DBOS.transaction()
def link_existing_entities_txn(doc_to_kg_data: dict) -> int:
    """Link existing entities to documents."""
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
    """Clean up orphaned entities when re-indexing."""
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
    """Create or link all entities atomically."""
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
    """Create all entity relationships atomically."""
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
# Claim Transactions - Database operations with ACID guarantees (checkpointed)
# ============================================================================


@DBOS.transaction()
def link_existing_claims_txn(doc_to_kg_data: dict) -> int:
    """Link existing claims to documents."""
    session = get_session()
    try:
        total_linked = 0
        for doc_id, kg_data in doc_to_kg_data.items():
            if kg_data.get("existing_claims"):
                linked_count = link_existing_claims(session, doc_id, kg_data["existing_claims"])
                total_linked += linked_count
        session.commit()
        return total_linked
    except Exception as e:
        logger.error(f"Error linking existing claims: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def cleanup_old_claims_txn(doc_to_kg_data: dict) -> int:
    """Clean up orphaned claims when re-indexing."""
    session = get_session()
    try:
        orphaned_count = cleanup_old_claims(session, doc_to_kg_data)
        session.commit()
        return orphaned_count
    except Exception as e:
        logger.error(f"Error cleaning up old claims: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def create_claims_txn(
    canonical_groups: dict[str, list[dict]],
    claim_text_to_docs: dict[str, list[dict]],
) -> dict[str, str]:
    """Create or link all claims atomically."""
    session = get_session()
    try:
        claim_text_to_id = create_claims(session, canonical_groups, claim_text_to_docs)
        session.commit()
        # Convert UUIDs to strings for DBOS serialization
        return {text: str(uuid) for text, uuid in claim_text_to_id.items()}
    except Exception as e:
        logger.error(f"Error creating claims: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def create_claim_entity_links_txn(
    claim_text_to_id_str: dict[str, str],
    claim_text_to_docs: dict[str, list[dict]],
    entity_name_to_id_str: dict[str, str],
) -> int:
    """Create all claim-entity links atomically."""
    from uuid import UUID

    session = get_session()
    try:
        # Convert string IDs back to UUIDs
        claim_text_to_id = {text: UUID(id_str) for text, id_str in claim_text_to_id_str.items()}
        entity_name_to_id = {name: UUID(id_str) for name, id_str in entity_name_to_id_str.items()}
        links_created = create_claim_entity_links(session, claim_text_to_id, claim_text_to_docs, entity_name_to_id)
        session.commit()
        return links_created
    except Exception as e:
        logger.error(f"Error creating claim-entity links: {e}")
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================================
# Workflow - Orchestrates steps with automatic checkpointing
# ============================================================================


@DBOS.workflow()
def complete_entity_resolution_workflow(index_results: list[dict]) -> dict:
    """Complete entity resolution workflow (Stages 2-4)."""
    import time
    from datetime import datetime

    from kurt.commands.content._live_display import format_display_timestamp

    # Stream: Started
    DBOS.write_stream(
        "entity_resolution_progress",
        {
            "message": f"{format_display_timestamp()}⠋ Starting entity resolution...",
            "style": "dim cyan",
        },
    )

    workflow_start = time.time()

    # Filter out skipped results and aggregate data
    valid_results = [r for r in index_results if not r.get("skipped") and "kg_data" in r]

    if not valid_results:
        logger.info("No documents with KG data to process")
        duration_ms = int((time.time() - workflow_start) * 1000)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "message": f"{format_display_timestamp()}○ Skipped: No documents with KG data ({duration_ms}ms)",
                "style": "dim yellow",
            },
        )
        DBOS.close_stream("entity_resolution_progress")
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
    all_new_claims = []

    for result in valid_results:
        from uuid import UUID

        doc_id = UUID(str(result["document_id"]).strip())
        kg_data = result["kg_data"]
        doc_to_kg_data[doc_id] = kg_data
        all_new_entities.extend(kg_data["new_entities"])
        all_new_claims.extend(kg_data.get("new_claims", []))

    all_document_ids = list(doc_to_kg_data.keys())

    # STAGE 2: Link existing entities (transaction - checkpointed)
    stage2_start = time.time()
    entities_linked_existing = link_existing_entities_txn(doc_to_kg_data)
    DBOS.write_stream(
        "entity_resolution_progress",
        {
            "status": "linked_existing",
            "count": entities_linked_existing,
            "duration_ms": int((time.time() - stage2_start) * 1000),
            "timestamp": datetime.now().isoformat(),
        },
    )

    # STAGE 3: Resolve new entities with LLM (4 sub-steps - each checkpointed)
    resolutions = []
    entities_created = 0
    entities_merged = 0

    if all_new_entities:
        # Step 3a: Cluster entities
        cluster_start = time.time()
        groups = cluster_entities_step(all_new_entities)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "clustered",
                "entity_count": len(all_new_entities),
                "group_count": len(groups),
                "duration_ms": int((time.time() - cluster_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 3b: Fetch similar entities from DB
        similarity_start = time.time()
        group_tasks = fetch_similar_entities_step(groups)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "searched_similar",
                "group_count": len(group_tasks),
                "duration_ms": int((time.time() - similarity_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 3c: Resolve with LLM
        llm_start = time.time()
        resolutions = resolve_with_llm_step(group_tasks)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "resolved_with_llm",
                "resolution_count": len(resolutions),
                "duration_ms": int((time.time() - llm_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 3d: Validate decisions
        validate_start = time.time()
        resolutions = validate_resolutions_step(resolutions)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "validated",
                "resolution_count": len(resolutions),
                "duration_ms": int((time.time() - validate_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        entities_created = sum(1 for r in resolutions if r["decision"] == "CREATE_NEW")
        entities_merged = len(resolutions) - entities_created

    # STAGE 4: Create entities and relationships (multiple steps - checkpointed)
    orphaned_count = 0
    relationships_created = 0

    if resolutions:
        # Step 4a: Clean up old entities
        cleanup_start = time.time()
        orphaned_count = cleanup_old_entities_txn(doc_to_kg_data)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "cleaned_orphans",
                "orphan_count": orphaned_count,
                "duration_ms": int((time.time() - cleanup_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 4b: Build entity->docs mapping
        entity_name_to_docs = build_entity_docs_mapping_step(doc_to_kg_data)

        # Step 4c: Resolve merge chains
        merge_map = resolve_merge_chains_step(resolutions)

        # Step 4d: Group by canonical entity
        canonical_groups = group_by_canonical_step(resolutions, merge_map)

        # Step 4e: Create/link all entities
        create_start = time.time()
        entity_name_to_id_str = create_entities_txn(canonical_groups, entity_name_to_docs)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "created_entities",
                "entity_count": len(entity_name_to_id_str),
                "duration_ms": int((time.time() - create_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 4f: Create relationships
        rel_start = time.time()
        relationships_created = create_relationships_txn(doc_to_kg_data, entity_name_to_id_str)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "created_relationships",
                "relationship_count": relationships_created,
                "duration_ms": int((time.time() - rel_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

    # STAGE 5: Link existing claims (transaction - checkpointed)
    claims_linked_existing = 0
    stage5_start = time.time()
    claims_linked_existing = link_existing_claims_txn(doc_to_kg_data)
    if claims_linked_existing > 0:
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "linked_existing_claims",
                "count": claims_linked_existing,
                "duration_ms": int((time.time() - stage5_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

    # STAGE 5b: Resolve new claims with LLM
    claim_resolutions = []
    claims_created = 0
    claims_merged = 0

    if all_new_claims:
        # Step 5a: Cluster claims
        claim_cluster_start = time.time()
        claim_groups = cluster_claims_step(all_new_claims)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "clustered_claims",
                "claim_count": len(all_new_claims),
                "group_count": len(claim_groups),
                "duration_ms": int((time.time() - claim_cluster_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 5b: Fetch similar claims from DB
        claim_similarity_start = time.time()
        claim_group_tasks = fetch_similar_claims_step(claim_groups)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "searched_similar_claims",
                "group_count": len(claim_group_tasks),
                "duration_ms": int((time.time() - claim_similarity_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 5c: Resolve with LLM
        claim_llm_start = time.time()
        claim_resolutions = resolve_claims_with_llm_step(claim_group_tasks)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "resolved_claims_with_llm",
                "resolution_count": len(claim_resolutions),
                "duration_ms": int((time.time() - claim_llm_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 5d: Validate decisions
        claim_validate_start = time.time()
        claim_resolutions = validate_claim_resolutions_step(claim_resolutions)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "validated_claims",
                "resolution_count": len(claim_resolutions),
                "duration_ms": int((time.time() - claim_validate_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        claims_created = sum(1 for r in claim_resolutions if r["decision"] == "CREATE_NEW")
        claims_merged = len(claim_resolutions) - claims_created

    # STAGE 6: Create claims and claim-entity links
    orphaned_claims_count = 0
    claim_entity_links_created = 0

    if claim_resolutions:
        # Step 6a: Clean up old claims
        claim_cleanup_start = time.time()
        orphaned_claims_count = cleanup_old_claims_txn(doc_to_kg_data)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "cleaned_orphan_claims",
                "orphan_count": orphaned_claims_count,
                "duration_ms": int((time.time() - claim_cleanup_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 6b: Build claim->docs mapping
        claim_text_to_docs = build_claim_docs_mapping_step(doc_to_kg_data)

        # Step 6c: Resolve merge chains
        claim_merge_map = resolve_claim_merge_chains_step(claim_resolutions)

        # Step 6d: Group by canonical text
        claim_canonical_groups = group_claims_by_canonical_step(claim_resolutions, claim_merge_map)

        # Step 6e: Create/link all claims
        claim_create_start = time.time()
        claim_text_to_id_str = create_claims_txn(claim_canonical_groups, claim_text_to_docs)
        DBOS.write_stream(
            "entity_resolution_progress",
            {
                "status": "created_claims",
                "claim_count": len(claim_text_to_id_str),
                "duration_ms": int((time.time() - claim_create_start) * 1000),
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Step 6f: Create claim-entity links
        if entity_name_to_id_str and claim_text_to_id_str:
            link_start = time.time()
            claim_entity_links_created = create_claim_entity_links_txn(
                claim_text_to_id_str, claim_text_to_docs, entity_name_to_id_str
            )
            DBOS.write_stream(
                "entity_resolution_progress",
                {
                    "status": "created_claim_entity_links",
                    "link_count": claim_entity_links_created,
                    "duration_ms": int((time.time() - link_start) * 1000),
                    "timestamp": datetime.now().isoformat(),
                },
            )

    # Stream: Completed
    total_duration = time.time() - workflow_start
    DBOS.write_stream(
        "entity_resolution_progress",
        {
            "status": "completed",
            "entities_created": entities_created,
            "entities_merged": entities_merged,
            "entities_linked": entities_linked_existing,
            "relationships_created": relationships_created,
            "orphaned_cleaned": orphaned_count,
            "claims_created": claims_created,
            "claims_merged": claims_merged,
            "claims_linked": claims_linked_existing,
            "claim_entity_links": claim_entity_links_created,
            "orphaned_claims_cleaned": orphaned_claims_count,
            "document_count": len(all_document_ids),
            "duration_ms": int(total_duration * 1000),
            "timestamp": datetime.now().isoformat(),
        },
    )
    DBOS.close_stream("entity_resolution_progress")

    logger.info(
        f"Complete entity resolution workflow finished: "
        f"Created {entities_created} new entities, "
        f"merged {entities_merged} entities, "
        f"linked {entities_linked_existing} existing entities, "
        f"{relationships_created} relationships, "
        f"cleaned {orphaned_count} orphaned entities, "
        f"created {claims_created} new claims, "
        f"merged {claims_merged} claims, "
        f"linked {claims_linked_existing} existing claims, "
        f"{claim_entity_links_created} claim-entity links "
        f"for {len(all_document_ids)} documents"
    )

    # Collect entity names for display
    created_entity_names = [r["entity_name"] for r in resolutions if r["decision"] == "CREATE_NEW"]

    # Collect linked entity names from Stage 3 (LLM resolutions)
    stage3_linked_names = [r["entity_name"] for r in resolutions if r["decision"] != "CREATE_NEW"]

    # Collect existing entity names from Stage 2 (direct matches from KG extract)
    stage2_linked_names = []
    if entities_linked_existing > 0:
        from uuid import UUID

        from kurt.db.database import get_session
        from kurt.db.models import Entity

        session = get_session()
        try:
            # Collect all existing entity IDs from kg_data
            existing_entity_ids = []
            for kg_data in doc_to_kg_data.values():
                if kg_data.get("existing_entities"):
                    existing_entity_ids.extend([UUID(eid) for eid in kg_data["existing_entities"]])

            # Fetch entity names from DB
            if existing_entity_ids:
                entities = session.query(Entity).filter(Entity.id.in_(existing_entity_ids)).all()
                stage2_linked_names = [e.name for e in entities]
        finally:
            session.close()

    # Combine all linked entity names
    linked_entity_names = stage2_linked_names + stage3_linked_names

    # Collect claim texts for display
    created_claim_texts = [r["claim_text"] for r in claim_resolutions if r["decision"] == "CREATE_NEW"]

    return {
        "document_ids": [str(d) for d in all_document_ids],
        "entities_created": entities_created,
        "entities_linked_existing": entities_linked_existing,
        "entities_merged": entities_merged,
        "relationships_created": relationships_created,
        "orphaned_entities_cleaned": orphaned_count,
        "created_entity_names": created_entity_names,
        "linked_entity_names": linked_entity_names,
        "claims_created": claims_created,
        "claims_linked_existing": claims_linked_existing,
        "claims_merged": claims_merged,
        "claim_entity_links_created": claim_entity_links_created,
        "orphaned_claims_cleaned": orphaned_claims_count,
        "created_claim_texts": created_claim_texts,
        "workflow_id": DBOS.workflow_id,
    }
