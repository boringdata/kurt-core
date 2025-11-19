"""Knowledge graph utilities for querying entities linked to documents.

This module provides utilities to retrieve entities from the knowledge graph:
- Per-document queries: Get entities for a specific document
- Cross-document queries: Get top entities across all documents

All functions accept an optional session parameter for transaction management and testing.
"""

from typing import Optional, Union
from uuid import UUID

from sqlmodel import Session, select

from kurt.content.indexing_models import EntityType
from kurt.db.database import get_session
from kurt.db.models import DocumentEntity, Entity

# Special entity type groupings for convenience
TECHNOLOGY_TYPES = [EntityType.TECHNOLOGY.value, EntityType.PRODUCT.value]


def get_document_entities(
    document_id: UUID,
    entity_type: Optional[Union[EntityType, str]] = None,
    names_only: bool = False,
    session: Optional[Session] = None,
) -> list[str] | list[tuple[str, str]]:
    """
    Get all entities for a document from the knowledge graph.

    Args:
        document_id: The document UUID
        entity_type: Optional entity type filter. Can be:
            - An EntityType enum value (e.g., EntityType.TOPIC)
            - A valid EntityType string: "Topic", "Technology", "Product", "Feature", "Company", "Integration"
            - Special value "technologies" to get Technology+Product types (commonly used for tools/tech)
            - None to get all entity types
        names_only: If True, return only canonical names (list[str])
                   If False, return tuples of (canonical_name, entity_type)
        session: Optional SQLModel session (will create one if not provided)

    Returns:
        list[str] if names_only=True, list[tuple[str, str]] otherwise

    Raises:
        ValueError: If entity_type is not a valid EntityType or special value

    Examples:
        # Get all entities with types
        entities = get_document_entities(doc.id)
        # Returns: [("Python", "Topic"), ("FastAPI", "Technology"), ...]

        # Get only topics (names only, using enum)
        topics = get_document_entities(doc.id, entity_type=EntityType.TOPIC, names_only=True)
        # Returns: ["Python", "Web Development", "API Design"]

        # Get only topics (names only, using string)
        topics = get_document_entities(doc.id, entity_type="Topic", names_only=True)
        # Returns: ["Python", "Web Development", "API Design"]

        # Get all technologies/products (names only)
        tools = get_document_entities(doc.id, entity_type="technologies", names_only=True)
        # Returns: ["FastAPI", "Pydantic", "Uvicorn"]
    """
    # Normalize entity_type to string value
    if isinstance(entity_type, EntityType):
        entity_type = entity_type.value

    # Validate entity_type if provided
    if entity_type is not None and entity_type != "technologies":
        valid_types = [e.value for e in EntityType]
        if entity_type not in valid_types:
            raise ValueError(
                f"Invalid entity_type '{entity_type}'. "
                f"Must be one of {valid_types} or special value 'technologies'"
            )

    fetch_session = session if session is not None else get_session()
    close_session = session is None

    try:
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

        # Handle entity type filtering
        if entity_type == "technologies":
            # Special case: get all technology-related types (Technology + Product)
            stmt = stmt.where(Entity.entity_type.in_(TECHNOLOGY_TYPES))
        elif entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)

        if names_only:
            results = [name for name in fetch_session.exec(stmt).all() if name]
        else:
            results = [
                (name, etype) for name, etype in fetch_session.exec(stmt).all() if name and etype
            ]
        return results
    finally:
        if close_session:
            fetch_session.close()


def get_top_entities(limit: int = 100, session: Optional[Session] = None) -> list[dict]:
    """
    Get most commonly mentioned entities across all documents.

    Entities are ranked by source_mentions count (number of documents mentioning the entity).

    Args:
        limit: Maximum number of entities to return (default: 100)
        session: Optional SQLModel session (will create one if not provided)

    Returns:
        List of entity dictionaries, sorted by mention count descending:
            - id: str (entity UUID)
            - name: str (entity name)
            - type: str (entity type: Topic, Technology, Tool, Product, etc.)
            - description: str (entity description)
            - aliases: list[str] (alternative names)
            - canonical_name: str (canonical/preferred name)

    Example:
        top_entities = get_top_entities(limit=50)
        # Returns: [
        #   {"id": "...", "name": "Python", "type": "Topic", "description": "...", ...},
        #   {"id": "...", "name": "FastAPI", "type": "Technology", ...},
        #   ...
        # ]
    """
    fetch_session = session if session is not None else get_session()
    close_session = session is None

    try:
        stmt = (
            select(Entity)
            .where(Entity.source_mentions > 0)
            .order_by(Entity.source_mentions.desc())
            .limit(limit)
        )
        entities = fetch_session.exec(stmt).all()

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
    finally:
        if close_session:
            fetch_session.close()


def find_documents_with_entity(
    entity_name: str,
    entity_type: Optional[Union[EntityType, str]] = None,
    session: Optional[Session] = None,
) -> set[UUID]:
    """
    Find all document IDs that contain a specific entity.

    Searches both Entity.name and Entity.canonical_name (case-insensitive partial match).

    Args:
        entity_name: Entity name or partial match (case-insensitive)
        entity_type: Optional entity type filter. Can be:
            - An EntityType enum value (e.g., EntityType.TOPIC)
            - A valid EntityType string: "Topic", "Technology", "Product", "Feature", "Company", "Integration"
            - Special value "technologies" to get Technology+Product types
            - None to search all entity types
        session: Optional SQLModel session

    Returns:
        Set of document UUIDs that contain the entity

    Raises:
        ValueError: If entity_type is not a valid EntityType or special value

    Examples:
        # Find documents with a topic (using enum)
        doc_ids = find_documents_with_entity("Python", entity_type=EntityType.TOPIC)
        # Returns: {UUID('...'), UUID('...'), ...}

        # Find documents with a topic (using string)
        doc_ids = find_documents_with_entity("Python", entity_type="Topic")
        # Returns: {UUID('...'), UUID('...'), ...}

        # Find documents with a technology (any tech type)
        doc_ids = find_documents_with_entity("FastAPI", entity_type="technologies")
        # Returns: {UUID('...'), UUID('...'), ...}

        # Partial match works too
        doc_ids = find_documents_with_entity("web", entity_type=EntityType.TOPIC)
        # Matches "Web Development", "Web APIs", etc.

        # Search across all entity types
        doc_ids = find_documents_with_entity("Python")
        # Finds any entity (Topic, Technology, etc.) matching "Python"
    """
    # Normalize entity_type to string value
    if isinstance(entity_type, EntityType):
        entity_type = entity_type.value

    # Validate entity_type if provided
    if entity_type is not None and entity_type != "technologies":
        valid_types = [e.value for e in EntityType]
        if entity_type not in valid_types:
            raise ValueError(
                f"Invalid entity_type '{entity_type}'. "
                f"Must be one of {valid_types} or special value 'technologies'"
            )

    fetch_session = session if session is not None else get_session()
    close_session = session is None

    try:
        stmt = (
            select(DocumentEntity.document_id)
            .join(Entity, DocumentEntity.entity_id == Entity.id)
            .where(
                (Entity.name.ilike(f"%{entity_name}%"))
                | (Entity.canonical_name.ilike(f"%{entity_name}%"))
            )
        )

        # Handle entity type filtering
        if entity_type == "technologies":
            # Special case: search across all technology-related types (Technology + Product)
            stmt = stmt.where(Entity.entity_type.in_(TECHNOLOGY_TYPES))
        elif entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)

        doc_ids = {doc_id for doc_id in fetch_session.exec(stmt).all()}
        return doc_ids
    finally:
        if close_session:
            fetch_session.close()
