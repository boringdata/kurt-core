"""Graph Claims Model - Materialize resolved claims to graph layer.

This model reads from staging_claim_resolution and materializes to graph_claims.
It produces the final, queryable claims table.

Input table: staging_claim_resolution
Output table: graph_claims
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


class GraphClaimRow(PipelineModelBase, table=True):
    """Materialized claim from staging resolution.

    This is the final, queryable claims table in the graph layer.
    Inherits: workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = TableNames.GRAPH_CLAIMS

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Claim content
    statement: str = Field(index=True)  # The claim text
    claim_type: str = Field(index=True)  # ClaimType value

    # Entity linkage
    subject_entity_id: Optional[UUID] = Field(default=None, index=True)  # Primary entity

    # Source tracking
    source_document_id: UUID = Field(index=True)
    source_quote: Optional[str] = Field(default=None)  # Exact quote from document
    source_section_id: Optional[str] = Field(default=None, index=True)

    # Temporal information
    temporal_qualifier: Optional[str] = Field(default=None)
    version_info: Optional[str] = Field(default=None)

    # Confidence scoring
    extraction_confidence: float = Field(default=0.0)
    source_authority: float = Field(default=0.5)
    corroboration_score: float = Field(default=0.0)
    overall_confidence: float = Field(default=0.0)

    # Resolution metadata
    resolution_status: str = Field(default="RESOLVED")  # RESOLVED, PENDING, MERGED
    merged_into_id: Optional[UUID] = Field(default=None)
    canonical_cluster_id: Optional[str] = Field(default=None)

    # Vector embedding
    embedding: bytes = Field(default=b"")


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="graph.claims.claims",
    primary_key=["id"],
    write_strategy="replace",
    description="Materialize resolved claims from staging to graph layer",
)
@table(GraphClaimRow)
def claims(
    ctx: PipelineContext,
    claim_resolution=Reference("staging.indexing.claim_resolution"),
    writer: TableWriter = None,
):
    """Read from staging_claim_resolution and materialize to graph_claims.

    This model:
    1. Reads resolved claims from staging_claim_resolution
    2. Creates/updates entries in graph_claims
    3. Handles claim merging (resolution_status, merged_into_id)
    """
    # TODO: Implement materialization logic

    logger.info("graph.claims.claims: Materializing claims from staging")

    return {"rows_written": 0, "message": "Not yet implemented"}
