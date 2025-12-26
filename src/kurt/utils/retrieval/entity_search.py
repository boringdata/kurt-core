"""Entity vector search utilities."""

import logging
from uuid import UUID

import numpy as np

from kurt.db.database import get_session
from kurt.db.models import (
    Document,
    DocumentClusterEdge,
    DocumentEntity,
    Entity,
    TopicCluster,
)
from kurt.models.staging.clustering.step_topic_clustering import TopicClusteringRow
from kurt.utils.embeddings import bytes_to_embedding
from kurt.utils.retrieval.similarity import cosine_similarity

logger = logging.getLogger(__name__)


def search_entities_by_embedding(
    query_embedding: list[float],
    top_k: int = 5,
    min_similarity: float = 0.3,
) -> list[tuple]:
    """Search entities by embedding similarity.

    Args:
        query_embedding: Query embedding vector
        top_k: Maximum number of entities to return
        min_similarity: Minimum similarity threshold

    Returns:
        List of (entity, similarity) tuples sorted by similarity desc
    """
    session = get_session()
    query_vec = np.array(query_embedding, dtype=np.float32)

    # Load all entities with embeddings
    entities = session.query(Entity).filter(Entity.embedding != b"").all()

    if not entities:
        logger.warning("No entities with embeddings found")
        return []

    # Compute similarities
    similarities = []
    for entity in entities:
        try:
            entity_vec = np.array(bytes_to_embedding(entity.embedding), dtype=np.float32)
            sim = cosine_similarity(query_vec, entity_vec)
            if sim >= min_similarity:
                similarities.append((entity, sim))
        except Exception as e:
            logger.debug(f"Failed to compute similarity for {entity.name}: {e}")
            continue

    # Sort by similarity and take top_k
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]


def get_topics_for_entities(entity_ids: list) -> list[str]:
    """Get topic names for documents containing given entities.

    Args:
        entity_ids: List of entity IDs

    Returns:
        List of topic names
    """
    if not entity_ids:
        return []

    session = get_session()

    # Get document IDs from DocumentEntity
    doc_ids = (
        session.query(DocumentEntity.document_id)
        .filter(DocumentEntity.entity_id.in_(entity_ids))
        .distinct()
        .all()
    )
    doc_id_strs = [str(d.document_id) for d in doc_ids]

    # Get topics from staging table first
    topics = []
    if doc_id_strs:
        topic_rows = (
            session.query(TopicClusteringRow.cluster_name)
            .filter(TopicClusteringRow.document_id.in_(doc_id_strs))
            .filter(TopicClusteringRow.cluster_name.isnot(None))
            .distinct()
            .all()
        )
        topics = [t.cluster_name for t in topic_rows if t.cluster_name]

    # Fallback to TopicCluster table if no topics found
    if not topics:
        topic_rows = (
            session.query(TopicCluster.name)
            .distinct()
            .join(DocumentClusterEdge, TopicCluster.id == DocumentClusterEdge.cluster_id)
            .join(Document, DocumentClusterEdge.document_id == Document.id)
            .join(DocumentEntity, Document.id == DocumentEntity.document_id)
            .filter(DocumentEntity.entity_id.in_(entity_ids))
            .all()
        )
        topics = [t.name for t in topic_rows]

    return topics


def get_document_ids_for_entities(entity_ids: list) -> list[UUID]:
    """Get document IDs for documents containing given entities.

    Args:
        entity_ids: List of entity IDs

    Returns:
        List of document UUIDs
    """
    if not entity_ids:
        return []

    session = get_session()
    doc_rows = (
        session.query(DocumentEntity.document_id)
        .filter(DocumentEntity.entity_id.in_(entity_ids))
        .distinct()
        .all()
    )
    return [row.document_id for row in doc_rows]
