"""Data models for document indexing and entity resolution.

This module contains all Pydantic models used throughout the indexing pipeline:
- Document metadata extraction models
- Entity and relationship extraction models
- Entity resolution models
- Type constants
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from kurt.db.models import ContentType

# ============================================================================
# Entity and Relationship Type Constants
# ============================================================================


class EntityType(str, Enum):
    """Canonical entity types extracted during document indexing."""

    PRODUCT = "Product"
    FEATURE = "Feature"
    TECHNOLOGY = "Technology"
    TOPIC = "Topic"
    COMPANY = "Company"
    INTEGRATION = "Integration"


class RelationshipType(str, Enum):
    """Canonical relationship types extracted during document indexing."""

    MENTIONS = "mentions"
    PART_OF = "part_of"
    INTEGRATES_WITH = "integrates_with"
    ENABLES = "enables"
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    REPLACES = "replaces"


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
    entity_type: str  # Must be one of: Product, Feature, Technology, Topic, Company, Integration
    description: str
    aliases: list[str] = []
    confidence: float  # 0.0-1.0
    resolution_status: str  # "EXISTING" or "NEW"
    matched_entity_index: Optional[int] = None  # If EXISTING, the index from existing_entities list
    quote: Optional[str] = None  # Exact quote/context where entity is mentioned (50-200 chars)

    @classmethod
    def model_validate(cls, value):
        """Validate entity_type is a valid EntityType value."""
        obj = super().model_validate(value)
        valid_types = [e.value for e in EntityType]
        if obj.entity_type not in valid_types:
            raise ValueError(
                f"Invalid entity_type '{obj.entity_type}'. Must be one of: {', '.join(valid_types)}"
            )
        return obj


class RelationshipExtraction(BaseModel):
    """Relationship between entities extracted from document."""

    source_entity: str
    target_entity: str
    relationship_type: str  # Must be one of: mentions, part_of, integrates_with, enables, related_to, depends_on, replaces
    context: Optional[str] = None
    confidence: float  # 0.0-1.0

    @classmethod
    def model_validate(cls, value):
        """Validate relationship_type is a valid RelationshipType value."""
        obj = super().model_validate(value)
        valid_types = [r.value for r in RelationshipType]
        if obj.relationship_type not in valid_types:
            raise ValueError(
                f"Invalid relationship_type '{obj.relationship_type}'. "
                f"Must be one of: {', '.join(valid_types)}"
            )
        return obj


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
