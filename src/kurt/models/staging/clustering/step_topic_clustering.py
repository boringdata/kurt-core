"""Step to compute topic clusters and classify content types for documents.

This model reads from documents table, performs LLM-based topic clustering
and content type classification using batch processing with apply_dspy_on_df.

The step outputs to a staging table, which can then be applied to update
the TopicCluster and DocumentClusterEdge tables.

Input: documents table (filtered by workflow filters)
Output table: staging_topic_clustering
"""

import logging
from typing import Optional

import dspy
import pandas as pd
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import (
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    apply_dspy_on_df,
    model,
    table,
)
from kurt.db.models import ContentType

logger = logging.getLogger(__name__)

# Generate valid content types from the enum
VALID_CONTENT_TYPES = ", ".join([ct.value for ct in ContentType])


# ============================================================================
# Configuration
# ============================================================================


class TopicClusteringConfig(ModelConfig):
    """Configuration for topic clustering step."""

    batch_size: int = ConfigParam(
        default=200,
        ge=10,
        le=500,
        description="Number of documents to process per LLM batch",
    )
    max_concurrent: int = ConfigParam(
        default=1,
        ge=1,
        le=10,
        description="Number of concurrent LLM calls (batches processed in parallel)",
    )
    llm_model: str = ConfigParam(
        default="claude-3-5-haiku-latest",
        fallback="INDEXING_LLM_MODEL",
        description="LLM model for clustering and classification",
    )
    force_fresh: bool = ConfigParam(
        default=False,
        description="Ignore existing clusters and create fresh (default: refine existing)",
    )


# ============================================================================
# Pydantic Models (DSPy inputs/outputs)
# ============================================================================


class PageMetadata(BaseModel):
    """Metadata for a single page."""

    url: str
    title: Optional[str] = None
    description: Optional[str] = None


class TopicClusterOutput(BaseModel):
    """A single topic cluster identified from the page collection."""

    name: str = PydanticField(description="Name of the topic cluster")
    description: str = PydanticField(
        description="Brief explanation of what this topic encompasses (1-2 sentences)"
    )


class ExistingCluster(BaseModel):
    """An existing cluster for incremental clustering."""

    name: str = PydanticField(description="Name of the existing cluster")
    description: str = PydanticField(description="Description of the existing cluster")


# ============================================================================
# DSPy Signatures
# ============================================================================


class ClassifyAndAssignDocument(dspy.Signature):
    """Classify a single document's content type and assign to a cluster.

    Given a document's URL, title, and description, plus a list of available clusters:
    1. Classify the content type (reference, tutorial, guide, blog, etc.)
    2. Assign to the best matching cluster (or null if none fit)

    CONTENT TYPE CLASSIFICATION:
    Classify into ONE of these types (use EXACT lowercase names):
    - reference: API docs, technical reference
    - tutorial: Step-by-step how-to with examples
    - guide: Explanatory, best practices, concepts
    - blog: Blog posts, articles, news
    - product_page: Product marketing, features
    - solution_page: Solutions, use-cases
    - homepage: Main landing pages
    - case_study: Customer stories
    - event: Webinars, conferences
    - info: About, company, legal
    - landing_page: Marketing campaigns
    - other: Doesn't fit above

    CLUSTER ASSIGNMENT:
    Pick the cluster that best matches the document's topic/content.
    If no cluster fits well, set cluster_name to null.
    """

    url: str = dspy.InputField(description="Document URL")
    title: str = dspy.InputField(description="Document title")
    description: str = dspy.InputField(description="Document description/summary")
    available_clusters: str = dspy.InputField(
        description="JSON list of available clusters with names and descriptions"
    )

    content_type: str = dspy.OutputField(
        description=f"Content type classification. Must be one of: {VALID_CONTENT_TYPES}"
    )
    cluster_name: str = dspy.OutputField(
        description="Name of best matching cluster, or 'null' if none fit"
    )
    reasoning: str = dspy.OutputField(
        description="Brief reasoning for classification and assignment"
    )


