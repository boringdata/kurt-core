"""
Document utility functions for Kurt.

These functions provide CRUD operations for documents:
- add_document: Create new document record (NOT_FETCHED status)
- resolve_or_create_document: Find or create document by ID/URL
- get_document: Get document by ID
- list_documents: List all documents with filtering
- load_document_content: Load document content from filesystem
- save_document_content_and_metadata: Update document content and metadata
- delete_document: Delete document by ID
- get_document_stats: Get statistics about documents

These can be used directly by agents or wrapped by CLI commands.
"""

from typing import Optional
from uuid import UUID

from sqlmodel import select

from kurt.config import load_config
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, PageAnalytics, SourceType
from kurt.integrations.analytics.utils import normalize_url_for_analytics

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
            ingestion_status=IngestionStatus.FETCHED,  # Already have the file
        )

        session.add(new_doc)
        created_docs.append(new_doc)

    # Commit all new documents
    if created_docs:
        session.commit()
        # Refresh to get IDs
        for doc in created_docs:
            session.refresh(doc)

    new_count = len(
        [d for d in created_docs if d.id and d.ingestion_status == IngestionStatus.FETCHED]
    )

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
    doc = Document(
        title=title,
        source_type=SourceType.URL,
        source_url=url,
        ingestion_status=IngestionStatus.NOT_FETCHED,
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
    status: Optional[IngestionStatus] = None,
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

    Args:
        status: Filter by ingestion status (NOT_FETCHED, FETCHED, ERROR)
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
        docs = list_documents(status=IngestionStatus.FETCHED)

        # List documents from specific domain
        docs = list_documents(url_prefix="https://example.com")

        # List documents with "blog" in URL
        docs = list_documents(url_contains="blog")

        # Combine filters
        docs = list_documents(status=IngestionStatus.FETCHED, url_prefix="https://example.com")

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

    # Apply basic filters
    if status:
        stmt = stmt.where(Document.ingestion_status == status)
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

    from kurt.config import load_config

    config = load_config()
    source_base = config.get_absolute_sources_path()
    content_file = source_base / doc.content_path

    if not content_file.exists():
        raise ValueError(f"Content file not found: {content_file}")

    content = content_file.read_text(encoding="utf-8")

    if not content.strip():
        raise ValueError(f"Document {doc.id} has empty content")

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
    from kurt.content.paths import create_cms_content_path, create_content_path

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

    # Store public URL (for CMS documents - used for link matching)
    if public_url:
        doc.discovery_url = public_url

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
    doc.ingestion_status = IngestionStatus.FETCHED

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

    Args:
        include_pattern: Optional glob pattern to filter documents (e.g., "*docs.dagster.io*")
        in_cluster: Optional cluster name to filter documents
        with_status: Optional ingestion status filter (NOT_FETCHED, FETCHED, ERROR)
        with_content_type: Optional content type filter (tutorial, guide, blog, etc.)
        limit: Optional limit on number of documents to include in stats

    Returns:
        Dictionary with statistics:
            - total: int (total number of documents)
            - not_fetched: int
            - fetched: int
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

    session = get_session()

    # Build base query
    stmt = select(Document)

    # Apply filters (SQL-based when possible)
    if with_status:
        status_enum = IngestionStatus[with_status.upper()]
        stmt = stmt.where(Document.ingestion_status == status_enum)

    if in_cluster:
        # Join with clusters to filter
        from kurt.db.models import ClusterMembership

        stmt = stmt.join(ClusterMembership, Document.id == ClusterMembership.document_id).where(
            ClusterMembership.cluster_name == in_cluster
        )

    if with_content_type:
        # Need to join with document_classifications
        from kurt.db.models import DocumentClassification

        stmt = stmt.join(
            DocumentClassification, Document.id == DocumentClassification.document_id
        ).where(DocumentClassification.document_type == with_content_type)

    # Fetch documents (need glob filtering)
    all_docs = session.exec(stmt).all()

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

    # Count by status
    total = len(all_docs)
    not_fetched = sum(1 for d in all_docs if d.ingestion_status == IngestionStatus.NOT_FETCHED)
    fetched = sum(1 for d in all_docs if d.ingestion_status == IngestionStatus.FETCHED)
    error = sum(1 for d in all_docs if d.ingestion_status == IngestionStatus.ERROR)

    return {
        "total": total,
        "not_fetched": not_fetched,
        "fetched": fetched,
        "error": error,
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

    Returns:
        List of dictionaries with cluster information:
            - id: UUID
            - name: str
            - description: str
            - created_at: datetime
            - doc_count: int

    Example:
        clusters = list_clusters()
        for cluster in clusters:
            print(f"{cluster['name']}: {cluster['doc_count']} docs")
    """
    from sqlalchemy import func, select

    from kurt.db.models import DocumentClusterEdge, TopicCluster

    session = get_session()

    # Get all clusters with document counts
    stmt = (
        select(
            TopicCluster.id,
            TopicCluster.name,
            TopicCluster.description,
            TopicCluster.created_at,
            func.count(DocumentClusterEdge.document_id).label("doc_count"),
        )
        .outerjoin(DocumentClusterEdge, TopicCluster.id == DocumentClusterEdge.cluster_id)
        .group_by(TopicCluster.id)
        .order_by(func.count(DocumentClusterEdge.document_id).desc())
    )

    results = session.exec(stmt).all()

    # Convert to list of dicts
    clusters = []
    for row in results:
        clusters.append(
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "created_at": row.created_at,
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

    # Apply status filter
    if with_status:
        status_enum = IngestionStatus(with_status)
        stmt = stmt.where(Document.ingestion_status == status_enum)

    # Apply content_type filter
    if with_content_type:
        from kurt.db.models import ContentType

        content_type_enum = ContentType(with_content_type.lower())
        stmt = stmt.where(Document.content_type == content_type_enum)

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
        from kurt.content.filtering import resolve_ids_to_uuids

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
        if with_status:
            try:
                status_filter = IngestionStatus[with_status]
            except KeyError:
                raise ValueError(
                    f"Invalid status: {with_status}. Must be one of: NOT_FETCHED, FETCHED, ERROR"
                )
        else:
            # Default to FETCHED for backwards compatibility
            status_filter = IngestionStatus.FETCHED

        # Get documents with status filter
        docs = list_documents(
            status=status_filter,
            url_prefix=None,
            url_contains=None,
            limit=None,
        )

        # Apply cluster filter if provided
        if in_cluster:
            docs = [d for d in docs if d.cluster and d.cluster == in_cluster]

        # Apply content type filter if provided
        if with_content_type:
            from kurt.db.database import get_session
            from kurt.db.models import DocumentClassification

            session = get_session()
            # Get document IDs with matching content type
            classified_ids = set()
            for doc in docs:
                classification = (
                    session.query(DocumentClassification)
                    .filter(DocumentClassification.document_id == doc.id)
                    .first()
                )
                if classification and classification.document_type == with_content_type:
                    classified_ids.add(doc.id)

            docs = [d for d in docs if d.id in classified_ids]

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
                status_counts = {}
                for d in matching_any_status:
                    status = d.ingestion_status.value
                    status_counts[status] = status_counts.get(status, 0) + 1

                status_summary = ", ".join(
                    [f"{count} {status}" for status, count in status_counts.items()]
                )
                raise ValueError(
                    f"Found {len(matching_any_status)} document(s) matching pattern '{include_pattern}' "
                    f"({status_summary}), but none are {status_filter.value}.\n"
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
    from sqlmodel import or_

    session = get_session()

    if not url_list:
        return {}

    # Query for documents matching these URLs
    # Check both source_url and discovery_url (for CMS documents with public URLs)
    stmt = select(Document).where(
        or_(Document.source_url.in_(url_list), Document.discovery_url.in_(url_list))
    )

    # Build mapping of URL -> doc_id (check both source_url and discovery_url)
    url_to_id = {}
    for doc in session.exec(stmt).all():
        if doc.source_url in url_list:
            url_to_id[doc.source_url] = doc.id
        if doc.discovery_url in url_list:
            url_to_id[doc.discovery_url] = doc.id

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
