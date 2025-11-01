"""
Content fetching and storage functions for Kurt.

This module handles downloading and storing document content:
- Fetching content from URLs using Firecrawl or Trafilatura
- Extracting metadata (title, author, dates, description)
- Storing content as markdown files
- Batch async fetching for performance

Fetch Engine Selection:
- If FIRECRAWL_API_KEY is set in environment → use Firecrawl
- Otherwise → use Trafilatura (fallback)

Key Functions:
- add_document: Create document record (NOT_FETCHED status)
- fetch_document: Download and store content for a document
- fetch_documents_batch: Async batch fetch for multiple documents
"""

import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import trafilatura
from dotenv import find_dotenv, load_dotenv

from kurt.config import KurtConfig, load_config
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType

# Load environment variables from .env file
# Search from current working directory upwards
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path, override=False)
else:
    # If no .env found from cwd, try the default search (from module location)
    load_dotenv(override=False)


def _get_fetch_engine(override: str = None) -> str:
    """
    Determine which fetch engine to use based on configuration and API key availability.

    Priority:
    1. If override is specified → use override (if valid)
    2. If INGESTION_FETCH_ENGINE is 'firecrawl' AND FIRECRAWL_API_KEY is set → use Firecrawl
    3. Otherwise → use Trafilatura (fallback)

    Args:
        override: Optional engine override ('firecrawl' or 'trafilatura')

    Returns:
        'firecrawl' if configured and API key available, otherwise 'trafilatura'
    """
    # Handle override
    if override:
        override = override.lower()
        if override == "firecrawl":
            firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
            if not firecrawl_api_key or firecrawl_api_key == "your_firecrawl_api_key_here":
                raise ValueError(
                    "Cannot use Firecrawl: FIRECRAWL_API_KEY not set or invalid.\n"
                    "Add your API key to .env file or use --fetch-engine=trafilatura"
                )
            return "firecrawl"
        elif override == "trafilatura":
            return "trafilatura"
        else:
            raise ValueError(
                f"Invalid fetch engine: {override}. Must be 'firecrawl' or 'trafilatura'"
            )

    # Use config default
    try:
        config = load_config()
        default_engine = config.INGESTION_FETCH_ENGINE.lower()
    except Exception:
        # If config fails to load, default to trafilatura
        default_engine = "trafilatura"

    # Check if Firecrawl is requested
    if default_engine == "firecrawl":
        firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")

        # Verify API key is set and valid (not a placeholder)
        if firecrawl_api_key and firecrawl_api_key != "your_firecrawl_api_key_here":
            return "firecrawl"

    # Default to trafilatura
    return "trafilatura"


def _fetch_with_firecrawl(url: str) -> tuple[str, dict]:
    """
    Fetch content using Firecrawl API.

    Args:
        url: URL to fetch

    Returns:
        Tuple of (content_markdown, metadata_dict)

    Raises:
        Exception: If fetch fails
    """
    from firecrawl import FirecrawlApp

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        raise ValueError("[Firecrawl] FIRECRAWL_API_KEY not set in environment")

    try:
        app = FirecrawlApp(api_key=api_key)
        # Scrape the URL and get markdown using the v2 API
        result = app.scrape(url, formats=["markdown", "html"])
    except Exception as e:
        raise ValueError(f"[Firecrawl] API error: {type(e).__name__}: {str(e)}") from e

    if not result or not hasattr(result, "markdown"):
        raise ValueError(f"[Firecrawl] No content extracted from: {url}")

    content = result.markdown

    # Extract metadata from Firecrawl response
    metadata = {}
    if hasattr(result, "metadata") and result.metadata:
        metadata = result.metadata if isinstance(result.metadata, dict) else {}

    return content, metadata


def _fetch_with_trafilatura(url: str) -> tuple[str, dict]:
    """
    Fetch content using Trafilatura.

    Args:
        url: URL to fetch

    Returns:
        Tuple of (content_markdown, metadata_dict)

    Raises:
        ValueError: If fetch fails
    """
    # Download content
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"[Trafilatura] Failed to download (no content returned): {url}")
    except Exception as e:
        raise ValueError(f"[Trafilatura] Download error: {type(e).__name__}: {str(e)}") from e

    # Extract metadata using trafilatura
    metadata = trafilatura.extract_metadata(
        downloaded,
        default_url=url,
        extensive=True,  # More comprehensive metadata extraction
    )

    # Extract content as markdown
    content = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_tables=True,
        include_links=True,
        url=url,  # Helps with metadata extraction
        with_metadata=True,  # Include metadata in extraction
    )

    if not content:
        raise ValueError(
            f"[Trafilatura] No content extracted (page might be empty or paywall blocked): {url}"
        )

    # Convert trafilatura metadata to dict
    metadata_dict = {}
    if metadata:
        metadata_dict = {
            "title": metadata.title,
            "author": metadata.author,
            "date": metadata.date,
            "description": metadata.description,
            "fingerprint": metadata.fingerprint,
        }

    return content, metadata_dict


