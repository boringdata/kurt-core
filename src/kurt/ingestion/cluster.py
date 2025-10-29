"""Topic clustering logic using DSPy."""

import logging
from typing import Optional
from uuid import uuid4

import dspy
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class PageMetadata(BaseModel):
    """Metadata for a single page."""

    url: str
    title: Optional[str] = None
    description: Optional[str] = None


class TopicClusterOutput(BaseModel):
    """A single topic cluster identified from the page collection."""

    name: str = Field(description="Name of the topic cluster")
    description: str = Field(
        description="Brief explanation of what this topic encompasses (1-2 sentences)"
    )
    example_urls: list[str] = Field(description="3-5 representative URLs from this cluster")


# ============================================================================
# DSPy Signature
# ============================================================================


class ComputeClusters(dspy.Signature):
    """Analyze a collection of web pages and identify 5-10 primary topic clusters.

    You are analyzing a collection of blog posts/web pages to identify the primary topics they cover.
    Your task is to cluster the content into 5-10 distinct, meaningful topics based on URLs, meta titles,
    and meta descriptions.

    Instructions:
    1. Analyze the URLs, titles to understand themes and subjects
    2. Look for patterns in:
       - URL structures and paths (e.g., /blog/category-name/)
       - Keyword repetition across titles
       - Related concepts and themes
    3. Group related content into 5-10 distinct topic clusters
    4. Ensure topics are:
       - Meaningful and specific (not overly broad like "technology" or "business")
       - Mutually exclusive where possible (minimal overlap between clusters")
       - Comprehensive (together they cover the main themes)
       - Balanced in size (avoid one massive cluster and several tiny ones)
    """

    pages: list[PageMetadata] = dspy.InputField(
        description="List of pages with URL, title, and description metadata"
    )
    clusters: list[TopicClusterOutput] = dspy.OutputField(
        description="5-10 distinct topic clusters"
    )


# ============================================================================
# Business Logic
# ============================================================================


def normalize_url(url: str) -> str:
    """Normalize URL for matching: lowercase, strip trailing slash."""
    if not url:
        return ""
    normalized = url.lower().strip()
    # Remove trailing slash unless it's just the domain
    if normalized.endswith("/") and normalized.count("/") > 2:
        normalized = normalized.rstrip("/")
    return normalized


def compute_topic_clusters(
    url_prefix: Optional[str] = None,
    url_contains: Optional[str] = None,
) -> dict:
    """
    Compute topic clusters from a collection of documents.

    Uses only document metadata (URL, title, description) to identify topic clusters.
    Does not require documents to be FETCHED - works with any document status.

    Args:
        url_prefix: Filter documents by URL prefix (e.g., https://example.com/blog/)
        url_contains: Filter documents by URL substring (e.g., "tutorial")

    Returns:
        Dictionary with clustering results:
            - clusters: list of topic clusters with name, description, example URLs
            - total_pages: number of pages analyzed
            - cluster_ids: UUIDs of created clusters
            - edges_created: number of document-cluster links created

    Raises:
        ValueError: If no documents found or no filtering criteria provided
    """
    from kurt.config import get_config_or_default
    from kurt.db.database import get_session
    from kurt.db.models import DocumentClusterEdge, TopicCluster
    from kurt.document import list_documents

    # Validate input
    if not url_prefix and not url_contains:
        raise ValueError("Provide either url_prefix or url_contains")

    # Get matching documents (any status - we only need metadata)
    docs = list_documents(
        url_prefix=url_prefix,
        url_contains=url_contains,
        limit=None,
    )

    if not docs:
        raise ValueError("No documents found matching criteria")

    logger.info(f"Computing clusters from {len(docs)} documents")

    # Prepare page metadata for clustering
    pages = []
    for doc in docs:
        page = PageMetadata(
            url=doc.source_url or "",
            title=doc.title,
            description=doc.description,
        )
        pages.append(page)

    # Run DSPy clustering
    config = get_config_or_default()
    lm = dspy.LM(config.INDEXING_LLM_MODEL)
    dspy.configure(lm=lm)

    clusterer = dspy.ChainOfThought(ComputeClusters)
    result = clusterer(pages=pages)
    clusters = result.clusters

    logger.info(f"Identified {len(clusters)} clusters from {len(pages)} pages")

    # Persist clusters to database
    session = get_session()
    cluster_ids = []
    edge_count = 0

    # Create URL to document_id mapping for fast lookup (normalized URLs)
    url_to_doc_id = {normalize_url(doc.source_url): doc.id for doc in docs if doc.source_url}

    for cluster_data in clusters:
        # Create TopicCluster record
        topic_cluster = TopicCluster(
            id=uuid4(),
            name=cluster_data.name,
            description=cluster_data.description,
        )
        session.add(topic_cluster)
        session.flush()  # Get cluster ID before creating edges
        cluster_ids.append(str(topic_cluster.id))

        # Create DocumentClusterEdge records for example URLs
        for example_url in cluster_data.example_urls:
            normalized_url = normalize_url(example_url)
            doc_id = url_to_doc_id.get(normalized_url)
            if doc_id:
                edge = DocumentClusterEdge(
                    id=uuid4(),
                    document_id=doc_id,
                    cluster_id=topic_cluster.id,
                )
                session.add(edge)
                edge_count += 1
            else:
                logger.warning(
                    f"URL not found in documents: {example_url} (normalized: {normalized_url})"
                )

    session.commit()

    logger.info(
        f"Saved {len(cluster_ids)} TopicCluster records and {edge_count} DocumentClusterEdge records"
    )

    # Return result
    return {
        "clusters": [
            {
                "name": c.name,
                "description": c.description,
                "example_urls": c.example_urls,
            }
            for c in clusters
        ],
        "total_pages": len(pages),
        "cluster_ids": cluster_ids,
        "edges_created": edge_count,
    }
