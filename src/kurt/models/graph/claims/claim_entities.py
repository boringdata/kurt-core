"""Graph Claim Entities Model - Materialize claim-entity links.

This model reads from staging section extractions and creates links
between claims and the entities they reference.

Input tables: graph_claims, graph_entities
Output table: graph_claim_entities
"""

import logging
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


class GraphClaimEntityRow(PipelineModelBase, table=True):
    """Claim-entity link materialized from staging.

    Links claims to entities with role information.
    Inherits: workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = TableNames.GRAPH_CLAIM_ENTITIES

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core relationship
    claim_id: UUID = Field(index=True)  # FK to graph_claims.id
    entity_id: UUID = Field(index=True)  # FK to graph_entities.id

    # Role of entity in the claim
    entity_role: str = Field(default="referenced")  # subject, object, referenced, compared_to

    # Confidence
    confidence: float = Field(default=0.0)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="graph.claims.claim_entities",
    primary_key=["id"],
    write_strategy="replace",
    description="Materialize claim-entity links from staging to graph layer",
)
@table(GraphClaimEntityRow)
def claim_entities(
    ctx: PipelineContext,
    claims=Reference("graph.claims.claims"),
    entities=Reference("graph.entities.entities"),
    writer: TableWriter = None,
):
    """Read from graph_claims and graph_entities, write to graph_claim_entities.

    This model:
    1. Reads entity mentions from claims
    2. Resolves to canonical entities in graph_entities
    3. Creates claim-entity links with role information
    """
    # TODO: Implement materialization logic

    logger.info("graph.claims.claim_entities: Materializing claim-entity links")

    return {"rows_written": 0, "message": "Not yet implemented"}
