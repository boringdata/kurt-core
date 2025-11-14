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
import logging
import os
from uuid import UUID

from dotenv import find_dotenv, load_dotenv

from kurt.config import KurtConfig, load_config
from kurt.content.fetch_firecrawl import fetch_with_firecrawl
from kurt.content.fetch_trafilatura import fetch_with_httpx, fetch_with_trafilatura
from kurt.content.paths import create_cms_content_path, create_content_path, parse_source_identifier
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType

logger = logging.getLogger(__name__)

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
    2. Use INGESTION_FETCH_ENGINE from kurt.config
    3. If config engine is 'firecrawl' but no API key → fall back to trafilatura
    4. Default to trafilatura if config not found

    Args:
        override: Optional engine override ('firecrawl', 'trafilatura', or 'httpx')

    Returns:
        Engine name: 'firecrawl', 'trafilatura', or 'httpx'
    """
    # Handle override
    if override:
        override = override.lower()
        if override not in KurtConfig.VALID_FETCH_ENGINES:
            raise ValueError(
                f"Invalid fetch engine: {override}. Must be one of {KurtConfig.VALID_FETCH_ENGINES}"
            )

        # Validate Firecrawl API key if using Firecrawl
        if override == "firecrawl":
            firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
            if not firecrawl_api_key or firecrawl_api_key == "your_firecrawl_api_key_here":
                raise ValueError(
                    "Cannot use Firecrawl: FIRECRAWL_API_KEY not set or invalid.\n"
                    f"Add your API key to .env file or use --fetch-engine={KurtConfig.VALID_FETCH_ENGINES[0]}"
                )
        return override

    # Priority 2: Use configured engine from kurt.config
    try:
        config = load_config()
        configured_engine = config.INGESTION_FETCH_ENGINE.lower()

        # Validate configured engine
        if configured_engine not in KurtConfig.VALID_FETCH_ENGINES:
            # Invalid engine in config - fall back to default
            return KurtConfig.DEFAULT_FETCH_ENGINE

        # If Firecrawl is configured, verify API key is available
        if configured_engine == "firecrawl":
            firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
            if not firecrawl_api_key or firecrawl_api_key == "your_firecrawl_api_key_here":
                # Silently fall back to trafilatura if Firecrawl configured but no API key
                return KurtConfig.DEFAULT_FETCH_ENGINE

        # Return the configured engine (httpx, trafilatura, or firecrawl with valid API key)
        return configured_engine

    except Exception:
        # Priority 3: Config file not found or failed to load → use default
        return KurtConfig.DEFAULT_FETCH_ENGINE


def _fetch_from_cms(platform: str, instance: str, doc: Document) -> tuple[str, dict]:
    """
    Fetch content from CMS using appropriate adapter.

    Args:
        platform: CMS platform name
        instance: Instance name
        doc: Document object (must have cms_document_id field populated)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If CMS fetch fails or cms_document_id is missing
    """
    from kurt.integrations.cms import get_adapter
    from kurt.integrations.cms.config import get_platform_config

    # Validate cms_document_id is present
    if not doc.cms_document_id:
        raise ValueError(
            f"Document {doc.id} is missing cms_document_id field. "
            f"This field is required to fetch from CMS. "
            f"Document may have been created before cms_document_id migration."
        )

    try:
        # Get CMS adapter
        cms_config = get_platform_config(platform, instance)
        adapter = get_adapter(platform, cms_config)

        # Fetch document using CMS document ID (not the slug)
        cms_document = adapter.fetch(doc.cms_document_id)

        # Extract metadata
        metadata_dict = {
            "title": cms_document.title,
            "author": cms_document.author,
            "date": cms_document.published_date,
            "description": cms_document.metadata.get("description")
            if cms_document.metadata
            else None,
        }

        return cms_document.content, metadata_dict

    except Exception as e:
        raise ValueError(
            f"Failed to fetch from {platform}/{instance} (cms_document_id: {doc.cms_document_id}): {e}"
        )


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
        # Check if this is a CMS document (using stored fields)
        if doc.cms_platform and doc.cms_instance:
            # CMS document - use stored platform/instance fields
            content, metadata_dict = _fetch_from_cms(
                platform=doc.cms_platform, instance=doc.cms_instance, doc=doc
            )
        else:
            # Web URL - use web scraping engines
            # First check if it looks like a CMS URL pattern (legacy check)
            source_type, parsed_data = parse_source_identifier(doc.source_url)

            if source_type == "cms":
                # CMS URL detected but missing platform/instance fields
                # This shouldn't happen with new documents
                raise ValueError(
                    f"Document {doc.id} has CMS URL pattern but missing cms_platform/cms_instance fields. "
                    f"URL: {doc.source_url}. Please recreate this document using 'kurt content map cms'."
                )

            # Standard web fetch
            engine = _get_fetch_engine(override=fetch_engine)

            if engine == "firecrawl":
                content, metadata_dict = fetch_with_firecrawl(doc.source_url)
            elif engine == "httpx":
                content, metadata_dict = fetch_with_httpx(doc.source_url)
            else:
                content, metadata_dict = fetch_with_trafilatura(doc.source_url)

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

        # Generate document embedding for knowledge graph (Stage 0)
        try:
            import dspy
            import numpy as np

            # Get configured embedding model
            embed_config = load_config()
            embedding_model = embed_config.EMBEDDING_MODEL

            # Use first 1000 chars of content for embedding
            content_sample = content[:1000] if len(content) > 1000 else content
            embedding_vector = dspy.Embedder(model=embedding_model)([content_sample])[0]
            doc.embedding = np.array(embedding_vector, dtype=np.float32).tobytes()
            logger.debug(
                f"Generated document embedding ({len(embedding_vector)} dims) using {embedding_model}"
            )
        except Exception as e:
            logger.warning(f"Could not generate document embedding: {e}")
            # Continue without embedding - it's optional

        # Store content to filesystem
        config = load_config()

        # Choose path based on document type (CMS vs Web)
        if doc.cms_platform and doc.cms_instance:
            # CMS: sources/cms/{platform}/{instance}/{cms_document_id}.md
            content_path = create_cms_content_path(
                platform=doc.cms_platform,
                instance=doc.cms_instance,
                doc_id=doc.cms_document_id,
                config=config,
            )
        else:
            # Web: sources/{domain}/{path}/page_name.md
            content_path = create_content_path(doc.source_url, config)

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
    progress_callback=None,
) -> list[dict]:
    """
    Fetch multiple documents in parallel using async HTTP.

    Args:
        document_ids: List of document UUIDs or URLs to fetch
        max_concurrent: Maximum number of concurrent downloads (default: 5)
        fetch_engine: Optional engine override ('firecrawl' or 'trafilatura')
        progress_callback: Optional callback function called after each document completes

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
    # Log batch fetch start
    logger.info(f"Starting batch fetch for {len(document_ids)} documents")
    logger.info(f"  Concurrency: {max_concurrent}")

    # Show warning if using Trafilatura for large batch
    engine = _get_fetch_engine(override=fetch_engine)
    logger.info(f"  Fetch engine: {engine}")

    if engine == "trafilatura" and len(document_ids) > 10:
        warning_msg = (
            "⚠️  Warning: Fetching large volumes with Trafilatura may encounter rate limits. "
            "For better reliability with large batches, consider using Firecrawl."
        )
        # Only print once, don't also log to avoid duplication
        print(f"\n{warning_msg}")
        print("\n   To switch to Firecrawl:")
        print('   1. Set in kurt.config: INGESTION_FETCH_ENGINE="firecrawl"')
        print("   2. Add FIRECRAWL_API_KEY to your .env file")
        print("   3. Get your API key at: https://firecrawl.dev")
        print("\n   Note: Both the config setting AND the API key are required.\n")

    async def _batch_fetch():
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _fetch_with_progress(doc_id):
            result = await _fetch_one_async(doc_id, semaphore, fetch_engine)
            if progress_callback:
                progress_callback()  # Call progress callback after each completion
            return result

        tasks = [_fetch_with_progress(doc_id) for doc_id in document_ids]
        results = await asyncio.gather(*tasks)

        # Log progress every 10 documents or at completion
        successful_count = sum(1 for r in results if r["success"])
        failed_count = len(results) - successful_count
        logger.info(
            f"Fetching complete: {successful_count} successful, {failed_count} failed [{len(results)}/{len(document_ids)}]"
        )

        return results

    results = asyncio.run(_batch_fetch())

    # Log final summary
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    logger.info(f"✓ Fetched {len(successful)}/{len(results)} documents successfully")
    if failed:
        logger.info(f"  Failed: {len(failed)}")

    return results


