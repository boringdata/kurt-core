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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import UUID, uuid4

import dspy
import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy import text
from sqlmodel import select

from kurt.content.indexing_helpers import (
    _embedding_to_bytes,
    _generate_embeddings,
    _search_similar_entities,
)
from kurt.content.indexing_models import GroupResolution
from kurt.db.database import get_session
from kurt.db.models import DocumentEntity, Entity, EntityRelationship

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


def _resolve_entity_groups(
    new_entities_batch: list[dict], activity_callback: callable = None
) -> list[dict]:
    """
    Stage 3: Resolve NEW entities using similarity grouping and entity-level LLM resolution.

    This function uses DSPy Trace #2 (ResolveEntityGroup) to resolve entities.

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
    embeddings = _generate_embeddings(entity_names)

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

    session = get_session()
    resolution_module = dspy.ChainOfThought(ResolveEntityGroup)

    total_groups = len(groups)
    completed_groups = 0

    # Prepare resolution tasks (one per group)
    group_tasks = []
    for group_id, group_entities in groups.items():
        # Get similar existing entities for this group (search using first entity's name as representative)
        representative_entity = group_entities[0]
        similar_existing = _search_similar_entities(
            session,
            representative_entity["name"],
            representative_entity["type"],
            limit=10,
        )

        group_tasks.append(
            {
                "group_id": group_id,
                "group_entities": group_entities,
                "similar_existing": similar_existing,
            }
        )

    async def resolve_group_async(task_data):
        """Resolve a single group asynchronously."""
        nonlocal completed_groups

        start_time = time.time()

        def _resolve():
            return resolution_module(
                group_entities=task_data["group_entities"],
                existing_candidates=task_data["similar_existing"],
            )

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, _resolve)

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
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_resolve(task):
            async with semaphore:
                return await resolve_group_async(task)

        results = await asyncio.gather(*[bounded_resolve(task) for task in group_tasks])
        # Flatten list of lists into single list
        return [resolution for group_resolutions in results for resolution in group_resolutions]

    # Execute parallel resolution
    resolutions = asyncio.run(resolve_all_groups())

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


# ============================================================================
# Stage 4: Create New Entities and Relationships
# ============================================================================


def _create_entities_and_relationships(doc_to_kg_data: dict, resolutions: list[dict]):
    """
    Stage 4: Create new entities and all relationship edges for multiple documents.

    Args:
        doc_to_kg_data: Dict mapping document_id (UUID) to kg_data dict with 'new_entities' and 'relationships'
        resolutions: List of resolution decisions from Stage 3
    """
    session = get_session()

    # Clean up old data for all documents (when re-indexing)
    # IMPORTANT: Delete ALL old links EXCEPT:
    # - Links to entities being linked via Stage 2 (existing_entities)
    # - Links to entities being created in Stage 4 (new_entities)
    all_document_ids = list(doc_to_kg_data.keys())
    all_old_entity_ids = set()

    for document_id in all_document_ids:
        kg_data = doc_to_kg_data[document_id]

        # Get entity IDs that should be kept (from Stage 2)
        existing_entity_ids_to_keep = set()
        for entity_id_str in kg_data.get("existing_entities", []):
            try:
                existing_entity_ids_to_keep.add(UUID(entity_id_str.strip()))
            except (ValueError, AttributeError):
                pass

        # Get entity names being created (from Stage 4)
        new_entity_names = {e["name"] for e in kg_data.get("new_entities", [])}

        # Step 1: Get all entities that were linked to this document
        stmt = select(DocumentEntity).where(DocumentEntity.document_id == document_id)
        old_doc_entities = session.exec(stmt).all()

        # Only clean links to entities that are NOT in current run
        old_entity_ids_to_clean = set()
        for de in old_doc_entities:
            # Keep if it's an existing entity from Stage 2
            if de.entity_id in existing_entity_ids_to_keep:
                continue

            # Keep if it's being recreated in Stage 4
            entity = session.get(Entity, de.entity_id)
            if entity and entity.name in new_entity_names:
                # This will be recreated, so delete the old version
                old_entity_ids_to_clean.add(de.entity_id)
            else:
                # Entity is no longer mentioned - orphan it
                old_entity_ids_to_clean.add(de.entity_id)

        all_old_entity_ids.update(old_entity_ids_to_clean)

        if old_entity_ids_to_clean:
            # Step 2: Delete old relationships where BOTH source and target were from this document
            for entity_id in old_entity_ids_to_clean:
                stmt_rel = select(EntityRelationship).where(
                    EntityRelationship.source_entity_id == entity_id,
                    EntityRelationship.target_entity_id.in_(old_entity_ids_to_clean),
                )
                old_relationships = session.exec(stmt_rel).all()
                for old_rel in old_relationships:
                    session.delete(old_rel)

            # Step 3: Delete old DocumentEntity links for entities being recreated
            for de in old_doc_entities:
                if de.entity_id in old_entity_ids_to_clean:
                    session.delete(de)

            logger.debug(
                f"Deleted {len([de for de in old_doc_entities if de.entity_id in old_entity_ids_to_clean])} old document-entity links for doc {document_id}"
            )

    # Step 4: Clean up orphaned entities (entities with no remaining document links)
    if all_old_entity_ids:
        orphaned_count = 0
        for entity_id in all_old_entity_ids:
            # Check if this entity still has any document links
            stmt_check = select(DocumentEntity).where(DocumentEntity.entity_id == entity_id)
            remaining_links = session.exec(stmt_check).first()

            if not remaining_links:
                # This entity has no more document links - delete it
                entity = session.get(Entity, entity_id)
                if entity:
                    # Also delete any remaining relationships involving this entity
                    stmt_rel_cleanup = select(EntityRelationship).where(
                        (EntityRelationship.source_entity_id == entity_id)
                        | (EntityRelationship.target_entity_id == entity_id)
                    )
                    orphan_rels = session.exec(stmt_rel_cleanup).all()
                    for rel in orphan_rels:
                        session.delete(rel)

                    session.delete(entity)
                    orphaned_count += 1

        if orphaned_count > 0:
            logger.debug(f"Cleaned up {orphaned_count} orphaned entities with no remaining links")

    # Map entity names to IDs (for relationship creation)
    entity_name_to_id = {}
    # Map entity names to which documents mention them
    entity_name_to_docs = {}

    # Build mapping of which documents mention which entity names
    for doc_id, kg_data in doc_to_kg_data.items():
        for new_entity in kg_data["new_entities"]:
            entity_name = new_entity["name"]
            if entity_name not in entity_name_to_docs:
                entity_name_to_docs[entity_name] = []
            entity_name_to_docs[entity_name].append(
                {
                    "document_id": doc_id,
                    "confidence": new_entity["confidence"],
                    "quote": new_entity.get("quote"),
                }
            )

    # First pass: Handle MERGE_WITH decisions to build canonical entity map
    # This maps entity names to their canonical merge target
    merge_map = {}  # entity_name -> canonical_entity_name
    all_entity_names = {r["entity_name"] for r in resolutions}

    for resolution in resolutions:
        entity_name = resolution["entity_name"]
        decision = resolution["decision"]

        if decision.startswith("MERGE_WITH:"):
            merge_target = decision.replace("MERGE_WITH:", "").strip()

            # Validate that merge target exists in the group
            if merge_target not in all_entity_names:
                logger.warning(
                    f"Invalid MERGE_WITH target '{merge_target}' for entity '{entity_name}'. "
                    f"Target not found in group {list(all_entity_names)}. "
                    f"Treating as CREATE_NEW instead."
                )
                # Change decision to CREATE_NEW since target is invalid
                resolution["decision"] = "CREATE_NEW"
                continue

            merge_map[entity_name] = merge_target

    # Build transitive closure of merges (A->B, B->C => A->C)
    # This ensures all entities in a merge chain point to the final canonical entity
    changed = True
    max_iterations = 10
    iteration = 0
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        for entity_name, merge_target in list(merge_map.items()):
            if merge_target in merge_map:
                # Follow the chain
                final_target = merge_map[merge_target]
                if merge_map[entity_name] != final_target:
                    merge_map[entity_name] = final_target
                    changed = True

    # Group resolutions by canonical entity
    # For merged entities, use the canonical name from the merge target's resolution
    canonical_groups = {}  # canonical_name -> list of resolutions
    for resolution in resolutions:
        entity_name = resolution["entity_name"]

        if entity_name in merge_map:
            # This entity merges with a peer - find the canonical resolution
            canonical_name = merge_map[entity_name]
            # Find the canonical entity's resolution to get its canonical_name
            canonical_resolution = next(
                (r for r in resolutions if r["entity_name"] == canonical_name), None
            )
            if canonical_resolution:
                canonical_key = canonical_resolution["canonical_name"]
            else:
                canonical_key = canonical_name
        else:
            # This entity is canonical (CREATE_NEW or links to existing)
            canonical_key = resolution["canonical_name"]

        if canonical_key not in canonical_groups:
            canonical_groups[canonical_key] = []
        canonical_groups[canonical_key].append(resolution)

    # Process each canonical group
    for canonical_name, group_resolutions in canonical_groups.items():
        # Find the primary resolution (the one that's not a MERGE_WITH)
        primary_resolution = next(
            (r for r in group_resolutions if not r["decision"].startswith("MERGE_WITH:")),
            group_resolutions[0],  # Fallback to first if all are merges (shouldn't happen)
        )

        decision = primary_resolution["decision"]

        if decision == "CREATE_NEW":
            # Create new entity
            entity_data = primary_resolution["entity_details"]
            entity_embedding = _generate_embeddings([canonical_name])[0]

            # Collect all entity names in this group
            all_entity_names = [r["entity_name"] for r in group_resolutions]

            # Collect all aliases from all resolutions in group
            all_aliases = set()
            for r in group_resolutions:
                all_aliases.update(r["aliases"])

            # Count how many unique documents mention any entity in this group
            unique_docs = set()
            for ent_name in all_entity_names:
                for doc_info in entity_name_to_docs.get(ent_name, []):
                    unique_docs.add(doc_info["document_id"])
            doc_count = len(unique_docs)

            # Average confidence scores from all entities in the group
            confidence_scores = [
                r["entity_details"].get("confidence", 0.9) for r in group_resolutions
            ]
            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.9
            )

            entity = Entity(
                id=uuid4(),
                name=canonical_name,
                entity_type=entity_data["type"],
                canonical_name=canonical_name,
                aliases=list(all_aliases),
                description=entity_data.get("description", ""),
                embedding=_embedding_to_bytes(entity_embedding),
                confidence_score=avg_confidence,
                source_mentions=doc_count,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(entity)
            session.flush()  # Get entity ID

            # Store entity_embeddings in vec0 table if available
            try:
                floats_str = ",".join(str(f) for f in entity_embedding)
                session.exec(
                    text(
                        f"INSERT INTO entity_embeddings (entity_id, embedding) VALUES ('{entity.id}', '[{floats_str}]')"
                    )
                )
            except Exception as e:
                logger.debug(f"Could not insert into entity_embeddings: {e}")

            # Map all names in this group to this entity ID
            for ent_name in all_entity_names:
                entity_name_to_id[ent_name] = entity.id

            # Create document-entity edges for ALL documents that mention any entity in this group
            docs_to_link = {}
            for ent_name in all_entity_names:
                for doc_info in entity_name_to_docs.get(ent_name, []):
                    doc_id = doc_info["document_id"]
                    # Keep the highest confidence if a doc mentions multiple variations
                    if (
                        doc_id not in docs_to_link
                        or doc_info["confidence"] > docs_to_link[doc_id]["confidence"]
                    ):
                        docs_to_link[doc_id] = doc_info

            for doc_info in docs_to_link.values():
                edge = DocumentEntity(
                    id=uuid4(),
                    document_id=doc_info["document_id"],
                    entity_id=entity.id,
                    mention_count=1,
                    confidence=doc_info["confidence"],
                    context=doc_info.get("quote"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(edge)

        else:  # Link to existing entity (should be a UUID)
            try:
                entity_id = UUID(decision)
            except ValueError:
                logger.warning(
                    f"Invalid entity ID in decision: '{decision}' for entity '{group_resolutions[0]['entity_name']}'. "
                    f"Expected UUID format (e.g., '123e4567-e89b-12d3-a456-426614174000'). "
                    f"This might be an entity name instead of UUID. Creating new entity instead."
                )
                # Log the full resolution for debugging
                logger.debug(f"Full resolution data: {primary_resolution}")

                # Fallback to CREATE_NEW logic
                entity_data = primary_resolution["entity_details"]
                entity_embedding = _generate_embeddings([canonical_name])[0]
                all_entity_names = [r["entity_name"] for r in group_resolutions]
                all_aliases = set()
                for r in group_resolutions:
                    all_aliases.update(r["aliases"])
                unique_docs = set()
                for ent_name in all_entity_names:
                    for doc_info in entity_name_to_docs.get(ent_name, []):
                        unique_docs.add(doc_info["document_id"])

                # Average confidence scores
                confidence_scores = [
                    r["entity_details"].get("confidence", 0.9) for r in group_resolutions
                ]
                avg_confidence = (
                    sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.9
                )

                entity = Entity(
                    id=uuid4(),
                    name=canonical_name,
                    entity_type=entity_data["type"],
                    canonical_name=canonical_name,
                    aliases=list(all_aliases),
                    description=entity_data.get("description", ""),
                    embedding=_embedding_to_bytes(entity_embedding),
                    confidence_score=avg_confidence,
                    source_mentions=len(unique_docs),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(entity)
                session.flush()

                try:
                    floats_str = ",".join(str(f) for f in entity_embedding)
                    session.exec(
                        text(
                            f"INSERT INTO entity_embeddings (entity_id, embedding) VALUES ('{entity.id}', '[{floats_str}]')"
                        )
                    )
                except Exception as e:
                    logger.debug(f"Could not insert into entity_embeddings: {e}")

                for ent_name in all_entity_names:
                    entity_name_to_id[ent_name] = entity.id

                docs_to_link = {}
                for ent_name in all_entity_names:
                    for doc_info in entity_name_to_docs.get(ent_name, []):
                        doc_id = doc_info["document_id"]
                        if (
                            doc_id not in docs_to_link
                            or doc_info["confidence"] > docs_to_link[doc_id]["confidence"]
                        ):
                            docs_to_link[doc_id] = doc_info

                for doc_info in docs_to_link.values():
                    edge = DocumentEntity(
                        id=uuid4(),
                        document_id=doc_info["document_id"],
                        entity_id=entity.id,
                        mention_count=1,
                        confidence=doc_info["confidence"],
                        context=doc_info.get("quote"),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    session.add(edge)

                # Continue to next group
                continue

            entity = session.get(Entity, entity_id)

            if entity:
                # Collect all entity names in this group
                all_entity_names = [r["entity_name"] for r in group_resolutions]

                # Collect all aliases from all resolutions
                all_aliases = set(entity.aliases or [])
                for r in group_resolutions:
                    all_aliases.update(r["aliases"])
                entity.aliases = list(all_aliases)

                # Count unique docs mentioning any entity in this group
                unique_docs = set()
                for ent_name in all_entity_names:
                    for doc_info in entity_name_to_docs.get(ent_name, []):
                        unique_docs.add(doc_info["document_id"])
                entity.source_mentions += len(unique_docs)
                entity.updated_at = datetime.utcnow()

                # Map all names to this entity
                for ent_name in all_entity_names:
                    entity_name_to_id[ent_name] = entity_id

                # Create document-entity edges for ALL documents that mention any entity in this group
                docs_to_link = {}
                for ent_name in all_entity_names:
                    for doc_info in entity_name_to_docs.get(ent_name, []):
                        doc_id = doc_info["document_id"]
                        # Keep the highest confidence if a doc mentions multiple variations
                        if (
                            doc_id not in docs_to_link
                            or doc_info["confidence"] > docs_to_link[doc_id]["confidence"]
                        ):
                            docs_to_link[doc_id] = doc_info

                for doc_info in docs_to_link.values():
                    edge = DocumentEntity(
                        id=uuid4(),
                        document_id=doc_info["document_id"],
                        entity_id=entity_id,
                        mention_count=1,
                        confidence=doc_info["confidence"],
                        context=doc_info.get("quote"),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    session.add(edge)

    # Create relationships from all documents
    for doc_id, kg_data in doc_to_kg_data.items():
        for rel in kg_data["relationships"]:
            source_id = entity_name_to_id.get(rel["source_entity"])
            target_id = entity_name_to_id.get(rel["target_entity"])

            if not source_id or not target_id:
                continue  # Skip if entities not found

            # Check if relationship already exists
            stmt = select(EntityRelationship).where(
                EntityRelationship.source_entity_id == source_id,
                EntityRelationship.target_entity_id == target_id,
                EntityRelationship.relationship_type == rel["relationship_type"],
            )
            existing_rel = session.exec(stmt).first()

            if existing_rel:
                # Update evidence count
                existing_rel.evidence_count += 1
                existing_rel.updated_at = datetime.utcnow()
            else:
                # Create new relationship
                relationship = EntityRelationship(
                    id=uuid4(),
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relationship_type=rel["relationship_type"],
                    confidence=rel["confidence"],
                    evidence_count=1,
                    context=rel.get("context"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(relationship)

    session.commit()

    # Count actual entities created/linked (not individual resolutions, but canonical groups)
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
        f"linked {entities_linked} to existing entities for {len(all_document_ids)} documents "
        f"(from {len(resolutions)} individual entity resolutions)"
    )


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