def _create_content_path(url: str, config: KurtConfig) -> Path:
    """
    Create filesystem path for storing content.

    Format: {source_path}/{domain}/{subdomain}/{path}/page_name.md

    Example:
        url: https://docs.example.com/guide/getting-started
        → sources/docs.example.com/guide/getting-started.md

        url: https://example.com/
        → sources/example.com/index.md

        url: https://www.example.com/
        → sources/example.com/index.md (www stripped for consistency)
    """
    parsed = urlparse(url)

    # Get domain (netloc includes port if present)
    domain = parsed.netloc or "unknown"

    # Normalize domain: strip 'www.' prefix for consistency
    # This ensures www.getdbt.com and getdbt.com map to the same folder
    if domain.startswith("www."):
        domain = domain[4:]  # Remove "www."

    # Get path components
    path = parsed.path.strip("/")

    # If empty path, use 'index'
    if not path:
        path = "index"

    # If path ends with /, append 'index'
    if path.endswith("/"):
        path = path + "index"

    # Add .md extension if not present
    if not path.endswith(".md"):
        path = path + ".md"

    # Build full path: source_path/domain/path
    source_base = config.get_absolute_sources_path()
    content_path = source_base / domain / path

    return content_path


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
    from sqlmodel import select

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


def fetch_document(identifier: str | UUID, fetch_engine: str = None) -> dict:
    """
    Fetch content for document (by ID or URL).

    If identifier is a URL and document doesn't exist, creates it first.
    Downloads content using the specified fetch engine or config default.

    Args:
        identifier: Document UUID (as string or UUID object) or source URL
        fetch_engine: Optional engine override ('firecrawl' or 'trafilatura')

    Returns:
        dict with keys:
            - document_id: UUID
            - title: str
            - content_length: int
            - status: str ('FETCHED' or 'ERROR')

    Raises:
        ValueError: If document not found or download fails

    Example:
        # Fetch by ID (string)
        result = fetch_document("550e8400-e29b-41d4-a716-446655440000")

        # Fetch by ID (UUID object)
        result = fetch_document(UUID("550e8400-e29b-41d4-a716-446655440000"))

        # Fetch by URL (creates if doesn't exist)
        result = fetch_document("https://example.com/page1")

        # Fetch using specific engine
        result = fetch_document("https://example.com/page1", fetch_engine="firecrawl")

        # Returns: {'document_id': UUID(...), 'title': 'Page 1', ...}
    """
    from sqlmodel import select

    session = get_session()
    doc = None

    # Try to find document
    try:
        # If already a UUID object, use it directly; otherwise try to parse as UUID
        if isinstance(identifier, UUID):
            doc_id = identifier
        else:
            doc_id = UUID(identifier)

        doc = session.get(Document, doc_id)
        if not doc:
            raise ValueError(f"Document not found: {identifier}")

    except (ValueError, AttributeError):
        # Not a UUID, treat as URL
        stmt = select(Document).where(Document.source_url == identifier)
        doc = session.exec(stmt).first()

        if not doc:
            # Create new document for this URL
            doc_id = add_document(str(identifier))
            doc = session.get(Document, doc_id)

    # Update status to indicate we're fetching
    doc.ingestion_status = IngestionStatus.FETCHED  # Will set to ERROR if fails

    try:
        # Determine which fetch engine to use
        engine = _get_fetch_engine(override=fetch_engine)

        # Fetch content using appropriate engine
        if engine == "firecrawl":
            content, metadata_dict = _fetch_with_firecrawl(doc.source_url)
        else:
            content, metadata_dict = _fetch_with_trafilatura(doc.source_url)

        # Update document with extracted metadata
        if metadata_dict:
            # Title (prefer metadata title over URL-derived title)
            if metadata_dict.get("title"):
                doc.title = metadata_dict["title"]

            # Content hash (fingerprint for deduplication)
            if metadata_dict.get("fingerprint"):
                doc.content_hash = metadata_dict["fingerprint"]

            # Description
            if metadata_dict.get("description"):
                doc.description = metadata_dict["description"]

            # Author(s) - convert to list if single author
            author = metadata_dict.get("author")
            if author:
                if isinstance(author, str):
                    doc.author = [author]
                else:
                    doc.author = list(author) if author else None

            # Published date
            date_str = metadata_dict.get("date")
            if date_str:
                # metadata.date is a string in YYYY-MM-DD format
                from datetime import datetime

                try:
                    doc.published_date = datetime.fromisoformat(date_str)
                except (ValueError, AttributeError):
                    # If parsing fails, store as None
                    doc.published_date = None

        # Store content to filesystem
        # Format: {project_root}/{source_path}/{domain}/{path}/page_name.md
        config = load_config()
        content_path = _create_content_path(doc.source_url, config)

        # Create directory structure
        content_path.parent.mkdir(parents=True, exist_ok=True)

        # Write markdown content
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Store relative path in document
        source_base = config.get_absolute_sources_path()
        doc.content_path = str(content_path.relative_to(source_base))
        doc.ingestion_status = IngestionStatus.FETCHED

        session.commit()

        return {
            "document_id": doc.id,
            "title": doc.title,
            "content_length": len(content),
            "status": "FETCHED",
            "content_path": str(content_path),
            "content": content,  # Return content for immediate use
            # Metadata fields
            "content_hash": doc.content_hash,
            "description": doc.description,
            "author": doc.author,
            "published_date": doc.published_date,
        }

    except Exception as e:
        # Mark as ERROR
        doc.ingestion_status = IngestionStatus.ERROR
        session.commit()
        raise e


