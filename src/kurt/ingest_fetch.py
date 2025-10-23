"""
Content fetching and storage functions for Kurt.

This module handles downloading and storing document content:
- Fetching content from URLs using trafilatura
- Extracting metadata (title, author, dates, description)
- Storing content as markdown files
- Batch async fetching for performance

Key Functions:
- add_document: Create document record (NOT_FETCHED status)
- fetch_document: Download and store content for a document
- fetch_documents_batch: Async batch fetch for multiple documents
"""

import asyncio
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import trafilatura

from kurt.config import KurtConfig, load_config
from kurt.database import get_session
from kurt.models.models import Document, IngestionStatus, SourceType


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
    source_base = config.get_absolute_source_path()
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


def fetch_document(identifier: str) -> dict:
    """
    Fetch content for document (by ID or URL).

    If identifier is a URL and document doesn't exist, creates it first.
    Downloads content using trafilatura and updates ingestion_status.

    Args:
        identifier: Document UUID or source URL

    Returns:
        dict with keys:
            - document_id: UUID
            - title: str
            - content_length: int
            - status: str ('FETCHED' or 'ERROR')

    Raises:
        ValueError: If document not found or download fails

    Example:
        # Fetch by ID
        result = fetch_document("550e8400-e29b-41d4-a716-446655440000")

        # Fetch by URL (creates if doesn't exist)
        result = fetch_document("https://example.com/page1")

        # Returns: {'document_id': UUID(...), 'title': 'Page 1', ...}
    """
    from sqlmodel import select

    session = get_session()
    doc = None

    # Try to find document
    try:
        # Try as UUID first
        doc_id = UUID(identifier)
        doc = session.get(Document, doc_id)
        if not doc:
            raise ValueError(f"Document not found: {identifier}")

    except ValueError:
        # Not a UUID, treat as URL
        stmt = select(Document).where(Document.source_url == identifier)
        doc = session.exec(stmt).first()

        if not doc:
            # Create new document for this URL
            doc_id = add_document(identifier)
            doc = session.get(Document, doc_id)

    # Update status to indicate we're fetching
    doc.ingestion_status = IngestionStatus.FETCHED  # Will set to ERROR if fails

    try:
        # Download content
        downloaded = trafilatura.fetch_url(doc.source_url)
        if not downloaded:
            raise ValueError(f"Failed to download: {doc.source_url}")

        # Extract metadata using trafilatura
        metadata = trafilatura.extract_metadata(
            downloaded,
            default_url=doc.source_url,
            extensive=True,  # More comprehensive metadata extraction
        )

        # Extract content as markdown
        content = trafilatura.extract(
            downloaded,
            output_format="markdown",
            include_tables=True,
            include_links=True,
            url=doc.source_url,  # Helps with metadata extraction
            with_metadata=True,  # Include metadata in extraction
        )

        if not content:
            raise ValueError(f"No content extracted from: {doc.source_url}")

        # Update document with extracted metadata
        if metadata:
            # Title (prefer metadata title over URL-derived title)
            if metadata.title:
                doc.title = metadata.title

            # Content hash (fingerprint for deduplication)
            if metadata.fingerprint:
                doc.content_hash = metadata.fingerprint

            # Description
            if metadata.description:
                doc.description = metadata.description

            # Author(s) - convert to list if single author
            if metadata.author:
                if isinstance(metadata.author, str):
                    doc.author = [metadata.author]
                else:
                    doc.author = list(metadata.author) if metadata.author else None

            # Published date
            if metadata.date:
                # metadata.date is a string in YYYY-MM-DD format
                from datetime import datetime

                try:
                    doc.published_date = datetime.fromisoformat(metadata.date)
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
        source_base = config.get_absolute_source_path()
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


async def _fetch_one_async(doc_id: str, semaphore: asyncio.Semaphore) -> dict:
    """Fetch single document with concurrency control."""
    async with semaphore:
        try:
            # Run sync fetch_document in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, fetch_document, doc_id)
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
) -> list[dict]:
    """
    Fetch multiple documents in parallel using async HTTP.

    Args:
        document_ids: List of document UUIDs or URLs to fetch
        max_concurrent: Maximum number of concurrent downloads (default: 5)

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

        # Check results
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
    """

    async def _batch_fetch():
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [_fetch_one_async(doc_id, semaphore) for doc_id in document_ids]
        return await asyncio.gather(*tasks)

    return asyncio.run(_batch_fetch())
