"""
Sitemap discovery functionality for Kurt.

This module handles discovering URLs from sitemap.xml files.
"""

import logging
import xml.etree.ElementTree as ET
from fnmatch import fnmatch
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Import centralized logging helper for workflows
try:
    from kurt.workflows.logging_utils import log_progress as _log_progress_helper

    def _log_progress(message: str, progress=None, task_id=None, completed=None, total=None):
        """Wrapper for centralized log_progress that passes our logger."""
        _log_progress_helper(logger, message, progress, task_id, completed, total)

except ImportError:
    # Fallback if workflows module not available
    def _log_progress(message: str, progress=None, task_id=None, completed=None, total=None):
        """Fallback progress logger."""
        log_msg = message
        if completed is not None and total is not None:
            log_msg = f"{message} [{completed}/{total}]"
        elif completed is not None:
            log_msg = f"{message} [completed: {completed}]"
        logger.info(log_msg)
        if progress and task_id is not None:
            progress.update(task_id, description=message, completed=completed, total=total)


def discover_sitemap_urls(base_url: str, progress=None, task_id=None) -> list[str]:
    """
    Discover sitemap URLs using httpx (reliable fetching).

    Workflow:
    1. Check robots.txt for sitemap location
    2. Try common sitemap URLs (/sitemap.xml, /sitemap_index.xml)
    3. Parse sitemap XML to extract URLs

    Args:
        base_url: Base URL to search for sitemaps
        progress: Optional progress object for status updates
        task_id: Optional task ID for progress updates

    Returns:
        List of URLs found in sitemap(s)

    Raises:
        ValueError: If no sitemap found or accessible
    """
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    sitemap_urls = []

    # Step 1: Check robots.txt
    _log_progress("Checking robots.txt...", progress, task_id)

    try:
        response = httpx.get(f"{base}/robots.txt", timeout=10.0, follow_redirects=True)
        if response.status_code == 200:
            for line in response.text.split("\n"):
                if line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    sitemap_urls.append(sitemap_url)
    except Exception:
        pass  # robots.txt not found or not accessible

    # Step 2: Try common sitemap locations
    common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]
    for path in common_paths:
        if f"{base}{path}" not in sitemap_urls:
            sitemap_urls.append(f"{base}{path}")

    # Step 3: Fetch and parse sitemaps
    _log_progress("Fetching sitemap...", progress, task_id)

    all_urls = []

    for sitemap_url in sitemap_urls:
        try:
            response = httpx.get(sitemap_url, timeout=30.0, follow_redirects=True)
            if response.status_code != 200:
                continue

            # Parse XML
            root = ET.fromstring(response.content)

            # Check if it's a sitemap index (contains <sitemap> tags)
            sitemaps = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap")
            if sitemaps:
                # It's a sitemap index - recursively fetch child sitemaps
                _log_progress(
                    f"Parsing sitemap index ({len(sitemaps)} sitemaps)...", progress, task_id
                )

                for idx, sitemap in enumerate(sitemaps):
                    loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                    if loc is not None and loc.text:
                        child_sitemap_url = loc.text.strip()
                        if progress and task_id is not None:
                            progress.update(
                                task_id, description=f"Parsing sitemap {idx+1}/{len(sitemaps)}..."
                            )

                        try:
                            child_response = httpx.get(
                                child_sitemap_url, timeout=30.0, follow_redirects=True
                            )
                            if child_response.status_code == 200:
                                child_root = ET.fromstring(child_response.content)
                                urls = child_root.findall(
                                    ".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"
                                )
                                for url_elem in urls:
                                    loc_elem = url_elem.find(
                                        "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                                    )
                                    if loc_elem is not None and loc_elem.text:
                                        all_urls.append(loc_elem.text.strip())

                                # Update progress with current count
                                if progress and task_id is not None and len(all_urls) % 50 == 0:
                                    progress.update(
                                        task_id, description=f"Discovered {len(all_urls)} URLs..."
                                    )
                        except Exception:
                            continue
            else:
                # It's a regular sitemap - extract URLs
                if progress and task_id is not None:
                    progress.update(task_id, description="Parsing sitemap...")

                urls = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")
                for url_elem in urls:
                    loc = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                    if loc is not None and loc.text:
                        all_urls.append(loc.text.strip())

            # If we found URLs, we're done
            if all_urls:
                return all_urls

        except Exception:
            continue  # Try next sitemap URL

    # No sitemap found
    if not all_urls:
        raise ValueError(f"No sitemap found for {base_url}")

    return all_urls


def map_sitemap(
    url: str,
    fetch_all: bool = False,
    limit: int = None,
    discover_blogrolls: bool = False,
    max_blogrolls: int = 10,
    llm_model: str = None,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    progress=None,
    task_id=None,
) -> list[dict]:
    """
    Discover sitemap and create documents in database with NOT_FETCHED status.

    Uses custom sitemap discovery which handles:
    - Common sitemap locations (/sitemap.xml, etc.)
    - Sitemap indexes (nested sitemaps)
    - robots.txt parsing
    - URL normalization

    Args:
        url: Base URL or specific sitemap URL
        fetch_all: If True, fetch content for all documents immediately
        limit: Maximum number of URLs to process (creates + fetches only this many)
        discover_blogrolls: If True, also discover posts from blogroll/changelog pages
        max_blogrolls: Maximum number of blogroll pages to scrape (if discover_blogrolls=True)
        llm_model: LLM model to use for blogroll extraction

    Returns:
        List of created documents with keys:
            - document_id: UUID
            - url: str
            - title: str
            - status: str ('NOT_FETCHED' or 'FETCHED' if fetch_all=True)
            - is_chronological: bool (only if discovered from blogroll)
            - discovery_method: str (only if discovered from blogroll)

    Raises:
        ValueError: If no sitemap found

    Example:
        # Basic sitemap mapping
        docs = map_sitemap("https://example.com")

        # With blogroll discovery
        docs = map_sitemap("https://example.com", discover_blogrolls=True)
        # Returns sitemap docs + additional posts found on blogroll pages
    """
    # Import fetch step here to avoid circular imports

    # Use custom sitemap discovery
    urls = discover_sitemap_urls(url, progress=progress, task_id=task_id)

    # Apply filters
    if include_patterns:
        filtered = []
        for discovered_url in urls:
            if any(fnmatch(discovered_url, pattern) for pattern in include_patterns):
                filtered.append(discovered_url)
        urls = filtered

    if exclude_patterns:
        filtered = []
        for discovered_url in urls:
            if not any(fnmatch(discovered_url, pattern) for pattern in exclude_patterns):
                filtered.append(discovered_url)
        urls = filtered

    # Apply limit to URL processing
    if limit:
        urls = list(urls)[:limit]

    # Use map-specific batch creation with discovery metadata
    from kurt.content.map.utils import batch_create_discovered_documents

    docs, new_count = batch_create_discovered_documents(
        url_list=urls,
        discovery_method="sitemap",
        discovery_url=url,
    )

    # Convert to dict format expected by callers
    created_docs = []
    existing_count = len(docs) - new_count

    for doc in docs:
        is_new = doc.id not in [d.id for d in docs[:existing_count]]
        created_docs.append(
            {
                "document_id": doc.id,
                "url": doc.source_url,
                "title": doc.title,
                "status": doc.ingestion_status.value,
                "created": is_new,
                "fetched": False,
            }
        )

    # Handle fetch_all option if requested
    if fetch_all:
        from kurt.content.fetch.workflow import fetch_queue, fetch_workflow

        # Enqueue fetch workflows for all newly created documents
        for doc_result in created_docs:
            if doc_result.get("created"):  # Only fetch newly created docs
                try:
                    # Enqueue fetch workflow (non-blocking, durable)
                    handle = fetch_queue.enqueue(
                        fetch_workflow,
                        identifiers=str(doc_result["document_id"]),
                    )
                    doc_result["workflow_id"] = handle.workflow_id
                    doc_result["fetched"] = "enqueued"  # Mark as enqueued, not fetched yet
                except Exception as e:
                    # Continue on enqueue errors
                    doc_result["fetch_error"] = str(e)

    # Optionally discover additional posts from blogroll/changelog pages
    if discover_blogrolls:
        from kurt.config import KurtConfig
        from kurt.content.map.blogroll import map_blogrolls

        if llm_model is None:
            llm_model = KurtConfig.DEFAULT_INDEXING_LLM_MODEL

        if progress and task_id is not None:
            progress.update(
                task_id, description="Discovering blogrolls...", completed=0, total=None
            )
        print("\n--- Discovering blogroll/changelog pages ---")
        sitemap_urls = [doc["url"] for doc in created_docs]
        blogroll_docs = map_blogrolls(
            sitemap_urls,
            llm_model=llm_model,
            max_blogrolls=max_blogrolls,
        )
        created_docs.extend(blogroll_docs)
        if progress and task_id is not None:
            progress.update(
                task_id,
                description="Discovery complete",
                completed=len(created_docs),
                total=len(created_docs),
            )

    return created_docs
