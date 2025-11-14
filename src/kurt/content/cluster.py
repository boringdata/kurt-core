"""Topic clustering logic using DSPy.

Includes both computation logic (LLM-based clustering) and query functions
for retrieving cluster information from the database.
"""

import logging
from typing import Dict, List, Optional
from uuid import uuid4

import dspy
from pydantic import BaseModel, Field

from kurt.db.models import ContentType
from kurt.utils.url_utils import normalize_url_for_matching

logger = logging.getLogger(__name__)

# Generate valid content types from the enum
VALID_CONTENT_TYPES = ", ".join([ct.value for ct in ContentType])


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


class ExistingCluster(BaseModel):
    """An existing cluster for incremental clustering."""

    name: str = Field(description="Name of the existing cluster")
    description: str = Field(description="Description of the existing cluster")


class ContentTypeClassification(BaseModel):
    """Content type classification for a single URL."""

    url: str = Field(description="The URL being classified")
    content_type: str = Field(
        description="Content type: reference, tutorial, guide, blog, product_page, solution_page, homepage, case_study, event, info, landing_page, or other"
    )


# ============================================================================
# DSPy Signature
# ============================================================================


class ComputeClustersAndClassify(dspy.Signature):
    """Analyze web pages to identify topic clusters AND classify content type for each URL.

    You are analyzing a collection of blog posts/web pages to:
    1. Refine/update existing topic clusters OR create new clusters from scratch
    2. Classify the content type of each individual URL

    INCREMENTAL CLUSTERING:
    If existing_clusters are provided, use them as a starting point:
    - KEEP clusters that are still valid and well-defined
    - REFINE cluster names/descriptions if needed to better reflect content
    - SPLIT large clusters that cover multiple distinct topics
    - MERGE similar/overlapping clusters
    - ADD new clusters for new topics not covered by existing clusters
    - REMOVE clusters by not including them in output (if topic no longer exists)

    If no existing_clusters provided, create fresh clusters from scratch.

    CLUSTERING GUIDELINES:
    1. Analyze the URLs, titles, and descriptions to understand themes and subjects
    2. Look for patterns in:
       - URL structures and paths (e.g., /blog/category-name/)
       - Keyword repetition across titles
       - Related concepts and themes
    3. Group related content into distinct topic clusters
    4. Create as many clusters as necessary to capture the diversity of topics
    5. Ensure topics are:
       - Meaningful and specific (not overly broad like "technology" or "business")
       - Mutually exclusive where possible (minimal overlap between clusters)
       - Comprehensive (together they cover the main themes)
       - Balanced in size (avoid one massive cluster and several tiny ones)

    CONTENT TYPE CLASSIFICATION:
    Classify each URL into ONE of these types (use EXACT lowercase names from ContentType enum).

    Types explained:
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

    IMPORTANT: Output should be COMPACT. Use EXACT type names above, nothing else.
    """

    pages: list[PageMetadata] = dspy.InputField(
        description="List of pages with URL, title, and description metadata"
    )
    existing_clusters: list[ExistingCluster] = dspy.InputField(
        description="Existing clusters to refine/update (empty list if starting fresh)", default=[]
    )
    clusters: list[TopicClusterOutput] = dspy.OutputField(
        description="All topic clusters (refined existing + new clusters)"
    )
    classifications: list[ContentTypeClassification] = dspy.OutputField(
        description=f"Content type classification for each URL. Valid types: {VALID_CONTENT_TYPES}"
    )


# ============================================================================
# Business Logic
# ============================================================================

# Use centralized normalize_url function (aliased for backward compatibility)
normalize_url = normalize_url_for_matching


