"""Entity resolution for knowledge graph - Stages 2-4.

This module contains DSPy Trace #2: ResolveEntityGroup
- Clusters similar entities using DBSCAN
- Resolves entity groups using LLM (CREATE_NEW, MERGE_WITH, or link to existing)
- Creates entities and relationships in database

Stages:
- Stage 2: Link existing entities to documents
- Stage 3: Resolve new entities (clustering + LLM deduplication)  ← DSPy Trace #2
- Stage 4: Create new entities and relationships
"""

import asyncio
import logging
import time
from datetime import datetime
from uuid import UUID, uuid4

import dspy
import numpy as np
from sklearn.cluster import DBSCAN
from sqlmodel import select

from kurt.content.embeddings import generate_embeddings
from kurt.content.indexing_models import GroupResolution
from kurt.db.database import get_session
from kurt.db.models import DocumentEntity, Entity
from kurt.utils.async_helpers import gather_with_semaphore

logger = logging.getLogger(__name__)


# ============================================================================
# DSPy Trace #2: ResolveEntityGroup
# ============================================================================


class ResolveEntityGroup(dspy.Signature):
    """Resolve a GROUP of similar NEW entities against existing entities.

    You are given:
    1. A group of similar NEW entities (clustered together by similarity)
    2. Existing entities from the knowledge base that might match

    Your task is to decide for EACH ENTITY in the group:
    - CREATE_NEW: Create a new entity (novel concept not in database)
    - MERGE_WITH:<exact_peer_name>: Merge with another entity in THIS group by using the EXACT name from group_entities
      Example: If group has ["Python", "Python Lang"], use "MERGE_WITH:Python" (exact match from group)
    - <existing_entity_id>: Link to an existing entity by using the EXACT UUID from existing_candidates
      Example: If existing has {id: "abc-123", name: "React"}, use "abc-123" (the UUID)

    Resolution rules:
    - If an existing entity is a clear match, return its EXACT UUID from existing_candidates (not the name!)
    - If multiple entities in the group refer to the same thing, merge them using MERGE_WITH:<exact_peer_name>
      The peer_name MUST be an exact match to one of the entity names in group_entities
    - If this is a novel concept, return CREATE_NEW
    - Provide canonical name and aliases for each resolution

    CRITICAL: When using MERGE_WITH, the target name MUST exactly match an entity name in group_entities.
    CRITICAL: When linking to existing entity, use the UUID (id field), NOT the name.

    IMPORTANT: Return one resolution decision for EACH entity in the group.
    """

    group_entities: list[dict] = dspy.InputField(
        desc="Group of similar entities to resolve: [{name, type, description, aliases, confidence}, ...]"
    )
    existing_candidates: list[dict] = dspy.InputField(
        default=[],
        desc="Similar existing entities from KB: [{id, name, type, description, aliases}, ...]. Use the 'id' field for linking.",
    )
    resolutions: GroupResolution = dspy.OutputField(
        desc="Resolution decision for EACH entity in the group"
    )


# ============================================================================
# Stage 2: Link Existing Entities
# ============================================================================


