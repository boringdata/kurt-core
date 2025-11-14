"""Helper utilities for document indexing.

This module contains shared utility functions used across the indexing pipeline:
- Embedding generation and manipulation
- Database queries for entities
- Document resolution and content loading
"""

import logging
import struct
from uuid import UUID

import dspy
import numpy as np
from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, Entity

logger = logging.getLogger(__name__)


# ============================================================================
# Embedding Utilities
# ============================================================================


def _get_embedding_model() -> str:
    """Get configured embedding model from Kurt config."""
    from kurt.config import load_config

    config = load_config()
    return config.EMBEDDING_MODEL


def _generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using configured model."""
    embedding_model = _get_embedding_model()
    embedder = dspy.Embedder(model=embedding_model)
    return embedder(texts)


def _embedding_to_bytes(embedding: list[float]) -> bytes:
    """Convert embedding list to bytes for storage."""
    return np.array(embedding, dtype=np.float32).tobytes()


def _bytes_to_embedding(embedding_bytes: bytes) -> list[float]:
    """Convert stored bytes back to embedding list."""
    return struct.unpack(f"{len(embedding_bytes)//4}f", embedding_bytes)


def _cosine_similarity(emb1: list[float], emb2: list[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    a = np.array(emb1)
    b = np.array(emb2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ============================================================================
# Entity Database Queries
# ============================================================================


def _get_top_entities(session, limit: int = 100) -> list[dict]:
    """Get most commonly mentioned entities for context.

    Args:
        session: Database session
        limit: Maximum number of entities to return

    Returns:
        List of entity dicts with id, name, type, description, aliases, canonical_name
    """
    stmt = (
        select(Entity)
        .where(Entity.source_mentions > 0)
        .order_by(Entity.source_mentions.desc())
        .limit(limit)
    )
    entities = session.exec(stmt).all()

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


def _search_similar_entities(
    session, entity_name: str, entity_type: str, limit: int = 20
) -> list[dict]:
    """Search for entities similar to the given name using vector search.

    Args:
        session: Database session
        entity_name: Name of entity to find similar entities for
        entity_type: Entity type filter (only return same type)
        limit: Maximum number of results

    Returns:
        List of similar entity dicts with similarity scores
    """
    try:
        # Generate embedding for search
        embedding_vector = _generate_embeddings([entity_name])[0]
        embedding_bytes = _embedding_to_bytes(embedding_vector)

        # Use SQLite client's vector search if available
        from kurt.db.sqlite import SQLiteClient

        client = SQLiteClient()
        results = client.search_similar_entities(embedding_bytes, limit=limit, min_similarity=0.70)

        # Load entity details
        similar_entities = []
        for entity_id, similarity in results:
            entity = session.get(Entity, UUID(entity_id))
            if entity and entity.entity_type == entity_type:  # Same type only
                similar_entities.append(
                    {
                        "id": str(entity.id),
                        "name": entity.name,
                        "type": entity.entity_type,
                        "description": entity.description or "",
                        "aliases": entity.aliases or [],
                        "canonical_name": entity.canonical_name or entity.name,
                        "similarity": similarity,
                    }
                )

        return similar_entities
    except Exception as e:
        logger.debug(f"Vector search not available (fallback to simple query): {e}")
        # Fallback: get top entities of same type
        stmt = (
            select(Entity)
            .where(Entity.entity_type == entity_type)
            .order_by(Entity.source_mentions.desc())
            .limit(limit)
        )
        entities = session.exec(stmt).all()
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


# ============================================================================
# Document Resolution and Content Loading
# ============================================================================


def _resolve_document_id(document_id: str) -> Document:
    """Resolve document ID (full or partial UUID) to Document object.

    Args:
        document_id: Full or partial document UUID

    Returns:
        Document object

    Raises:
        ValueError: If document not found or ID is ambiguous
    """
    session = get_session()

    try:
        doc_uuid = UUID(document_id)
        doc = session.get(Document, doc_uuid)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
        return doc
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

        return matches[0]


def _load_document_content(doc: Document) -> str:
    """Load document content from filesystem.

    Args:
        doc: Document object with content_path

    Returns:
        Document content as string

    Raises:
        ValueError: If content_path is missing or file doesn't exist
    """
    if not doc.content_path:
        raise ValueError(f"Document {doc.id} has no content_path")

    from kurt.config import load_config

    config = load_config()
    source_base = config.get_absolute_sources_path()
    content_file = source_base / doc.content_path

    if not content_file.exists():
        raise ValueError(f"Content file not found: {content_file}")

    content = content_file.read_text(encoding="utf-8")

    if not content.strip():
        raise ValueError(f"Document {doc.id} has empty content")

    return content
