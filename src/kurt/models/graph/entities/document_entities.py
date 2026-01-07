"""Graph Document Entities Model - Materialize document-entity links.

This model reads from staging section extractions and entity resolution,
then materializes document-entity relationships to the graph layer.

Input tables: staging_section_extractions, graph_entities
Output table: graph_document_entities
"""

import logging
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field

from kurt.core import (
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
    table,
)
from kurt.db.tables import TableNames

logger = logging.getLogger(__name__)


# ============================================================================
# Output Schema
# ============================================================================


class GraphDocumentEntityRow(PipelineModelBase, table=True):
    """Document-entity link materialized from staging.

    Links documents to entities with section-level granularity.
    Inherits: workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = TableNames.GRAPH_DOCUMENT_ENTITIES

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core relationship
    document_id: UUID = Field(index=True)  # FK to landing_discovery.id
    entity_id: UUID = Field(index=True)  # FK to graph_entities.id

    # Section-level granularity
    section_id: Optional[str] = Field(default=None, index=True)

    # Relationship metadata
    mention_count: int = Field(default=1)
    confidence: float = Field(default=0.0)
    context: Optional[str] = Field(default=None)  # Quote from document


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="graph.entities.document_entities",
    primary_key=["id"],
    write_strategy="replace",
    description="Materialize document-entity links from staging to graph layer",
)
@table(GraphDocumentEntityRow)
def document_entities(
    ctx: PipelineContext,
    section_extractions=Reference("staging.indexing.section_extractions"),
    entities=Reference("graph.entities.entities"),
    writer: TableWriter = None,
):
    """Read from staging and graph_entities, write to graph_document_entities.

    This model:
    1. Reads entity mentions from staging_section_extractions
    2. Resolves to canonical entities in graph_entities
    3. Creates document-entity links with section granularity
    """
    # TODO: Implement materialization logic

    logger.info("graph.entities.document_entities: Materializing document-entity links")

    return {"rows_written": 0, "message": "Not yet implemented"}
