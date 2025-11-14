"""Document knowledge graph queries.

This module provides read-only query functions for the knowledge graph.
No DSPy traces - pure database queries.
"""

import logging
from uuid import UUID

from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, DocumentEntity, Entity, EntityRelationship

logger = logging.getLogger(__name__)


def get_document_knowledge_graph(document_id: str) -> dict:
    """
    Get the knowledge graph extraction for a single document.

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
