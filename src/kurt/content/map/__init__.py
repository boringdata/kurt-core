"""
URL and content discovery module for Kurt.

This module provides high-level functions for discovering content from various sources:
- URLs (via sitemap or crawling)
- Local folders
- CMS platforms

All discovery operations create documents with NOT_FETCHED status.
"""

import logging
from fnmatch import fnmatch

from kurt.content.map.blogroll import (
    extract_chronological_content,
    identify_blogroll_candidates,
    map_blogrolls,
)
from kurt.content.map.cms import map_cms_content
from kurt.content.map.crawl import crawl_website
from kurt.content.map.folder import map_folder_content
from kurt.content.map.sitemap import discover_sitemap_urls, map_sitemap

logger = logging.getLogger(__name__)

__all__ = [
    "map_url_content",
    "map_sitemap",
    "map_blogrolls",
    "map_folder_content",
    "map_cms_content",
    "discover_sitemap_urls",
    "crawl_website",
    "identify_blogroll_candidates",
    "extract_chronological_content",
]


def map_url_content(
    url: str,
    sitemap_path: str = None,
    include_blogrolls: bool = False,
    max_depth: int = None,
    max_pages: int = 1000,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    allow_external: bool = False,
    dry_run: bool = False,
    cluster_urls: bool = False,
    progress=None,
) -> dict:
    """
    High-level URL mapping function - discover content from web sources.

    Handles:
    - Sitemap detection and parsing
    - Blogroll date extraction (optional)
    - Crawling fallback if no sitemap
    - Pattern filtering
    - Document creation (NOT_FETCHED status)
    - Optional clustering (if cluster_urls=True)

    Args:
        url: Base URL to map
        sitemap_path: Override sitemap location
        include_blogrolls: Enable LLM blogroll date extraction
        max_depth: Crawl depth if no sitemap found
        max_pages: Max pages to discover (default: 1000)
        include_patterns: Include URL patterns (glob)
        exclude_patterns: Exclude URL patterns (glob)
        allow_external: Follow external links
        dry_run: If True, discover URLs but don't save to database
        cluster_urls: If True, automatically cluster documents after mapping

    Returns:
        dict with:
            - discovered: List of discovered document dicts or URLs (if dry_run)
            - total: Total count
            - new: Count of new documents created (0 if dry_run)
            - existing: Count of existing documents (0 if dry_run)
            - method: Discovery method used (sitemap|blogrolls|crawl)
            - dry_run: Boolean indicating if this was a dry run
    """
    from kurt.utils.url_utils import is_single_page_url

    # DRY RUN MODE: Discover URLs without saving to database
    if dry_run:
        discovery_method = "sitemap"

        # Add progress task
        task_id = None
        if progress:
            task_id = progress.add_task("Discovering URLs...", total=None)

        # Discover URLs from sitemap or crawling
        try:
            # Note: sitemap_path parameter is not used by discover_sitemap_urls yet
            discovered_urls = discover_sitemap_urls(url, progress=progress, task_id=task_id)
            if progress and task_id is not None:
                progress.update(
                    task_id,
                    description="Discovery complete",
                    completed=len(discovered_urls),
                    total=len(discovered_urls),
                )
        except Exception as e:
            # Sitemap failed - try crawling if max_depth is specified
            if max_depth is not None:
                logger.info(
                    f"Sitemap discovery failed in dry-run: {e}. Trying crawl with max_depth={max_depth}"
                )
                discovered_urls = crawl_website(
                    homepage=url,
                    max_depth=max_depth,
                    max_pages=max_pages,
                    allow_external=allow_external,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    progress=progress,
                    task_id=task_id,
                )
                if progress and task_id is not None:
                    progress.update(
                        task_id, completed=len(discovered_urls), total=len(discovered_urls)
                    )
                discovery_method = "crawl"
            else:
                # Fallback to single URL if discovery fails and no max_depth
                discovered_urls = [url]

        # Apply filters (if not already applied by crawl_website)
        if discovery_method == "sitemap":
            filtered_urls = []
            for discovered_url in discovered_urls:
                # Apply include patterns
                if include_patterns:
                    if not any(fnmatch(discovered_url, pattern) for pattern in include_patterns):
                        continue

                # Apply exclude patterns
                if exclude_patterns:
                    if any(fnmatch(discovered_url, pattern) for pattern in exclude_patterns):
                        continue

                filtered_urls.append(discovered_url)

            # Apply limit
            if max_pages:
                filtered_urls = filtered_urls[:max_pages]
        else:
            # Crawling already applied filters
            filtered_urls = discovered_urls

        return {
            "discovered": filtered_urls,  # Just URLs, not document objects
            "total": len(filtered_urls),
            "new": 0,  # Not saved
            "existing": 0,  # Not checked
            "method": discovery_method,
            "dry_run": True,
        }

    # NORMAL MODE: Single page detection
    if is_single_page_url(url):
        # Single page - just create document
        from kurt.content.fetch import add_document

        doc_id = add_document(url)
        result = {
            "discovered": [{"url": url, "doc_id": str(doc_id), "created": True}],
            "total": 1,
            "new": 1,
            "existing": 0,
            "method": "single_page",
            "dry_run": False,
        }

        # Auto-cluster if requested (though clustering 1 page doesn't make sense)
        if cluster_urls:
            from kurt.content.cluster import compute_topic_clusters

            if progress:
                cluster_task = progress.add_task("Clustering documents...", total=None)

                def progress_callback(message):
                    progress.update(cluster_task, description=message)

                cluster_result = compute_topic_clusters(progress_callback=progress_callback)
            else:
                cluster_result = compute_topic_clusters()

            result["clusters"] = cluster_result["clusters"]
            result["cluster_count"] = len(cluster_result["clusters"])

            if progress:
                progress.update(
                    cluster_task, description="Clustering complete", completed=1, total=1
                )

        return result

    # NORMAL MODE: Multi-page discovery with filters
    # Try sitemap first, fall back to crawling if requested and sitemap fails
    docs = []
    discovery_method = "sitemap"

    # Add progress task for discovery
    task_id = None
    if progress:
        task_id = progress.add_task("Discovering URLs...", total=None)

    try:
        docs = map_sitemap(
            url,
            fetch_all=False,
            discover_blogrolls=include_blogrolls,
            max_blogrolls=50 if include_blogrolls else 10,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            limit=max_pages,
            progress=progress,
            task_id=task_id,
        )
        if progress and task_id is not None:
            progress.update(task_id, completed=len(docs), total=len(docs))
    except (ValueError, Exception) as e:
        # Sitemap failed - fall back to crawling
        # Use provided max_depth or default to 2 for automatic fallback
        fallback_depth = max_depth if max_depth is not None else 2

        logger.info(
            f"Sitemap discovery failed: {e}. Falling back to crawling with max_depth={fallback_depth}"
        )

        # Use crawler to discover URLs
        crawled_urls = crawl_website(
            homepage=url,
            max_depth=fallback_depth,  # Use fallback_depth instead of max_depth
            max_pages=max_pages,
            allow_external=allow_external,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            progress=progress,
            task_id=task_id,
        )

        # Create documents for crawled URLs using map-specific batch creation
        from kurt.content.map.utils import batch_create_discovered_documents

        if progress and task_id is not None:
            progress.update(
                task_id,
                description="Creating documents...",
                total=len(crawled_urls),
                completed=len(crawled_urls),
            )

        crawled_docs, new_count = batch_create_discovered_documents(
            url_list=crawled_urls,
            discovery_method="crawl",
            discovery_url=url,
        )

        # Convert to dict format
        for doc in crawled_docs:
            docs.append(
                {
                    "url": doc.source_url,
                    "doc_id": str(doc.id),
                    "created": True,  # Simplified - all from crawl are treated as new
                }
            )

        discovery_method = "crawl"

    new_count = sum(1 for d in docs if d.get("created", False))
    existing_count = len(docs) - new_count

    result = {
        "discovered": docs,
        "total": len(docs),
        "new": new_count,
        "existing": existing_count,
        "method": discovery_method,
        "dry_run": False,
    }

    # Log final summary
    logger.info(f"✓ Discovered {len(docs)} pages")
    logger.info(f"  New: {new_count}")
    logger.info(f"  Existing: {existing_count}")
    logger.info(f"  Method: {discovery_method}")

    # Log sample URLs
    if docs:
        logger.info("")
        logger.info("Sample URLs:")
        for doc in docs[:5]:
            url = doc.get("url", doc.get("path", "N/A"))
            logger.info(f"  • {url}")
        if len(docs) > 5:
            logger.info(f"  ... and {len(docs) - 5} more")

    # Auto-cluster if requested
    if cluster_urls and len(docs) > 0:
        from kurt.content.cluster import compute_topic_clusters

        if progress and task_id is not None:
            progress.update(
                task_id, description=f"Clustering {len(docs)} documents...", completed=0, total=None
            )

            def progress_callback(message):
                progress.update(task_id, description=message)

            cluster_result = compute_topic_clusters(progress_callback=progress_callback)
        else:
            cluster_result = compute_topic_clusters()

        result["clusters"] = cluster_result["clusters"]
        result["cluster_count"] = len(cluster_result["clusters"])

        if progress and task_id is not None:
            progress.update(task_id, description="Clustering complete", completed=1, total=1)

    return result
