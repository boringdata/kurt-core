"""Enhanced answer generation using claims and knowledge graph context.

This module extends the basic answer functionality by incorporating
claims as a primary source of factual information.
"""

import logging

import dspy
from pydantic import BaseModel, Field

from kurt.content.answer import generate_answer
from kurt.db.claim_queries import (
    get_claim_with_context,
    get_claims_for_entity,
    search_claims_by_text,
)
from kurt.db.database import get_session
from kurt.db.models import Document, Entity

logger = logging.getLogger(__name__)


class ClaimContext(BaseModel):
    """Context retrieved from claims for answering questions."""

    claims: list[dict] = Field(default_factory=list)
    conflicting_claims: list[dict] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
    source_documents: list[dict] = Field(default_factory=list)


class AnswerWithClaims(dspy.Signature):
    """Generate answer using claims and knowledge graph context.

    Claims provide specific, factual statements that can directly answer questions.
    When conflicts exist, present both perspectives and note the conflict.
    """

    question: str = dspy.InputField(desc="User's question")
    claims: list[dict] = dspy.InputField(desc="Relevant claims with confidence scores and sources")
    conflicting_claims: list[dict] = dspy.InputField(
        desc="Claims that conflict with the main claims"
    )
    entities: list[dict] = dspy.InputField(desc="Related entities from knowledge graph")
    documents: list[dict] = dspy.InputField(desc="Source documents for additional context")

    answer: str = dspy.OutputField(desc="Comprehensive answer based on claims and context")
    confidence: float = dspy.OutputField(desc="Confidence in the answer (0.0-1.0)")
    sources: list[str] = dspy.OutputField(desc="List of source references used")


def retrieve_claim_context(
    question: str,
    max_claims: int = 20,
    min_confidence: float = 0.3,
) -> ClaimContext:
    """Retrieve relevant claims and context for answering a question.

    Strategy:
    1. Search for claims using semantic similarity
    2. Get entities mentioned in relevant claims
    3. Find additional claims about those entities
    4. Detect and include conflicting claims
    5. Gather source documents

    Args:
        question: User's question
        max_claims: Maximum number of claims to retrieve
        min_confidence: Minimum confidence threshold for claims

    Returns:
        ClaimContext with claims, conflicts, entities, and sources
    """
    session = get_session()
    context = ClaimContext()

    try:
        # Step 1: Find claims directly relevant to the question
        relevant_claims = search_claims_by_text(
            question, session, limit=max_claims, min_confidence=min_confidence
        )

        # Process claims and gather entity IDs
        entity_ids = set()
        claim_dicts = []

        for claim, similarity in relevant_claims:
            # Get full claim context
            claim_context = get_claim_with_context(claim.id, session)
            if not claim_context:
                continue

            claim_dict = {
                "id": str(claim.id),
                "statement": claim.statement,
                "claim_type": claim.claim_type,
                "confidence": claim.overall_confidence,
                "similarity": similarity,
                "source_quote": claim.source_quote,
                "temporal_qualifier": claim.temporal_qualifier,
                "version_info": claim.version_info,
                "subject_entity": claim_context["subject_entity"].name
                if claim_context["subject_entity"]
                else None,
            }

            claim_dicts.append(claim_dict)
            entity_ids.add(claim.subject_entity_id)

            # Track conflicts
            for conflict in claim_context.get("conflicts", []):
                conflict_dict = {
                    "claim1": claim.statement,
                    "claim2": conflict["claim"].statement,
                    "conflict_type": conflict["relationship"].relationship_type,
                    "resolution_status": conflict["relationship"].resolution_status,
                }
                if conflict_dict not in context.conflicting_claims:
                    context.conflicting_claims.append(conflict_dict)

            # Add additional entities
            for entity_ref in claim_context.get("additional_entities", []):
                entity_ids.add(entity_ref["entity"].id)

        context.claims = claim_dicts

        # Step 2: Get entity information
        for entity_id in entity_ids:
            entity = session.get(Entity, entity_id)
            if entity:
                entity_dict = {
                    "id": str(entity.id),
                    "name": entity.name,
                    "type": entity.entity_type,
                    "description": entity.description,
                    "canonical_name": entity.canonical_name,
                }
                context.entities.append(entity_dict)

                # Get additional high-confidence claims about this entity
                entity_claims = get_claims_for_entity(
                    entity_id,
                    session,
                    min_confidence=min_confidence + 0.2,  # Higher threshold
                    include_superseded=False,
                )

                for claim in entity_claims[:5]:  # Limit per entity
                    claim_dict = {
                        "id": str(claim.id),
                        "statement": claim.statement,
                        "claim_type": claim.claim_type,
                        "confidence": claim.overall_confidence,
                        "similarity": 0.0,  # Not from similarity search
                        "source_quote": claim.source_quote,
                        "temporal_qualifier": claim.temporal_qualifier,
                        "version_info": claim.version_info,
                        "subject_entity": entity.name,
                    }
                    if claim_dict not in context.claims:
                        context.claims.append(claim_dict)

        # Step 3: Get source documents
        from kurt.db.claim_models import Claim

        document_ids = set()
        for claim_dict in context.claims:
            # Get the actual claim to find its source document
            claim_id = claim_dict["id"]
            claim = session.query(Claim).filter(Claim.id == claim_id).first()
            if claim:
                document_ids.add(claim.source_document_id)

        for doc_id in document_ids:
            doc = session.get(Document, doc_id)
            if doc:
                doc_dict = {
                    "id": str(doc.id),
                    "title": doc.title,
                    "url": doc.source_url,
                    "content_type": doc.content_type.value if doc.content_type else None,
                }
                context.source_documents.append(doc_dict)

        return context

    finally:
        session.close()


