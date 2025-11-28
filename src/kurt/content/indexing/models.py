"""Data models for document indexing and entity resolution.

This module contains all Pydantic models used throughout the indexing pipeline:
- Document metadata extraction models
- Entity and relationship extraction models
- Entity resolution models
"""

from typing import Optional

from pydantic import BaseModel, Field

from kurt.db.models import ClaimEntityRole, ClaimType, ContentType, EntityType, RelationshipType

# ============================================================================
# Document Metadata Models (used by IndexDocument DSPy signature)
# ============================================================================


class DocumentMetadataOutput(BaseModel):
    """Metadata extracted from document content.

    Note: Topics and technologies are extracted separately as entities in the knowledge graph,
    not as part of this metadata output. See EntityExtraction model for entity extraction.
    """

    content_type: ContentType
    extracted_title: Optional[str] = None
    has_code_examples: bool = False
    has_step_by_step_procedures: bool = False
    has_narrative_structure: bool = False


# ============================================================================
# Entity Extraction Models (used by IndexDocument DSPy signature)
# ============================================================================


class EntityExtraction(BaseModel):
    """Entity extracted from document with resolution status."""

    name: str
    entity_type: EntityType
    description: str
    aliases: list[str] = []
    confidence: float  # 0.0-1.0
    resolution_status: str  # "EXISTING" or "NEW"
    matched_entity_index: Optional[int] = None  # If EXISTING, the index from existing_entities list
    quote: Optional[str] = None  # Exact quote/context where entity is mentioned (50-200 chars)


class RelationshipExtraction(BaseModel):
    """Relationship between entities extracted from document."""

    source_entity: str
    target_entity: str
    relationship_type: RelationshipType
    context: Optional[str] = None
    confidence: float  # 0.0-1.0


# ============================================================================
# Entity Resolution Models (used by ResolveEntityGroup DSPy signature)
# ============================================================================


class EntityResolution(BaseModel):
    """Resolution decision for a single entity."""

    entity_name: str = Field(description="Name of the entity being resolved")
    resolution_decision: str = Field(
        description="Decision: 'CREATE_NEW' to create new entity, 'MERGE_WITH:<entity_name>' to merge with peer in cluster, or UUID of existing entity to link to"
    )
    canonical_name: str = Field(description="Canonical name for the resolved entity")
    aliases: list[str] = Field(default=[], description="All aliases for the resolved entity")
    reasoning: str = Field(description="Brief explanation of the resolution decision")


class GroupResolution(BaseModel):
    """Resolution decisions for all entities in a group."""

    resolutions: list[EntityResolution] = Field(
        description="Resolution decision for each entity in the group"
    )


# ============================================================================
# Claim Extraction Models (used by IndexDocument DSPy signature)
# ============================================================================


class ClaimEntityReference(BaseModel):
    """Reference to an entity involved in a claim."""

    entity_name: str = Field(description="Name of the entity")
    role: ClaimEntityRole = Field(description="Role: source (who made claim), subject (claim about), object (compared to)")


class ClaimExtraction(BaseModel):
    """Claim extracted from document with resolution status."""

    claim_text: str = Field(description="The claim as stated in the document (50-200 chars)")
    claim_type: ClaimType = Field(description="Type of claim: factual, comparative, capability, performance, benefit, limitation, integration, other")
    entities: list[ClaimEntityReference] = Field(
        default=[],
        description="Entities involved in this claim with their roles"
    )
    confidence: float = Field(description="Confidence score 0.0-1.0")
    quote: Optional[str] = Field(
        default=None,
        description="Exact quote from document where claim appears (50-200 chars)"
    )
    resolution_status: str = Field(
        default="NEW",
        description="'EXISTING' if matches existing claim, 'NEW' if novel"
    )
    matched_claim_index: Optional[int] = Field(
        default=None,
        description="If EXISTING, the index from existing_claims list"
    )


# ============================================================================
# Claim Resolution Models (used by ResolveClaimGroup DSPy signature)
# ============================================================================


class ClaimResolution(BaseModel):
    """Resolution decision for a single claim."""

    claim_text: str = Field(description="The claim being resolved")
    resolution_decision: str = Field(
        description="Decision: 'CREATE_NEW' to create new claim, 'MERGE_WITH:<claim_text>' to merge with peer, or UUID of existing claim to link to"
    )
    canonical_text: str = Field(description="Canonical form of the claim for deduplication")
    aliases: list[str] = Field(default=[], description="Alternative phrasings of this claim")
    reasoning: str = Field(description="Brief explanation of the resolution decision")


class ClaimGroupResolution(BaseModel):
    """Resolution decisions for all claims in a group."""

    resolutions: list[ClaimResolution] = Field(
        description="Resolution decision for each claim in the group"
    )
