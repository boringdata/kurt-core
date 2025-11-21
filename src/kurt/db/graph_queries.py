"""Knowledge graph query operations.

This module contains read-only query operations for the knowledge graph:
- Document entity queries
- Entity type queries
- Relationship queries
- Entity validation utilities
"""

import logging
from typing import Optional, Union
from uuid import UUID

from sqlmodel import Session, and_, col, func, or_, select

from kurt.db.database import get_session
from kurt.db.models import (
    Document,
    DocumentEntity,
    Entity,
    EntityRelationship,
    EntityType,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Validation Utilities
# ============================================================================


def _normalize_entity_type(entity_type: Optional[Union[EntityType, str]]) -> Optional[str]:
    """Normalize and validate entity type input.

    Args:
        entity_type: EntityType enum, string, "technologies" special value, or None

    Returns:
        Normalized entity type string or None
    """
    if entity_type is None:
        return None

    # Handle EntityType enum
    if isinstance(entity_type, EntityType):
        return entity_type.value

    # Handle string input
    if isinstance(entity_type, str):
        # Special case: "technologies" -> "Technology"
        if entity_type.lower() == "technologies":
            return "Technology"

        # Normalize to title case (Product, Feature, Technology, Topic, Company, Integration)
        normalized = entity_type.capitalize()

        # Validate against EntityType enum values
        valid_types = {et.value for et in EntityType}
        if normalized in valid_types:
            return normalized

        logger.warning(
            f"Invalid entity type '{entity_type}'. Valid types: {', '.join(valid_types)}. "
            f"Returning as-is (may cause query issues)."
        )
        return normalized

    logger.error(
        f"Unsupported entity_type type: {type(entity_type)}. Expected EntityType enum or string."
    )
    return None


# ============================================================================
# Document Entity Queries
# ============================================================================


def get_document_entities(
    document_id: UUID,
    entity_type: Optional[Union[EntityType, str]] = None,
    names_only: bool = False,
    session: Optional[Session] = None,
) -> Union[list[str], list[tuple[str, str]]]:
    """Get entities mentioned in a document.

    Args:
        document_id: Document UUID
        entity_type: Filter by entity type (optional)
        names_only: If True, return list[str] of canonical names. If False, return list of (name, type) tuples.
        session: SQLModel session (optional)

    Returns:
        If names_only=True: list[str] of canonical names
        If names_only=False: list[tuple[str, str]] of (canonical_name, entity_type)
    """
    if session is None:
        session = get_session()

    normalized_type = _normalize_entity_type(entity_type)

    # Query DocumentEntity join Entity
    if names_only:
        query = (
            select(Entity.canonical_name)
            .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
            .where(DocumentEntity.document_id == document_id)
        )
    else:
        query = (
            select(Entity.canonical_name, Entity.entity_type)
            .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
            .where(DocumentEntity.document_id == document_id)
        )

    if normalized_type:
        query = query.where(Entity.entity_type == normalized_type)

    if names_only:
        results = session.exec(query).all()
        return [name for name in results if name]
    else:
        results = session.exec(query).all()
        return [(name, etype) for name, etype in results if name and etype]


def get_top_entities(limit: int = 100, session: Optional[Session] = None) -> list[dict]:
    """Get top entities by source mentions."""
    if session is None:
        session = get_session()

    # Query top entities by source_mentions
    query = select(Entity).order_by(col(Entity.source_mentions).desc()).limit(limit)

    entities = session.exec(query).all()

    return [
        {
            "id": str(entity.id),
            "name": entity.name,
            "canonical_name": entity.canonical_name,
            "type": entity.entity_type,
            "aliases": entity.aliases,
            "description": entity.description,
            "source_mentions": entity.source_mentions,
        }
        for entity in entities
    ]


# ============================================================================
# Relationship Queries
# ============================================================================


def find_documents_with_relationship(
    source_entity_name: str,
    target_entity_name: str,
    relationship_type: Optional[str] = None,
    session: Optional[Session] = None,
) -> list[dict]:
    """Find documents where a specific relationship exists between two entities."""
    if session is None:
        session = get_session()

    # Find the entities
    source_entity = session.exec(
        select(Entity).where(
            or_(
                Entity.name == source_entity_name,
                Entity.canonical_name == source_entity_name,
            )
        )
    ).first()

    target_entity = session.exec(
        select(Entity).where(
            or_(
                Entity.name == target_entity_name,
                Entity.canonical_name == target_entity_name,
            )
        )
    ).first()

    if not source_entity or not target_entity:
        return []

    # Find relationships
    query = select(EntityRelationship).where(
        EntityRelationship.source_entity_id == source_entity.id,
        EntityRelationship.target_entity_id == target_entity.id,
    )

    if relationship_type:
        query = query.where(EntityRelationship.relationship_type == relationship_type)

    relationships = session.exec(query).all()

    if not relationships:
        return []

    # Find documents that mention both entities
    # (simplified - just find docs mentioning both)
    source_docs = session.exec(
        select(DocumentEntity.document_id).where(DocumentEntity.entity_id == source_entity.id)
    ).all()

    target_docs = session.exec(
        select(DocumentEntity.document_id).where(DocumentEntity.entity_id == target_entity.id)
    ).all()

    common_doc_ids = set(source_docs) & set(target_docs)

    if not common_doc_ids:
        return []

    # Get document details
    documents = session.exec(select(Document).where(col(Document.id).in_(common_doc_ids))).all()

    return [
        {
            "id": str(doc.id),
            "title": doc.title,
            "source_url": doc.source_url,
            "relationships": [
                {
                    "type": rel.relationship_type,
                    "confidence": rel.confidence,
                    "evidence_count": rel.evidence_count,
                    "context": rel.context,
                }
                for rel in relationships
            ],
        }
        for doc in documents
    ]


def get_document_links(
    document_id: UUID, link_type: Optional[str] = None, session: Optional[Session] = None
) -> list[dict]:
    """Get linked documents (via shared entities or explicit relationships)."""
    if session is None:
        session = get_session()

    # Get entities in this document
    doc_entity_ids = session.exec(
        select(DocumentEntity.entity_id).where(DocumentEntity.document_id == document_id)
    ).all()

    if not doc_entity_ids:
        return []

    # Find other documents sharing these entities
    linked_doc_ids = session.exec(
        select(DocumentEntity.document_id)
        .where(
            and_(
                col(DocumentEntity.entity_id).in_(doc_entity_ids),
                DocumentEntity.document_id != document_id,
            )
        )
        .distinct()
    ).all()

    if not linked_doc_ids:
        return []

    # Get document details with shared entity count
    linked_docs = []
    for linked_doc_id in linked_doc_ids:
        # Count shared entities
        shared_count = session.exec(
            select(func.count(DocumentEntity.entity_id)).where(
                and_(
                    DocumentEntity.document_id == linked_doc_id,
                    col(DocumentEntity.entity_id).in_(doc_entity_ids),
                )
            )
        ).one()

        doc = session.get(Document, linked_doc_id)
        if doc:
            linked_docs.append(
                {
                    "id": str(doc.id),
                    "title": doc.title,
                    "source_url": doc.source_url,
                    "shared_entities": shared_count,
                }
            )

    # Sort by shared entity count (descending)
    linked_docs.sort(key=lambda x: x["shared_entities"], reverse=True)

    return linked_docs


# ============================================================================
# Entity Type Queries
# ============================================================================


def list_entities_by_type(
    entity_type: Union[EntityType, str], limit: int = 100, session: Optional[Session] = None
) -> list[dict]:
    """List entities of a specific type."""
    if session is None:
        session = get_session()

    normalized_type = _normalize_entity_type(entity_type)

    if not normalized_type:
        logger.error(f"Invalid entity type: {entity_type}")
        return []

    query = (
        select(Entity)
        .where(Entity.entity_type == normalized_type)
        .order_by(col(Entity.source_mentions).desc())
        .limit(limit)
    )

    entities = session.exec(query).all()

    return [
        {
            "id": str(entity.id),
            "name": entity.name,
            "canonical_name": entity.canonical_name,
            "type": entity.entity_type,
            "aliases": entity.aliases,
            "description": entity.description,
            "source_mentions": entity.source_mentions,
        }
        for entity in entities
    ]


def find_documents_with_entity(
    entity_name: str,
    entity_type: Optional[Union[EntityType, str]] = None,
    session: Optional[Session] = None,
) -> set[UUID]:
    """Find documents mentioning a specific entity (case-insensitive partial match).

    Args:
        entity_name: Entity name or canonical name to search for (partial match)
        entity_type: Filter by entity type (optional)
        session: SQLModel session (optional)

    Returns:
        Set of document UUIDs
    """
    if session is None:
        session = get_session()

    normalized_type = _normalize_entity_type(entity_type)

    # Find matching entities (try both name and canonical_name, with partial matching)
    query = (
        select(DocumentEntity.document_id)
        .join(Entity, DocumentEntity.entity_id == Entity.id)
        .where(
            or_(
                Entity.name.ilike(f"%{entity_name}%"),
                Entity.canonical_name.ilike(f"%{entity_name}%"),
            )
        )
    )

    if normalized_type:
        query = query.where(Entity.entity_type == normalized_type)

    doc_ids = session.exec(query).all()

    return {doc_id for doc_id in doc_ids}


def get_document_knowledge_graph(document_id: str) -> dict:
    """Get the knowledge graph extraction for a single document.

    Returns all entities and relationships associated with the document.

    Args:
        document_id: Document UUID (full or partial)

    Returns:
        Dictionary with:
            - document_id: str
            - title: str
            - source_url: str
            - entities: list of dicts with entity info
            - relationships: list of dicts with relationship info
            - stats: counts and metrics

    Example:
        >>> kg = get_document_knowledge_graph("abc12345")
        >>> print(f"Found {len(kg['entities'])} entities")
        >>> for entity in kg['entities']:
        >>>     print(f"  {entity['name']} [{entity['type']}]")
    """
    session = get_session()

    # Get document using same logic as extract_document_metadata
    try:
        doc_uuid = UUID(document_id)
        doc = session.get(Document, doc_uuid)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
    except ValueError:
        # Try partial UUID match
        if len(document_id) < 8:
            raise ValueError(f"Document ID too short (minimum 8 characters): {document_id}")

        stmt = select(Document)
        docs = session.exec(stmt).all()
        partial_lower = document_id.lower().replace("-", "")
        matches = [d for d in docs if str(d.id).replace("-", "").startswith(partial_lower)]

        if len(matches) == 0:
            raise ValueError(f"Document not found: {document_id}")
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous document ID '{document_id}' matches {len(matches)} documents. "
                f"Please provide more characters."
            )

        doc = matches[0]

    # Get all entities linked to this document
    doc_entity_stmt = select(DocumentEntity).where(DocumentEntity.document_id == doc.id)
    doc_entities = session.exec(doc_entity_stmt).all()

    # Get full entity details
    entities = []
    entity_ids = set()
    for de in doc_entities:
        entity = session.get(Entity, de.entity_id)
        if entity:
            entity_ids.add(entity.id)
            entities.append(
                {
                    "id": str(entity.id),
                    "name": entity.name,
                    "type": entity.entity_type,
                    "canonical_name": entity.canonical_name,
                    "aliases": entity.aliases or [],
                    "description": entity.description,
                    "confidence": entity.confidence_score,
                    "mentions_in_doc": de.mention_count,
                    "mention_confidence": de.confidence,
                    "mention_context": de.context,
                }
            )

    # Get relationships between these entities
    relationships = []
    if entity_ids:
        # Find relationships where both source and target are in this document's entities
        rel_stmt = select(EntityRelationship).where(
            EntityRelationship.source_entity_id.in_(entity_ids)
        )
        all_rels = session.exec(rel_stmt).all()

        for rel in all_rels:
            # Only include if target is also in this document
            if rel.target_entity_id in entity_ids:
                source = session.get(Entity, rel.source_entity_id)
                target = session.get(Entity, rel.target_entity_id)
                if source and target:
                    relationships.append(
                        {
                            "id": str(rel.id),
                            "source_entity": source.name,
                            "source_id": str(source.id),
                            "target_entity": target.name,
                            "target_id": str(target.id),
                            "relationship_type": rel.relationship_type,
                            "confidence": rel.confidence,
                            "evidence_count": rel.evidence_count,
                            "context": rel.context,
                        }
                    )

    return {
        "document_id": str(doc.id),
        "title": doc.title,
        "source_url": doc.source_url,
        "entities": entities,
        "relationships": relationships,
        "stats": {
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "avg_entity_confidence": (
                sum(e["confidence"] for e in entities) / len(entities) if entities else 0.0
            ),
            "avg_relationship_confidence": (
                sum(r["confidence"] for r in relationships) / len(relationships)
                if relationships
                else 0.0
            ),
        },
    }
