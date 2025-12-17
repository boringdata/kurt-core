"""Database operations for claim management, conflict detection, and resolution.

This module provides functions for:
- Creating and updating claims
- Detecting and managing claim conflicts
- Resolving claim entities
- Computing confidence scores
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import numpy as np
from sqlalchemy import and_
from sqlalchemy.orm import Session

from kurt.content.embeddings import generate_embeddings as get_embeddings
from kurt.db.claim_models import Claim, ClaimEntity, ClaimRelationship, ClaimType
from kurt.db.models import Document

logger = logging.getLogger(__name__)


def create_claim(
    session: Session,
    statement: str,
    claim_type: str,
    subject_entity_id: UUID,
    source_document_id: UUID,
    source_quote: str,
    source_location_start: int,
    source_location_end: int,
    extraction_confidence: float,
    source_context: Optional[str] = None,
    temporal_qualifier: Optional[str] = None,
    version_info: Optional[str] = None,
    git_commit: Optional[str] = None,
) -> Claim:
    """Create a new claim in the database.

    Args:
        session: Database session
        statement: The claim statement text
        claim_type: Type of claim (capability, limitation, etc.)
        subject_entity_id: Primary entity the claim is about
        source_document_id: Document where claim was found
        source_quote: Exact quote containing the claim
        source_location_start: Character offset start
        source_location_end: Character offset end
        extraction_confidence: LLM extraction confidence (0.0-1.0)
        source_context: Optional surrounding context
        temporal_qualifier: Optional time qualifier
        version_info: Optional version information
        git_commit: Optional git commit hash when extracted

    Returns:
        Created Claim object
    """
    # Generate embedding for the claim
    embedding_vector = get_embeddings([statement])[0]
    embedding_bytes = np.array(embedding_vector, dtype=np.float32).tobytes()

    # Calculate source authority based on document metadata
    source_authority = calculate_source_authority(session, source_document_id)

    # Calculate initial overall confidence
    overall_confidence = extraction_confidence * source_authority

    claim = Claim(
        statement=statement,
        claim_type=claim_type,
        subject_entity_id=subject_entity_id,
        source_document_id=source_document_id,
        source_quote=source_quote,
        source_location_start=source_location_start,
        source_location_end=source_location_end,
        source_context=source_context,
        temporal_qualifier=temporal_qualifier,
        version_info=version_info,
        extraction_confidence=extraction_confidence,
        source_authority=source_authority,
        overall_confidence=overall_confidence,
        embedding=embedding_bytes,
        indexed_with_git_commit=git_commit,
    )

    session.add(claim)
    return claim


def link_claim_to_entities(
    session: Session,
    claim_id: UUID,
    entity_ids: list[UUID],
    entity_roles: Optional[dict[UUID, str]] = None,
) -> list[ClaimEntity]:
    """Link a claim to additional entities it references.

    Args:
        session: Database session
        claim_id: The claim to link
        entity_ids: List of entity IDs to link
        entity_roles: Optional mapping of entity_id to role (subject, object, referenced, compared_to)

    Returns:
        List of created ClaimEntity links
    """
    entity_roles = entity_roles or {}
    links = []

    for entity_id in entity_ids:
        role = entity_roles.get(entity_id, "referenced")
        link = ClaimEntity(
            claim_id=claim_id,
            entity_id=entity_id,
            entity_role=role,
        )
        session.add(link)
        links.append(link)

    return links


def detect_duplicate_claims(
    session: Session,
    new_claim_statement: str,
    subject_entity_id: UUID,
    threshold: float = 0.85,
) -> list[Claim]:
    """Detect potential duplicate claims using semantic similarity.

    Args:
        session: Database session
        new_claim_statement: The new claim text to check
        subject_entity_id: Entity the claim is about
        threshold: Similarity threshold for duplicate detection (0.0-1.0)

    Returns:
        List of potentially duplicate existing claims
    """
    # Get existing claims about the same entity - use proper SQLAlchemy query
    existing_claims = (
        session.query(Claim).filter(Claim.subject_entity_id == subject_entity_id).all()
    )

    if not existing_claims:
        return []

    # Generate embedding for new claim
    new_embedding = get_embeddings([new_claim_statement])[0]
    new_embedding_np = np.array(new_embedding, dtype=np.float32)

    duplicates = []
    for claim in existing_claims:
        # Skip claims without embeddings
        # Use hasattr to check if embedding exists (for SQLModel compatibility)
        if not hasattr(claim, "embedding") or not claim.embedding:
            continue

        # Calculate cosine similarity
        existing_embedding_np = np.frombuffer(claim.embedding, dtype=np.float32)
        similarity = cosine_similarity(new_embedding_np, existing_embedding_np)

        if similarity >= threshold:
            duplicates.append(claim)
    return duplicates


def detect_conflicting_claims(
    session: Session,
    new_claim: dict,
    entity_id: UUID,
) -> list[tuple[Claim, str, float]]:
    """Detect claims that conflict with a new claim.

    Conflicts are detected based on:
    1. Semantic opposition (capabilities vs limitations)
    2. Version/temporal conflicts
    3. Mutually exclusive statements

    Args:
        session: Database session
        new_claim: Dictionary with claim details (statement, claim_type, temporal_qualifier, version_info)
        entity_id: Entity the claims are about

    Returns:
        List of tuples: (conflicting_claim, conflict_type, confidence)
    """
    conflicts = []

    # Get existing claims about the same entity
    existing_claims = session.query(Claim).filter(Claim.subject_entity_id == entity_id).all()

    for existing in existing_claims:
        conflict_type, confidence = analyze_conflict(new_claim, existing)
        if conflict_type:
            conflicts.append((existing, conflict_type, confidence))

    return conflicts


def analyze_conflict(new_claim: dict, existing_claim: Claim) -> tuple[Optional[str], float]:
    """Analyze if two claims conflict and determine the type of conflict.

    Args:
        new_claim: New claim dictionary
        existing_claim: Existing claim from database

    Returns:
        Tuple of (conflict_type, confidence) or (None, 0.0) if no conflict
    """
    # Check for capability vs limitation conflicts
    if (
        new_claim["claim_type"] == ClaimType.CAPABILITY
        and existing_claim.claim_type == ClaimType.LIMITATION
    ) or (
        new_claim["claim_type"] == ClaimType.LIMITATION
        and existing_claim.claim_type == ClaimType.CAPABILITY
    ):
        # Check if they're about the same feature/aspect
        # If no embedding or empty embedding, skip semantic similarity check
        if (
            not hasattr(existing_claim, "embedding")
            or not existing_claim.embedding
            or len(existing_claim.embedding) == 0
        ):
            # Fall back to simple string comparison
            # If statements are similar enough, consider them conflicting
            new_stmt_lower = new_claim["statement"].lower()
            existing_stmt_lower = existing_claim.statement.lower()

            # Simple heuristic: check if they mention same key terms
            # Extract key terms (simple approach - split and compare)
            new_words = set(new_stmt_lower.split())
            existing_words = set(existing_stmt_lower.split())
            overlap = len(new_words & existing_words)

            if overlap >= 3:  # If 3 or more words overlap, consider conflicting
                return "contradictory", 0.75
            return None, 0.0

        new_embedding = get_embeddings([new_claim["statement"]])[0]
        existing_embedding_np = np.frombuffer(existing_claim.embedding, dtype=np.float32)
        similarity = cosine_similarity(
            np.array(new_embedding, dtype=np.float32), existing_embedding_np
        )

        if similarity > 0.7:  # High semantic similarity but opposite types
            return "contradictory", similarity

    # Check for version conflicts
    if new_claim.get("version_info") and existing_claim.version_info:
        if new_claim["version_info"] != existing_claim.version_info:
            # Different versions might have different capabilities
            return "version_difference", 0.8

    # Check for temporal conflicts
    if new_claim.get("temporal_qualifier") and existing_claim.temporal_qualifier:
        # Simple check - could be enhanced with date parsing
        if (
            "deprecated" in new_claim["temporal_qualifier"].lower()
            and "current" in existing_claim.temporal_qualifier.lower()
        ):
            return "temporal_conflict", 0.9
        elif (
            "current" in new_claim["temporal_qualifier"].lower()
            and "deprecated" in existing_claim.temporal_qualifier.lower()
        ):
            return "temporal_conflict", 0.9

    return None, 0.0


def create_claim_conflict(
    session: Session,
    claim1_id: UUID,
    claim2_id: UUID,
    conflict_type: str,
    confidence: float,
) -> ClaimRelationship:
    """Create a conflict relationship between two claims.

    Args:
        session: Database session
        claim1_id: First claim ID
        claim2_id: Second claim ID
        conflict_type: Type of conflict
        confidence: Confidence in the conflict (0.0-1.0)

    Returns:
        Created ClaimRelationship
    """
    relationship = ClaimRelationship(
        source_claim_id=claim1_id,
        target_claim_id=claim2_id,
        relationship_type="in_conflict",
        resolution_status="pending",
        confidence=confidence,
    )
    session.add(relationship)
    return relationship


def update_claim_confidence(
    session: Session,
    claim_id: UUID,
    corroboration_count: Optional[int] = None,
) -> None:
    """Update the overall confidence score of a claim based on corroboration.

    Args:
        session: Database session
        claim_id: Claim to update
        corroboration_count: Number of supporting claims
    """
    claim = session.get(Claim, claim_id)
    if not claim:
        return

    # Calculate corroboration score
    if corroboration_count is not None:
        # Logarithmic scale for corroboration (diminishing returns)
        claim.corroboration_score = min(1.0, np.log1p(corroboration_count) / 3.0)

    # Recalculate overall confidence
    # Weighted average: extraction (40%), source (30%), corroboration (30%)
    claim.overall_confidence = (
        claim.extraction_confidence * 0.4
        + claim.source_authority * 0.3
        + claim.corroboration_score * 0.3
    )

    session.add(claim)


def calculate_source_authority(session: Session, document_id: UUID) -> float:
    """Calculate the authority score of a document source.

    Args:
        session: Database session
        document_id: Document ID

    Returns:
        Authority score (0.0-1.0)
    """
    document = session.get(Document, document_id)
    if not document:
        return 0.5  # Default middle authority

    score = 0.5  # Base score

    # Boost for reference documentation
    if document.content_type == "reference":
        score += 0.2
    elif document.content_type == "tutorial" or document.content_type == "guide":
        score += 0.1

    # Boost for official sources (simple heuristic based on URL)
    if document.source_url:
        url_lower = document.source_url.lower()
        if "docs." in url_lower or "documentation." in url_lower:
            score += 0.1
        if "official" in url_lower or "api." in url_lower:
            score += 0.1

    # Penalty for old content (if published_date available)
    if document.published_date:
        age_days = (datetime.utcnow() - document.published_date).days
        if age_days > 365:  # More than a year old
            score -= 0.1
        if age_days > 730:  # More than 2 years old
            score -= 0.1

    return max(0.0, min(1.0, score))  # Clamp to [0.0, 1.0]


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

    return dot_product / (norm1 * norm2)


def find_supporting_claims(
    session: Session,
    claim: Claim,
    threshold: float = 0.75,
) -> list[Claim]:
    """Find claims that support or corroborate a given claim.

    Args:
        session: Database session
        claim: The claim to find support for
        threshold: Similarity threshold for support detection

    Returns:
        List of supporting claims
    """
    # Get claims about the same entity - use proper SQLAlchemy query
    related_claims = (
        session.query(Claim)
        .filter(
            and_(
                Claim.subject_entity_id == claim.subject_entity_id,
                Claim.id != claim.id,
                Claim.claim_type == claim.claim_type,  # Same type likely supports
            )
        )
        .all()
    )

    if not related_claims:
        return []

    claim_embedding_np = np.frombuffer(claim.embedding, dtype=np.float32)
    supporting = []

    for related in related_claims:
        related_embedding_np = np.frombuffer(related.embedding, dtype=np.float32)
        similarity = cosine_similarity(claim_embedding_np, related_embedding_np)

        if similarity >= threshold:
            supporting.append(related)

    return supporting


def resolve_claim_conflict(
    session: Session,
    relationship_id: UUID,
    resolution_status: str,
    resolved_by: str,
    resolution_notes: Optional[str] = None,
) -> None:
    """Mark a claim conflict as resolved.

    Args:
        session: Database session
        relationship_id: ClaimRelationship ID for the conflict
        resolution_status: New status (resolved, ignored)
        resolved_by: Username of resolver
        resolution_notes: Optional notes about resolution
    """
    relationship = session.get(ClaimRelationship, relationship_id)
    if not relationship:
        return

    relationship.resolution_status = resolution_status
    relationship.resolved_by_user = resolved_by
    relationship.resolution_notes = resolution_notes
    relationship.resolved_at = datetime.utcnow()

    session.add(relationship)