def _link_existing_entities(document_id: UUID, existing_entity_ids: list[str]):
    """
    Stage 2: Create document-entity edges for EXISTING entities.

    Args:
        document_id: Document UUID
        existing_entity_ids: List of entity IDs that were matched during indexing
    """
    session = get_session()

    for entity_id_str in existing_entity_ids:
        # Parse UUID with validation
        try:
            entity_id = UUID(entity_id_str.strip())
        except (ValueError, TypeError) as e:
            logger.error(
                f"Invalid entity_id '{entity_id_str}' for document {document_id}: {e}. "
                f"This should not happen - entity IDs are now validated during extraction."
            )
            continue  # Skip and continue

        # Check if edge already exists
        stmt = select(DocumentEntity).where(
            DocumentEntity.document_id == document_id,
            DocumentEntity.entity_id == entity_id,
        )
        existing_edge = session.exec(stmt).first()

        if existing_edge:
            # Update mention count
            existing_edge.mention_count += 1
            existing_edge.updated_at = datetime.utcnow()
        else:
            # Create new edge
            edge = DocumentEntity(
                id=uuid4(),
                document_id=document_id,
                entity_id=entity_id,
                mention_count=1,
                confidence=0.9,  # High confidence since LLM matched it
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(edge)

        # Update entity mention count
        entity = session.get(Entity, entity_id)
        if entity:
            entity.source_mentions += 1
            entity.updated_at = datetime.utcnow()

    session.commit()
    logger.info(
        f"Stage 2: Linked {len(existing_entity_ids)} existing entities to document {document_id}"
    )


# ============================================================================
# Stage 3: Resolve NEW Entities (DSPy Trace)
# ============================================================================


async def _resolve_entity_groups_async(
    new_entities_batch: list[dict], activity_callback: callable = None
) -> list[dict]:
    """
    Stage 3: Resolve NEW entities using similarity grouping and entity-level LLM resolution.

    This is the ASYNC version that uses native async DSPy and async database operations.

    Args:
        new_entities_batch: List of NEW entity dicts from multiple documents
        activity_callback: Optional callback(activity: str) for progress updates

    Returns:
        List of resolution decisions (one per entity) with keys:
            - entity_name: Name of the entity
            - entity_details: Entity dict
            - decision: "CREATE_NEW", "MERGE_WITH:<peer_name>", or entity_id
            - canonical_name: Canonical name for entity
            - aliases: All aliases
            - reasoning: LLM's reasoning
    """
    if not new_entities_batch:
        return []

    # Generate embeddings for all NEW entities
    if activity_callback:
        activity_callback(f"Clustering {len(new_entities_batch)} new entities...")
    entity_names = [e["name"] for e in new_entities_batch]
    embeddings = generate_embeddings(entity_names)

    # Group similar entities using DBSCAN clustering
    embeddings_array = np.array(embeddings)
    clustering = DBSCAN(eps=0.25, min_samples=1, metric="cosine")
    labels = clustering.fit_predict(embeddings_array)

    # Organize entities into groups
    groups = {}
    for idx, label in enumerate(labels):
        if label not in groups:
            groups[label] = []
        groups[label].append(new_entities_batch[idx])

    logger.info(
        f"Stage 3: Grouped {len(new_entities_batch)} NEW entities into {len(groups)} groups"
    )
    logger.debug(
        f"  Groups: {[(gid, [e['name'] for e in ents]) for gid, ents in list(groups.items())[:3]]}"
    )
    if activity_callback:
        activity_callback(f"Found {len(groups)} entity groups, resolving entities with LLM...")

    # Resolve EACH GROUP using DSPy (groups processed in parallel)
    from kurt.config import load_config

    config = load_config()
    max_concurrent = config.MAX_CONCURRENT_INDEXING  # Reuse same config

    resolution_module = dspy.ChainOfThought(ResolveEntityGroup)

    from kurt.db.database import async_session_scope
    from kurt.db.graph_similarity import search_similar_entities

    total_groups = len(groups)
    completed_groups = 0

    # Stage 1: Fetch similar entities for all groups in parallel using ASYNC!
    async def fetch_group_similarities(group_item):
        """Fetch similar entities for one group using async session."""
        group_id, group_entities = group_item

        # Each task creates its own async session (official SQLAlchemy pattern)
        async with async_session_scope() as session:
            similar = await search_similar_entities(
                entity_name=group_entities[0]["name"],  # Representative entity
                entity_type=group_entities[0]["type"],
                limit=10,
                session=session,
            )
            return {
                "group_id": group_id,
                "group_entities": group_entities,
                "similar_existing": similar,
            }

    # Execute all similarity searches in parallel with semaphore
    group_tasks = await gather_with_semaphore(
        tasks=[fetch_group_similarities(item) for item in groups.items()],
        max_concurrent=max_concurrent,
        task_description="similarity search",
    )

    # Stage 2: Resolve groups with DSPy using NATIVE ASYNC (acall)!
    async def resolve_group_async(task_data):
        """Resolve a single group using async DSPy."""
        nonlocal completed_groups

        start_time = time.time()

        # Use DSPy's native async method - NO ThreadPoolExecutor!
        result = await resolution_module.acall(
            group_entities=task_data["group_entities"],
            existing_candidates=task_data["similar_existing"],
        )

        elapsed = time.time() - start_time
        completed_groups += 1

        # Convert GroupResolution output to individual resolution dicts
        group_resolutions = []
        # Match resolutions to entities by index (handles multiple entities with same name)
        for idx, entity_resolution in enumerate(result.resolutions.resolutions):
            # Try to match by index first (most reliable for same-named entities)
            if idx < len(task_data["group_entities"]):
                entity_details = task_data["group_entities"][idx]
            else:
                # Fallback: find by name if index is out of range
                entity_details = next(
                    (
                        e
                        for e in task_data["group_entities"]
                        if e["name"] == entity_resolution.entity_name
                    ),
                    task_data["group_entities"][0],
                )

            group_resolutions.append(
                {
                    "entity_name": entity_resolution.entity_name,
                    "entity_details": entity_details,
                    "decision": entity_resolution.resolution_decision,
                    "canonical_name": entity_resolution.canonical_name,
                    "aliases": entity_resolution.aliases,
                    "reasoning": entity_resolution.reasoning,
                }
            )

        # Progress callback with decisions
        if activity_callback:
            # Build summary of decisions
            decision_summary = []
            for res in group_resolutions:
                entity_name = res["entity_name"]
                decision = res["decision"]

                if decision == "CREATE_NEW":
                    decision_summary.append(f"{entity_name} → NEW")
                elif decision.startswith("MERGE_WITH:"):
                    target = decision.replace("MERGE_WITH:", "")
                    decision_summary.append(f"{entity_name} → MERGE({target})")
                else:
                    # Linking to existing (UUID - show just first 8 chars)
                    decision_summary.append(f"{entity_name} → LINK")

            # Format output
            if len(decision_summary) <= 3:
                decisions_str = ", ".join(decision_summary)
            else:
                decisions_str = (
                    ", ".join(decision_summary[:3]) + f", +{len(decision_summary) - 3} more"
                )

            activity_callback(
                f"Resolved group {completed_groups}/{total_groups}: {decisions_str} "
                f"({elapsed:.1f}s)"
            )

        return group_resolutions

    async def resolve_all_groups():
        """Resolve all groups with controlled concurrency."""
        valid_results = await gather_with_semaphore(
            tasks=[resolve_group_async(task) for task in group_tasks],
            max_concurrent=max_concurrent,
            task_description="group resolution",
        )

        # Flatten list of lists into single list
        return [
            resolution for group_resolutions in valid_results for resolution in group_resolutions
        ]

    # Execute parallel resolution (we're already in async function)
    resolutions = await resolve_all_groups()

    # Validate MERGE_WITH decisions - ensure targets exist in resolutions
    all_entity_names = {r["entity_name"] for r in resolutions}
    validated_resolutions = []

    for resolution in resolutions:
        decision = resolution["decision"]
        entity_name = resolution["entity_name"]

        if decision.startswith("MERGE_WITH:"):
            merge_target = decision.replace("MERGE_WITH:", "").strip()

            # When merge_target == entity_name, this means "merge with another entity that has the same name"
            # This is VALID when there are multiple entities with the same name from different documents
            # We should NOT convert this to CREATE_NEW

            # Only validate that the merge target name exists in the resolution list
            if merge_target not in all_entity_names:
                logger.warning(
                    f"Invalid MERGE_WITH target '{merge_target}' for entity '{entity_name}'. "
                    f"Target not found in group {list(all_entity_names)[:10]}{'...' if len(all_entity_names) > 10 else ''}. "
                    f"Converting to CREATE_NEW."
                )
                resolution["decision"] = "CREATE_NEW"

        validated_resolutions.append(resolution)

    # Log resolution summary
    create_new_count = sum(1 for r in validated_resolutions if r["decision"] == "CREATE_NEW")
    merge_count = sum(1 for r in validated_resolutions if r["decision"].startswith("MERGE_WITH:"))
    link_count = len(validated_resolutions) - create_new_count - merge_count

    logger.info(
        f"Stage 3: Resolved {len(validated_resolutions)} entities across {len(groups)} clusters "
        f"({create_new_count} CREATE_NEW, {merge_count} MERGE, {link_count} LINK)"
    )

    # Log detailed decisions if logger is at DEBUG level
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Resolution decisions:")
        for r in validated_resolutions:
            logger.debug(f"  - {r['entity_name']}: {r['decision']} → {r['canonical_name']}")

    return validated_resolutions


def _resolve_entity_groups(
    new_entities_batch: list[dict], activity_callback: callable = None
) -> list[dict]:
    """
    Sync wrapper for _resolve_entity_groups_async (for backward compatibility).

    This maintains the same interface as before while using async internally.
    """
    return asyncio.run(_resolve_entity_groups_async(new_entities_batch, activity_callback))


# ============================================================================
# Stage 4: Create New Entities and Relationships
# ============================================================================


def _create_entities_and_relationships(doc_to_kg_data: dict, resolutions: list[dict]):
    """Stage 4: Create new entities and all relationship edges for multiple documents.

    Calls the DBOS workflow (or falls back to direct function calls in tests).

    Args:
        doc_to_kg_data: Dict mapping document_id (UUID) to kg_data dict
        resolutions: List of resolution decisions from Stage 3

    Returns:
        dict with entities_created, entities_linked, relationships_created
    """
    # Try DBOS workflow first (production)
    try:
        from kurt.workflows.entity_resolution import entity_resolution_workflow

        result = entity_resolution_workflow(doc_to_kg_data, resolutions)
        logger.info(
            f"Stage 4: Created {result['entities_created']} new entities, "
            f"linked {result['entities_linked']} to existing for {len(result['document_ids'])} documents"
        )
        return result
    except Exception as e:
        # Fallback for tests where DBOS isn't initialized
        if "DBOS" in str(e):
            logger.debug("DBOS not initialized, calling graph_resolution functions directly")
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
                # Execute same logic as workflow, without DBOS decorators
                cleanup_old_entities(session, doc_to_kg_data)
                entity_name_to_docs = build_entity_docs_mapping(doc_to_kg_data)
                merge_map = resolve_merge_chains(resolutions)
                canonical_groups = group_by_canonical_entity(resolutions, merge_map)
                entity_name_to_id = create_entities(session, canonical_groups, entity_name_to_docs)
                relationships_created = create_relationships(
                    session, doc_to_kg_data, entity_name_to_id
                )
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
        else:
            raise


# ============================================================================
# Main API Function
# ============================================================================


def finalize_knowledge_graph_from_index_results(
    index_results: list[dict], activity_callback: callable = None
) -> dict:
    """
    Finalize knowledge graph from indexing results.

    This orchestrates stages 2-4:
    - Stage 2: Link existing entities to documents
    - Stage 3: Resolve new entities (clustering + LLM deduplication)  ← Uses DSPy Trace #2
    - Stage 4: Create new entities and relationships

    Args:
        index_results: List of results from extract_document_metadata()
                      Each should have 'kg_data' with entities/relationships
        activity_callback: Optional callback(activity: str) for progress updates

    Returns:
        dict with finalization results:
            - entities_created: number of new entities created
            - entities_merged: number of entities merged with existing
            - entities_linked: number of existing entities linked
            - relationships_created: number of relationships created

    Note: Stage 1 (entity extraction) happens during indexing itself.
    """
    logger.info(f"🔄 Finalizing knowledge graph for {len(index_results)} documents")

    if activity_callback:
        activity_callback("Aggregating knowledge graph data...")

    # Filter out skipped results
    valid_results = [r for r in index_results if not r.get("skipped") and "kg_data" in r]

    if not valid_results:
        logger.info("No documents with KG data to process")
        return {
            "entities_created": 0,
            "entities_merged": 0,
            "entities_linked": 0,
            "relationships_created": 0,
        }

    # Aggregate data from all documents
    all_existing_entity_ids = []
    all_new_entities = []
    all_relationships = []
    doc_to_kg_data = {}

    for result in valid_results:
        try:
            # Clean the document_id - strip whitespace and ensure it's a string
            doc_id_str = str(result["document_id"]).strip()
            doc_id = UUID(doc_id_str)
        except (ValueError, TypeError) as e:
            # Log which document_id is malformed
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
        f"📊 Aggregated: {len(all_existing_entity_ids)} existing, "
        f"{len(all_new_entities)} new entities, {len(all_relationships)} relationships"
    )

    # Stage 2: Link existing entities
    if activity_callback:
        activity_callback(f"Linking {len(all_existing_entity_ids)} existing entities...")
    logger.info(f"🔗 Stage 2: Linking {len(all_existing_entity_ids)} existing entities...")
    for doc_id, kg_data in doc_to_kg_data.items():
        if kg_data["existing_entities"]:
            _link_existing_entities(doc_id, kg_data["existing_entities"])

    # Stage 3: Resolve new entities
    entities_created = 0
    entities_merged = 0

    if all_new_entities:
        if activity_callback:
            activity_callback(f"Resolving {len(all_new_entities)} new entities...")
        logger.info(f"🧩 Stage 3: Resolving {len(all_new_entities)} new entities...")
        resolutions = _resolve_entity_groups(all_new_entities, activity_callback=activity_callback)

        # Stage 4: Create entities and relationships (single call for all documents)
        if activity_callback:
            activity_callback("Creating entities and relationships...")
        logger.info("💾 Stage 4: Creating entities and relationships...")
        _create_entities_and_relationships(doc_to_kg_data, resolutions)

        entities_created = sum(1 for r in resolutions if r["decision"] == "CREATE_NEW")
        entities_merged = len(resolutions) - entities_created

        # Log resolution decisions if activity callback provided
        if activity_callback:
            activity_callback(
                f"Resolved: {entities_created} new entities, {entities_merged} merged with existing"
            )

    logger.info(
        f"🎉 Knowledge graph finalized: "
        f"{entities_created} created, {entities_merged} merged, "
        f"{len(set(all_existing_entity_ids))} linked"
    )

    return {
        "entities_created": entities_created,
        "entities_merged": entities_merged,
        "entities_linked": len(set(all_existing_entity_ids)),
        "relationships_created": len(all_relationships),
    }
