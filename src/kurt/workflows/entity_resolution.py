"""DBOS workflow for entity resolution with fine-grained checkpointing.

This workflow breaks down the monolithic _create_entities_and_relationships()
into fine-grained steps with automatic checkpointing and recovery.

Benefits:
- LLM calls are checkpointed per entity group (saves $$$ on retries)
- Clear transaction boundaries with ACID guarantees
- Automatic workflow recovery on failure
- Easy to test individual steps
"""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from dbos import DBOS
from sqlmodel import select

from kurt.content.entity_operations import (
    build_entity_docs_mapping,
    group_by_canonical_entity,
    resolve_merge_chains,
)
from kurt.db.knowledge_graph import (
    create_entity_with_document_edges,
    find_existing_entity,
    find_or_create_document_entity_link,
)
from kurt.db.models import DocumentEntity, Entity, EntityRelationship
from kurt.db.session import get_session

logger = logging.getLogger(__name__)


# ============================================================================
# Steps - Lightweight compute operations (checkpointed)
# ============================================================================


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
def cleanup_old_entities_txn(doc_to_kg_data: dict) -> int:
    """Transaction 1: Clean up old document-entity links when re-indexing.

    This removes stale entity links from previous indexing runs, but preserves:
    - Links to entities being linked via Stage 2 (existing_entities)
    - Links to entities being created in Stage 4 (new_entities)

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all deletes succeed or all roll back.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data

    Returns:
        Number of orphaned entities cleaned up
    """
    session = get_session()
    all_document_ids = list(doc_to_kg_data.keys())
    all_old_entity_ids = set()

    try:
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

            # Get all entities linked to this document
            stmt = select(DocumentEntity).where(DocumentEntity.document_id == document_id)
            old_doc_entities = session.exec(stmt).all()

            # Identify entities to clean up
            old_entity_ids_to_clean = set()
            for de in old_doc_entities:
                # Keep if it's an existing entity from Stage 2
                if de.entity_id in existing_entity_ids_to_keep:
                    continue

                # Keep if it's being recreated in Stage 4
                entity = session.get(Entity, de.entity_id)
                if entity and entity.name in new_entity_names:
                    continue
                else:
                    old_entity_ids_to_clean.add(de.entity_id)

            all_old_entity_ids.update(old_entity_ids_to_clean)

            if old_entity_ids_to_clean:
                # Delete old relationships where BOTH source and target are being cleaned
                for entity_id in old_entity_ids_to_clean:
                    stmt_rel = select(EntityRelationship).where(
                        EntityRelationship.source_entity_id == entity_id,
                        EntityRelationship.target_entity_id.in_(old_entity_ids_to_clean),
                    )
                    old_relationships = session.exec(stmt_rel).all()
                    for old_rel in old_relationships:
                        session.delete(old_rel)

                # Delete old DocumentEntity links
                for de in old_doc_entities:
                    if de.entity_id in old_entity_ids_to_clean:
                        session.delete(de)

                logger.debug(
                    f"Deleted {len([de for de in old_doc_entities if de.entity_id in old_entity_ids_to_clean])} "
                    f"old document-entity links for doc {document_id}"
                )

        # Clean up orphaned entities (entities with no remaining document links)
        orphaned_count = 0
        if all_old_entity_ids:
            for entity_id in all_old_entity_ids:
                stmt_check = select(DocumentEntity).where(DocumentEntity.entity_id == entity_id)
                remaining_links = session.exec(stmt_check).first()

                if not remaining_links:
                    entity = session.get(Entity, entity_id)
                    if entity:
                        # Delete relationships involving this entity
                        stmt_rel_cleanup = select(EntityRelationship).where(
                            (EntityRelationship.source_entity_id == entity_id)
                            | (EntityRelationship.target_entity_id == entity_id)
                        )
                        orphan_rels = session.exec(stmt_rel_cleanup).all()
                        for rel in orphan_rels:
                            session.delete(rel)

                        session.delete(entity)
                        orphaned_count += 1

        session.commit()

        if orphaned_count > 0:
            logger.debug(f"Cleaned up {orphaned_count} orphaned entities with no remaining links")

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
) -> dict[str, UUID]:
    """Transaction 2: Create or link all entities atomically.

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all entities created/linked or none.

    Args:
        canonical_groups: Dict mapping canonical_name -> list of resolutions
        entity_name_to_docs: Dict mapping entity_name -> list of doc mentions

    Returns:
        Dict mapping entity_name -> entity_id
    """
    session = get_session()
    entity_name_to_id = {}

    try:
        for canonical_name, group_resolutions in canonical_groups.items():
            # Find the primary resolution (the one that's not a MERGE_WITH)
            primary_resolution = next(
                (r for r in group_resolutions if not r["decision"].startswith("MERGE_WITH:")),
                None,
            )

            # Defensive check: if all resolutions are MERGE_WITH
            if primary_resolution is None:
                logger.error(
                    f"All resolutions for '{canonical_name}' are MERGE_WITH decisions. "
                    f"This should not happen - indicates a bug in cycle detection. "
                    f"Converting to CREATE_NEW as fallback."
                )
                primary_resolution = group_resolutions[0]
                primary_resolution["decision"] = "CREATE_NEW"

            decision = primary_resolution["decision"]

            # Handle re-indexing: check if entity already exists
            if decision == "CREATE_NEW":
                entity_data = primary_resolution["entity_details"]
                existing = find_existing_entity(session, canonical_name, entity_data["type"])
                if existing:
                    logger.debug(
                        f"Re-indexing: Entity '{canonical_name}' exists, linking to {existing.id}"
                    )
                    decision = str(existing.id)

            if decision == "CREATE_NEW":
                # Create new entity
                entity_data = primary_resolution["entity_details"]
                entity = create_entity_with_document_edges(
                    session=session,
                    canonical_name=canonical_name,
                    group_resolutions=group_resolutions,
                    entity_name_to_docs=entity_name_to_docs,
                    entity_name_to_id=entity_name_to_id,
                    entity_data=entity_data,
                )

            else:
                # Link to existing entity
                try:
                    entity_id = UUID(decision)
                except ValueError:
                    logger.warning(
                        f"Invalid entity ID in decision: '{decision}' for entity '{group_resolutions[0]['entity_name']}'. "
                        f"Expected UUID format. Creating new entity instead."
                    )
                    entity_data = primary_resolution["entity_details"]
                    entity = create_entity_with_document_edges(
                        session=session,
                        canonical_name=canonical_name,
                        group_resolutions=group_resolutions,
                        entity_name_to_docs=entity_name_to_docs,
                        entity_name_to_id=entity_name_to_id,
                        entity_data=entity_data,
                    )
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

                    # Create document-entity edges for all mentions
                    docs_to_link = {}
                    for ent_name in all_entity_names:
                        for doc_info in entity_name_to_docs.get(ent_name, []):
                            doc_id = doc_info["document_id"]
                            # Keep the highest confidence if doc mentions multiple variations
                            if (
                                doc_id not in docs_to_link
                                or doc_info["confidence"] > docs_to_link[doc_id]["confidence"]
                            ):
                                docs_to_link[doc_id] = doc_info

                    for doc_info in docs_to_link.values():
                        find_or_create_document_entity_link(
                            session=session,
                            document_id=doc_info["document_id"],
                            entity_id=entity_id,
                            confidence=doc_info["confidence"],
                            context=doc_info.get("quote"),
                        )

        session.commit()
        return entity_name_to_id

    except Exception as e:
        logger.error(f"Error creating entities: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def create_relationships_txn(
    doc_to_kg_data: dict,
    entity_name_to_id: dict[str, UUID],
) -> int:
    """Transaction 3: Create all entity relationships atomically.

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all relationships created or none.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data with 'relationships'
        entity_name_to_id: Dict mapping entity_name -> entity_id

    Returns:
        Number of relationships created
    """
    session = get_session()
    relationships_created = 0

    try:
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
                    relationships_created += 1

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
def entity_resolution_workflow(doc_to_kg_data: dict, resolutions: list[dict]) -> dict:
    """Durable entity resolution workflow with fine-grained checkpointing.

    If this workflow crashes, DBOS automatically resumes from last completed step.

    Steps (each checkpointed):
    1. Clean up old entities (transaction)
    2. Build entity->docs mapping (step)
    3. Resolve merge chains (step)
    4. Group by canonical entity (step)
    5. Create/link all entities (transaction)
    6. Create relationships (transaction)

    Benefits:
    - LLM calls checkpointed per entity group (in Stage 3, before this workflow)
    - Clear transaction boundaries with automatic rollback
    - No duplicate entity creation on re-indexing
    - Easy to test individual steps

    Args:
        doc_to_kg_data: Dict mapping doc_id (UUID) -> kg_data dict
        resolutions: List of resolution decisions from Stage 3

    Returns:
        dict with:
            - document_ids: list of document IDs processed
            - entities_created: number of new entities created
            - entities_linked: number of existing entities linked
            - relationships_created: number of relationships created
            - orphaned_entities_cleaned: number of orphaned entities removed
            - workflow_id: DBOS workflow ID (for tracking/debugging)
    """
    all_document_ids = list(doc_to_kg_data.keys())

    # Step 1: Clean up old entities (transaction - checkpointed)
    orphaned_count = cleanup_old_entities_txn(doc_to_kg_data)

    # Step 2: Build entity->docs mapping (step - checkpointed)
    entity_name_to_docs = build_entity_docs_mapping_step(doc_to_kg_data)

    # Step 3: Resolve merge chains (step - checkpointed)
    merge_map = resolve_merge_chains_step(resolutions)

    # Step 4: Group by canonical entity (step - checkpointed)
    canonical_groups = group_by_canonical_step(resolutions, merge_map)

    # Step 5: Create/link all entities (transaction - checkpointed)
    entity_name_to_id = create_entities_txn(canonical_groups, entity_name_to_docs)

    # Step 6: Create relationships (transaction - checkpointed)
    relationships_created = create_relationships_txn(doc_to_kg_data, entity_name_to_id)

    # Calculate summary
    entities_created = len(
        [
            g
            for g, resols in canonical_groups.items()
            if any(r["decision"] == "CREATE_NEW" for r in resols)
        ]
    )
    entities_linked = len(canonical_groups) - entities_created

    logger.info(
        f"Entity resolution workflow complete: "
        f"Created {entities_created} new entities, "
        f"linked {entities_linked} to existing, "
        f"{relationships_created} relationships, "
        f"cleaned {orphaned_count} orphaned entities "
        f"for {len(all_document_ids)} documents"
    )

    return {
        "document_ids": [str(d) for d in all_document_ids],
        "entities_created": entities_created,
        "entities_linked": entities_linked,
        "relationships_created": relationships_created,
        "orphaned_entities_cleaned": orphaned_count,
        "workflow_id": DBOS.workflow_id,
    }
