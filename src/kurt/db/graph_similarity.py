"""Knowledge graph utilities for querying entities linked to documents."""

import asyncio
import logging
from typing import TYPE_CHECKING, Optional
from uuid import UUID

import numpy as np
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.content.embeddings import embedding_to_bytes, generate_embeddings
from kurt.db.database import async_session_scope
from kurt.db.models import Entity, EntityType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Special entity type groupings
TECHNOLOGY_TYPES = [EntityType.TECHNOLOGY.value, EntityType.PRODUCT.value]


# ============================================================================
# Entity Search and Similarity
# ============================================================================


def cosine_similarity(emb1: list[float], emb2: list[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    a = np.array(emb1)
    b = np.array(emb2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def search_similar_entities(
    entity_name: str,
    entity_type: str,
    limit: int = 20,
    session: Optional[AsyncSession] = None,
) -> list[dict]:
    """Search for entities similar to the given name using vector search.

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
            similar = await search_similar_entities(
                "Python", "Technology", session=session
            )

        # Batch queries (each creates its own session)
        async def fetch_similar(name: str, entity_type: str):
            async with async_session_scope() as session:
                return await search_similar_entities(
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

        # Get event loop once for all async operations
        loop = asyncio.get_event_loop()

        if existing_entity:
            embedding_bytes = existing_entity.embedding
        else:
            # Generate new embedding (sync operation - run in executor)
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
