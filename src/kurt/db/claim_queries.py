"""Query functions for claim retrieval and analysis.

This module provides read-only query operations for claims,
including search, filtering, and relationship traversal.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import numpy as np
from sqlalchemy import and_, or_
from sqlmodel import Session, select

from kurt.db.claim_models import Claim, ClaimEntity, ClaimRelationship
from kurt.db.models import Document, Entity
from kurt.utils.embeddings import generate_embeddings as get_embeddings

logger = logging.getLogger(__name__)


def get_claims_for_entity(
    entity_id: UUID,
    session: Session,
    claim_type: Optional[str] = None,
    min_confidence: float = 0.0,
    include_superseded: bool = False,
) -> list[Claim]:
    """Get all claims about a specific entity.

    Args:
        entity_id: Entity UUID
        session: Database session
        claim_type: Optional filter by claim type
        min_confidence: Minimum overall confidence threshold
        include_superseded: Whether to include superseded claims

    Returns:
        List of claims about the entity
    """
    query = select(Claim).where(
        or_(
            Claim.subject_entity_id == entity_id,
            Claim.id.in_(select(ClaimEntity.claim_id).where(ClaimEntity.entity_id == entity_id)),
        )
    )

    if claim_type:
        query = query.where(Claim.claim_type == claim_type)

    if min_confidence > 0:
        query = query.where(Claim.overall_confidence >= min_confidence)

    if not include_superseded:
        query = query.where(Claim.is_superseded is False)

    return list(session.exec(query).all())


def get_claims_for_document(
    document_id: UUID,
    session: Session,
    claim_type: Optional[str] = None,
) -> list[Claim]:
    """Get all claims extracted from a specific document.

    Args:
        document_id: Document UUID
        session: Database session
        claim_type: Optional filter by claim type

    Returns:
        List of claims from the document
    """
    query = select(Claim).where(Claim.source_document_id == document_id)

    if claim_type:
        query = query.where(Claim.claim_type == claim_type)

    query = query.order_by(Claim.source_location_start)

    return list(session.exec(query).all())


def get_conflicting_claims(
    claim_id: UUID,
    session: Session,
    include_resolved: bool = False,
) -> list[tuple[Claim, ClaimRelationship]]:
    """Get claims that conflict with a given claim.

    Args:
        claim_id: Claim UUID
        session: Database session
        include_resolved: Whether to include resolved conflicts

    Returns:
        List of tuples: (conflicting_claim, relationship)
    """
    query = (
        select(Claim, ClaimRelationship)
        .join(
            ClaimRelationship,
            or_(
                and_(
                    ClaimRelationship.source_claim_id == claim_id,
                    ClaimRelationship.target_claim_id == Claim.id,
                ),
                and_(
                    ClaimRelationship.target_claim_id == claim_id,
                    ClaimRelationship.source_claim_id == Claim.id,
                ),
            ),
        )
        .where(ClaimRelationship.relationship_type == "in_conflict")
    )

    if not include_resolved:
        query = query.where(
            or_(
                ClaimRelationship.resolution_status is None,
                ClaimRelationship.resolution_status == "pending",
            )
        )

    return list(session.exec(query).all())


def search_claims_by_text(
    query_text: str,
    session: Session,
    limit: int = 20,
    min_confidence: float = 0.0,
) -> list[tuple[Claim, float]]:
    """Search for claims using semantic similarity.

    Args:
        query_text: Text to search for
        session: Database session
        limit: Maximum number of results
        min_confidence: Minimum confidence threshold

    Returns:
        List of tuples: (claim, similarity_score)
    """
    # Generate embedding for query
    query_embedding = get_embeddings([query_text])[0]
    query_embedding_np = np.array(query_embedding, dtype=np.float32)

    # Get all claims (with confidence filter)
    query = select(Claim)
    if min_confidence > 0:
        query = query.where(Claim.overall_confidence >= min_confidence)

    claims = session.exec(query).all()

    # Calculate similarities
    results = []
    for claim in claims:
        if claim.embedding:
            claim_embedding_np = np.frombuffer(claim.embedding, dtype=np.float32)
            similarity = cosine_similarity(query_embedding_np, claim_embedding_np)
            results.append((claim, similarity))

    # Sort by similarity and return top N
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


def get_claim_with_context(
    claim_id: UUID,
    session: Session,
) -> dict:
    """Get a claim with full context including entities and source.

    Args:
        claim_id: Claim UUID
        session: Database session

    Returns:
        Dictionary with claim details and context
    """
    claim = session.get(Claim, claim_id)
    if not claim:
        return None

    # Get subject entity
    subject_entity = session.get(Entity, claim.subject_entity_id)

    # Get additional entities
    additional_entities_query = (
        select(Entity, ClaimEntity.entity_role)
        .join(ClaimEntity, ClaimEntity.entity_id == Entity.id)
        .where(ClaimEntity.claim_id == claim_id)
    )
    additional_entities = session.exec(additional_entities_query).all()

    # Get source document
    source_document = session.get(Document, claim.source_document_id)

    # Get conflicts
    conflicts = get_conflicting_claims(claim_id, session, include_resolved=False)

    # Get supporting claims (high similarity, same type)
    supporting = find_similar_claims(claim, session, threshold=0.8, limit=5)

    return {
        "claim": claim,
        "subject_entity": subject_entity,
        "additional_entities": [{"entity": e, "role": role} for e, role in additional_entities],
        "source_document": source_document,
        "conflicts": [{"claim": c, "relationship": r} for c, r in conflicts],
        "supporting_claims": supporting,
    }


def find_similar_claims(
    claim: Claim,
    session: Session,
    threshold: float = 0.75,
    limit: int = 10,
    same_type_only: bool = True,
) -> list[tuple[Claim, float]]:
    """Find claims similar to a given claim.

    Args:
        claim: The reference claim
        session: Database session
        threshold: Minimum similarity threshold
        limit: Maximum number of results
        same_type_only: Whether to only return claims of the same type

    Returns:
        List of tuples: (similar_claim, similarity_score)
    """
    if not claim.embedding:
        return []

    claim_embedding_np = np.frombuffer(claim.embedding, dtype=np.float32)

    # Build query
    query = select(Claim).where(Claim.id != claim.id)

    if same_type_only:
        query = query.where(Claim.claim_type == claim.claim_type)

    # Filter by same entity for efficiency
    query = query.where(
        or_(
            Claim.subject_entity_id == claim.subject_entity_id,
            Claim.id.in_(
                select(ClaimEntity.claim_id).where(ClaimEntity.entity_id == claim.subject_entity_id)
            ),
        )
    )

    candidates = session.exec(query).all()

    # Calculate similarities
    results = []
    for candidate in candidates:
        if candidate.embedding:
            candidate_embedding_np = np.frombuffer(candidate.embedding, dtype=np.float32)
            similarity = cosine_similarity(claim_embedding_np, candidate_embedding_np)
            if similarity >= threshold:
                results.append((candidate, similarity))

    # Sort by similarity and return top N
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:limit]


def get_claims_by_type(
    claim_type: str,
    session: Session,
    entity_id: Optional[UUID] = None,
    min_confidence: float = 0.0,
) -> list[Claim]:
    """Get all claims of a specific type.

    Args:
        claim_type: Type of claims to retrieve
        session: Database session
        entity_id: Optional filter by entity
        min_confidence: Minimum confidence threshold

    Returns:
        List of claims
    """
    query = select(Claim).where(Claim.claim_type == claim_type)

    if entity_id:
        query = query.where(
            or_(
                Claim.subject_entity_id == entity_id,
                Claim.id.in_(
                    select(ClaimEntity.claim_id).where(ClaimEntity.entity_id == entity_id)
                ),
            )
        )

    if min_confidence > 0:
        query = query.where(Claim.overall_confidence >= min_confidence)

    query = query.order_by(Claim.overall_confidence.desc())

    return list(session.exec(query).all())


def get_unresolved_conflicts(
    session: Session,
    entity_id: Optional[UUID] = None,
) -> list[dict]:
    """Get all unresolved claim conflicts.

    Args:
        session: Database session
        entity_id: Optional filter by entity

    Returns:
        List of conflict dictionaries with both claims
    """
    query = (
        select(
            ClaimRelationship,
            Claim.label("claim1"),
            Claim.label("claim2"),
        )
        .select_from(ClaimRelationship)
        .join(
            Claim,
            ClaimRelationship.source_claim_id == Claim.id,
            isouter=True,
        )
        .join(
            Claim,
            ClaimRelationship.target_claim_id == Claim.id,
            isouter=True,
        )
        .where(
            and_(
                ClaimRelationship.relationship_type == "in_conflict",
                or_(
                    ClaimRelationship.resolution_status is None,
                    ClaimRelationship.resolution_status == "pending",
                ),
            )
        )
    )

    if entity_id:
        # Filter by entity involvement
        query = query.where(
            or_(
                Claim.subject_entity_id == entity_id,
                Claim.id.in_(
                    select(ClaimEntity.claim_id).where(ClaimEntity.entity_id == entity_id)
                ),
            )
        )

    results = session.exec(query).all()

    conflicts = []
    for relationship, claim1, claim2 in results:
        conflicts.append(
            {
                "relationship": relationship,
                "claim1": claim1,
                "claim2": claim2,
            }
        )

    return conflicts


def get_claims_timeline(
    entity_id: UUID,
    session: Session,
) -> list[dict]:
    """Get claims about an entity organized by temporal information.

    Args:
        entity_id: Entity UUID
        session: Database session

    Returns:
        List of claims with temporal information, sorted chronologically
    """
    claims = get_claims_for_entity(entity_id, session, include_superseded=True)

    # Group by temporal qualifier and version
    timeline = []
    for claim in claims:
        timeline.append(
            {
                "claim": claim,
                "temporal_qualifier": claim.temporal_qualifier,
                "version_info": claim.version_info,
                "extracted_date": claim.extracted_date,
                "is_current": not claim.is_superseded,
            }
        )

    # Sort by version/date if available
    timeline.sort(
        key=lambda x: (
            x["version_info"] or "",
            x["temporal_qualifier"] or "",
            x["extracted_date"] or datetime.min,
        )
    )

    return timeline


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity (0.0-1.0)
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))