async def _fetch_one_async(
    doc_id: str, semaphore: asyncio.Semaphore, fetch_engine: str = None
) -> dict:
    """Fetch single document with concurrency control."""
    async with semaphore:
        try:
            # Run sync fetch_document in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch_document, doc_id, fetch_engine)
            return {"success": True, **result}
        except Exception as e:
            return {
                "success": False,
                "document_id": doc_id,
                "error": str(e),
            }


def fetch_documents_batch(
    document_ids: list[str],
    max_concurrent: int = 5,
    fetch_engine: str = None,
) -> list[dict]:
    """
    Fetch multiple documents in parallel using async HTTP.

    Args:
        document_ids: List of document UUIDs or URLs to fetch
        max_concurrent: Maximum number of concurrent downloads (default: 5)
        fetch_engine: Optional engine override ('firecrawl' or 'trafilatura')

    Returns:
        List of results, one per document:
            - success: bool
            - document_id: UUID
            - title: str (if success)
            - content_length: int (if success)
            - error: str (if failed)

    Example:
        # Fetch all NOT_FETCHED documents from a URL
        results = fetch_documents_batch([
            "550e8400-e29b-41d4-a716-446655440000",
            "660e9500-f30c-52e5-b827-557766551111",
        ], max_concurrent=10)

        # Fetch using specific engine
        results = fetch_documents_batch(doc_ids, fetch_engine="firecrawl")

        # Check results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
    """
    # Show warning if using Trafilatura for large batch
    engine = _get_fetch_engine(override=fetch_engine)
    if engine == "trafilatura" and len(document_ids) > 10:
        print("\n⚠️  Warning: Fetching large volumes with Trafilatura may encounter rate limits.")
        print("   For better reliability with large batches, consider using Firecrawl:")
        print('   1. Update kurt.config: INGESTION_FETCH_ENGINE="firecrawl"')
        print("   2. Add FIRECRAWL_API_KEY to your .env file")
        print("   Get your API key at: https://firecrawl.dev\n")

    async def _batch_fetch():
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [_fetch_one_async(doc_id, semaphore, fetch_engine) for doc_id in document_ids]
        return await asyncio.gather(*tasks)

    return asyncio.run(_batch_fetch())


