"""Data models for document indexing and entity resolution.

This module contains all Pydantic models used throughout the indexing pipeline:
- Document metadata extraction models
- Entity and relationship extraction models
- Entity resolution models
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from kurt.db.models import ContentType, EntityType, RelationshipType

# ============================================================================
# Document Metadata Models (used by IndexDocument DSPy signature)
# ============================================================================


class ClaimExtraction(BaseModel):
    """Claim extraction from documents during indexing.

    Claims are linked to entities by their indices in the OUTPUT entities list (0-based).
    The first index is the primary/subject entity, additional indices are referenced entities.
    Example: If you extract entities ["Kurt", "Python"], use indices [0, 1] not indices from existing_entities.
    """

    statement: str = Field(description="The factual claim statement")
    claim_type: str = Field(
        description="Claim type from ClaimType enum: capability, definition, explanation, instruction, background, feature, integration, performance, limitation, requirement, compatibility, comparison, statistic, pricing, availability, process, or other. See prompt for detailed descriptions."
    )
    entity_indices: List[int] = Field(
        description="Indices of entities mentioned in claim (from YOUR OUTPUT entities list, 0-based). First index is the primary subject, rest are referenced entities. Example: [0, 2] means first and third entity from YOUR entities output"
    )
    source_quote: str = Field(description="Exact quote from document (50-500 chars)")
    quote_start_offset: int = Field(description="Character offset where quote starts")
    quote_end_offset: int = Field(description="Character offset where quote ends")
    confidence: float = Field(description="Extraction confidence (0.0-1.0)", ge=0.0, le=1.0)


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
    resolution_status: str  # Must be one of ResolutionStatus enum values: "EXISTING" or "NEW"
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
    """Resolution decision for a single entity.

    Resolution decisions use indexes instead of text to avoid matching errors:
    - entity_index: Index of the entity in the input group (0-based)
    - decision_type: One of 'CREATE_NEW', 'MERGE_WITH_PEER', 'LINK_TO_EXISTING'
    - target_index: For MERGE_WITH_PEER, the index of the peer entity to merge with.
                    For LINK_TO_EXISTING, the index of the existing entity in existing_candidates.
    """

    entity_index: int = Field(description="Index of the entity in group_entities (0-based)")
    decision_type: str = Field(
        description="One of: 'CREATE_NEW', 'MERGE_WITH_PEER', 'LINK_TO_EXISTING'"
    )
    target_index: Optional[int] = Field(
        default=None,
        description="For MERGE_WITH_PEER: index of peer in group_entities. For LINK_TO_EXISTING: index of entity in existing_candidates.",
    )
    canonical_name: str = Field(description="Canonical name for the resolved entity")
    aliases: list[str] = Field(default=[], description="All aliases for the resolved entity")
    reasoning: str = Field(description="Brief explanation of the resolution decision")


class GroupResolution(BaseModel):
    """Resolution decisions for all entities in a group."""

    resolutions: list[EntityResolution] = Field(
        description="Resolution decision for each entity in the group"
    )
