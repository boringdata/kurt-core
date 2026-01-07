"""Graph Document Topics Model - Materialize document-topic links.

This model reads from staging topic clustering and creates links
between documents and their assigned topic clusters.

Input tables: staging_topic_clustering, graph_topic_clusters
Output table: graph_document_topics
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


class GraphDocumentTopicRow(PipelineModelBase, table=True):
    """Document-topic link materialized from staging.

    Links documents to topic clusters with content type information.
    Inherits: workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = TableNames.GRAPH_DOCUMENT_TOPICS

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Core relationship
    document_id: UUID = Field(index=True)  # FK to landing_discovery.id
    topic_cluster_id: UUID = Field(index=True)  # FK to graph_topic_clusters.id

    # Content type classification
    content_type: Optional[str] = Field(default=None, index=True)

    # LLM reasoning for assignment
    reasoning: Optional[str] = Field(default=None)

    # Confidence
    confidence: float = Field(default=0.0)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="graph.topics.document_topics",
    primary_key=["id"],
    write_strategy="replace",
    description="Materialize document-topic links from staging to graph layer",
)
@table(GraphDocumentTopicRow)
def document_topics(
    ctx: PipelineContext,
    topic_clustering=Reference("staging.clustering.topic_clustering"),
    topic_clusters=Reference("graph.topics.topic_clusters"),
    writer: TableWriter = None,
):
    """Read from staging and graph_topic_clusters, write to graph_document_topics.

    This model:
    1. Reads document assignments from staging_topic_clustering
    2. Resolves cluster names to graph_topic_clusters IDs
    3. Creates document-topic links with content type information
    """
    # TODO: Implement materialization logic

    logger.info("graph.topics.document_topics: Materializing document-topic links")

    return {"rows_written": 0, "message": "Not yet implemented"}