def fetch_content(
    include_pattern: str = None,
    urls: str = None,
    ids: str = None,
    in_cluster: str = None,
    with_status: str = None,
    with_content_type: str = None,
    exclude: str = None,
    limit: int = None,
    concurrency: int = 5,
    engine: str = None,
    skip_index: bool = False,
    refetch: bool = False,
) -> dict:
    """
    High-level fetch function with filtering, validation, and orchestration.

    This function handles all the business logic for fetching documents:
    - Filter selection and validation
    - Database query building
    - Glob pattern matching
    - Document count warnings
    - Batch fetching orchestration

    Args:
        include_pattern: Glob pattern matching source_url or content_path
        urls: Comma-separated list of source URLs
        ids: Comma-separated list of document IDs
        in_cluster: Cluster name to fetch from
        with_status: Status filter (NOT_FETCHED | FETCHED | ERROR)
        with_content_type: Content type filter (tutorial | guide | blog | etc)
        exclude: Glob pattern to exclude
        limit: Max documents to process
        concurrency: Parallel requests (default: 5)
        engine: Fetch engine (trafilatura | firecrawl)
        skip_index: Skip LLM indexing
        refetch: Include already FETCHED documents

    Returns:
        dict with:
            - docs: List of Document objects to fetch
            - doc_ids: List of document IDs
            - total: Total count
            - warnings: List of warning messages
            - errors: List of error messages

    Raises:
        ValueError: If no filter is provided or invalid parameters
    """
    from fnmatch import fnmatch

    from sqlmodel import select

    from kurt.db.database import get_session
    from kurt.db.models import Document, IngestionStatus

    # Validate: at least one filter required
    if not (include_pattern or urls or ids or in_cluster or with_status or with_content_type):
        raise ValueError(
            "Requires at least ONE filter: --include, --urls, --ids, --in-cluster, --with-status, or --with-content-type"
        )

    warnings = []
    errors = []

    session = get_session()

    # Build query based on filters
    stmt = select(Document)

    # Filter by IDs
    if ids:
        from uuid import UUID

        doc_ids = [UUID(id.strip()) for id in ids.split(",")]
        stmt = stmt.where(Document.id.in_(doc_ids))

    # Filter by URLs
    if urls:
        url_list = [url.strip() for url in urls.split(",")]
        stmt = stmt.where(Document.source_url.in_(url_list))

    # Filter by cluster (JOIN with edges and clusters tables)
    if in_cluster:
        from kurt.db.models import DocumentClusterEdge, TopicCluster

        stmt = (
            stmt.join(DocumentClusterEdge, Document.id == DocumentClusterEdge.document_id)
            .join(TopicCluster, DocumentClusterEdge.cluster_id == TopicCluster.id)
            .where(TopicCluster.name.ilike(f"%{in_cluster}%"))
        )

    # Filter by content type
    if with_content_type:
        from kurt.db.models import ContentType

        try:
            content_type_enum = ContentType(with_content_type.lower())
            stmt = stmt.where(Document.content_type == content_type_enum)
        except ValueError:
            raise ValueError(
                f"Invalid content type: {with_content_type}. "
                f"Valid types: {', '.join([ct.value for ct in ContentType])}"
            )

    # Count total documents before status filter (to track excluded FETCHED docs)
    docs_before_status_filter = list(session.exec(stmt).all())

    # Filter by status (default: exclude FETCHED unless --refetch or --with-status FETCHED)
    if with_status:
        stmt = stmt.where(Document.ingestion_status == IngestionStatus[with_status])
    elif not refetch:
        # Default: exclude FETCHED documents
        stmt = stmt.where(Document.ingestion_status != IngestionStatus.FETCHED)

    docs = list(session.exec(stmt).all())

    # Apply include/exclude patterns (glob matching on source_url or content_path)
    if include_pattern:
        docs = [
            d
            for d in docs
            if (d.source_url and fnmatch(d.source_url, include_pattern))
            or (d.content_path and fnmatch(d.content_path, include_pattern))
        ]

    if exclude:
        docs = [
            d
            for d in docs
            if not (
                (d.source_url and fnmatch(d.source_url, exclude))
                or (d.content_path and fnmatch(d.content_path, exclude))
            )
        ]

    # Apply limit
    if limit:
        docs = docs[:limit]

    # Warn if >100 docs
    if len(docs) > 100:
        warnings.append(f"About to fetch {len(docs)} documents")

    # Calculate estimated cost
    estimated_cost = len(docs) * 0.005 if not skip_index else 0

    # Count excluded FETCHED documents (only if we applied the default filter)
    excluded_fetched_count = 0
    if not with_status and not refetch:
        fetched_docs = [
            d for d in docs_before_status_filter if d.ingestion_status == IngestionStatus.FETCHED
        ]
        excluded_fetched_count = len(fetched_docs)

    return {
        "docs": docs,
        "doc_ids": [str(doc.id) for doc in docs],
        "total": len(docs),
        "warnings": warnings,
        "errors": errors,
        "estimated_cost": estimated_cost,
        "excluded_fetched_count": excluded_fetched_count,
    }