def fetch_content(
    include_pattern: str = None,
    urls: str = None,
    files: str = None,
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
        files: Comma-separated list of local file paths (creates documents, skips fetch)
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
    if not (
        include_pattern or urls or files or ids or in_cluster or with_status or with_content_type
    ):
        raise ValueError(
            "Requires at least ONE filter: --include, --url, --urls, --file, --files, --ids, --in-cluster, --with-status, or --with-content-type"
        )

    warnings = []
    errors = []

    session = get_session()

    # Build query based on filters
    stmt = select(Document)

    # Filter by IDs (supports partial UUIDs, URLs, and file paths)
    if ids:
        from uuid import UUID

        from kurt.content.filtering import resolve_ids_to_uuids

        try:
            # Resolve all identifiers to full UUIDs (handles partial UUIDs, URLs, file paths)
            uuid_strs = resolve_ids_to_uuids(ids)
            doc_ids = [UUID(uuid_str) for uuid_str in uuid_strs]

            if doc_ids:
                stmt = stmt.where(Document.id.in_(doc_ids))
        except ValueError as e:
            errors.append(str(e))

    # Filter by URLs (auto-create documents that don't exist)
    if urls:
        url_list = [url.strip() for url in urls.split(",")]

        # Check which URLs already exist in database
        existing_urls_stmt = select(Document).where(Document.source_url.in_(url_list))
        existing_docs = list(session.exec(existing_urls_stmt).all())
        existing_urls = {doc.source_url for doc in existing_docs}

        # Auto-create documents for URLs that don't exist
        new_urls = [url for url in url_list if url not in existing_urls]
        if new_urls:
            for url in new_urls:
                add_document(url)
            # Commit the new documents
            session.commit()
            warnings.append(f"Auto-created {len(new_urls)} document(s) for new URLs")

        # Now filter for all URLs (including newly created ones)
        stmt = stmt.where(Document.source_url.in_(url_list))

    # Handle local files (create documents, mark as FETCHED since content already exists)
    if files:
        from pathlib import Path

        file_list = [f.strip() for f in files.split(",")]
        config = load_config()
        source_base = config.get_absolute_sources_path()

        created_file_docs = []
        for file_path_str in file_list:
            file_path = Path(file_path_str).resolve()

            # Validate file exists
            if not file_path.exists():
                errors.append(f"File not found: {file_path_str}")
                continue

            if not file_path.is_file():
                errors.append(f"Not a file: {file_path_str}")
                continue

            # Check if document already exists for this file
            # Try to find by content_path (relative to sources directory)
            try:
                relative_path = file_path.relative_to(source_base)
                content_path_str = str(relative_path)
            except ValueError:
                # File is outside sources directory - copy it there
                # Create a reasonable path structure
                file_name = file_path.name
                dest_path = source_base / "local" / file_name
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file content
                import shutil

                shutil.copy2(file_path, dest_path)

                relative_path = dest_path.relative_to(source_base)
                content_path_str = str(relative_path)
                warnings.append(f"Copied {file_path.name} to sources/local/")

            # Check if document exists
            existing_stmt = select(Document).where(Document.content_path == content_path_str)
            existing_doc = session.exec(existing_stmt).first()

            if existing_doc:
                created_file_docs.append(existing_doc)
                continue

            # Create new document
            # Extract title from filename (without extension)
            title = file_path.stem

            # Read content to get a basic description
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Use first line as description if it looks like a title
                    first_line = content.split("\n")[0].strip()
                    if first_line.startswith("#"):
                        title = first_line.lstrip("#").strip()
            except Exception:
                content = None

            new_doc = Document(
                title=title,
                source_type=SourceType.FILE_UPLOAD,
                content_path=content_path_str,
                ingestion_status=IngestionStatus.FETCHED,  # Already have the file
            )

            session.add(new_doc)
            created_file_docs.append(new_doc)

        # Commit file documents
        if created_file_docs:
            session.commit()
            # Refresh to get IDs
            for doc in created_file_docs:
                session.refresh(doc)

            new_file_count = len([d for d in created_file_docs if d.id])
            if new_file_count > 0:
                warnings.append(f"Created {new_file_count} document(s) for local files")

        # Filter for these documents
        if created_file_docs:
            file_doc_ids = [doc.id for doc in created_file_docs if doc.id]
            stmt = stmt.where(Document.id.in_(file_doc_ids))

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
