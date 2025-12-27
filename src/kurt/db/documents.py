"""
Document utility functions for Kurt.

These functions provide CRUD operations for documents:
- add_document: Create new document record
- resolve_or_create_document: Find or create document by ID/URL
- get_document: Get document by ID
- list_documents: List all documents with filtering
- load_document_content: Load document content from filesystem
- save_document_content_and_metadata: Update document content and metadata
- delete_document: Delete document by ID
- get_document_stats: Get statistics about documents
- get_document_status: Get document status derived from staging tables
- get_document_with_metadata: Get document with full metadata from staging tables

Status and metadata are derived from staging tables:
- Status: landing_discovery, landing_fetch, staging_section_extractions
- Metadata: staging_topic_clustering, staging_section_extractions

These can be used directly by agents or wrapped by CLI commands.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlmodel import select

from kurt.config import load_config
from kurt.db.database import get_session
from kurt.db.models import Document, PageAnalytics, SourceType
from kurt.integrations.analytics.utils import normalize_url_for_analytics

# ============================================================================
# Staging Table Helpers
# ============================================================================


def _table_exists(session, table_name: str) -> bool:
    """Check if a table exists in the database.

    This is used to handle queries on staging tables that may not exist yet
    (e.g., landing_fetch, landing_discovery, staging_section_extractions).
    These tables are created dynamically when pipeline models run.
    """
    result = session.execute(
        text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    )
    return result.fetchone() is not None


def _get_status_subquery(session, status_upper: str) -> str | None:
    """Build a status filter subquery, handling missing staging tables gracefully.

    Returns a SQL WHERE clause string, or None if the status cannot be satisfied
    (e.g., filtering for FETCHED when landing_fetch table doesn't exist).

    Status hierarchy: INDEXED > FETCHED > DISCOVERED > NOT_FETCHED

    Note: Staging tables store UUIDs WITHOUT hyphens (from pandas reading SQLite),
    so we use REPLACE(CAST(id AS TEXT), '-', '') to compare.
    """
    has_landing_fetch = _table_exists(session, "landing_fetch")
    has_landing_discovery = _table_exists(session, "landing_discovery")
    has_section_extractions = _table_exists(session, "staging_section_extractions")

    # Helper: converts Document.id to format matching staging tables (no hyphens)
    doc_id_expr = "REPLACE(CAST(id AS TEXT), '-', '')"

    if status_upper == "INDEXED":
        if not has_section_extractions:
            return "1=0"  # No documents can be INDEXED if table doesn't exist
        return f"{doc_id_expr} IN (SELECT document_id FROM staging_section_extractions)"

    elif status_upper == "FETCHED":
        if not has_landing_fetch:
            return "1=0"  # No documents can be FETCHED if table doesn't exist
        # Has records in landing_fetch with status=FETCHED, but NOT indexed
        base = f"{doc_id_expr} IN (SELECT document_id FROM landing_fetch WHERE status = 'FETCHED')"
        if has_section_extractions:
            return f"{base} AND {doc_id_expr} NOT IN (SELECT document_id FROM staging_section_extractions)"
        return base

    elif status_upper == "DISCOVERED":
        if not has_landing_discovery:
            return "1=0"  # No documents can be DISCOVERED if table doesn't exist
        base = f"{doc_id_expr} IN (SELECT document_id FROM landing_discovery)"
        if has_landing_fetch:
            return f"{base} AND {doc_id_expr} NOT IN (SELECT document_id FROM landing_fetch WHERE status = 'FETCHED')"
        return base

    elif status_upper == "NOT_FETCHED":
        if not has_landing_fetch:
            return "1=1"  # All documents are NOT_FETCHED if no landing_fetch table
        return (
            f"{doc_id_expr} NOT IN (SELECT document_id FROM landing_fetch WHERE status = 'FETCHED')"
        )

    elif status_upper == "ERROR":
        parts = []
        if has_landing_fetch:
            parts.append("SELECT document_id FROM landing_fetch WHERE error IS NOT NULL")
        if has_landing_discovery:
            parts.append("SELECT document_id FROM landing_discovery WHERE error IS NOT NULL")
        if not parts:
            return "1=0"  # No error records possible if no staging tables
        return f"{doc_id_expr} IN ({' UNION '.join(parts)})"

    return None  # Unknown status


# ============================================================================
# Document Creation (CRUD - Create)
# ============================================================================


def add_documents_for_urls(url_list: list[str]) -> tuple[list[Document], int]:
    """
    Create document records for URLs (auto-creates if don't exist).

    Basic CRUD operation - no discovery metadata.
    For discovery operations, use map-specific functions in content/map/.

    Args:
        url_list: List of URLs

    Returns:
        Tuple of (list of Document objects, count of newly created documents)

    Example:
        >>> docs, new_count = add_documents_for_urls(["https://example.com/page1", "https://example.com/page2"])
        >>> # Returns: ([Document(...), Document(...)], 2)
    """
    session = get_session()

    # Check which URLs already exist (using IN for efficiency)
    from sqlmodel import select

    existing_urls_stmt = select(Document).where(Document.source_url.in_(url_list))
    existing_docs = list(session.exec(existing_urls_stmt).all())
    existing_urls = {doc.source_url for doc in existing_docs}

    # Create documents for new URLs
    new_urls = [url for url in url_list if url not in existing_urls]
    new_count = 0

    if new_urls:
        for url in new_urls:
            add_document(url)
        session.commit()
        new_count = len(new_urls)

    # Return all documents (existing + newly created)
    all_docs_stmt = select(Document).where(Document.source_url.in_(url_list))
    all_docs = list(session.exec(all_docs_stmt).all())

    return all_docs, new_count


def add_documents_for_files(
    file_list: list[str],
) -> tuple[list[Document], int, list[str], list[str]]:
    """
    Create document records for local files.

    Files outside sources directory are copied to sources/local/.
    Documents are marked as FETCHED since content already exists.

    Args:
        file_list: List of file paths

    Returns:
        Tuple of (list of Document objects, count of newly created, list of errors, list of copied file messages)

    Example:
        >>> docs, new_count, errors, copied = add_documents_for_files(["./docs/page1.md", "./docs/page2.md"])
        >>> # Returns: ([Document(...), Document(...)], 2, [], [])
    """
    from pathlib import Path

    from sqlmodel import select

    session = get_session()
    config = load_config()
    source_base = config.get_absolute_sources_path()

    created_docs = []
    errors = []
    copied_files = []

    for file_path_str in file_list:
        file_path = Path(file_path_str).resolve()

        # Validate file exists
        if not file_path.exists():
            errors.append(f"File not found: {file_path_str}")
            continue

        if not file_path.is_file():
            errors.append(f"Not a file: {file_path_str}")
            continue

        # Determine content path relative to sources directory
        try:
            relative_path = file_path.relative_to(source_base)
            content_path_str = str(relative_path)
        except ValueError:
            # File is outside sources directory - copy it there
            file_name = file_path.name
            dest_path = source_base / "local" / file_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            import shutil

            shutil.copy2(file_path, dest_path)

            relative_path = dest_path.relative_to(source_base)
            content_path_str = str(relative_path)
            copied_files.append(f"Copied {file_path.name} to sources/local/")

        # Check if document exists
        existing_stmt = select(Document).where(Document.content_path == content_path_str)
        existing_doc = session.exec(existing_stmt).first()

        if existing_doc:
            created_docs.append(existing_doc)
            continue

        # Create new document
        title = file_path.stem

        # Read content to extract title from first line if it's a markdown heading
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                first_line = content.split("\n")[0].strip()
                if first_line.startswith("#"):
                    title = first_line.lstrip("#").strip()
        except Exception:
            pass

        new_doc = Document(
            title=title,
            source_type=SourceType.FILE_UPLOAD,
            content_path=content_path_str,
            # Note: Status is now derived from staging tables via get_document_status()
            # For local files, content is already available so they're effectively "fetched"
        )

        session.add(new_doc)
        created_docs.append(new_doc)

    # Commit all new documents
    if created_docs:
        session.commit()
        # Refresh to get IDs
        for doc in created_docs:
            session.refresh(doc)

    # Count newly created docs (local files have content, so count all with IDs)
    new_count = len([d for d in created_docs if d.id])

    return created_docs, new_count, errors, copied_files


def add_document(url: str, title: str = None) -> UUID:
    """
    Create document record with NOT_FETCHED status.

    If document with URL already exists, returns existing document ID.

    Args:
        url: Source URL
        title: Optional title (defaults to last path segment)

    Returns:
        UUID of created or existing document

    Example:
        doc_id = add_document("https://example.com/page1", "Page 1")
        # Returns: UUID('550e8400-e29b-41d4-a716-446655440000')
    """
    session = get_session()

    # Check if document already exists
    stmt = select(Document).where(Document.source_url == url)
    existing_doc = session.exec(stmt).first()

    if existing_doc:
        return existing_doc.id

    # Generate title from URL if not provided
    if not title:
        title = url.rstrip("/").split("/")[-1] or url

    # Create document
    # Note: Status is now derived from staging tables via get_document_status()
    # New documents without landing_fetch records are considered NOT_FETCHED
    doc = Document(
        title=title,
        source_type=SourceType.URL,
        source_url=url,
    )

    session.add(doc)
    session.commit()
    session.refresh(doc)

    return doc.id


def resolve_or_create_document(identifier: str | UUID) -> dict:
    """
    Find existing document or create new one.

    Fast database operation - returns lightweight dict to minimize checkpoint data.

    Args:
        identifier: Document UUID or source URL

    Returns:
        dict with keys:
            - id: str (document UUID)
            - source_url: str
            - cms_platform: str | None
            - cms_instance: str | None
            - cms_document_id: str | None

    Example:
        >>> doc_info = resolve_or_create_document("https://example.com/page1")
        >>> # Returns: {'id': 'uuid...', 'source_url': 'https://...', ...}
    """
    session = get_session()

    # Try UUID lookup
    try:
        doc_id = UUID(identifier) if not isinstance(identifier, UUID) else identifier
        doc = session.get(Document, doc_id)
        if doc:
            return {
                "id": str(doc.id),
                "source_url": doc.source_url,
                "cms_platform": doc.cms_platform,
                "cms_instance": doc.cms_instance,
                "cms_document_id": doc.cms_document_id,
            }
    except (ValueError, AttributeError):
        pass

    # Try URL lookup
    stmt = select(Document).where(Document.source_url == str(identifier))
    doc = session.exec(stmt).first()

    if not doc:
        # Create new document
        doc_id = add_document(str(identifier))
        doc = session.get(Document, doc_id)

    return {
        "id": str(doc.id),
        "source_url": doc.source_url,
        "cms_platform": doc.cms_platform,
        "cms_instance": doc.cms_instance,
        "cms_document_id": doc.cms_document_id,
    }


# ============================================================================
# Document Retrieval (CRUD - Read)
# ============================================================================


def list_documents(
    status: Optional[str] = None,
    url_prefix: Optional[str] = None,
    url_contains: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    # Analytics filters
    with_analytics: bool = False,
    pageviews_30d_min: Optional[int] = None,
    pageviews_30d_max: Optional[int] = None,
    pageviews_trend: Optional[str] = None,
    order_by: Optional[str] = None,
) -> list[Document]:
    """
    List all documents with optional filtering.

    Note: Status is now derived from staging tables, not stored on Document.
    Use get_document_status() for individual document status.

    Args:
        status: Filter by derived status (NOT_FETCHED, FETCHED, INDEXED, ERROR)
                Uses subqueries on staging tables for efficient filtering.
        url_prefix: Filter by URL prefix (e.g., "https://example.com")
        url_contains: Filter by URL substring (e.g., "blog")
        limit: Maximum number of documents to return
        offset: Number of documents to skip (for pagination)
        with_analytics: Include analytics data in results (LEFT JOIN on normalized URL)
        pageviews_30d_min: Filter by minimum pageviews (last 30 days)
        pageviews_30d_max: Filter by maximum pageviews (last 30 days)
        pageviews_trend: Filter by trend ("increasing", "stable", "decreasing")
        order_by: Sort results by field (created_at, pageviews_30d, pageviews_60d, trend_percentage)

    Returns:
        List of Document objects (with analytics data attached as 'analytics' attribute if with_analytics=True)

    Example:
        # List all documents
        docs = list_documents()

        # List only fetched documents
        docs = list_documents(status="FETCHED")

        # List documents from specific domain
        docs = list_documents(url_prefix="https://example.com")

        # List documents with "blog" in URL
        docs = list_documents(url_contains="blog")

        # Combine filters
        docs = list_documents(status="FETCHED", url_prefix="https://example.com")

        # List first 10 documents
        docs = list_documents(limit=10)

        # Pagination: skip first 10, get next 10
        docs = list_documents(limit=10, offset=10)

        # Filter by analytics (high-traffic pages)
        docs = list_documents(with_analytics=True, pageviews_30d_min=500, order_by="pageviews_30d")

        # Filter by traffic trend
        docs = list_documents(with_analytics=True, pageviews_trend="decreasing")
    """
    session = get_session()

    # Determine if we need analytics
    needs_analytics = (
        with_analytics
        or pageviews_30d_min is not None
        or pageviews_30d_max is not None
        or pageviews_trend is not None
        or (order_by and order_by in ["pageviews_30d", "pageviews_60d", "trend_percentage"])
    )

    # Build base document query
    stmt = select(Document)

    # Apply status filter using helper that handles missing staging tables
    if status:
        status_upper = status.upper() if isinstance(status, str) else status.value
        status_subquery = _get_status_subquery(session, status_upper)
        if status_subquery:
            stmt = stmt.where(text(status_subquery))
    if url_prefix:
        stmt = stmt.where(Document.source_url.startswith(url_prefix))
    if url_contains:
        stmt = stmt.where(Document.source_url.contains(url_contains))

    # Execute base query to get documents
    documents = session.exec(stmt).all()
    documents = list(documents)

    # If analytics needed, fetch and merge
    if needs_analytics and documents:
        # Build URL -> PageAnalytics map
        analytics_map = {}

        # Get all PageAnalytics records that might match these documents
        # We'll fetch all analytics and match in Python since JOIN on computed field is complex
        all_analytics = session.exec(select(PageAnalytics)).all()
        for analytics in all_analytics:
            analytics_map[analytics.url] = analytics

        # Match documents with analytics by normalized URL
        matched_docs = []
        for doc in documents:
            if doc.source_url:
                normalized_url = normalize_url_for_analytics(doc.source_url)
                analytics = analytics_map.get(normalized_url)

                # Apply analytics filters
                if pageviews_30d_min is not None and (
                    not analytics or analytics.pageviews_30d < pageviews_30d_min
                ):
                    continue
                if pageviews_30d_max is not None and (
                    not analytics or analytics.pageviews_30d > pageviews_30d_max
                ):
                    continue
                if pageviews_trend and (
                    not analytics or analytics.pageviews_trend != pageviews_trend
                ):
                    continue

                # Attach analytics data to document
                if with_analytics:
                    # Store as dict to match command layer expectations
                    # Use __dict__ to bypass Pydantic validation for SQLModel tables
                    if analytics:
                        doc.__dict__["analytics"] = {
                            "pageviews_30d": analytics.pageviews_30d,
                            "pageviews_60d": analytics.pageviews_60d,
                            "pageviews_previous_30d": analytics.pageviews_previous_30d,
                            "unique_visitors_30d": analytics.unique_visitors_30d,
                            "unique_visitors_60d": analytics.unique_visitors_60d,
                            "pageviews_trend": analytics.pageviews_trend,
                            "trend_percentage": analytics.trend_percentage,
                            "bounce_rate": analytics.bounce_rate,
                            "avg_session_duration_seconds": analytics.avg_session_duration_seconds,
                        }
                    else:
                        doc.__dict__["analytics"] = None

                matched_docs.append((doc, analytics))
            else:
                # No source_url, can't match analytics
                if with_analytics:
                    doc.__dict__["analytics"] = None
                matched_docs.append((doc, None))

        # Apply ordering
        if order_by:
            if order_by == "pageviews_30d":
                matched_docs.sort(key=lambda x: x[1].pageviews_30d if x[1] else 0, reverse=True)
            elif order_by == "pageviews_60d":
                matched_docs.sort(key=lambda x: x[1].pageviews_60d if x[1] else 0, reverse=True)
            elif order_by == "trend_percentage":
                matched_docs.sort(
                    key=lambda x: x[1].trend_percentage
                    if x[1] and x[1].trend_percentage
                    else float("-inf"),
                    reverse=True,
                )
            elif order_by == "created_at":
                matched_docs.sort(key=lambda x: x[0].created_at, reverse=True)
        else:
            # Default ordering by created_at
            matched_docs.sort(key=lambda x: x[0].created_at, reverse=True)

        # Extract just documents from tuples
        documents = [doc for doc, _ in matched_docs]
    else:
        # No analytics needed, just apply default ordering
        if order_by == "created_at" or not order_by:
            documents.sort(key=lambda x: x.created_at, reverse=True)

    # Apply pagination
    if offset or limit:
        start = offset
        end = offset + limit if limit else None
        documents = documents[start:end]

    return documents


def get_document(document_id: str) -> Document:
    """
    Get document by ID (supports partial UUIDs).

    Args:
        document_id: Document UUID as string (full or partial, minimum 8 chars)

    Returns:
        Document object

    Raises:
        ValueError: If document not found or ID is ambiguous

    Example:
        doc = get_document("550e8400-e29b-41d4-a716-446655440000")
        doc = get_document("550e8400")  # Partial UUID also works
        print(doc.title)
        print(doc.description)
    """
    session = get_session()

    # Try full UUID first
    try:
        doc_uuid = UUID(document_id)
        doc = session.get(Document, doc_uuid)

        if not doc:
            raise ValueError(f"Document not found: {document_id}")
    except ValueError:
        # Try partial UUID match
        if len(document_id) < 8:
            raise ValueError(f"Document ID too short (minimum 8 characters): {document_id}")

        # Search for documents where ID starts with the partial UUID
        # Convert UUID to string format without hyphens for matching
        stmt = select(Document)
        docs = session.exec(stmt).all()

        # Filter by partial match (comparing without hyphens)
        partial_lower = document_id.lower().replace("-", "")
        matches = [d for d in docs if str(d.id).replace("-", "").startswith(partial_lower)]

        if len(matches) == 0:
            raise ValueError(f"Document not found: {document_id}")
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous document ID '{document_id}' matches {len(matches)} documents. "
                f"Please provide more characters."
            )

        doc = matches[0]

    # Return Document object
    return doc


def load_document_content(doc: Document, strip_frontmatter: bool = True) -> str:
    """
    Load document content from filesystem.

    Args:
        doc: Document object with content_path
        strip_frontmatter: If True (default), removes YAML frontmatter from content

    Returns:
        Document content as string (with frontmatter stripped by default)

    Raises:
        ValueError: If content_path is missing or file doesn't exist

    Example:
        doc = get_document("550e8400")
        content = load_document_content(doc)  # Strips frontmatter
        content_with_metadata = load_document_content(doc, strip_frontmatter=False)
    """
    if not doc.content_path:
        raise ValueError(f"Document {doc.id} has no content_path")

    return load_content_by_path(doc.content_path, strip_frontmatter=strip_frontmatter)


def load_content_by_path(
    content_path: str, strip_frontmatter: bool = True, raise_on_error: bool = False
) -> str:
    """
    Load document content from filesystem by content_path.

    This is a lower-level utility that works with just the content_path string,
    useful for DataFrame operations where you don't have a full Document object.

    Args:
        content_path: Relative path to content file (from sources directory)
        strip_frontmatter: If True (default), removes YAML frontmatter from content
        raise_on_error: If True, raises ValueError on errors; otherwise returns ""

    Returns:
        Document content as string (with frontmatter stripped by default),
        or empty string if file not found and raise_on_error=False

    Raises:
        ValueError: If content_path is missing or file doesn't exist (only when raise_on_error=True)

    Example:
        # Direct usage (raises on error)
        content = load_content_by_path("example.com/page.md", raise_on_error=True)

        # DataFrame apply usage (returns empty string on error)
        df["content"] = df["content_path"].apply(load_content_by_path)
    """
    if not content_path:
        if raise_on_error:
            raise ValueError("content_path is empty or None")
        return ""

    from kurt.config import load_config

    config = load_config()
    source_base = config.get_absolute_sources_path()
    content_file = source_base / content_path

    if not content_file.exists():
        if raise_on_error:
            raise ValueError(f"Content file not found: {content_file}")
        return ""

    content = content_file.read_text(encoding="utf-8")

    if not content.strip():
        if raise_on_error:
            raise ValueError(f"Content file is empty: {content_file}")
        return ""

    if strip_frontmatter:
        content = _strip_frontmatter(content)

    return content


def _strip_frontmatter(content: str) -> str:
    """
    Strip YAML frontmatter from content.

    Args:
        content: Full content that may contain YAML frontmatter

    Returns:
        Content without frontmatter

    Example:
        >>> content = "---\\ntitle: Test\\n---\\nBody content"
        >>> _strip_frontmatter(content)
        'Body content'
    """
    # Check if content starts with YAML frontmatter delimiter
    if not content.startswith("---"):
        return content

    # Find the closing delimiter
    lines = content.split("\n")
    closing_index = None

    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_index = i
            break

    # If we found the closing delimiter, return everything after it
    if closing_index is not None:
        body_lines = lines[closing_index + 1 :]
        return "\n".join(body_lines).strip()

    # If no closing delimiter found, return original content
    return content


# ============================================================================
# Document Update (CRUD - Update)
# ============================================================================


def save_document_content_and_metadata(
    doc_id: UUID,
    content: str,
    metadata: dict,
    embedding: bytes | None,
    public_url: str | None = None,
) -> dict:
    """
    Save content to filesystem and update database.

    Transactional operation - should be wrapped in @DBOS.transaction() for workflows.

    Args:
        doc_id: Document UUID
        content: Markdown content
        metadata: Metadata dict (title, author, date, etc.)
        embedding: Optional embedding bytes
        public_url: Optional public URL (for CMS documents, stored in discovery_url for link matching)

    Returns:
        dict with keys:
            - content_path: str (path to saved file)
            - status: str ('FETCHED')

    Example:
        >>> result = save_document_content_and_metadata(
        ...     doc_id, "# Title\\n\\nContent", {"title": "..."}, embedding_bytes
        ... )
        >>> # Returns: {'content_path': 'sources/example.com/page1.md', ...}

        >>> # CMS document with public URL
        >>> result = save_document_content_and_metadata(
        ...     doc_id, content, metadata, embedding, public_url="https://technically.dev/posts/slug"
        ... )
    """
    from datetime import datetime

    from kurt.config import load_config
    from kurt.utils.paths import create_cms_content_path, create_content_path

    session = get_session()
    doc = session.get(Document, doc_id)

    if not doc:
        raise ValueError(f"Document not found: {doc_id}")

    # Update metadata
    if metadata:
        # Title (prefer metadata title over URL-derived title)
        if metadata.get("title"):
            doc.title = metadata["title"]

        # Content hash (fingerprint for deduplication)
        if metadata.get("fingerprint"):
            doc.content_hash = metadata["fingerprint"]

        # Description
        if metadata.get("description"):
            doc.description = metadata["description"]

        # Author(s) - convert to list if single author
        author = metadata.get("author")
        if author:
            doc.author = [author] if isinstance(author, str) else list(author)

        # Published date
        if metadata.get("date"):
            try:
                doc.published_date = datetime.fromisoformat(metadata["date"])
            except (ValueError, AttributeError):
                pass

    # Note: public_url (discovery_url) is now stored in landing_discovery table
    # and passed to fetch model, not on the Document model itself

    # Store embedding
    if embedding:
        doc.embedding = embedding

    # Determine content path
    config = load_config()

    if doc.cms_platform and doc.cms_instance:
        content_path = create_cms_content_path(
            platform=doc.cms_platform,
            instance=doc.cms_instance,
            doc_id=doc.cms_document_id,
            config=config,
            source_url=doc.source_url,
        )
    else:
        content_path = create_content_path(doc.source_url, config)

    # Write file
    content_path.parent.mkdir(parents=True, exist_ok=True)
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Update document record
    source_base = config.get_absolute_sources_path()
    doc.content_path = str(content_path.relative_to(source_base))
    # Note: Status is now derived from landing_fetch table, not stored on Document
    # The landing.fetch model writes to landing_fetch with status=FETCHED

    session.commit()

    return {
        "content_path": str(content_path),
        "status": "FETCHED",
    }


# ============================================================================
# Document Deletion (CRUD - Delete)
# ============================================================================


def delete_document(document_id: str, delete_content: bool = False) -> dict:
    """
    Delete document by ID (supports partial UUIDs).

    Args:
        document_id: Document UUID as string (full or partial, minimum 8 chars)
        delete_content: If True, also delete content file from filesystem

    Returns:
        Dictionary with deletion result:
            - deleted_id: str
            - title: str
            - content_deleted: bool

    Raises:
        ValueError: If document not found or ID is ambiguous

    Example:
        # Delete document (keep content file)
        result = delete_document("550e8400-e29b-41d4-a716-446655440000")
        result = delete_document("550e8400")  # Partial UUID also works

        # Delete document and content file
        result = delete_document("550e8400", delete_content=True)
    """

    from kurt.config import load_config

    session = get_session()

    # Try full UUID first
    try:
        doc_uuid = UUID(document_id)
        doc = session.get(Document, doc_uuid)

        if not doc:
            raise ValueError(f"Document not found: {document_id}")
    except ValueError:
        # Try partial UUID match
        if len(document_id) < 8:
            raise ValueError(f"Document ID too short (minimum 8 characters): {document_id}")

        # Search for documents where ID starts with the partial UUID
        stmt = select(Document)
        docs = session.exec(stmt).all()

        # Filter by partial match (comparing without hyphens)
        partial_lower = document_id.lower().replace("-", "")
        matches = [d for d in docs if str(d.id).replace("-", "").startswith(partial_lower)]

        if len(matches) == 0:
            raise ValueError(f"Document not found: {document_id}")
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous document ID '{document_id}' matches {len(matches)} documents. "
                f"Please provide more characters."
            )

        doc = matches[0]

    # Store info for result
    title = doc.title
    content_path = doc.content_path
    content_deleted = False

    # Delete content file if requested
    if delete_content and content_path:
        try:
            config = load_config()
            source_base = config.get_absolute_sources_path()
            full_path = source_base / content_path

            if full_path.exists():
                full_path.unlink()
                content_deleted = True
        except Exception:
            # Ignore content deletion errors
            pass

    # Delete document from database
    session.delete(doc)
    session.commit()

    return {
        "deleted_id": str(doc_uuid),
        "title": title,
        "content_deleted": content_deleted,
    }


def get_document_stats(
    include_pattern: Optional[str] = None,
    in_cluster: Optional[str] = None,
    with_status: Optional[str] = None,
    with_content_type: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict:
    """
    Get statistics about documents in the database.

    Note: Status is now derived from staging tables, not stored on Document.

    Args:
        include_pattern: Optional glob pattern to filter documents (e.g., "*docs.dagster.io*")
        in_cluster: Optional cluster name to filter documents
        with_status: Optional status filter (NOT_FETCHED, FETCHED, INDEXED, ERROR)
        with_content_type: Optional content type filter (tutorial, guide, blog, etc.)
        limit: Optional limit on number of documents to include in stats

    Returns:
        Dictionary with statistics:
            - total: int (total number of documents)
            - not_fetched: int
            - fetched: int (includes indexed)
            - indexed: int
            - error: int

    Example:
        stats = get_document_stats()
        print(f"Total: {stats['total']}")
        print(f"Fetched: {stats['fetched']}")

        # With filter
        stats = get_document_stats(include_pattern="*docs.dagster.io*")
        stats = get_document_stats(in_cluster="Tutorials", with_status="FETCHED")
    """
    from fnmatch import fnmatch

    from sqlalchemy import text

    session = get_session()

    # Get all document IDs first
    stmt = select(Document)

    # Check if staging_topic_clustering table exists for cluster/content_type filters
    has_topic_clustering = _table_exists(session, "staging_topic_clustering")

    if in_cluster:
        if has_topic_clustering:
            # Join with staging_topic_clustering to filter by cluster
            stmt = stmt.where(
                text(
                    "CAST(id AS TEXT) IN ("
                    "SELECT document_id FROM staging_topic_clustering "
                    f"WHERE cluster_name = '{in_cluster}')"
                )
            )
        else:
            # No documents can match if table doesn't exist
            stmt = stmt.where(text("1=0"))

    if with_content_type:
        if has_topic_clustering:
            # Filter by content_type from staging_topic_clustering
            stmt = stmt.where(
                text(
                    "CAST(id AS TEXT) IN ("
                    "SELECT document_id FROM staging_topic_clustering "
                    f"WHERE content_type = '{with_content_type}')"
                )
            )
        else:
            # No documents can match if table doesn't exist
            stmt = stmt.where(text("1=0"))

    # Fetch documents
    all_docs = list(session.exec(stmt).all())

    # Apply glob pattern filtering (post-fetch)
    if include_pattern:
        filtered_docs = []
        for doc in all_docs:
            if doc.source_url and fnmatch(doc.source_url, include_pattern):
                filtered_docs.append(doc)
            elif doc.content_path and fnmatch(str(doc.content_path), include_pattern):
                filtered_docs.append(doc)
        all_docs = filtered_docs

    # Apply limit
    if limit and len(all_docs) > limit:
        all_docs = all_docs[:limit]

    # Get status counts using SQL for efficiency
    # Staging tables store document_id WITHOUT hyphens (from pandas reading SQLite)
    doc_ids = [str(d.id).replace("-", "") for d in all_docs]
    if not doc_ids:
        return {"total": 0, "not_fetched": 0, "fetched": 0, "indexed": 0, "error": 0}

    # Create a temporary view of filtered doc IDs for counting
    doc_ids_str = ",".join(f"'{d}'" for d in doc_ids)

    # Count indexed (has section extractions)
    try:
        indexed_sql = text(f"""
            SELECT COUNT(DISTINCT document_id) as count
            FROM staging_section_extractions
            WHERE document_id IN ({doc_ids_str})
        """)
        indexed_count = session.execute(indexed_sql).scalar() or 0
    except Exception:
        indexed_count = 0

    # Count fetched (has landing_fetch with FETCHED status)
    try:
        fetched_sql = text(f"""
            SELECT COUNT(DISTINCT document_id) as count
            FROM landing_fetch
            WHERE document_id IN ({doc_ids_str})
            AND status = 'FETCHED'
        """)
        fetched_count = session.execute(fetched_sql).scalar() or 0
    except Exception:
        fetched_count = 0

    # Count errors
    try:
        error_sql = text(f"""
            SELECT COUNT(DISTINCT document_id) as count
            FROM (
                SELECT document_id FROM landing_fetch
                WHERE document_id IN ({doc_ids_str}) AND error IS NOT NULL
                UNION
                SELECT document_id FROM landing_discovery
                WHERE document_id IN ({doc_ids_str}) AND error IS NOT NULL
            )
        """)
        error_count = session.execute(error_sql).scalar() or 0
    except Exception:
        error_count = 0

    total = len(all_docs)
    # not_fetched = total - fetched (those not in landing_fetch with FETCHED)
    not_fetched = total - fetched_count

    # Apply status filter if specified
    if with_status:
        status_upper = with_status.upper()
        if status_upper == "FETCHED":
            # Return only fetched count
            return {
                "total": fetched_count,
                "not_fetched": 0,
                "fetched": fetched_count,
                "indexed": indexed_count,
                "error": 0,
            }
        elif status_upper == "NOT_FETCHED":
            return {
                "total": not_fetched,
                "not_fetched": not_fetched,
                "fetched": 0,
                "indexed": 0,
                "error": 0,
            }
        elif status_upper == "ERROR":
            return {
                "total": error_count,
                "not_fetched": 0,
                "fetched": 0,
                "indexed": 0,
                "error": error_count,
            }
        elif status_upper == "INDEXED":
            return {
                "total": indexed_count,
                "not_fetched": 0,
                "fetched": indexed_count,
                "indexed": indexed_count,
                "error": 0,
            }

    return {
        "total": total,
        "not_fetched": not_fetched,
        "fetched": fetched_count,
        "indexed": indexed_count,
        "error": error_count,
    }


# Analytics stats moved to telemetry module
# For backwards compatibility, re-export it here
def get_analytics_stats(include_pattern: Optional[str] = None) -> dict:
    """Get analytics statistics (deprecated: use kurt.telemetry.analytics.get_analytics_stats)."""
    from kurt.admin.telemetry.analytics import get_analytics_stats as _get_analytics_stats

    return _get_analytics_stats(include_pattern=include_pattern)


def list_clusters() -> list[dict]:
    """
    List all topic clusters with document counts.

    Queries the staging_topic_clustering table for cluster information.

    Returns:
        List of dictionaries with cluster information:
            - name: str
            - description: str
            - doc_count: int

    Example:
        clusters = list_clusters()
        for cluster in clusters:
            print(f"{cluster['name']}: {cluster['doc_count']} docs")
    """
    from sqlalchemy import text

    session = get_session()

    # Query staging_topic_clustering for cluster summary
    sql = text("""
        SELECT
            cluster_name as name,
            cluster_description as description,
            COUNT(*) as doc_count
        FROM staging_topic_clustering
        WHERE cluster_name IS NOT NULL
        GROUP BY cluster_name, cluster_description
        ORDER BY doc_count DESC
    """)

    try:
        results = session.execute(sql).fetchall()
    except Exception:
        # Table may not exist yet
        return []

    # Convert to list of dicts
    clusters = []
    for row in results:
        clusters.append(
            {
                "name": row.name,
                "description": row.description,
                "doc_count": row.doc_count,
            }
        )

    return clusters


def list_content(
    with_status: str = None,
    include_pattern: str = None,
    in_cluster: str = None,
    with_content_type: str = None,
    max_depth: int = None,
    limit: int = None,
    offset: int = 0,
    with_analytics: bool = False,
    order_by: str = None,
    min_pageviews: int = None,
    max_pageviews: int = None,
    trend: str = None,
    entity_name: str = None,
    entity_type: str = None,
    relationship_type: str = None,
    relationship_source: str = None,
    relationship_target: str = None,
) -> list[Document]:
    """
    List documents with new explicit naming (for CLI-SPEC.md compliance).

    This is the new API-compliant version of list_documents() with explicit naming.

    Args:
        with_status: Filter by status (NOT_FETCHED | FETCHED | ERROR)
        include_pattern: Glob pattern matching source_url or content_path
        in_cluster: Filter by cluster name (case-insensitive)
        with_content_type: Filter by content type (tutorial | guide | blog | etc)
        max_depth: Filter by maximum URL depth (e.g., 2 for example.com/a/b)
        limit: Maximum number of documents to return
        offset: Number of documents to skip (for pagination)
        with_analytics: Include analytics data (pageviews, trends)
        order_by: Sort by analytics metric (pageviews_30d | pageviews_60d | trend_percentage)
        min_pageviews: Minimum pageviews_30d filter
        max_pageviews: Maximum pageviews_30d filter
        trend: Filter by trend (increasing | decreasing | stable)
        entity_name: Entity name to search for (partial match)
        entity_type: Entity type filter (Topic, Technology, Product, Feature, Company, Integration, or "technologies")
        relationship_type: Relationship type filter (mentions, part_of, integrates_with, enables, related_to, depends_on, replaces)
        relationship_source: Optional source entity name filter for relationships
        relationship_target: Optional target entity name filter for relationships

    Returns:
        List of Document objects (with analytics dict attribute if with_analytics=True)

    Example:
        # List all documents
        docs = list_content()

        # List only fetched documents
        docs = list_content(with_status="FETCHED")

        # List documents matching pattern
        docs = list_content(include_pattern="*/docs/*")

        # List documents in cluster
        docs = list_content(in_cluster="Tutorials")

        # Filter by URL depth
        docs = list_content(max_depth=2)

        # Filter by entity
        docs = list_content(entity_name="Python", entity_type="Topic")

        # Filter by relationship
        docs = list_content(relationship_type="integrates_with")
        docs = list_content(relationship_type="integrates_with", relationship_source="FastAPI")
        docs = list_content(relationship_type="depends_on", relationship_target="Python")

        # With analytics
        docs = list_content(with_analytics=True, order_by="pageviews_30d", limit=10)
        docs = list_content(with_analytics=True, trend="decreasing", min_pageviews=1000)

        # Combine filters
        docs = list_content(with_status="FETCHED", include_pattern="*/blog/*", max_depth=2)
    """
    from fnmatch import fnmatch

    from sqlalchemy import text

    from kurt.db.models import DocumentClusterEdge, TopicCluster

    session = get_session()

    # Build base query (analytics will be joined separately via URL)
    stmt = select(Document)

    # Apply cluster filter (JOIN with edges and clusters tables)
    if in_cluster:
        stmt = (
            stmt.join(DocumentClusterEdge, Document.id == DocumentClusterEdge.document_id)
            .join(TopicCluster, DocumentClusterEdge.cluster_id == TopicCluster.id)
            .where(TopicCluster.name.ilike(f"%{in_cluster}%"))
        )

    # Apply status filter using helper that handles missing staging tables
    if with_status:
        status_upper = with_status.upper() if isinstance(with_status, str) else with_status
        status_subquery = _get_status_subquery(session, status_upper)
        if status_subquery:
            stmt = stmt.where(text(status_subquery))

    # Apply content_type filter using staging_topic_clustering table
    if with_content_type:
        has_topic_clustering = _table_exists(session, "staging_topic_clustering")
        if has_topic_clustering:
            stmt = stmt.where(
                text(
                    f"CAST(id AS TEXT) IN ("
                    f"SELECT document_id FROM staging_topic_clustering "
                    f"WHERE content_type = '{with_content_type.lower()}')"
                )
            )
        else:
            # No documents can match if table doesn't exist
            stmt = stmt.where(text("1=0"))

    # Apply ordering (if not analytics-based, since analytics needs post-query sorting)
    if not (with_analytics and order_by):
        # Default ordering (most recent first)
        stmt = stmt.order_by(Document.created_at.desc())

    # Execute base query
    documents = list(session.exec(stmt).all())

    # If analytics needed, fetch and merge via URL
    if with_analytics and documents:
        # Build URL -> PageAnalytics map
        analytics_map = {}
        all_analytics = session.exec(select(PageAnalytics)).all()
        for analytics in all_analytics:
            analytics_map[analytics.url] = analytics

        # Match documents with analytics and apply filters
        matched_docs = []
        for doc in documents:
            if doc.source_url:
                normalized_url = normalize_url_for_analytics(doc.source_url)
                analytics = analytics_map.get(normalized_url)

                # Apply analytics filters
                if min_pageviews is not None and (
                    not analytics or analytics.pageviews_30d < min_pageviews
                ):
                    continue
                if max_pageviews is not None and (
                    not analytics or analytics.pageviews_30d > max_pageviews
                ):
                    continue
                if trend and (not analytics or analytics.pageviews_trend != trend):
                    continue

                # Attach analytics data using __dict__ to bypass Pydantic validation
                if analytics:
                    doc.__dict__["analytics"] = {
                        "pageviews_30d": analytics.pageviews_30d,
                        "pageviews_60d": analytics.pageviews_60d,
                        "pageviews_previous_30d": analytics.pageviews_previous_30d,
                        "unique_visitors_30d": analytics.unique_visitors_30d,
                        "unique_visitors_60d": analytics.unique_visitors_60d,
                        "pageviews_trend": analytics.pageviews_trend,
                        "trend_percentage": analytics.trend_percentage,
                        "bounce_rate": analytics.bounce_rate,
                        "avg_session_duration_seconds": analytics.avg_session_duration_seconds,
                    }
                else:
                    doc.__dict__["analytics"] = None

                matched_docs.append((doc, analytics))
            else:
                # No source_url, can't match analytics
                doc.__dict__["analytics"] = None
                matched_docs.append((doc, None))

        # Apply analytics-based ordering if requested
        if order_by:
            if order_by == "pageviews_30d":
                matched_docs.sort(key=lambda x: x[1].pageviews_30d if x[1] else 0, reverse=True)
            elif order_by == "pageviews_60d":
                matched_docs.sort(key=lambda x: x[1].pageviews_60d if x[1] else 0, reverse=True)
            elif order_by == "trend_percentage":
                matched_docs.sort(
                    key=lambda x: x[1].trend_percentage
                    if x[1] and x[1].trend_percentage
                    else float("-inf"),
                    reverse=True,
                )
        else:
            # Default created_at ordering
            matched_docs.sort(key=lambda x: x[0].created_at, reverse=True)

        # Extract just documents
        documents = [doc for doc, _ in matched_docs]

    # Apply glob pattern filtering (post-query)
    if include_pattern:
        documents = [
            d
            for d in documents
            if (d.source_url and fnmatch(d.source_url, include_pattern))
            or (d.content_path and fnmatch(d.content_path, include_pattern))
        ]

    # Apply max_depth filtering (post-query)
    if max_depth is not None:
        from kurt.utils.url_utils import get_url_depth

        documents = [d for d in documents if get_url_depth(d.source_url) <= max_depth]

    # Apply entity filtering (knowledge graph only)
    if entity_name:
        from kurt.db.graph_queries import find_documents_with_entity

        graph_doc_ids = {
            str(doc_id)
            for doc_id in find_documents_with_entity(
                entity_name, entity_type=entity_type, session=session
            )
        }
        documents = [d for d in documents if str(d.id) in graph_doc_ids]

    # Apply relationship filtering (knowledge graph only)
    if relationship_type:
        from kurt.db.graph_queries import find_documents_with_relationship

        relationship_doc_ids = {
            str(doc_id)
            for doc_id in find_documents_with_relationship(
                relationship_type,
                source_entity_name=relationship_source,
                target_entity_name=relationship_target,
                session=session,
            )
        }
        documents = [d for d in documents if str(d.id) in relationship_doc_ids]

    # Apply pagination (after all filtering)
    if offset or limit:
        start = offset
        end = offset + limit if limit else None
        documents = documents[start:end]

    return documents


def list_documents_for_indexing(
    ids: Optional[str] = None,
    include_pattern: Optional[str] = None,
    in_cluster: Optional[str] = None,
    with_status: Optional[str] = None,
    with_content_type: Optional[str] = None,
    all_flag: bool = False,
) -> list[Document]:
    """
    Get documents that need to be indexed based on filtering criteria.

    This function encapsulates the business logic for selecting documents
    for the indexing process. It handles multiple modes:
    1. Single or multiple documents by IDs (comma-separated)
    2. All FETCHED documents in a cluster
    3. All FETCHED documents matching a glob pattern
    4. All FETCHED documents with specific status
    5. All FETCHED documents with specific content type
    6. All FETCHED documents (when all_flag is True)

    Args:
        ids: Comma-separated list of document IDs (full/partial UUIDs, URLs, or file paths)
        include_pattern: Glob pattern to filter documents (e.g., "*/docs/*")
        in_cluster: Cluster name to filter documents
        with_status: Filter by ingestion status (NOT_FETCHED, FETCHED, ERROR)
        with_content_type: Filter by content type (tutorial, guide, blog, etc.)
        all_flag: If True, return all FETCHED documents

    Returns:
        List of Document objects ready for indexing

    Raises:
        ValueError: If identifier cannot be resolved or is ambiguous
        ValueError: If no filtering criteria provided

    Example:
        # Get single or multiple documents by IDs
        docs = list_documents_for_indexing(ids="44ea066e")
        docs = list_documents_for_indexing(ids="44ea066e,550e8400,a73af781")

        # Get documents in a cluster
        docs = list_documents_for_indexing(in_cluster="Tutorials")

        # Get all documents matching pattern
        docs = list_documents_for_indexing(include_pattern="*/docs/*")

        # Get all FETCHED documents
        docs = list_documents_for_indexing(all_flag=True)

        # Get documents by status
        docs = list_documents_for_indexing(with_status="FETCHED")

        # Get documents by content type
        docs = list_documents_for_indexing(with_content_type="tutorial")
    """
    from fnmatch import fnmatch

    # Validate input - need at least one filtering criterion
    if (
        not ids
        and not include_pattern
        and not in_cluster
        and not with_status
        and not with_content_type
        and not all_flag
    ):
        raise ValueError(
            "Must provide either ids, include_pattern, in_cluster, with_status, with_content_type, or all_flag=True"
        )

    # Mode 1: Documents by IDs (single or multiple, supports partial UUIDs/URLs/file paths)
    if ids:
        from kurt.utils.filtering import resolve_ids_to_uuids

        try:
            # Resolve all identifiers to full UUIDs
            uuid_strs = resolve_ids_to_uuids(ids)
            docs = []
            for uuid_str in uuid_strs:
                try:
                    doc = get_document(uuid_str)
                    docs.append(doc)
                except ValueError:
                    # Skip invalid IDs but continue with others
                    pass
            return docs
        except ValueError as e:
            raise ValueError(f"Failed to resolve identifiers: {e}")

    # Mode 2+: Batch mode - get documents by filters
    if include_pattern or in_cluster or with_status or with_content_type or all_flag:
        # Determine status filter (default to FETCHED if not specified)
        # Status is now derived from staging tables, not stored on Document
        status_filter = with_status.upper() if with_status else "FETCHED"

        # Get documents with status filter
        docs = list_documents(
            status=status_filter,
            url_prefix=None,
            url_contains=None,
            limit=None,
        )

        # Apply cluster filter if provided (use staging_topic_clustering)
        if in_cluster:
            from sqlalchemy import text

            session = get_session()
            cluster_doc_ids = set()
            try:
                cluster_sql = text("""
                    SELECT document_id FROM staging_topic_clustering
                    WHERE cluster_name = :cluster_name
                """)
                results = session.execute(cluster_sql, {"cluster_name": in_cluster}).fetchall()
                cluster_doc_ids = {r[0] for r in results}
            except Exception:
                pass
            docs = [d for d in docs if str(d.id) in cluster_doc_ids]

        # Apply content type filter if provided (use staging_topic_clustering)
        if with_content_type:
            from sqlalchemy import text

            session = get_session()
            content_type_doc_ids = set()
            try:
                content_type_sql = text("""
                    SELECT document_id FROM staging_topic_clustering
                    WHERE content_type = :content_type
                """)
                results = session.execute(
                    content_type_sql, {"content_type": with_content_type.lower()}
                ).fetchall()
                content_type_doc_ids = {r[0] for r in results}
            except Exception:
                pass
            docs = [d for d in docs if str(d.id) in content_type_doc_ids]

        # Apply glob pattern filter if provided
        if include_pattern:
            # First, check if pattern matches any documents (regardless of status)
            all_docs_any_status = list_documents(limit=None)
            matching_any_status = [
                d
                for d in all_docs_any_status
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            ]

            # Filter documents by pattern
            docs = [
                d
                for d in docs
                if (d.source_url and fnmatch(d.source_url, include_pattern))
                or (d.content_path and fnmatch(d.content_path, include_pattern))
            ]

            # If no docs with requested status but pattern matched other statuses, provide helpful error
            if not docs and matching_any_status:
                # Get status from staging tables for each doc
                status_counts = {}
                for d in matching_any_status:
                    try:
                        doc_status = get_document_status(d.id)["status"]
                    except Exception:
                        doc_status = "UNKNOWN"
                    status_counts[doc_status] = status_counts.get(doc_status, 0) + 1

                status_summary = ", ".join(
                    [f"{count} {status}" for status, count in status_counts.items()]
                )
                raise ValueError(
                    f"Found {len(matching_any_status)} document(s) matching pattern '{include_pattern}' "
                    f"({status_summary}), but none are {status_filter}.\n"
                    f"Tip: Use 'kurt content fetch --include \"{include_pattern}\"' to fetch these documents first."
                )

        return docs

    # Should never reach here due to initial validation
    raise ValueError(
        "Must provide either ids, include_pattern, in_cluster, with_status, with_content_type, or all_flag=True"
    )


# ============================================================================
# Document Link Resolution (Helper for workflows)
# ============================================================================


def resolve_urls_to_doc_ids(url_list: list[str]) -> dict[str, UUID]:
    """
    Resolve URLs to document IDs.

    Checks both source_url and discovery_url fields to match URLs.
    Used by link saving logic to find target documents.

    Args:
        url_list: List of URLs to resolve

    Returns:
        Dictionary mapping URL -> document UUID

    Example:
        >>> url_to_id = resolve_urls_to_doc_ids(["https://example.com/page1", "https://example.com/page2"])
        >>> # Returns: {"https://example.com/page1": UUID(...), ...}
    """
    session = get_session()

    if not url_list:
        return {}

    # Query for documents matching these URLs by source_url
    # Note: discovery_url was removed from Document model - now in landing_discovery table
    stmt = select(Document).where(Document.source_url.in_(url_list))

    # Build mapping of URL -> doc_id
    url_to_id = {}
    for doc in session.exec(stmt).all():
        if doc.source_url in url_list:
            url_to_id[doc.source_url] = doc.id

    return url_to_id


def save_document_links(doc_id: UUID, links: list[dict]) -> int:
    """
    Save document links to database, replacing existing links.

    Args:
        doc_id: Source document UUID
        links: List of link dicts with "url" and "anchor_text"

    Returns:
        Number of links saved
    """
    from kurt.db.models import DocumentLink

    session = get_session()

    # Delete existing links (for refetch)
    existing_links = session.exec(
        select(DocumentLink).where(DocumentLink.source_document_id == doc_id)
    ).all()
    for link in existing_links:
        session.delete(link)

    # Early return if no links
    target_urls = [link["url"] for link in links]
    if not target_urls:
        session.commit()
        return 0

    # Resolve URLs to document IDs
    url_to_doc_id = resolve_urls_to_doc_ids(target_urls)

    # Create links for URLs with matching documents
    saved_count = 0
    for link in links:
        target_url = link["url"]
        if target_url in url_to_doc_id:
            document_link = DocumentLink(
                source_document_id=doc_id,
                target_document_id=url_to_doc_id[target_url],
                anchor_text=link["anchor_text"],
            )
            session.add(document_link)
            saved_count += 1

    session.commit()
    return saved_count


# ============================================================================
# Document Status and Metadata (Derived from Staging Tables)
# ============================================================================


def get_document_status(document_id: str | UUID) -> dict:
    """
    Get document status derived from staging tables.

    Status is determined by checking staging tables in priority order:
    1. staging_section_extractions → INDEXED (content has been indexed)
    2. landing_fetch → FETCHED (content downloaded but not indexed)
    3. landing_discovery → DISCOVERED (URL discovered but not fetched)
    4. None of above → NOT_FETCHED

    Any error in staging tables → ERROR

    Args:
        document_id: Document UUID as string or UUID object

    Returns:
        dict with keys:
            - status: str (INDEXED, FETCHED, DISCOVERED, NOT_FETCHED, ERROR)
            - is_indexed: bool (has section extractions)
            - is_fetched: bool (has fetch record)
            - is_discovered: bool (has discovery record)
            - fetch_engine: str | None (from landing_fetch)
            - discovery_method: str | None (from landing_discovery)
            - error: str | None (first error found)
            - error_source: str | None (table where error was found)

    Example:
        >>> status = get_document_status("550e8400")
        >>> print(status["status"])  # "INDEXED", "FETCHED", etc.
        >>> if status["is_indexed"]:
        ...     print("Document has been indexed")
    """
    from sqlalchemy import text

    session = get_session()

    # Resolve document ID
    doc = get_document(str(document_id))
    # Staging tables store document_id WITHOUT hyphens (from pandas reading SQLite)
    doc_id_str = str(doc.id).replace("-", "")

    result = {
        "status": "NOT_FETCHED",
        "is_indexed": False,
        "is_fetched": False,
        "is_discovered": False,
        "fetch_engine": None,
        "discovery_method": None,
        "error": None,
        "error_source": None,
    }

    # Check staging_section_extractions (INDEXED status)
    try:
        extractions_sql = text("""
            SELECT COUNT(*) as count, MAX(error) as error
            FROM staging_section_extractions
            WHERE document_id = :doc_id
        """)
        extractions_result = session.execute(extractions_sql, {"doc_id": doc_id_str}).fetchone()

        if extractions_result and extractions_result.count > 0:
            result["is_indexed"] = True
            if extractions_result.error:
                result["error"] = extractions_result.error
                result["error_source"] = "staging_section_extractions"
    except Exception:
        # Table may not exist yet
        pass

    # Check landing_fetch (FETCHED status)
    try:
        fetch_sql = text("""
            SELECT status, fetch_engine, error
            FROM landing_fetch
            WHERE document_id = :doc_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        fetch_result = session.execute(fetch_sql, {"doc_id": doc_id_str}).fetchone()

        if fetch_result:
            result["is_fetched"] = fetch_result.status == "FETCHED"
            result["fetch_engine"] = fetch_result.fetch_engine
            if fetch_result.error and not result["error"]:
                result["error"] = fetch_result.error
                result["error_source"] = "landing_fetch"
    except Exception:
        # Table may not exist yet
        pass

    # Check landing_discovery (DISCOVERED status)
    try:
        discovery_sql = text("""
            SELECT status, discovery_method, error
            FROM landing_discovery
            WHERE document_id = :doc_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        discovery_result = session.execute(discovery_sql, {"doc_id": doc_id_str}).fetchone()

        if discovery_result:
            result["is_discovered"] = discovery_result.status in ("DISCOVERED", "EXISTING")
            result["discovery_method"] = discovery_result.discovery_method
            if discovery_result.error and not result["error"]:
                result["error"] = discovery_result.error
                result["error_source"] = "landing_discovery"
    except Exception:
        # Table may not exist yet
        pass

    # Determine overall status (priority: ERROR > INDEXED > FETCHED > DISCOVERED > NOT_FETCHED)
    if result["error"]:
        result["status"] = "ERROR"
    elif result["is_indexed"]:
        result["status"] = "INDEXED"
    elif result["is_fetched"]:
        result["status"] = "FETCHED"
    elif result["is_discovered"]:
        result["status"] = "DISCOVERED"
    else:
        result["status"] = "NOT_FETCHED"

    return result


def get_document_with_metadata(document_id: str | UUID) -> dict:
    """
    Get document with full metadata reconstructed from staging tables.

    Joins the minimal Document record with metadata from staging tables:
    - landing_discovery: discovery_method, discovery_url
    - landing_fetch: content_hash, content_length, fetch_engine
    - staging_topic_clustering: content_type, cluster_name
    - staging_section_extractions: has_code_examples, has_step_by_step_procedures, has_narrative_structure

    Args:
        document_id: Document UUID as string or UUID object

    Returns:
        dict with all document fields plus derived metadata:
            # Core document fields
            - id: str (UUID)
            - title: str | None
            - source_type: str
            - source_url: str | None
            - content_path: str | None
            - cms_document_id: str | None
            - cms_platform: str | None
            - cms_instance: str | None
            - content_hash: str | None
            - description: str | None
            - author: list | None
            - published_date: datetime | None
            - indexed_with_hash: str | None
            - created_at: datetime
            - updated_at: datetime

            # Derived from staging tables
            - status: str (from get_document_status)
            - discovery_method: str | None (from landing_discovery)
            - discovery_url: str | None (from landing_discovery)
            - fetch_engine: str | None (from landing_fetch)
            - content_type: str | None (from staging_topic_clustering)
            - cluster_name: str | None (from staging_topic_clustering)
            - has_code_examples: bool (from staging_section_extractions)
            - has_step_by_step_procedures: bool (from staging_section_extractions)
            - has_narrative_structure: bool (from staging_section_extractions)

    Example:
        >>> doc = get_document_with_metadata("550e8400")
        >>> print(doc["title"], doc["content_type"])
        >>> if doc["has_code_examples"]:
        ...     print("Document contains code examples")
    """
    from sqlalchemy import text

    session = get_session()

    # Get base document
    doc = get_document(str(document_id))
    # Staging tables store document_id WITHOUT hyphens (from pandas reading SQLite)
    doc_id_str = str(doc.id).replace("-", "")

    # Build result with core document fields
    result = {
        # Identity
        "id": str(doc.id),
        "title": doc.title,
        "source_type": doc.source_type.value if doc.source_type else None,
        "source_url": doc.source_url,
        # Content location
        "content_path": doc.content_path,
        # CMS integration
        "cms_document_id": doc.cms_document_id,
        "cms_platform": doc.cms_platform,
        "cms_instance": doc.cms_instance,
        # Content metadata
        "content_hash": doc.content_hash,
        "description": doc.description,
        "author": doc.author,
        "published_date": doc.published_date,
        # Indexing tracking
        "indexed_with_hash": doc.indexed_with_hash,
        # Timestamps
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
        # Derived fields (to be filled from staging tables)
        "status": "NOT_FETCHED",
        "discovery_method": None,
        "discovery_url": None,
        "fetch_engine": None,
        "content_type": None,
        "cluster_name": None,
        "has_code_examples": False,
        "has_step_by_step_procedures": False,
        "has_narrative_structure": False,
    }

    # Get status info (includes discovery_method, fetch_engine)
    status_info = get_document_status(doc.id)
    result["status"] = status_info["status"]
    result["discovery_method"] = status_info["discovery_method"]
    result["fetch_engine"] = status_info["fetch_engine"]

    # Get discovery_url from landing_discovery
    try:
        discovery_sql = text("""
            SELECT discovery_url
            FROM landing_discovery
            WHERE document_id = :doc_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        discovery_result = session.execute(discovery_sql, {"doc_id": doc_id_str}).fetchone()

        if discovery_result:
            result["discovery_url"] = discovery_result.discovery_url
    except Exception:
        pass

    # Get content_type and cluster_name from staging_topic_clustering
    try:
        clustering_sql = text("""
            SELECT content_type, cluster_name
            FROM staging_topic_clustering
            WHERE document_id = :doc_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        clustering_result = session.execute(clustering_sql, {"doc_id": doc_id_str}).fetchone()

        if clustering_result:
            result["content_type"] = clustering_result.content_type
            result["cluster_name"] = clustering_result.cluster_name
    except Exception:
        pass

    # Get content analysis flags from staging_section_extractions
    # These are stored in metadata_json field
    try:
        extractions_sql = text("""
            SELECT metadata_json
            FROM staging_section_extractions
            WHERE document_id = :doc_id
            AND metadata_json IS NOT NULL
            ORDER BY section_number ASC
            LIMIT 1
        """)
        extractions_result = session.execute(extractions_sql, {"doc_id": doc_id_str}).fetchone()

        if extractions_result and extractions_result.metadata_json:
            import json

            metadata = extractions_result.metadata_json
            # Handle both string and dict forms
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            result["has_code_examples"] = metadata.get("has_code_examples", False)
            result["has_step_by_step_procedures"] = metadata.get(
                "has_step_by_step_procedures", False
            )
            result["has_narrative_structure"] = metadata.get("has_narrative_structure", False)

            # Also get content_type from extractions if not from clustering
            if not result["content_type"] and metadata.get("content_type"):
                result["content_type"] = metadata["content_type"]
    except Exception:
        pass

    return result


def get_document_links(document_id: UUID, direction: str) -> list[dict]:
    """
    Get document links from the DocumentLink table.

    Args:
        document_id: Document UUID
        direction: "outbound" (links FROM this document) or "inbound" (links TO this document)

    Returns:
        List of dicts with link information:
        - source_document_id: UUID of source document
        - target_document_id: UUID of target document
        - source_title: Title of source document
        - target_title: Title of target document
        - anchor_text: Link anchor text

    Raises:
        ValueError: If direction is invalid or document doesn't exist

    Example:
        >>> # Get all links FROM a document
        >>> outbound = get_document_links(doc_id, direction="outbound")
        >>> # Get all links TO a document
        >>> inbound = get_document_links(doc_id, direction="inbound")
    """
    from sqlmodel import select

    from kurt.db.models import Document, DocumentLink

    if direction not in ("inbound", "outbound"):
        raise ValueError(f"Invalid direction: {direction}. Must be 'inbound' or 'outbound'")

    session = get_session()

    # Verify document exists
    doc = session.get(Document, document_id)
    if not doc:
        raise ValueError(f"Document not found: {document_id}")

    # Build query based on direction
    if direction == "outbound":
        # Links FROM this document
        stmt = (
            select(DocumentLink, Document)
            .join(Document, DocumentLink.target_document_id == Document.id)
            .where(DocumentLink.source_document_id == document_id)
        )
    else:  # inbound
        # Links TO this document
        stmt = (
            select(DocumentLink, Document)
            .join(Document, DocumentLink.source_document_id == Document.id)
            .where(DocumentLink.target_document_id == document_id)
        )

    results = session.exec(stmt).all()

    # Format results
    links = []
    for link, related_doc in results:
        if direction == "outbound":
            # related_doc is the target
            links.append(
                {
                    "source_document_id": link.source_document_id,
                    "target_document_id": link.target_document_id,
                    "source_title": doc.title or doc.source_url,
                    "target_title": related_doc.title or related_doc.source_url,
                    "anchor_text": link.anchor_text,
                }
            )
        else:  # inbound
            # related_doc is the source
            links.append(
                {
                    "source_document_id": link.source_document_id,
                    "target_document_id": link.target_document_id,
                    "source_title": related_doc.title or related_doc.source_url,
                    "target_title": doc.title or doc.source_url,
                    "anchor_text": link.anchor_text,
                }
            )

    return links
