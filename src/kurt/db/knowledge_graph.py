"""Knowledge graph utilities for querying entities linked to documents."""

import asyncio
import logging
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

import numpy as np
from sqlmodel import Session, select
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.content.embeddings import embedding_to_bytes, generate_embeddings
from kurt.content.indexing_models import EntityType
from kurt.db.database import async_session_scope, session_scope
from kurt.db.models import DocumentEntity, Entity

if TYPE_CHECKING:
    from kurt.content.indexing_models import RelationshipType

logger = logging.getLogger(__name__)

# Special entity type groupings
TECHNOLOGY_TYPES = [EntityType.TECHNOLOGY.value, EntityType.PRODUCT.value]


# ============================================================================
# Validation Utilities
# ============================================================================


def _normalize_entity_type(entity_type: Optional[Union[EntityType, str]]) -> Optional[str]:
    """Normalize and validate entity type input.

    Args:
        entity_type: EntityType enum, string, "technologies" special value, or None

    Returns:
        Normalized string value or None

    Raises:
        ValueError: If entity_type is invalid
    """
    if entity_type is None:
        return None

    if isinstance(entity_type, EntityType):
        return entity_type.value

    # Special multi-type value
    if entity_type == "technologies":
        return "technologies"

    # Normalize case
    normalized = entity_type.capitalize()

    # Validate
    valid_types = [e.value for e in EntityType]
    if normalized not in valid_types:
        raise ValueError(
            f"Invalid entity_type '{entity_type}'. "
            f"Must be one of {valid_types} or special value 'technologies'"
        )

    return normalized


def get_document_entities(
    document_id: UUID,
    entity_type: Optional[Union[EntityType, str]] = None,
    names_only: bool = False,
    session: Optional[Session] = None,
) -> list[str] | list[tuple[str, str]]:
    """Get all entities for a document from the knowledge graph.

    Args:
        document_id: Document UUID
        entity_type: Filter by EntityType enum, string, or "technologies" (Tech+Product)
        names_only: If True, return list[str], else list[tuple[str, str]]
        session: Optional SQLModel session

    Returns:
        Entity names or (name, type) tuples
    """
    entity_type = _normalize_entity_type(entity_type)

    with session_scope(session) as s:
        if names_only:
            stmt = (
                select(Entity.canonical_name)
                .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
                .where(DocumentEntity.document_id == document_id)
            )
        else:
            stmt = (
                select(Entity.canonical_name, Entity.entity_type)
                .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
                .where(DocumentEntity.document_id == document_id)
            )

        # Apply entity type filter
        if entity_type == "technologies":
            stmt = stmt.where(Entity.entity_type.in_(TECHNOLOGY_TYPES))
        elif entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)

        if names_only:
            return [name for name in s.exec(stmt).all() if name]
        else:
            return [(name, etype) for name, etype in s.exec(stmt).all() if name and etype]


def get_top_entities(limit: int = 100, session: Optional[Session] = None) -> list[dict]:
    """Get most commonly mentioned entities across all documents.

    Args:
        limit: Maximum number of entities to return
        session: Optional SQLModel session

    Returns:
        List of dicts with id, name, type, description, aliases, canonical_name
    """
    with session_scope(session) as s:
        stmt = (
            select(Entity)
            .where(Entity.source_mentions > 0)
            .order_by(Entity.source_mentions.desc())
            .limit(limit)
        )
        entities = s.exec(stmt).all()

        return [
            {
                "id": str(e.id),
                "name": e.name,
                "type": e.entity_type,
                "description": e.description or "",
                "aliases": e.aliases or [],
                "canonical_name": e.canonical_name or e.name,
            }
            for e in entities
        ]


def find_documents_with_relationship(
    relationship_type: Union["RelationshipType", str],
    source_entity_name: Optional[str] = None,
    target_entity_name: Optional[str] = None,
    session: Optional[Session] = None,
) -> set[UUID]:
    """Find document IDs containing entities with a specific relationship.

    Args:
        relationship_type: RelationshipType enum or string
        source_entity_name: Filter for source entity (case-insensitive partial match)
        target_entity_name: Filter for target entity (case-insensitive partial match)
        session: Optional SQLModel session

    Returns:
        Set of document UUIDs
    """
    from kurt.content.indexing_models import RelationshipType
    from kurt.db.models import Entity, EntityRelationship

    # Normalize and validate
    if isinstance(relationship_type, RelationshipType):
        relationship_type = relationship_type.value

    valid_types = [r.value for r in RelationshipType]
    if relationship_type not in valid_types:
        raise ValueError(
            f"Invalid relationship_type '{relationship_type}'. Must be one of {valid_types}"
        )

    with session_scope(session) as s:
        stmt = select(EntityRelationship).where(
            EntityRelationship.relationship_type == relationship_type
        )

        # Apply entity name filters
        if source_entity_name:
            source_entity_alias = Entity.__table__.alias("source_entity")
            stmt = stmt.join(
                source_entity_alias,
                EntityRelationship.source_entity_id == source_entity_alias.c.id,
            ).where(
                (source_entity_alias.c.name.ilike(f"%{source_entity_name}%"))
                | (source_entity_alias.c.canonical_name.ilike(f"%{source_entity_name}%"))
            )

        if target_entity_name:
            target_entity_alias = Entity.__table__.alias("target_entity")
            stmt = stmt.join(
                target_entity_alias,
                EntityRelationship.target_entity_id == target_entity_alias.c.id,
            ).where(
                (target_entity_alias.c.name.ilike(f"%{target_entity_name}%"))
                | (target_entity_alias.c.canonical_name.ilike(f"%{target_entity_name}%"))
            )

        relationships = s.exec(stmt).all()

        # Collect entity IDs
        entity_ids = {
            e_id for rel in relationships for e_id in (rel.source_entity_id, rel.target_entity_id)
        }
        if not entity_ids:
            return set()

        # Find documents mentioning these entities
        doc_stmt = select(DocumentEntity.document_id).where(
            DocumentEntity.entity_id.in_(entity_ids)
        )
        return {doc_id for doc_id in s.exec(doc_stmt).all()}


