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

from kurt.content.indexing_models import EntityType
from kurt.db.database import get_session
from kurt.db.models import Document, DocumentEntity, Entity, EntityRelationship

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
        # Special case: "technologies" -> "TOOL"
        if entity_type.lower() == "technologies":
            return "TOOL"

        # Normalize to uppercase
        normalized = entity_type.upper()

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
    session: Optional[Session] = None,
) -> list[dict]:
    """Get entities mentioned in a document."""
    if session is None:
        session = get_session()

    normalized_type = _normalize_entity_type(entity_type)

    # Query DocumentEntity join Entity
    query = (
        select(Entity, DocumentEntity.confidence)
        .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
        .where(DocumentEntity.document_id == document_id)
    )

    if normalized_type:
        query = query.where(Entity.entity_type == normalized_type)

    results = session.exec(query).all()

    return [
        {
            "id": str(entity.id),
            "name": entity.name,
            "canonical_name": entity.canonical_name,
            "type": entity.entity_type,
            "aliases": entity.aliases,
            "description": entity.description,
            "confidence": confidence,
            "source_mentions": entity.source_mentions,
        }
        for entity, confidence in results
    ]


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
    entity_name: str, limit: int = 100, session: Optional[Session] = None
) -> list[dict]:
    """Find documents mentioning a specific entity (by name or canonical name)."""
    if session is None:
        session = get_session()

    # Find the entity (try both name and canonical_name)
    entity = session.exec(
        select(Entity).where(
            or_(
                Entity.name == entity_name,
                Entity.canonical_name == entity_name,
            )
        )
    ).first()

    if not entity:
        return []

    # Find documents mentioning this entity
    query = (
        select(Document, DocumentEntity.confidence)
        .join(DocumentEntity, Document.id == DocumentEntity.document_id)
        .where(DocumentEntity.entity_id == entity.id)
        .limit(limit)
    )

    results = session.exec(query).all()

    return [
        {
            "id": str(doc.id),
            "title": doc.title,
            "source_url": doc.source_url,
            "confidence": confidence,
            "content_type": doc.content_type,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc, confidence in results
    ]
