"""Step to extract metadata from document sections using DSPy.

This model reads from `indexing_document_sections` table and extracts
entities, relationships, and claims using DSPy LLM calls.

Input table: indexing_document_sections
Output table: indexing_section_extractions
"""

import json
import logging
from typing import Any, List, Optional

import dspy
import pandas as pd
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import JSON, Column
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.content.indexing_new.framework import (
    LLMTelemetryMixin,
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
)
from kurt.content.indexing_new.framework.dspy_helpers import run_batch_sync
from kurt.db.models import ContentType, EntityType, RelationshipType

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class SectionExtractionsConfig(ModelConfig):
    """Configuration for section extractions step."""

    llm_model: str = ConfigParam(
        default="claude-3-5-haiku-latest",
        fallback="INDEXING_LLM_MODEL",
        description="LLM model for DSPy extraction",
    )
    max_concurrent: int = ConfigParam(
        default=10,
        fallback="MAX_CONCURRENT_INDEXING",
        description="Maximum concurrent LLM calls",
    )
    max_entities_context: int = ConfigParam(
        default=20,
        ge=0,
        le=100,
        description="Maximum existing entities to pass as context",
    )


# ============================================================================
# Pydantic Models for DSPy outputs (from indexing/models.py)
# ============================================================================


class ClaimExtraction(BaseModel):
    """Claim extraction from documents during indexing."""

    statement: str = PydanticField(description="The factual claim statement")
    claim_type: str = PydanticField(description="Claim type from ClaimType enum")
    entity_indices: List[int] = PydanticField(
        description="Indices of entities mentioned in claim (from YOUR OUTPUT entities list, 0-based)"
    )
    source_quote: str = PydanticField(description="Exact quote from document (50-500 chars)")
    quote_start_offset: int = PydanticField(description="Character offset where quote starts")
    quote_end_offset: int = PydanticField(description="Character offset where quote ends")
    confidence: float = PydanticField(description="Extraction confidence (0.0-1.0)", ge=0.0, le=1.0)


class DocumentMetadataOutput(BaseModel):
    """Document metadata from extraction."""

    content_type: ContentType
    has_code_examples: bool = False
    has_step_by_step_procedures: bool = False
    has_narrative_structure: bool = False


class EntityExtraction(BaseModel):
    """Entity extracted from document with resolution status."""

    name: str
    entity_type: EntityType
    description: str
    aliases: list[str] = []
    confidence: float  # 0.0-1.0
    resolution_status: str  # Must be one of ResolutionStatus enum values
    matched_entity_index: Optional[int] = None
    quote: Optional[str] = None  # Exact quote where entity is mentioned


class RelationshipExtraction(BaseModel):
    """Relationship between entities extracted from document."""

    source_entity: str
    target_entity: str
    relationship_type: RelationshipType
    context: Optional[str] = None
    confidence: float  # 0.0-1.0


# ============================================================================
# DSPy Signature
# ============================================================================


class IndexDocument(dspy.Signature):
    """Index a document: extract metadata, entities, relationships, and claims.

    This is the core indexing operation that understands a document's:

    1. Document Metadata:
       - Content Type: reference, tutorial, guide, blog, product_page, etc.
       - Title: Extract or generate concise title
       - Topics: 3-5 main topics (e.g., "ML", "Data Engineering")
       - Tools: Technologies mentioned (e.g., "PostgreSQL", "React")
       - Structure: code examples, procedures, narrative
       - Claims: Factual statements with exact source quotes and character offsets

    2. Knowledge Graph Entities:
       WHAT IS AN ENTITY?
       An entity is any distinct concept, thing, or capability that has its own identity and can be referenced.
       This includes:
       - Named things (products, companies, technologies)
       - Capabilities and features (what things can do)
       - Methods and approaches (how things work)
       - Concepts and domains (areas of knowledge)

       For each entity provide:
       * name: The entity name as it appears in text
       * entity_type: MUST be EXACTLY one of: Product, Feature, Technology, Topic, Company, Integration
       * quote: Exact text (50-200 chars) where entity is mentioned
       * resolution_status: MUST be EXACTLY one of: EXISTING or NEW
       * matched_entity_index: If EXISTING, provide the 'index' value from the matching entity

    3. Relationships:
       - Extract relationships between entities
       - MUST use EXACTLY one of the valid RelationshipType values
       - Provide context snippet showing the relationship

    4. Claims (Knowledge Extraction):
       - Extract ALL types of knowledge from the document
       - IMPORTANT: Look for technical instructions, explanations, and background context
       - Aim for comprehensive coverage (10-20 claims for technical documentation)
       - CRITICAL: entity_indices must reference YOUR OUTPUT entities list
       - Include ALL entities: product AND its capabilities/features/types
       - Provide exact quote (50-500 chars) with character offsets
       - Include confidence score (0.0-1.0)

    Be accurate - only list prominently discussed topics/tools/entities/claims.
    Always include exact quotes from the document for entities, relationships, and claims.
    """

    document_content: str = dspy.InputField(desc="Markdown document content (first 5000 chars)")
    existing_entities: str = dspy.InputField(
        default="[]",
        desc="JSON string of known entities: [{index, name, type, description, aliases}, ...]",
    )

    # Outputs
    metadata: DocumentMetadataOutput = dspy.OutputField(
        desc="Document metadata (content_type, title, structure flags)"
    )
    entities: list[EntityExtraction] = dspy.OutputField(
        desc="All meaningful entities: products, companies, technologies, features, and concepts"
    )
    relationships: list[RelationshipExtraction] = dspy.OutputField(
        desc="Relationships between entities"
    )
    claims: list[ClaimExtraction] = dspy.OutputField(
        desc="Factual claims extracted from the document, linked to entities by indices"
    )