def get_document_links(
    document_id: UUID,
    direction: str = "outbound",
    session: Optional[Session] = None,
) -> list[dict]:
    """Get links from or to a document.

    Args:
        document_id: Document UUID
        direction: "outbound" (FROM doc) or "inbound" (TO doc)
        session: Optional SQLModel session

    Returns:
        List of dicts with source_id, source_title, target_id, target_title, anchor_text
    """
    from kurt.db.models import Document, DocumentLink

    if direction not in ("outbound", "inbound"):
        raise ValueError(f"Invalid direction: {direction}. Must be 'outbound' or 'inbound'")

    with session_scope(session) as s:
        doc = s.get(Document, document_id)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # Query based on direction
        if direction == "outbound":
            stmt = (
                select(DocumentLink, Document)
                .where(DocumentLink.source_document_id == document_id)
                .join(Document, DocumentLink.target_document_id == Document.id)
            )
        else:
            stmt = (
                select(DocumentLink, Document)
                .where(DocumentLink.target_document_id == document_id)
                .join(Document, DocumentLink.source_document_id == Document.id)
            )

        results = s.exec(stmt).all()

        # Format results
        links = []
        for link, related_doc in results:
            if direction == "outbound":
                links.append(
                    {
                        "source_id": str(link.source_document_id),
                        "source_title": doc.title,
                        "target_id": str(link.target_document_id),
                        "target_title": related_doc.title,
                        "anchor_text": link.anchor_text,
                    }
                )
            else:
                links.append(
                    {
                        "source_id": str(link.source_document_id),
                        "source_title": related_doc.title,
                        "target_id": str(link.target_document_id),
                        "target_title": doc.title,
                        "anchor_text": link.anchor_text,
                    }
                )

        return links


def list_entities_by_type(
    entity_type: Optional[str] = None,
    min_docs: int = 1,
    include_pattern: Optional[str] = None,
    session: Optional[Session] = None,
) -> list[dict[str, any]]:
    """List entities with document counts.

    Args:
        entity_type: Filter by entity type (Topic, Technology, etc.)
        min_docs: Minimum document count threshold
        include_pattern: Glob pattern to filter documents
        session: Optional SQLModel session

    Returns:
        List of dicts with entity, entity_type, doc_count (sorted by count desc)
    """
    from fnmatch import fnmatch

    from kurt.db.models import Document, IngestionStatus

    with session_scope(session) as s:
        normalized_entity_type = entity_type.capitalize() if entity_type else None

        stmt = select(
            Entity.name, Entity.canonical_name, Entity.entity_type, DocumentEntity.document_id
        ).join(DocumentEntity, Entity.id == DocumentEntity.entity_id)

        if normalized_entity_type:
            stmt = stmt.where(Entity.entity_type == normalized_entity_type)

        entity_mentions = s.exec(stmt).all()

        # Build doc count per entity
        entity_docs = {}
        for entity_name, canonical_name, etype, doc_id in entity_mentions:
            entity_display_name = canonical_name or entity_name
            key = (entity_display_name, etype)
            if key not in entity_docs:
                entity_docs[key] = set()
            entity_docs[key].add(doc_id)

        # Filter by pattern if needed
        if include_pattern:
            doc_stmt = select(Document).where(Document.ingestion_status == IngestionStatus.FETCHED)
            matching_docs = s.exec(doc_stmt).all()
            matching_doc_ids = {
                str(d.id)
                for d in matching_docs
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            }

            for key in list(entity_docs.keys()):
                entity_docs[key] &= matching_doc_ids

        # Filter and sort
        filtered_entities = [
            (entity_name, etype, len(doc_ids))
            for (entity_name, etype), doc_ids in entity_docs.items()
            if len(doc_ids) >= min_docs
        ]
        filtered_entities.sort(key=lambda x: (-x[2], x[0]))

        return [
            {"entity": entity_name, "entity_type": etype, "doc_count": count}
            for entity_name, etype, count in filtered_entities
        ]


