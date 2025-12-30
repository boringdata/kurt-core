"""Knowledge graph utilities for querying entities linked to documents."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import numpy as np
from sklearn.cluster import DBSCAN
from sqlmodel import select

from kurt.db.models import DocumentEntity, Entity, EntityType
from kurt.utils.embeddings import embedding_to_bytes, generate_embeddings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Special entity type groupings
TECHNOLOGY_TYPES = [EntityType.TECHNOLOGY.value, EntityType.PRODUCT.value]


# ============================================================================
# Entity Clustering
# ============================================================================


def cluster_entities_by_similarity(
    entities: list[dict], eps: float = 0.25, min_samples: int = 1
) -> dict[int, list[dict]]:
    """Cluster entities using DBSCAN on their embeddings.

    Args:
        entities: List of entity dicts with 'name' field
        eps: Maximum distance between two samples for clustering
        min_samples: Minimum samples in a neighborhood for a core point

    Returns:
        Dict mapping cluster_id -> list of entities in that cluster
    """
    if not entities:
        return {}

    # Generate embeddings for all entities
    entity_names = [e["name"] for e in entities]
    embeddings = generate_embeddings(entity_names)

    # Cluster using DBSCAN
    embeddings_array = np.array(embeddings)
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    labels = clustering.fit_predict(embeddings_array)

    # Organize into groups
    groups = {}
    for idx, label in enumerate(labels):
        if label not in groups:
            groups[label] = []
        groups[label].append(entities[idx])

    logger.info(f"Clustered {len(entities)} entities into {len(groups)} groups")
    logger.debug(
        f"  Sample groups: {[(gid, [e['name'] for e in ents]) for gid, ents in list(groups.items())[:3]]}"
    )

    return groups


def split_large_groups(
    groups: dict[int, list[dict]], max_group_size: int = 20
) -> dict[int, list[dict]]:
    """Split groups that exceed max_group_size into smaller sub-groups.

    Large groups can cause LLM token limits to be exceeded. This function
    splits them into smaller chunks while preserving the clustering intent.

    Args:
        groups: Dict mapping cluster_id -> list of entities
        max_group_size: Maximum entities per group (default 20)

    Returns:
        New dict with large groups split into sub-groups with new IDs
    """
    if max_group_size <= 0:
        return groups

    result = {}
    next_id = max(groups.keys()) + 1 if groups else 0
    split_count = 0

    for group_id, entities in groups.items():
        if len(entities) <= max_group_size:
            # Group is small enough, keep as-is
            result[group_id] = entities
        else:
            # Split into chunks
            split_count += 1
            for i in range(0, len(entities), max_group_size):
                chunk = entities[i : i + max_group_size]
                if i == 0:
                    # First chunk keeps original ID
                    result[group_id] = chunk
                else:
                    # Subsequent chunks get new IDs
                    result[next_id] = chunk
                    next_id += 1

    if split_count > 0:
        logger.info(
            f"Split {split_count} large groups (>{max_group_size} entities) into {len(result)} total groups"
        )

    return result


# ============================================================================
# Entity Creation
# ============================================================================


def create_entity_with_document_edges(
    session,
    canonical_name: str,
    group_resolutions: list,
    entity_name_to_docs: dict,
    entity_name_to_id: dict,
    entity_data: dict,
    entity_embedding: list = None,
) -> Entity:
    """Create a new entity with document edges from entity resolution.

    This function handles the complete entity creation workflow:
    1. Aggregates data from all entity name variations in a group
    2. Creates the Entity with embeddings
    3. Creates DocumentEntity edges for all mentioning documents

    Args:
        session: Database session
        canonical_name: Canonical name for the entity
        group_resolutions: List of resolutions in this group (from LLM)
        entity_name_to_docs: Mapping of entity names to document info
        entity_name_to_id: Mapping to update with new entity ID
        entity_data: Entity details from resolution (type, description, etc.)
        entity_embedding: Pre-computed embedding (optional, will generate if None)

    Returns:
        Created Entity object

    Note:
        If entity_embedding is None, this function will generate it synchronously.
        For async contexts, compute the embedding beforehand using run_in_executor.
    """
    from datetime import datetime
    from uuid import uuid4

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
    confidence_scores = [r["entity_details"].get("confidence", 0.9) for r in group_resolutions]
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.9

    # Create entity with embedding (generate if not provided)
    if entity_embedding is None:
        entity_embedding = generate_embeddings([canonical_name])[0]

    entity = Entity(
        id=uuid4(),
        name=canonical_name,
        entity_type=entity_data["type"],
        canonical_name=canonical_name,
        aliases=list(all_aliases),
        description=entity_data.get("description", ""),
        embedding=embedding_to_bytes(entity_embedding),
        confidence_score=avg_confidence,
        source_mentions=doc_count,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(entity)
    session.flush()

    # Map all names in this group to this entity ID
    for ent_name in all_entity_names:
        entity_name_to_id[ent_name] = entity.id

    # Create document-entity edges for ALL documents/sections that mention any entity in this group
    # Key by (doc_id, section_id) to allow same entity in multiple sections
    docs_to_link = {}
    for ent_name in all_entity_names:
        for doc_info in entity_name_to_docs.get(ent_name, []):
            doc_id = doc_info["document_id"]
            section_id = doc_info.get("section_id")
            key = (doc_id, section_id)
            # Keep the highest confidence if same doc/section mentions multiple variations
            if key not in docs_to_link or doc_info["confidence"] > docs_to_link[key]["confidence"]:
                docs_to_link[key] = doc_info

    for doc_info in docs_to_link.values():
        edge = DocumentEntity(
            id=uuid4(),
            document_id=doc_info["document_id"],
            entity_id=entity.id,
            section_id=doc_info.get("section_id"),
            mention_count=1,
            confidence=doc_info["confidence"],
            context=doc_info.get("quote"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(edge)

    return entity


def find_existing_entity(session, canonical_name: str, entity_type: str = None) -> Entity | None:
    """Find an existing entity by canonical name (case-insensitive).

    Used during re-indexing to check if entity already exists before creating duplicate.
    Matches by name only - entity_type is ignored to prevent duplicates with different types.

    Args:
        session: Database session
        canonical_name: Canonical name to search for
        entity_type: Ignored (kept for backward compatibility)

    Returns:
        Entity if found, None otherwise
    """
    from sqlalchemy import func

    # Use case-insensitive comparison for canonical name only
    # Don't filter by type - same entity shouldn't exist with multiple types
    stmt = select(Entity).where(
        func.lower(Entity.canonical_name) == func.lower(canonical_name),
    )
    return session.exec(stmt).first()


def find_or_create_document_entity_link(
    session,
    document_id: UUID,
    entity_id: UUID,
    confidence: float,
    context: str | None = None,
    section_id: str | None = None,
) -> DocumentEntity:
    """Find existing document-entity link or create new one.

    Used during re-indexing to prevent duplicate links and UNIQUE constraint violations.

    Args:
        session: Database session
        document_id: Document UUID
        entity_id: Entity UUID
        confidence: Confidence score
        context: Optional context/quote
        section_id: Optional section ID where entity is mentioned

    Returns:
        DocumentEntity (existing or newly created)
    """
    # Check if link already exists (considering section_id for uniqueness)
    stmt = select(DocumentEntity).where(
        DocumentEntity.document_id == document_id,
        DocumentEntity.entity_id == entity_id,
        DocumentEntity.section_id == section_id,
    )
    existing_edge = session.exec(stmt).first()

    if existing_edge:
        # Update existing edge
        existing_edge.confidence = confidence
        existing_edge.context = context
        existing_edge.updated_at = datetime.utcnow()
        return existing_edge
    else:
        # Create new edge
        edge = DocumentEntity(
            id=uuid4(),
            document_id=document_id,
            entity_id=entity_id,
            section_id=section_id,
            mention_count=1,
            confidence=confidence,
            context=context,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(edge)
        return edge