def compute_topic_clusters(
    include_pattern: Optional[str] = None,
    force: bool = False,
    progress_callback=None,
) -> dict:
    """
    Compute topic clusters from a collection of documents.

    Uses only document metadata (URL, title, description) to identify topic clusters.
    Does not require documents to be FETCHED - works with any document status.

    Args:
        include_pattern: Glob pattern to filter documents (e.g., "*docs.dagster.io*", "*/blog/*")
                        If None, clusters ALL documents in database
        force: If False, raises error if documents are already clustered. If True, re-clusters anyway.
        progress_callback: Optional callback function(message: str) to report progress

    Returns:
        Dictionary with clustering results:
            - clusters: list of topic clusters with name, description, example URLs
            - total_pages: number of pages analyzed
            - cluster_ids: UUIDs of created clusters
            - edges_created: number of document-cluster links created

    Raises:
        ValueError: If no documents found or if documents already clustered (without force=True)
    """
    from kurt.config import get_config_or_default
    from kurt.content.document import list_content
    from kurt.db.database import get_session
    from kurt.db.models import DocumentClusterEdge, TopicCluster

    # Get matching documents (any status - we only need metadata)
    if progress_callback:
        progress_callback("Loading documents...")

    docs = list_content(
        include_pattern=include_pattern,
        limit=None,
    )

    if not docs:
        raise ValueError("No documents found matching criteria")

    if progress_callback:
        progress_callback(f"Loaded {len(docs)} documents")

    session = get_session()

    if progress_callback:
        progress_callback("Checking existing clusters...")

    # Fetch existing clusters (for incremental clustering)
    # IMPORTANT: Only fetch clusters that are linked to documents in our filtered set
    existing_clusters = []
    if not force:
        # Get clusters that are linked to documents in our filtered set
        doc_ids = [doc.id for doc in docs]
        existing_cluster_records = (
            session.query(TopicCluster)
            .join(DocumentClusterEdge)
            .filter(DocumentClusterEdge.document_id.in_(doc_ids))
            .distinct()
            .all()
        )

        if existing_cluster_records:
            existing_clusters = [
                ExistingCluster(name=cluster.name, description=cluster.description or "")
                for cluster in existing_cluster_records
            ]
            logger.info(
                f"Found {len(existing_clusters)} existing clusters for filtered documents - will refine/update them"
            )
        else:
            logger.info("No existing clusters found for these documents - creating fresh clusters")
    else:
        logger.info("Force mode: ignoring existing clusters and creating fresh")

    logger.info(f"Computing clusters from {len(docs)} documents")

    # Batch processing: 200 documents per batch for large sets
    batch_size = 200
    all_classifications = []

    if len(docs) > batch_size:
        logger.info(f"Processing {len(docs)} documents in batches of {batch_size}")
        total_batches = (len(docs) + batch_size - 1) // batch_size

        if progress_callback:
            progress_callback(f"Processing in {total_batches} batches...")

        # Process in batches, each batch refines previous clusters
        current_clusters = existing_clusters

        for batch_num, i in enumerate(range(0, len(docs), batch_size), 1):
            batch_docs = docs[i : i + batch_size]
            logger.info(
                f"Processing batch {batch_num}/{total_batches}: {len(batch_docs)} documents"
            )

            if progress_callback:
                progress_callback(
                    f"LLM analyzing batch {batch_num}/{total_batches} ({len(batch_docs)} docs)..."
                )

            # Prepare page metadata for this batch
            batch_pages = []
            for doc in batch_docs:
                page = PageMetadata(
                    url=doc.source_url or "",
                    title=doc.title,
                    description=doc.description,
                )
                batch_pages.append(page)

            # Run DSPy clustering AND classification for this batch
            config = get_config_or_default()
            estimated_tokens = len(batch_pages) * 50 + 2000
            max_tokens = max(8000, min(estimated_tokens, 16000))

            lm = dspy.LM(config.INDEXING_LLM_MODEL, max_tokens=max_tokens)
            dspy.configure(lm=lm)

            clusterer = dspy.ChainOfThought(ComputeClustersAndClassify)
            result = clusterer(pages=batch_pages, existing_clusters=current_clusters)

            # Update clusters for next batch (incremental refinement)
            clusters = result.clusters
            current_clusters = [
                ExistingCluster(name=c.name, description=c.description) for c in clusters
            ]

            # Collect classifications
            all_classifications.extend(result.classifications)

            logger.info(
                f"Batch {batch_num}: {len(clusters)} clusters, {len(result.classifications)} classifications"
            )

            if progress_callback:
                progress_callback(
                    f"Batch {batch_num}/{total_batches} complete → {len(clusters)} clusters identified"
                )

        classifications = all_classifications
        logger.info(
            f"Completed batching: {len(clusters)} final clusters, {len(classifications)} total classifications"
        )

    else:
        # Single batch processing (< 200 documents)
        logger.info(f"Processing {len(docs)} documents in single batch")

        if progress_callback:
            progress_callback(f"LLM analyzing {len(docs)} documents...")

        # Prepare page metadata for clustering
        pages = []
        for doc in docs:
            page = PageMetadata(
                url=doc.source_url or "",
                title=doc.title,
                description=doc.description,
            )
            pages.append(page)

        # Run DSPy clustering AND classification (single LLM call)
        config = get_config_or_default()
        estimated_tokens = len(pages) * 50 + 2000
        max_tokens = max(8000, min(estimated_tokens, 16000))

        lm = dspy.LM(config.INDEXING_LLM_MODEL, max_tokens=max_tokens)
        dspy.configure(lm=lm)

        logger.info(f"Using max_tokens={max_tokens} for {len(pages)} documents")

        clusterer = dspy.ChainOfThought(ComputeClustersAndClassify)
        result = clusterer(pages=pages, existing_clusters=existing_clusters)
        clusters = result.clusters
        classifications = result.classifications

    logger.info(
        f"Identified {len(clusters)} clusters and {len(classifications)} classifications from {len(docs)} documents"
    )
    if existing_clusters:
        logger.info(
            f"Refined from {len(existing_clusters)} existing clusters to {len(clusters)} clusters"
        )

    # Persist clusters to database
    session = get_session()
    cluster_ids = []
    edge_count = 0

    # Create URL to document_id mapping for fast lookup (normalized URLs)
    url_to_doc_id = {normalize_url(doc.source_url): doc.id for doc in docs if doc.source_url}

    # Step 1: Delete old edges for filtered documents, and orphan clusters
    if existing_clusters:
        from sqlalchemy import func

        # Delete edges for documents in our filtered set
        doc_ids = [doc.id for doc in docs]
        deleted_edges = (
            session.query(DocumentClusterEdge)
            .filter(DocumentClusterEdge.document_id.in_(doc_ids))
            .delete(synchronize_session=False)
        )
        session.flush()

        # Delete orphan clusters (clusters with no remaining edges)
        # Find clusters that have NO edges left
        orphan_clusters = (
            session.query(TopicCluster)
            .outerjoin(DocumentClusterEdge)
            .group_by(TopicCluster.id)
            .having(func.count(DocumentClusterEdge.id) == 0)
            .all()
        )

        deleted_cluster_count = 0
        for cluster in orphan_clusters:
            session.delete(cluster)
            deleted_cluster_count += 1

        session.flush()
        logger.info(
            f"Deleted {deleted_edges} edges for filtered documents and {deleted_cluster_count} orphan clusters"
        )

    # Step 2: Create new clusters from LLM output
    if progress_callback:
        progress_callback(f"Creating {len(clusters)} topic clusters...")

    cluster_name_to_id = {}

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
        cluster_name_to_id[cluster_data.name] = topic_cluster.id

    # Persist content type classifications to database
    from kurt.db.models import ContentType, Document

    if progress_callback:
        progress_callback(f"Classifying {len(classifications)} documents...")

    classification_counts = {}
    classified_count = 0

    for classification in classifications:
        normalized_url = normalize_url(classification.url)
        doc_id = url_to_doc_id.get(normalized_url)

        if not doc_id:
            logger.warning(f"URL not found in documents: {classification.url}")
            continue

        # Validate and convert content_type string to enum
        try:
            content_type_value = classification.content_type.lower().strip()

            # Try to map common variations to correct types
            type_mapping = {
                "example": "tutorial",  # LLM sometimes says "example" for tutorials
                "examples": "tutorial",
                "documentation": "reference",
                "doc": "reference",
                "docs": "reference",
                "article": "blog",
                "post": "blog",
            }
            content_type_value = type_mapping.get(content_type_value, content_type_value)

            content_type_enum = ContentType(content_type_value)

            # Fetch document from current session and update
            doc = session.get(Document, doc_id)
            if doc:
                doc.content_type = content_type_enum
                session.add(doc)
                classified_count += 1

                # Track stats
                classification_counts[content_type_value] = (
                    classification_counts.get(content_type_value, 0) + 1
                )

        except ValueError:
            logger.warning(
                f"Invalid content_type '{classification.content_type}' for {classification.url}, using 'other'"
            )
            doc = session.get(Document, doc_id)
            if doc:
                doc.content_type = ContentType.OTHER
                session.add(doc)
                classified_count += 1
                classification_counts["other"] = classification_counts.get("other", 0) + 1

    logger.info(f"Classified {classified_count} documents with content_type")

    # Now link ALL documents to clusters (not just example URLs)
    # We use a second LLM call to assign each document to the best matching cluster
    logger.info(f"Assigning all {len(docs)} documents to clusters...")

    # Batch assign documents to clusters (process in batches to avoid token limits)
    batch_size = 100
    for i in range(0, len(docs), batch_size):
        batch_docs = docs[i : i + batch_size]
        batch_pages = [
            PageMetadata(
                url=doc.source_url or "",
                title=doc.title,
                description=doc.description,
            )
            for doc in batch_docs
        ]

        # Use LLM to assign documents to clusters
        # For now, use a simple heuristic: assign to cluster if URL in example_urls
        # TODO: Use LLM to assign all documents to best matching cluster
        for doc in batch_docs:
            if not doc.source_url:
                continue

            normalized_url = normalize_url(doc.source_url)

            # Find best matching cluster (check example URLs)
            assigned = False
            for cluster_data in clusters:
                for example_url in cluster_data.example_urls:
                    if normalize_url(example_url) == normalized_url:
                        edge = DocumentClusterEdge(
                            id=uuid4(),
                            document_id=doc.id,
                            cluster_id=cluster_name_to_id[cluster_data.name],
                        )
                        session.add(edge)
                        edge_count += 1
                        assigned = True
                        break
                if assigned:
                    break

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
        "total_pages": len(docs),  # Use docs instead of pages (pages may not exist after batching)
        "cluster_ids": cluster_ids,
        "edges_created": edge_count,
        "classifications": {
            "classified": classified_count,
            "content_types": classification_counts,
        },
        "existing_clusters_count": len(existing_clusters),
        "refined": len(existing_clusters) > 0,
    }