def find_documents_with_entity(
    entity_name: str,
    entity_type: Optional[Union[EntityType, str]] = None,
    session: Optional[Session] = None,
) -> set[UUID]:
    """Find document IDs containing a specific entity (case-insensitive partial match).

    Args:
        entity_name: Entity name or partial match
        entity_type: Filter by EntityType enum, string, or "technologies"
        session: Optional SQLModel session

    Returns:
        Set of document UUIDs
    """
    entity_type = _normalize_entity_type(entity_type)

    with session_scope(session) as s:
        stmt = (
            select(DocumentEntity.document_id)
            .join(Entity, DocumentEntity.entity_id == Entity.id)
            .where(
                (Entity.name.ilike(f"%{entity_name}%"))
                | (Entity.canonical_name.ilike(f"%{entity_name}%"))
            )
        )

        if entity_type == "technologies":
            stmt = stmt.where(Entity.entity_type.in_(TECHNOLOGY_TYPES))
        elif entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)

        return {doc_id for doc_id in s.exec(stmt).all()}


# ============================================================================
# Entity Search and Similarity
# ============================================================================


def cosine_similarity(emb1: list[float], emb2: list[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    a = np.array(emb1)
    b = np.array(emb2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_similar_entities(
    entity_name: str,
    entity_type: str,
    limit: int = 20,
    session: Optional[Session] = None,
) -> list[dict]:
    """Search for entities similar to the given name using vector search.

    Args:
        entity_name: Entity name to find similar entities for
        entity_type: Entity type filter (only return same type)
        limit: Maximum number of results
        session: Optional SQLModel session

    Returns:
        List of dicts with id, name, type, description, aliases, canonical_name, similarity
    """
    from kurt.db.sqlite import SQLiteClient

    with session_scope(session) as s:
        # Try to get stored embedding first
        existing_entity = s.exec(
            select(Entity).where(Entity.name == entity_name, Entity.entity_type == entity_type)
        ).first()

        if existing_entity:
            embedding_bytes = existing_entity.embedding
        else:
            # Generate new embedding for search query
            embedding_vector = generate_embeddings([entity_name])[0]
            embedding_bytes = embedding_to_bytes(embedding_vector)

        # Use SQLite client's vector search
        client = SQLiteClient()
        results = client.search_similar_entities(embedding_bytes, limit=limit, min_similarity=0.70)

        # Load and filter entity details
        similar_entities = []
        for entity_id, similarity in results:
            entity = s.get(Entity, UUID(entity_id))
            if entity and entity.entity_type == entity_type:
                entity_dict = entity.model_dump(exclude={"embedding"}, mode="python")
                entity_dict["id"] = str(entity_dict["id"])
                entity_dict["type"] = entity_dict.pop("entity_type")
                entity_dict["similarity"] = similarity
                similar_entities.append(entity_dict)

        return similar_entities


# ============================================================================
# Async Functions
# ============================================================================


async def search_similar_entities_async(
    entity_name: str,
    entity_type: str,
    limit: int = 20,
    session: Optional[AsyncSession] = None,
) -> list[dict]:
    """Async version of search_similar_entities.

    Search for entities similar to the given name using vector search.

    Args:
        entity_name: Entity name to find similar entities for
        entity_type: Entity type filter (only return same type)
        limit: Maximum number of results
        session: Optional AsyncSession

    Returns:
        List of dicts with id, name, type, description, aliases, canonical_name, similarity

    Usage:
        # Single query
        async with async_session_scope() as session:
            similar = await search_similar_entities_async(
                "Python", "Technology", session=session
            )

        # Batch queries (each creates its own session)
        async def fetch_similar(name: str, entity_type: str):
            async with async_session_scope() as session:
                return await search_similar_entities_async(
                    name, entity_type, session=session
                )

        results = await asyncio.gather(*[
            fetch_similar(name, type) for name, type in entities
        ])
    """
    async with async_session_scope(session) as s:
        # Try to get stored embedding first
        result = await s.exec(
            select(Entity).where(Entity.name == entity_name, Entity.entity_type == entity_type)
        )
        existing_entity = result.first()

        if existing_entity:
            embedding_bytes = existing_entity.embedding
        else:
            # Generate new embedding (sync operation - run in executor)
            loop = asyncio.get_event_loop()
            embedding_vector = await loop.run_in_executor(
                None, lambda: generate_embeddings([entity_name])[0]
            )
            embedding_bytes = embedding_to_bytes(embedding_vector)

        # Vector search is sync (SQLite limitation) - run in executor
        from kurt.db.sqlite import SQLiteClient

        client = SQLiteClient()
        search_results = await loop.run_in_executor(
            None,
            lambda: client.search_similar_entities(
                embedding_bytes, limit=limit, min_similarity=0.70
            ),
        )

        # Load and filter entity details
        similar_entities = []
        for entity_id, similarity in search_results:
            entity = await s.get(Entity, UUID(entity_id))
            if entity and entity.entity_type == entity_type:
                entity_dict = entity.model_dump(exclude={"embedding"}, mode="python")
                entity_dict["id"] = str(entity_dict["id"])
                entity_dict["type"] = entity_dict.pop("entity_type")
                entity_dict["similarity"] = similarity
                similar_entities.append(entity_dict)

        return similar_entities