# ============================================================================
# Output Model with model_validator
# ============================================================================


class SectionExtractionRow(PipelineModelBase, LLMTelemetryMixin, table=True):
    """Model for section extraction results.

    Inherits from:
    - PipelineModelBase: workflow_id, created_at, updated_at, model_name, error
    - LLMTelemetryMixin: tokens_prompt, tokens_completion, extraction_time_ms, llm_model_name

    Uses declarative transformations:
    - _field_renames: heading → section_heading
    - _dspy_mappings: dspy_result → *_json columns
    - Telemetry extraction handled by base class
    """

    __tablename__ = "indexing_section_extractions"

    # Declarative transformations (handled by PipelineModelBase.__init__)
    _field_renames = {"heading": "section_heading"}
    _dspy_mappings = {
        "metadata_json": "metadata",
        "entities_json": "entities",
        "relationships_json": "relationships",
        "claims_json": "claims",
    }

    # Primary keys
    document_id: str = Field(primary_key=True)
    section_id: str = Field(primary_key=True)

    # Section info
    section_number: int = Field(default=1)
    section_heading: Optional[str] = Field(default=None)

    # Extraction results (stored as JSON)
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)
    entities_json: Optional[list] = Field(sa_column=Column(JSON), default=None)
    relationships_json: Optional[list] = Field(sa_column=Column(JSON), default=None)
    claims_json: Optional[list] = Field(sa_column=Column(JSON), default=None)

    # Context passed to LLM (for resolving matched_entity_index to actual UUIDs)
    existing_entities_context_json: Optional[list] = Field(sa_column=Column(JSON), default=None)

    def __init__(self, **data: Any):
        """Handle custom transformation for existing_entities_context.

        Standard transformations (field renames, DSPy mappings, telemetry)
        are handled by PipelineModelBase via _field_renames and _dspy_mappings.
        """
        # Custom logic: transform existing_entities_context to JSON
        if "existing_entities_context" in data:
            context = data.pop("existing_entities_context")
            # Only store id and index for resolution, not full data
            data["existing_entities_context_json"] = [
                {"index": e.get("index"), "id": e.get("id")} for e in (context or [])
            ]

        # Base class handles: _field_renames, _dspy_mappings, dspy_telemetry
        super().__init__(**data)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="indexing.section_extractions",
    db_model=SectionExtractionRow,
    primary_key=["document_id", "section_id"],
    write_strategy="replace",
    description="Extract metadata from document sections using DSPy",
    config_schema=SectionExtractionsConfig,
)
def section_extractions(
    ctx: PipelineContext,
    # Dict filter with callable - SQL pushdown with runtime value from ctx
    sections=Reference(
        "indexing.document_sections",
        filter={"workflow_id": lambda ctx: ctx.workflow_id},
    ),
    writer: TableWriter = None,
    config: SectionExtractionsConfig = None,
):
    """Extract metadata from document sections using DSPy.

    This model reads sections from indexing_document_sections (auto-loaded via Reference),
    processes them with DSPy to extract entities, relationships, and claims,
    and writes results to indexing_section_extractions.

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        sections: Lazy reference to document sections from previous model
        writer: TableWriter for outputting extraction rows
        config: Step configuration (auto-injected by decorator)
    """
    # Lazy load - data fetched when accessed
    sections_df = sections.df

    if sections_df.empty:
        logger.warning("No sections found to process")
        return {"rows_written": 0}

    sections = sections_df.to_dict("records")
    logger.info(f"Processing {len(sections)} sections for extraction")

    # Load existing entities per document (not a single flat list)
    doc_entities = _load_existing_entities_by_document(sections_df)

    # Prepare extraction tasks with document-specific entity context
    tasks = [
        _prepare_task(
            section,
            doc_entities.get(section.get("document_id", ""), []),
            config.max_entities_context,
        )
        for section in sections
    ]

    # Run DSPy extractions (no progress callback - stats shown at step completion)
    batch_results = run_batch_sync(
        signature=IndexDocument,
        items=tasks,
        max_concurrent=config.max_concurrent,
        llm_model=config.llm_model,
    )

    # Create rows using model_validator - handles all transformations
    # Filter out fields that would conflict with explicit args
    exclude_fields = {
        "error",
        "dspy_result",
        "dspy_telemetry",
        "created_at",
        "updated_at",
        "existing_entities_context",
    }
    rows = [
        SectionExtractionRow(
            **{k: v for k, v in section.items() if k not in exclude_fields},
            dspy_result=result.result if not result.error else None,
            dspy_telemetry=result.telemetry,
            error=str(result.error) if result.error else None,
            # Pass existing entities context for resolving matched_entity_index later
            existing_entities_context=doc_entities.get(section.get("document_id", ""), []),
        )
        for section, result in zip(sections, batch_results)
    ]

    # Log extraction stats
    successful = sum(1 for r in rows if r.error is None)
    total_entities = sum(len(r.entities_json or []) for r in rows)
    total_claims = sum(len(r.claims_json or []) for r in rows)
    logger.info(
        f"Extracted {successful}/{len(rows)} sections: "
        f"{total_entities} entities, {total_claims} claims"
    )

    result = writer.write(rows)
    result["sections"] = len(rows)
    result["entities"] = total_entities
    result["claims"] = total_claims
    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _load_existing_entities_by_document(sections_df: pd.DataFrame) -> dict[str, list[dict]]:
    """Load existing entities grouped by document ID.

    Returns a dict mapping document_id -> list of entity dicts for that document.
    This ensures each section receives only the entities relevant to its document,
    enabling the LLM to properly match entities with resolution_status=EXISTING.

    Args:
        sections_df: DataFrame with document_id column

    Returns:
        Dict mapping document_id (str) -> list of entity dicts with id, index, name, type, description
    """
    from kurt.db import get_session
    from kurt.db.models import Entity

    document_ids = sections_df["document_id"].unique().tolist()
    doc_entities: dict[str, list[dict]] = {}

    with get_session() as session:
        for doc_id in document_ids:
            try:
                from uuid import UUID

                doc_uuid = UUID(doc_id) if isinstance(doc_id, str) else doc_id

                # Get entities for this specific document
                from sqlmodel import select

                from kurt.db.models import DocumentEntity

                stmt = (
                    select(Entity)
                    .join(DocumentEntity)
                    .where(DocumentEntity.document_id == doc_uuid)
                )
                entities = session.exec(stmt).all()

                # Format with index for LLM matching
                doc_entities[str(doc_id)] = [
                    {
                        "index": idx,
                        "id": str(entity.id),
                        "name": entity.name,
                        "type": entity.entity_type,
                        "description": entity.description or "",
                        "aliases": entity.aliases or [],
                    }
                    for idx, entity in enumerate(entities)
                ]
            except Exception as e:
                logger.warning(f"Error loading entities for document {doc_id}: {e}")
                doc_entities[str(doc_id)] = []

    total_entities = sum(len(ents) for ents in doc_entities.values())
    logger.debug(f"Loaded {total_entities} existing entities across {len(doc_entities)} documents")

    return doc_entities


def _prepare_task(
    section: dict, existing_entities: list[dict], max_entities_context: int = 20
) -> dict:
    """Prepare a single DSPy extraction task from section data."""
    # Build section content with overlap context
    content = section.get("content", section.get("section_content", ""))
    if section.get("overlap_prefix"):
        content = f"[...{section['overlap_prefix']}]\n\n{content}"
    if section.get("overlap_suffix"):
        content = f"{content}\n\n[{section['overlap_suffix']}...]"

    # Build title with section info
    title = section.get("document_title", "Unknown Document")
    heading = section.get("heading") or section.get("section_heading")
    section_number = section.get("section_number", 1)
    if heading:
        title = f"{title} - {heading}"
    else:
        title = f"{title} - Section {section_number}"

    return {
        "document_title": title,
        "document_content": content,
        "existing_entities": json.dumps(existing_entities[:max_entities_context])
        if existing_entities
        else "[]",
        # Pass through for progress callback
        "document_id": section.get("document_id", ""),
        "section_number": section_number,
    }
