"""Utility functions for working with knowledge graph entities."""

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
    document_id: UUID, entity_type: Optional[str] = None, session: Optional[Session] = None
) -> list[tuple[str, str]]:
    """
    Get all entities for a document from the knowledge graph.

    Args:
        document_id: The document UUID
        entity_type: Optional entity type filter (e.g., "Topic", "Technology")
        session: Optional SQLModel session (will create one if not provided)

    Returns:
        List of tuples (canonical_name, entity_type)
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