class DiscoverTopicClusters(dspy.Signature):
    """Discover topic clusters from a batch of documents.

    Analyze the URLs, titles, and descriptions to identify natural topic groupings.
    If existing_clusters are provided, refine/update them:
    - KEEP clusters that are still valid
    - REFINE names/descriptions if needed
    - SPLIT large clusters
    - MERGE similar clusters
    - ADD new clusters for new topics
    - REMOVE outdated clusters (by not including them)

    CLUSTERING GUIDELINES:
    1. Analyze URLs, titles, descriptions for themes
    2. Look for patterns in URL structures, keywords, related concepts
    3. Create meaningful, specific clusters (not overly broad)
    4. Ensure clusters are mutually exclusive where possible
    5. Balance cluster sizes (avoid one massive cluster)
    """

    documents_json: str = dspy.InputField(
        description="JSON array of documents with url, title, description"
    )
    existing_clusters_json: str = dspy.InputField(
        description="JSON array of existing clusters to refine (empty array if starting fresh)"
    )

    clusters_json: str = dspy.OutputField(
        description="JSON array of topic clusters [{name: string, description: string}, ...]"
    )


# ============================================================================
# Output Model
# ============================================================================


class TopicClusteringRow(PipelineModelBase, table=True):
    """Topic clustering and classification results for a document.

    Each row represents one document's cluster assignment and content type.
    """

    __tablename__ = "staging_topic_clustering"

    # Primary key
    document_id: str = Field(primary_key=True)
    workflow_id: str = Field(primary_key=True)

    # Document metadata (for context)
    source_url: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)

    # Cluster assignment
    cluster_name: Optional[str] = Field(default=None, index=True)
    cluster_description: Optional[str] = Field(default=None)

    # Content type classification
    content_type: Optional[str] = Field(default=None, index=True)

    # LLM reasoning
    reasoning: Optional[str] = Field(default=None)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="staging.topic_clustering",
    primary_key=["document_id", "workflow_id"],
    write_strategy="replace",
    description="Compute topic clusters and classify content types for documents",
    config_schema=TopicClusteringConfig,
)
@table(TopicClusteringRow)
def topic_clustering(
    ctx: PipelineContext,
    documents=Reference("documents"),
    writer: TableWriter = None,
    config: TopicClusteringConfig = None,
):
    """Compute topic clusters and classify content types for documents.

    This model:
    1. Reads document metadata from documents table
    2. Discovers/refines topic clusters using LLM
    3. Classifies each document's content type and assigns to cluster
    4. Writes results to staging table

    Args:
        ctx: Pipeline context with filters, workflow_id
        documents: Lazy reference to documents table
        writer: TableWriter for outputting rows
        config: Topic clustering configuration
    """
    import json

    workflow_id = ctx.workflow_id

    # Filter documents by ctx.document_ids
    query = documents.query
    if ctx.document_ids:
        query = query.filter(documents.model_class.id.in_(ctx.document_ids))
    docs_df = pd.read_sql(query.statement, documents.session.bind)

    if docs_df.empty:
        logger.warning("No documents found to cluster")
        return {"rows_written": 0, "documents_processed": 0}

    logger.info(f"Processing {len(docs_df)} documents for topic clustering")

    # Step 1: Discover/refine topic clusters
    existing_clusters = []
    if not config.force_fresh:
        existing_clusters = _fetch_existing_clusters(docs_df, documents.session)
        if existing_clusters:
            logger.info(
                f"Found {len(existing_clusters)} existing clusters - will refine/update them"
            )

    # Discover clusters from document batch
    clusters = _discover_clusters(
        docs_df,
        existing_clusters=existing_clusters,
        config=config,
    )
    logger.info(f"Discovered {len(clusters)} topic clusters")

    # Build cluster lookup
    cluster_lookup = {c["name"]: c["description"] for c in clusters}
    clusters_json = json.dumps(clusters)

    # Step 2: Prepare DataFrame for classification
    docs_df["url"] = docs_df["source_url"].fillna("")
    docs_df["title"] = docs_df["title"].fillna("")
    docs_df["description"] = docs_df["description"].fillna("")
    docs_df["available_clusters"] = clusters_json

    # Step 3: Apply DSPy to classify and assign each document
    docs_df = apply_dspy_on_df(
        docs_df,
        ClassifyAndAssignDocument,
        input_fields={
            "url": "url",
            "title": "title",
            "description": "description",
            "available_clusters": "available_clusters",
        },
        output_fields={
            "content_type": "content_type",
            "cluster_name": "cluster_name",
            "reasoning": "reasoning",
        },
        max_concurrent=config.max_concurrent,
        llm_model=config.llm_model,
        progress=True,
    )

    # Step 4: Post-process using df.apply
    docs_df["content_type"] = docs_df["content_type"].apply(_normalize_content_type)
    docs_df["cluster_name"] = docs_df["cluster_name"].apply(_normalize_cluster_name)
    docs_df["cluster_description"] = docs_df["cluster_name"].apply(
        lambda name: cluster_lookup.get(name) if name else None
    )

    # Create output rows using apply
    def create_output_row(row):
        return TopicClusteringRow(
            document_id=str(row["id"]),
            workflow_id=workflow_id,
            source_url=row.get("source_url"),
            title=row.get("title"),
            cluster_name=row.get("cluster_name"),
            cluster_description=row.get("cluster_description"),
            content_type=row.get("content_type"),
            reasoning=row.get("reasoning"),
        )

    rows = docs_df.apply(create_output_row, axis=1).tolist()

    # Compute stats
    classified_count = int(docs_df["content_type"].notna().sum())
    assigned_count = int(docs_df["cluster_name"].notna().sum())

    logger.info(
        f"Topic clustering complete: {len(clusters)} clusters, "
        f"{classified_count} classified, {assigned_count} assigned"
    )

    result = writer.write(rows)
    result["documents_processed"] = len(docs_df)
    result["clusters_discovered"] = len(clusters)
    result["documents_classified"] = classified_count
    result["documents_assigned"] = assigned_count
    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _fetch_existing_clusters(docs_df: pd.DataFrame, session) -> list[dict]:
    """Fetch existing clusters linked to the documents being processed."""
    from uuid import UUID

    from kurt.db.models import DocumentClusterEdge, TopicCluster

    # Ensure doc_ids are UUID objects (pd.read_sql may return strings)
    doc_ids = [
        UUID(str(doc_id)) if not isinstance(doc_id, UUID) else doc_id
        for doc_id in docs_df["id"].tolist()
    ]

    existing_cluster_records = (
        session.query(TopicCluster)
        .join(DocumentClusterEdge)
        .filter(DocumentClusterEdge.document_id.in_(doc_ids))
        .distinct()
        .all()
    )

    return [
        {"name": cluster.name, "description": cluster.description or ""}
        for cluster in existing_cluster_records
    ]