# ============================================================================
# Query Functions (formerly in services/clustering_service.py)
# ============================================================================


def get_existing_clusters_summary() -> Dict[str, any]:
    """
    Get summary of existing clusters in the database.

    Returns:
        Dictionary with:
            - count: int (number of clusters)
            - clusters: list of TopicCluster objects

    Example:
        summary = get_existing_clusters_summary()
        print(f"Found {summary['count']} clusters")
        for cluster in summary['clusters']:
            print(f"  - {cluster.name}")
    """
    from kurt.db.database import get_session
    from kurt.db.models import TopicCluster

    session = get_session()

    clusters = session.query(TopicCluster).all()

    return {
        "count": len(clusters),
        "clusters": clusters,
    }


def get_cluster_document_counts(cluster_names: List[str]) -> Dict[str, int]:
    """
    Get document counts for specific clusters by name.

    Args:
        cluster_names: List of cluster names to get counts for

    Returns:
        Dictionary mapping cluster names to document counts

    Example:
        counts = get_cluster_document_counts(["Documentation", "Blog Posts"])
        print(f"Documentation has {counts['Documentation']} docs")
    """
    from kurt.db.database import get_session
    from kurt.db.models import DocumentClusterEdge, TopicCluster

    session = get_session()

    counts = {}

    for cluster_name in cluster_names:
        # Find cluster by name
        cluster_record = (
            session.query(TopicCluster).filter(TopicCluster.name == cluster_name).first()
        )

        if cluster_record:
            # Count documents in cluster (from edges)
            doc_count = (
                session.query(DocumentClusterEdge)
                .filter(DocumentClusterEdge.cluster_id == cluster_record.id)
                .count()
            )
            counts[cluster_name] = doc_count
        else:
            counts[cluster_name] = 0

    return counts


def get_cluster_document_count(cluster_name: str) -> int:
    """
    Get document count for a single cluster by name.

    Args:
        cluster_name: Name of the cluster

    Returns:
        Number of documents in the cluster (0 if cluster not found)

    Example:
        count = get_cluster_document_count("Documentation")
        print(f"Documentation has {count} docs")
    """
    from kurt.db.database import get_session
    from kurt.db.models import DocumentClusterEdge, TopicCluster

    session = get_session()

    # Find cluster by name
    cluster_record = session.query(TopicCluster).filter(TopicCluster.name == cluster_name).first()

    if not cluster_record:
        return 0

    # Count documents in cluster (from edges)
    doc_count = (
        session.query(DocumentClusterEdge)
        .filter(DocumentClusterEdge.cluster_id == cluster_record.id)
        .count()
    )

    return doc_count
