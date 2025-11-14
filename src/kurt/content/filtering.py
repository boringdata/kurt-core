"""Document filtering and resolution utilities.

This module provides document filtering and identifier resolution functionality
that can be used by CLI commands, agents, and other parts of the system.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DocumentFilters:
    """Resolved document filters for querying.

    Attributes:
        ids: Comma-separated document IDs (supports partial UUIDs, URLs, file paths)
        include_pattern: Glob pattern matching source_url or content_path
        in_cluster: Cluster name filter
        with_status: Ingestion status filter (NOT_FETCHED, FETCHED, ERROR)
        with_content_type: Content type filter (tutorial, guide, blog, etc.)
        limit: Maximum number of documents to process/display
        exclude_pattern: Glob pattern for exclusion (used in fetch)
    """

    ids: Optional[str] = None
    include_pattern: Optional[str] = None
    in_cluster: Optional[str] = None
    with_status: Optional[str] = None
    with_content_type: Optional[str] = None
    limit: Optional[int] = None
    exclude_pattern: Optional[str] = None


def resolve_identifier_to_doc_id(identifier: str) -> str:
    """
    Resolve an identifier (ID, URL, or file path) to a document ID.

    Supports:
    - Full UUIDs: "550e8400-e29b-41d4-a716-446655440000"
    - Partial UUIDs: "550e8400" (minimum 8 characters)
    - URLs: "https://example.com/article"
    - File paths: "./docs/article.md"

    Args:
        identifier: Document ID, URL, or file path

    Returns:
        Document ID as string (full UUID)

    Raises:
        ValueError: If identifier cannot be resolved or is ambiguous

    Example:
        doc_id = resolve_identifier_to_doc_id("550e8400")
        doc_id = resolve_identifier_to_doc_id("https://example.com/article")
        doc_id = resolve_identifier_to_doc_id("./docs/article.md")
    """
    from kurt.content.document import get_document, list_documents

    # Check if it's a URL
    if identifier.startswith(("http://", "https://")):
        # Look up document by URL
        matching_docs = [d for d in list_documents() if d.source_url == identifier]
        if not matching_docs:
            raise ValueError(f"Document not found: {identifier}")
        return str(matching_docs[0].id)

    # Check if it's a file path
    elif (
        os.path.exists(identifier) or identifier.startswith(("./", "../", "/")) or "/" in identifier
    ):
        # Look up document by content_path
        # Try both absolute and relative path matching
        abs_path = os.path.abspath(identifier)

        # Get all documents
        all_docs = list_documents()

        # Try multiple matching strategies
        matching_docs = []

        # Strategy 1: Exact match on content_path
        for d in all_docs:
            if d.content_path == identifier:
                matching_docs.append(d)

        # Strategy 2: Absolute path match
        if not matching_docs:
            for d in all_docs:
                if d.content_path and os.path.abspath(d.content_path) == abs_path:
                    matching_docs.append(d)

        # Strategy 3: Relative path from sources/ directory (common case)
        if not matching_docs and identifier.startswith("sources/"):
            rel_path = identifier[8:]  # Remove "sources/" prefix
            for d in all_docs:
                if d.content_path and d.content_path == rel_path:
                    matching_docs.append(d)

        # Strategy 4: Suffix match (last resort)
        if not matching_docs:
            for d in all_docs:
                if d.content_path and d.content_path.endswith(identifier):
                    matching_docs.append(d)

        if not matching_docs:
            raise ValueError(
                f"Document not found for file: {identifier}\nTip: Use 'kurt content list' to see available documents"
            )

        if len(matching_docs) > 1:
            raise ValueError(
                f"Ambiguous file path: {identifier} matches {len(matching_docs)} documents. "
                f"Use document ID instead."
            )

        return str(matching_docs[0].id)

    # Assume it's a document ID (full or partial)
    else:
        # get_document already supports partial UUIDs
        doc = get_document(identifier)
        return str(doc.id)


def resolve_ids_to_uuids(ids_str: str) -> list[str]:
    """
    Resolve comma-separated identifiers to full UUIDs.

    Each identifier can be:
    - Full UUID
    - Partial UUID (minimum 8 characters)
    - URL (resolves to document with that URL)
    - File path (resolves to document with that content_path)

    Args:
        ids_str: Comma-separated list of identifiers

    Returns:
        List of full UUIDs as strings

    Raises:
        ValueError: If any identifier cannot be resolved

    Example:
        uuids = resolve_ids_to_uuids("550e8400,https://example.com/article,docs/file.md")
    """
    uuids = []
    errors = []

    for id_str in ids_str.split(","):
        id_str = id_str.strip()
        if not id_str:
            continue

        try:
            doc_id = resolve_identifier_to_doc_id(id_str)
            uuids.append(doc_id)
        except ValueError as e:
            errors.append(f"{id_str}: {e}")

    if errors:
        raise ValueError("Failed to resolve identifiers:\n" + "\n".join(errors))

    return uuids


def resolve_filters(
    identifier: Optional[str] = None,
    ids: Optional[str] = None,
    include_pattern: Optional[str] = None,
    in_cluster: Optional[str] = None,
    with_status: Optional[str] = None,
    with_content_type: Optional[str] = None,
    limit: Optional[int] = None,
    exclude_pattern: Optional[str] = None,
) -> DocumentFilters:
    """
    Resolve and merge filters, especially handling positional IDENTIFIER.

    The positional IDENTIFIER argument (if provided) is resolved to a document ID
    and merged into the ids filter. This provides a clean API where:
    - `kurt index DOC_ID` is shorthand for `kurt index --ids DOC_ID`
    - `kurt index DOC_ID --ids "ID1,ID2"` becomes `--ids "DOC_ID,ID1,ID2"`

    Args:
        identifier: Positional identifier (doc ID, URL, or file path)
        ids: Comma-separated document IDs
        include_pattern: Glob pattern for inclusion
        in_cluster: Cluster name filter
        with_status: Ingestion status filter
        with_content_type: Content type filter
        limit: Maximum number of documents
        exclude_pattern: Glob pattern for exclusion

    Returns:
        DocumentFilters instance with resolved and merged filters

    Example:
        # Simple case
        filters = resolve_filters(identifier="44ea066e")
        # filters.ids == "44ea066e-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

        # Merging case
        filters = resolve_filters(
            identifier="44ea066e",
            ids="550e8400,a73af781",
            include_pattern="*/docs/*"
        )
        # filters.ids == "44ea066e-xxxx-xxxx-xxxx-xxxxxxxxxxxx,550e8400,a73af781"
        # filters.include_pattern == "*/docs/*"
    """
    # If identifier provided, resolve and merge into ids
    resolved_ids = ids
    if identifier:
        try:
            doc_id = resolve_identifier_to_doc_id(identifier)
            if resolved_ids:
                # Merge: identifier comes first
                resolved_ids = f"{doc_id},{resolved_ids}"
            else:
                resolved_ids = doc_id
        except ValueError as e:
            # Let the caller handle the error
            raise ValueError(f"Failed to resolve identifier '{identifier}': {e}")

    return DocumentFilters(
        ids=resolved_ids,
        include_pattern=include_pattern,
        in_cluster=in_cluster,
        with_status=with_status,
        with_content_type=with_content_type,
        limit=limit,
        exclude_pattern=exclude_pattern,
    )


# ============================================================================
# Topic and Technology Discovery Services
# ============================================================================


def list_topics(
    min_docs: int = 1,
    include_pattern: Optional[str] = None,
    source: str = "metadata",
) -> list[dict[str, any]]:
    """
    List all unique topics from indexed documents with document counts.

    Aggregates topics from two sources:
    1. Document metadata (primary_topics field)
    2. Knowledge graph entities (entity_type='Topic')

    Args:
        min_docs: Minimum number of documents a topic must appear in (default: 1)
        include_pattern: Optional glob pattern to filter documents (e.g., "*/docs/*")
        source: Data source - "metadata" (fast), "graph" (comprehensive), or "both"

    Returns:
        List of dictionaries with topic information, sorted by document count descending:
            - topic: str (topic name)
            - doc_count: int (number of documents mentioning this topic)
            - source: str ("metadata", "graph", or "both")

    Example:
        # Get all topics from metadata
        topics = list_topics()

        # Get common topics (in 5+ documents)
        topics = list_topics(min_docs=5)

        # Get topics from knowledge graph
        topics = list_topics(source="graph")

        # Get comprehensive list (metadata + graph)
        topics = list_topics(source="both")
    """
    from collections import Counter
    from fnmatch import fnmatch

    from sqlmodel import select

    from kurt.db.database import get_session
    from kurt.db.models import Document, DocumentEntity, Entity, IngestionStatus

    session = get_session()
    topic_counts = Counter()
    topic_sources = {}  # Track which source each topic came from

    # Source 1: Document metadata (primary_topics)
    if source in ("metadata", "both"):
        stmt = select(Document).where(Document.ingestion_status == IngestionStatus.FETCHED)
        documents = session.exec(stmt).all()

        # Filter by pattern if provided
        if include_pattern:
            documents = [
                d
                for d in documents
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            ]

        # Count topic occurrences from metadata
        for doc in documents:
            if doc.primary_topics:
                for topic in doc.primary_topics:
                    topic_counts[topic] += 1
                    if topic not in topic_sources:
                        topic_sources[topic] = "metadata"

    # Source 2: Knowledge graph entities
    if source in ("graph", "both"):
        # Get all Topic entities and their document mentions
        stmt = (
            select(Entity.name, Entity.canonical_name, DocumentEntity.document_id)
            .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
            .where(Entity.entity_type == "Topic")
        )
        entity_mentions = session.exec(stmt).all()

        # Build doc count per topic
        graph_topic_docs = {}
        for entity_name, canonical_name, doc_id in entity_mentions:
            topic_name = canonical_name or entity_name
            if topic_name not in graph_topic_docs:
                graph_topic_docs[topic_name] = set()
            graph_topic_docs[topic_name].add(doc_id)

        # Filter by pattern if needed
        if include_pattern:
            doc_stmt = select(Document).where(Document.ingestion_status == IngestionStatus.FETCHED)
            matching_docs = session.exec(doc_stmt).all()
            matching_doc_ids = {
                str(d.id)
                for d in matching_docs
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            }

            # Filter topic doc sets
            for topic_name in graph_topic_docs:
                graph_topic_docs[topic_name] &= matching_doc_ids

        # Add graph counts
        for topic_name, doc_ids in graph_topic_docs.items():
            count = len(doc_ids)
            if count > 0:
                if topic_name in topic_counts:
                    # Combine with metadata count (take max to avoid double-counting)
                    topic_counts[topic_name] = max(topic_counts[topic_name], count)
                    topic_sources[topic_name] = "both"
                else:
                    topic_counts[topic_name] = count
                    topic_sources[topic_name] = "graph"

    # Filter by minimum document count
    filtered_topics = [(topic, count) for topic, count in topic_counts.items() if count >= min_docs]

    # Sort by count descending, then alphabetically
    filtered_topics.sort(key=lambda x: (-x[1], x[0]))

    # Format output
    return [
        {"topic": topic, "doc_count": count, "source": topic_sources.get(topic, "unknown")}
        for topic, count in filtered_topics
    ]


def list_technologies(
    min_docs: int = 1,
    include_pattern: Optional[str] = None,
    source: str = "metadata",
) -> list[dict[str, any]]:
    """
    List all unique technologies from indexed documents with document counts.

    Aggregates technologies from two sources:
    1. Document metadata (tools_technologies field)
    2. Knowledge graph entities (entity_type='Technology' or 'Tool')

    Args:
        min_docs: Minimum number of documents a technology must appear in (default: 1)
        include_pattern: Optional glob pattern to filter documents (e.g., "*/docs/*")
        source: Data source - "metadata" (fast), "graph" (comprehensive), or "both"

    Returns:
        List of dictionaries with technology information, sorted by document count descending:
            - technology: str (technology name)
            - doc_count: int (number of documents mentioning this technology)
            - source: str ("metadata", "graph", or "both")

    Example:
        # Get all technologies from metadata
        techs = list_technologies()

        # Get common technologies (in 5+ documents)
        techs = list_technologies(min_docs=5)

        # Get technologies from knowledge graph
        techs = list_technologies(source="graph")

        # Get comprehensive list (metadata + graph)
        techs = list_technologies(source="both")
    """
    from collections import Counter
    from fnmatch import fnmatch

    from sqlmodel import select

    from kurt.db.database import get_session
    from kurt.db.models import Document, DocumentEntity, Entity, IngestionStatus

    session = get_session()
    tech_counts = Counter()
    tech_sources = {}  # Track which source each tech came from

    # Source 1: Document metadata (tools_technologies)
    if source in ("metadata", "both"):
        stmt = select(Document).where(Document.ingestion_status == IngestionStatus.FETCHED)
        documents = session.exec(stmt).all()

        # Filter by pattern if provided
        if include_pattern:
            documents = [
                d
                for d in documents
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            ]

        # Count technology occurrences from metadata
        for doc in documents:
            if doc.tools_technologies:
                for tech in doc.tools_technologies:
                    tech_counts[tech] += 1
                    if tech not in tech_sources:
                        tech_sources[tech] = "metadata"

    # Source 2: Knowledge graph entities
    if source in ("graph", "both"):
        # Get all Technology/Tool entities and their document mentions
        stmt = (
            select(Entity.name, Entity.canonical_name, DocumentEntity.document_id)
            .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
            .where(Entity.entity_type.in_(["Technology", "Tool", "Product"]))
        )
        entity_mentions = session.exec(stmt).all()

        # Build doc count per technology
        graph_tech_docs = {}
        for entity_name, canonical_name, doc_id in entity_mentions:
            tech_name = canonical_name or entity_name
            if tech_name not in graph_tech_docs:
                graph_tech_docs[tech_name] = set()
            graph_tech_docs[tech_name].add(doc_id)

        # Filter by pattern if needed
        if include_pattern:
            doc_stmt = select(Document).where(Document.ingestion_status == IngestionStatus.FETCHED)
            matching_docs = session.exec(doc_stmt).all()
            matching_doc_ids = {
                str(d.id)
                for d in matching_docs
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            }

            # Filter tech doc sets
            for tech_name in graph_tech_docs:
                graph_tech_docs[tech_name] &= matching_doc_ids

        # Add graph counts
        for tech_name, doc_ids in graph_tech_docs.items():
            count = len(doc_ids)
            if count > 0:
                if tech_name in tech_counts:
                    # Combine with metadata count (take max to avoid double-counting)
                    tech_counts[tech_name] = max(tech_counts[tech_name], count)
                    tech_sources[tech_name] = "both"
                else:
                    tech_counts[tech_name] = count
                    tech_sources[tech_name] = "graph"

    # Filter by minimum document count
    filtered_techs = [(tech, count) for tech, count in tech_counts.items() if count >= min_docs]

    # Sort by count descending, then alphabetically
    filtered_techs.sort(key=lambda x: (-x[1], x[0]))

    # Format output
    return [
        {"technology": tech, "doc_count": count, "source": tech_sources.get(tech, "unknown")}
        for tech, count in filtered_techs
    ]


def get_document_links(document_id: str, direction: str = "outbound") -> list[dict]:
    """
    Get links from or to a document.

    Args:
        document_id: Document ID (UUID string or partial UUID)
        direction: Link direction - "outbound" (links FROM doc) or "inbound" (links TO doc)

    Returns:
        List of dictionaries with link information:
            - source_id: UUID of source document
            - source_title: Title of source document
            - target_id: UUID of target document
            - target_title: Title of target document
            - anchor_text: Link anchor text (or None)

    Raises:
        ValueError: If document not found or direction is invalid

    Example:
        # Get outbound links (links FROM this document)
        links = get_document_links("550e8400", direction="outbound")

        # Get inbound links (links TO this document)
        links = get_document_links("550e8400", direction="inbound")
    """
    from sqlmodel import select

    from kurt.content.document import get_document
    from kurt.db.database import get_session
    from kurt.db.models import Document, DocumentLink

    # Validate direction
    if direction not in ("outbound", "inbound"):
        raise ValueError(f"Invalid direction: {direction}. Must be 'outbound' or 'inbound'")

    # Resolve document ID (supports partial UUIDs)
    doc = get_document(document_id)
    doc_uuid = doc.id

    session = get_session()

    # Query based on direction
    if direction == "outbound":
        # Links FROM this document
        stmt = (
            select(DocumentLink, Document)
            .where(DocumentLink.source_document_id == doc_uuid)
            .join(Document, DocumentLink.target_document_id == Document.id)
        )
    else:  # inbound
        # Links TO this document
        stmt = (
            select(DocumentLink, Document)
            .where(DocumentLink.target_document_id == doc_uuid)
            .join(Document, DocumentLink.source_document_id == Document.id)
        )

    results = session.exec(stmt).all()

    # Format results
    links = []
    for link, related_doc in results:
        if direction == "outbound":
            # related_doc is the target
            links.append(
                {
                    "source_id": str(link.source_document_id),
                    "source_title": doc.title,
                    "target_id": str(link.target_document_id),
                    "target_title": related_doc.title,
                    "anchor_text": link.anchor_text,
                }
            )
        else:  # inbound
            # related_doc is the source
            links.append(
                {
                    "source_id": str(link.source_document_id),
                    "source_title": related_doc.title,
                    "target_id": str(link.target_document_id),
                    "target_title": doc.title,
                    "anchor_text": link.anchor_text,
                }
            )

    return links
