"""Document filtering and resolution utilities.

This module provides document filtering and identifier resolution functionality
that can be used by CLI commands, agents, and other parts of the system.
"""

import os
from dataclasses import dataclass
from typing import Optional

# Re-export for backward compatibility (deprecated - use kurt.db.knowledge_graph instead)
from kurt.db.graph_queries import get_document_links, list_entities_by_type  # noqa: F401


@dataclass
class DocumentFilters:
    """Resolved document filters for querying.

    Attributes:
        ids: Comma-separated document IDs (supports partial UUIDs, URLs, file paths)
        include_pattern: Glob pattern matching source_url or content_path
        in_cluster: Cluster name filter
        with_status: Ingestion status filter (NOT_FETCHED, FETCHED, ERROR)
        with_content_type: Content type filter (tutorial, guide, blog, etc.)
        with_entity: Entity filter in format "EntityType:EntityName" (e.g., "Topic:Python", "Technology:FastAPI")
        with_relationship: Relationship filter in format "Entity1:RelationType:Entity2" (e.g., "Python:USES:FastAPI")
        limit: Maximum number of documents to process/display
        exclude_pattern: Glob pattern for exclusion (used in fetch)
    """

    ids: Optional[str] = None
    include_pattern: Optional[str] = None
    in_cluster: Optional[str] = None
    with_status: Optional[str] = None
    with_content_type: Optional[str] = None
    with_entity: Optional[str] = None
    with_relationship: Optional[str] = None
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
    with_entity: Optional[str] = None,
    with_relationship: Optional[str] = None,
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
        with_entity: Entity filter in format "EntityType:EntityName"
        with_relationship: Relationship filter in format "Entity1:RelationType:Entity2"
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

        # Entity filtering
        filters = resolve_filters(with_entity="Topic:Python")
        # filters.with_entity == "Topic:Python"

        # Relationship filtering
        filters = resolve_filters(with_relationship="Python:USES:FastAPI")
        # filters.with_relationship == "Python:USES:FastAPI"
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
        with_entity=with_entity,
        with_relationship=with_relationship,
        limit=limit,
        exclude_pattern=exclude_pattern,
    )