def answer_with_claims(
    question: str,
    max_claims: int = 20,
    min_confidence: float = 0.3,
    use_standard_context: bool = True,
) -> dict:
    """Generate an answer using claims and optionally standard KG context.

    Args:
        question: User's question
        max_claims: Maximum claims to retrieve
        min_confidence: Minimum claim confidence
        use_standard_context: Whether to also use standard KG retrieval

    Returns:
        Dictionary with answer, confidence, sources, and metadata
    """
    # Retrieve claim-based context
    claim_context = retrieve_claim_context(question, max_claims, min_confidence)

    # Optionally retrieve standard context
    standard_context = None
    if use_standard_context:
        from kurt.content.answer import retrieve_context

        standard_context = retrieve_context(question)

    # Prepare context for LLM
    claims = claim_context.claims
    conflicts = claim_context.conflicting_claims
    entities = claim_context.entities

    # Merge with standard context if available
    documents = claim_context.source_documents
    if standard_context:
        # Add documents from standard retrieval
        for doc in standard_context.documents:
            doc_dict = {
                "id": str(doc.id),
                "title": doc.title,
                "url": doc.url,
                "content_type": doc.content_type,
                "relevance_score": doc.relevance_score,
            }
            if doc_dict not in documents:
                documents.append(doc_dict)

        # Add entities from standard retrieval
        for entity in standard_context.entities:
            entity_dict = {
                "id": str(entity.id),
                "name": entity.name,
                "type": entity.type,
                "description": entity.description,
                "relevance_score": entity.relevance_score,
            }
            if not any(e["id"] == entity_dict["id"] for e in entities):
                entities.append(entity_dict)

    # Generate answer using DSPy
    answer_generator = dspy.ChainOfThought(AnswerWithClaims)

    try:
        result = answer_generator(
            question=question,
            claims=claims,
            conflicting_claims=conflicts,
            entities=entities,
            documents=documents,
        )

        # Build response
        response = {
            "answer": result.answer,
            "confidence": result.confidence,
            "sources": result.sources,
            "metadata": {
                "claims_used": len(claims),
                "conflicts_found": len(conflicts),
                "entities_referenced": len(entities),
                "documents_referenced": len(documents),
            },
            "claims": claims[:10],  # Include top claims in response
            "conflicts": conflicts,
        }

        # Add warning if conflicts exist
        if conflicts:
            response["warning"] = (
                f"Found {len(conflicts)} conflicting claims. "
                "Answer presents multiple perspectives where conflicts exist."
            )

        return response

    except Exception as e:
        logger.error(f"Error generating answer with claims: {e}")
        # Fallback to standard answer if available
        if use_standard_context:
            logger.info("Falling back to standard answer generation")
            return generate_answer(question)
        raise


def explain_claim_conflicts(entity_name: str) -> dict:
    """Explain all conflicting claims about an entity.

    Args:
        entity_name: Name of the entity to analyze

    Returns:
        Dictionary with conflict analysis
    """
    session = get_session()

    try:
        # Find entity
        entity = session.query(Entity).filter(Entity.name == entity_name).first()
        if not entity:
            return {"error": f"Entity '{entity_name}' not found"}

        # Get all claims about the entity
        claims = get_claims_for_entity(entity.id, session, include_superseded=True)

        # Group claims by type and detect conflicts
        claim_groups = {}
        conflicts = []

        for claim in claims:
            claim_type = claim.claim_type
            if claim_type not in claim_groups:
                claim_groups[claim_type] = []
            claim_groups[claim_type].append(claim)

        # Analyze each group for conflicts
        for claim_type, group_claims in claim_groups.items():
            if len(group_claims) > 1:
                # Check for conflicts within the group
                for i, claim1 in enumerate(group_claims):
                    for claim2 in group_claims[i + 1 :]:
                        # Simple conflict detection based on opposing statements
                        if (
                            claim1.temporal_qualifier != claim2.temporal_qualifier
                            or claim1.version_info != claim2.version_info
                        ):
                            conflicts.append(
                                {
                                    "type": "version_or_temporal",
                                    "claim1": claim1.statement,
                                    "claim2": claim2.statement,
                                    "claim1_context": {
                                        "temporal": claim1.temporal_qualifier,
                                        "version": claim1.version_info,
                                    },
                                    "claim2_context": {
                                        "temporal": claim2.temporal_qualifier,
                                        "version": claim2.version_info,
                                    },
                                }
                            )

        return {
            "entity": entity_name,
            "total_claims": len(claims),
            "claim_types": {k: len(v) for k, v in claim_groups.items()},
            "conflicts": conflicts,
            "superseded_claims": sum(1 for c in claims if c.is_superseded),
        }

    finally:
        session.close()
