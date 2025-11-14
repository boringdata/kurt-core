"""Data models for document indexing and entity resolution.

This module contains all Pydantic models used throughout the indexing pipeline:
- Document metadata extraction models
- Entity and relationship extraction models
- Entity resolution models
- Type constants
"""

from typing import Optional

from pydantic import BaseModel, Field

from kurt.db.models import ContentType

# ============================================================================
# Entity and Relationship Type Constants
# ============================================================================

ENTITY_TYPES = [
    "Product",
    "Feature",
    "Technology",
    "Topic",
    "Company",
    "Integration",
]

RELATIONSHIP_TYPES = [
    "mentions",
    "part_of",
    "integrates_with",
    "enables",
    "related_to",
    "depends_on",
    "replaces",
]


# ============================================================================
# Document Metadata Models (used by IndexDocument DSPy signature)
# ============================================================================


class DocumentMetadataOutput(BaseModel):
    """Metadata extracted from document content."""

    content_type: ContentType
    extracted_title: Optional[str] = None
    primary_topics: list[str] = []
    tools_technologies: list[str] = []
    has_code_examples: bool = False
    has_step_by_step_procedures: bool = False
    has_narrative_structure: bool = False


# ============================================================================
# Entity Extraction Models (used by IndexDocument DSPy signature)
# ============================================================================


class EntityExtraction(BaseModel):
    """Entity extracted from document with resolution status."""

    name: str
    entity_type: str  # Product, Feature, Technology, Topic, Company, Integration
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
    relationship_type: str  # mentions, part_of, integrates_with, etc.
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
