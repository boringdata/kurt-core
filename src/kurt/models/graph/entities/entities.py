"""Graph Entities Model - Materialize resolved entities to graph layer.

This model reads from staging_entity_resolution and materializes to graph_entities.
It produces the final, queryable entities table.

Input table: staging_entity_resolution
Output table: graph_entities
"""

import logging
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
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


class GraphEntityRow(PipelineModelBase, table=True):
    """Materialized entity from staging resolution.

    This is the final, queryable entities table in the graph layer.
    Inherits: workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = TableNames.GRAPH_ENTITIES

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core entity fields
    name: str = Field(index=True)
    entity_type: str = Field(index=True)  # Topic, Technology, Person, Organization, etc.
    canonical_name: Optional[str] = Field(default=None, index=True)

    # Extended metadata
    aliases_json: Optional[list] = Field(sa_column=Column(JSON), default=None)
    description: Optional[str] = Field(default=None)

    # Embedding for similarity search
    embedding: bytes = Field(default=b"")

    # Resolution metadata
    resolution_status: str = Field(default="RESOLVED")  # RESOLVED, PENDING, MERGED
    merged_into_id: Optional[str] = Field(default=None)  # If merged, points to canonical entity

    # Statistics
    confidence_score: float = Field(default=0.0)
    source_mentions: int = Field(default=0)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="graph.entities.entities",
    primary_key=["id"],
    write_strategy="replace",
    description="Materialize resolved entities from staging to graph layer",
)
@table(GraphEntityRow)
def entities(
    ctx: PipelineContext,
    entity_resolution=Reference("staging.indexing.entity_resolution"),
    writer: TableWriter = None,
):
    """Read from staging_entity_resolution and materialize to graph_entities.

    This model:
    1. Reads resolved entities from staging_entity_resolution
    2. Creates/updates entries in graph_entities
    3. Handles entity merging (resolution_status, merged_into_id)
    """
    # TODO: Implement materialization logic
    # For now, this is a placeholder that will be implemented
    # when the staging models are updated to support this pattern

    logger.info("graph.entities.entities: Materializing entities from staging")

    # Query resolved entities from staging
    # entity_resolution_df = entity_resolution.read()

    # Transform and write to graph_entities
    # ...

    return {"rows_written": 0, "message": "Not yet implemented"}