def _discover_clusters(
    docs_df: pd.DataFrame,
    existing_clusters: list[dict],
    config: TopicClusteringConfig,
) -> list[dict]:
    """Discover topic clusters from documents using LLM.

    Uses df.apply to prepare document metadata, then sends to LLM in batches.
    """
    import json

    from kurt.core.dspy_helpers import configure_dspy_model

    configure_dspy_model(config.llm_model)

    # Use df.apply to prepare document metadata
    def extract_doc_metadata(row):
        return {
            "url": row.get("source_url") or "",
            "title": row.get("title") or "",
            "description": row.get("description") or "",
        }

    documents = docs_df.apply(extract_doc_metadata, axis=1).tolist()

    # Process in batches for large datasets (cluster discovery is aggregation, not per-row)
    batch_size = config.batch_size
    current_clusters = existing_clusters

    total_batches = (len(documents) + batch_size - 1) // batch_size
    if total_batches > 1:
        logger.info(
            f"Discovering clusters from {len(documents)} documents in {total_batches} batches"
        )

    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i : i + batch_size]

        if total_batches > 1:
            batch_num = (i // batch_size) + 1
            logger.info(
                f"Cluster discovery batch {batch_num}/{total_batches} ({len(batch_docs)} docs)"
            )

        # Call LLM to discover/refine clusters
        clusterer = dspy.ChainOfThought(DiscoverTopicClusters)
        result = clusterer(
            documents_json=json.dumps(batch_docs),
            existing_clusters_json=json.dumps(current_clusters),
        )

        # Parse result
        try:
            current_clusters = json.loads(result.clusters_json)
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse clusters JSON, keeping previous: {result.clusters_json}"
            )

    return current_clusters


def _normalize_cluster_name(name) -> Optional[str]:
    """Convert null string to None."""
    if name is None:
        return None
    name_str = str(name).lower().strip()
    if name_str in ("null", "none", ""):
        return None
    return name


def _normalize_content_type(content_type_str) -> Optional[str]:
    """Normalize content type string to valid enum value."""
    if not content_type_str:
        return "other"

    content_type_value = str(content_type_str).lower().strip()

    # Map common variations to correct types
    type_mapping = {
        "example": "tutorial",
        "examples": "tutorial",
        "documentation": "reference",
        "doc": "reference",
        "docs": "reference",
        "article": "blog",
        "post": "blog",
    }
    content_type_value = type_mapping.get(content_type_value, content_type_value)

    # Validate against enum
    try:
        ContentType(content_type_value)
        return content_type_value
    except ValueError:
        logger.debug(f"Invalid content_type '{content_type_str}', using 'other'")
        return "other"
