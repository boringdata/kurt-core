"""Knowledge graph utilities for querying entities linked to documents.

This module provides utilities to retrieve entities from the knowledge graph:
- Per-document queries: Get entities for a specific document
- Cross-document queries: Get top entities across all documents

All functions accept an optional session parameter for transaction management and testing.
"""

from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from kurt.db.database import get_session
from kurt.db.models import DocumentEntity, Entity


def get_document_topics(document_id: UUID, session: Optional[Session] = None) -> list[str]:
    """
    Get all topics for a document from the knowledge graph.

    Args:
        document_id: The document UUID
        session: Optional SQLModel session (will create one if not provided)

    Returns:
        List of topic canonical names

    Example:
        topics = get_document_topics(doc.id)
        # Returns: ["Python", "Web Development", "API Design"]
    """
    fetch_session = session if session is not None else get_session()
    close_session = session is None

    try:
        stmt = (
            select(Entity.canonical_name)
            .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
            .where(DocumentEntity.document_id == document_id)
            .where(Entity.entity_type == "Topic")
        )
        topics = [name for name in fetch_session.exec(stmt).all() if name]
        return topics
    finally:
        if close_session:
            fetch_session.close()


def get_document_technologies(document_id: UUID, session: Optional[Session] = None) -> list[str]:
    """
    Get all technologies/tools for a document from the knowledge graph.

    Args:
        document_id: The document UUID
        session: Optional SQLModel session (will create one if not provided)

    Returns:
        List of technology/tool canonical names (includes Technology, Tool, and Product entity types)

    Example:
        tools = get_document_technologies(doc.id)
        # Returns: ["FastAPI", "Pydantic", "Uvicorn"]
    """
    fetch_session = session if session is not None else get_session()
    close_session = session is None

    try:
        stmt = (
            select(Entity.canonical_name)
            .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
            .where(DocumentEntity.document_id == document_id)
            .where(Entity.entity_type.in_(["Technology", "Tool", "Product"]))
        )
        technologies = [name for name in fetch_session.exec(stmt).all() if name]
        return technologies
    finally:
        if close_session:
            fetch_session.close()


def get_document_entities(
    document_id: UUID,
    entity_type: Optional[str] = None,
    session: Optional[Session] = None,
) -> list[tuple[str, str]]:
    """
    Get all entities for a document from the knowledge graph.

    Args:
        document_id: The document UUID
        entity_type: Optional entity type filter (e.g., "Topic", "Technology")
        session: Optional SQLModel session (will create one if not provided)

    Returns:
        List of tuples (canonical_name, entity_type)

    Example:
        entities = get_document_entities(doc.id)
        # Returns: [("Python", "Topic"), ("FastAPI", "Technology"), ...]

        topics_only = get_document_entities(doc.id, entity_type="Topic")
        # Returns: [("Python", "Topic"), ("Web Development", "Topic")]
    """
    fetch_session = session if session is not None else get_session()
    close_session = session is None

    try:
        stmt = (
            select(Entity.canonical_name, Entity.entity_type)
            .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
            .where(DocumentEntity.document_id == document_id)
        )

        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)

        entities = [
            (name, etype) for name, etype in fetch_session.exec(stmt).all() if name and etype
        ]
        return entities
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


def find_documents_with_topic(topic: str, session: Optional[Session] = None) -> set[UUID]:
    """
    Find all document IDs that contain a specific topic.

    Searches both Entity.name and Entity.canonical_name (case-insensitive partial match).

    Args:
        topic: Topic name or partial match (case-insensitive)
        session: Optional SQLModel session

    Returns:
        Set of document UUIDs that contain the topic

    Example:
        doc_ids = find_documents_with_topic("Python")
        # Returns: {UUID('...'), UUID('...'), ...}

        # Partial match works too
        doc_ids = find_documents_with_topic("web")
        # Matches "Web Development", "Web APIs", etc.
    """
    fetch_session = session if session is not None else get_session()
    close_session = session is None

    try:
        stmt = (
            select(DocumentEntity.document_id)
            .join(Entity, DocumentEntity.entity_id == Entity.id)
            .where(Entity.entity_type == "Topic")
            .where((Entity.name.ilike(f"%{topic}%")) | (Entity.canonical_name.ilike(f"%{topic}%")))
        )
        doc_ids = {doc_id for doc_id in fetch_session.exec(stmt).all()}
        return doc_ids
    finally:
        if close_session:
            fetch_session.close()


def find_documents_with_technology(technology: str, session: Optional[Session] = None) -> set[UUID]:
    """
    Find all document IDs that contain a specific technology/tool.

    Searches both Entity.name and Entity.canonical_name (case-insensitive partial match).

    Args:
        technology: Technology/tool name or partial match (case-insensitive)
        session: Optional SQLModel session

    Returns:
        Set of document UUIDs that contain the technology

    Example:
        doc_ids = find_documents_with_technology("FastAPI")
        # Returns: {UUID('...'), UUID('...'), ...}

        # Partial match works too
        doc_ids = find_documents_with_technology("react")
        # Matches "React", "React Native", etc.
    """
    fetch_session = session if session is not None else get_session()
    close_session = session is None

    try:
        stmt = (
            select(DocumentEntity.document_id)
            .join(Entity, DocumentEntity.entity_id == Entity.id)
            .where(Entity.entity_type.in_(["Technology", "Tool", "Product"]))
            .where(
                (Entity.name.ilike(f"%{technology}%"))
                | (Entity.canonical_name.ilike(f"%{technology}%"))
            )
        )
        doc_ids = {doc_id for doc_id in fetch_session.exec(stmt).all()}
        return doc_ids
    finally:
        if close_session:
            fetch_session.close()
