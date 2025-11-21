"""Entity resolution operations for knowledge graph construction.

These functions handle the complex logic of entity deduplication and resolution:
- Building entity-document mappings
- Resolving merge chains and detecting cycles
- Grouping entities by canonical names
- Cleaning up old entities during re-indexing
- Creating entities and relationships

Organized into:
- Pure logic functions (no I/O)
- Database operation functions (session-based I/O)
"""

import logging
from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import select

from kurt.db.graph_entities import (
    create_entity_with_document_edges,
    find_existing_entity,
    find_or_create_document_entity_link,
)
from kurt.db.models import DocumentEntity, Entity, EntityRelationship

logger = logging.getLogger(__name__)


# ============================================================================
# Stage 2: Link Existing Entities
# ============================================================================


def link_existing_entities(session, document_id: UUID, existing_entity_ids: list[str]) -> int:
    """
    Stage 2: Create document-entity edges for EXISTING entities.

    Args:
        session: Database session
        document_id: Document UUID
        existing_entity_ids: List of entity IDs that were matched during indexing

    Returns:
        Number of entities linked
    """
    linked_count = 0

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

        linked_count += 1

    logger.info(f"Stage 2: Linked {linked_count} existing entities to document {document_id}")
    return linked_count


# ============================================================================
# Stage 3/4: Entity Resolution Logic
# ============================================================================


def build_entity_docs_mapping(doc_to_kg_data: dict) -> dict[str, list[dict]]:
    """Build mapping of which documents mention which entity names.

    Pure function - no I/O, just data transformation.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data with 'new_entities'

    Returns:
        Dict mapping entity_name -> list of {document_id, confidence, quote}
    """
    entity_name_to_docs = {}

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

    return entity_name_to_docs


def resolve_merge_chains(resolutions: list[dict]) -> dict[str, str]:
    """Handle MERGE_WITH decisions and build canonical entity map.

    This function:
    1. Extracts MERGE_WITH decisions from resolutions
    2. Validates merge targets exist in the group
    3. Detects and breaks cycles in merge chains
    4. Builds transitive closure (A->B, B->C => A->C)

    Pure function - no I/O, just graph algorithms.

    Args:
        resolutions: List of resolution decisions with 'entity_name' and 'decision'

    Returns:
        Dict mapping entity_name -> canonical_entity_name

    Side effects:
        Modifies resolutions in-place to fix invalid MERGE_WITH targets
    """
    merge_map = {}  # entity_name -> canonical_entity_name
    all_entity_names = {r["entity_name"] for r in resolutions}

    # Extract MERGE_WITH decisions
    for resolution in resolutions:
        entity_name = resolution["entity_name"]
        decision = resolution["decision"]

        if decision.startswith("MERGE_WITH:"):
            merge_target = decision.replace("MERGE_WITH:", "").strip()

            # Validate merge target exists
            if merge_target not in all_entity_names:
                logger.warning(
                    f"Invalid MERGE_WITH target '{merge_target}' for entity '{entity_name}'. "
                    f"Target not found in group {list(all_entity_names)}. "
                    f"Treating as CREATE_NEW instead."
                )
                resolution["decision"] = "CREATE_NEW"
                continue

            merge_map[entity_name] = merge_target

    # Cycle detection helper
    def find_canonical_with_cycle_detection(entity_name: str, visited: set) -> str | None:
        """Follow merge chain to find canonical entity. Returns None if cycle detected."""
        if entity_name not in merge_map:
            return entity_name  # This is canonical

        if entity_name in visited:
            return None  # Cycle detected!

        visited.add(entity_name)
        return find_canonical_with_cycle_detection(merge_map[entity_name], visited)

    # Detect and break cycles
    for entity_name in list(merge_map.keys()):
        canonical = find_canonical_with_cycle_detection(entity_name, set())
        if canonical is None:
            # Cycle detected - find all entities in cycle
            cycle_entities = []
            current = entity_name
            visited = set()
            while current not in visited:
                visited.add(current)
                cycle_entities.append(current)
                if current not in merge_map:
                    break
                current = merge_map[current]

            logger.warning(
                f"Cycle detected in merge chain: {' -> '.join(cycle_entities)} -> {current}. "
                f"Breaking cycle by choosing '{cycle_entities[0]}' as canonical entity."
            )

            # Break cycle: first entity becomes canonical
            canonical_entity = cycle_entities[0]
            for ent in cycle_entities:
                if ent == canonical_entity:
                    merge_map.pop(ent, None)
                    # Update resolution to CREATE_NEW
                    for res in resolutions:
                        if res["entity_name"] == ent:
                            res["decision"] = "CREATE_NEW"
                            break
                else:
                    merge_map[ent] = canonical_entity

    # Build transitive closure for remaining (non-cyclic) chains
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

    return merge_map


def group_by_canonical_entity(
    resolutions: list[dict], merge_map: dict[str, str]
) -> dict[str, list[dict]]:
    """Group resolutions by their canonical entity name.

    For merged entities, uses the canonical name from the merge target's resolution.

    Pure function - no I/O, just data transformation.

    Args:
        resolutions: List of resolution decisions
        merge_map: Dict mapping entity_name -> canonical_entity_name

    Returns:
        Dict mapping canonical_name -> list of resolutions in that group
    """
    canonical_groups = {}

    for resolution in resolutions:
        entity_name = resolution["entity_name"]

        if entity_name in merge_map:
            # This entity merges with a peer - find canonical resolution
            canonical_name = merge_map[entity_name]
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

    return canonical_groups


# ============================================================================
# Database Operation Functions
# ============================================================================


def cleanup_old_entities(session, doc_to_kg_data: dict) -> int:
    """Clean up old document-entity links when re-indexing.

    This removes stale entity links from previous indexing runs, but preserves:
    - Links to entities being linked via Stage 2 (existing_entities)
    - Links to entities being created in Stage 4 (new_entities)

    Args:
        session: SQLModel session
        doc_to_kg_data: Dict mapping doc_id -> kg_data

    Returns:
        Number of orphaned entities cleaned up
    """
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

    if orphaned_count > 0:
        logger.debug(f"Cleaned up {orphaned_count} orphaned entities with no remaining links")

    return orphaned_count


def create_entities(
    session,
    canonical_groups: dict[str, list[dict]],
    entity_name_to_docs: dict[str, list[dict]],
) -> dict[str, UUID]:
    """Create or link all entities.

    Args:
        session: SQLModel session
        canonical_groups: Dict mapping canonical_name -> list of resolutions
        entity_name_to_docs: Dict mapping entity_name -> list of doc mentions

    Returns:
        Dict mapping entity_name -> entity_id
    """
    entity_name_to_id = {}

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

    return entity_name_to_id


def create_relationships(
    session,
    doc_to_kg_data: dict,
    entity_name_to_id: dict[str, UUID],
) -> int:
    """Create all entity relationships.

    Args:
        session: SQLModel session
        doc_to_kg_data: Dict mapping doc_id -> kg_data with 'relationships'
        entity_name_to_id: Dict mapping entity_name -> entity_id

    Returns:
        Number of relationships created
    """
    relationships_created = 0

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

    return relationships_created
