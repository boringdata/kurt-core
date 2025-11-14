"""
DBOS Workflows for Content Discovery (Map Operations)

This module provides durable, resumable workflows for content discovery operations
that can take significant time (crawling, clustering).

Key Features:
- Automatic checkpointing after discovery steps
- Resume from last completed step on crash/restart
- Priority queue support for urgent discovery operations
- Background execution for long-running crawls

Workflows:
- map_url_workflow: Discover content from URL with optional clustering (durable)
"""

from typing import Any

from dbos import DBOS, Queue, SetEnqueueOptions

# Lazy queue initialization - created on first access
_map_queue = None


def get_map_queue():
    """Get or create the map queue (lazy initialization)."""
    global _map_queue
    if _map_queue is None:
        from kurt.workflows import get_dbos

        get_dbos()  # Ensure DBOS is initialized
        _map_queue = Queue("map_queue", priority_enabled=True, concurrency=3)
    return _map_queue


# For backward compatibility
@property
def map_queue():
    return get_map_queue()


@DBOS.step()
def map_url_step(
    url: str,
    sitemap_path: str | None = None,
    include_blogrolls: bool = False,
    max_depth: int | None = None,
    max_pages: int = 1000,
    allow_external: bool = False,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    cluster_urls: bool = False,
) -> dict[str, Any]:
    """
    Individual map step - DBOS checkpoints after completion.

    This can be a long-running operation (crawling), protected by checkpoint.
    Won't re-run if workflow restarts after this step completes.

    Args:
        url: URL to discover content from
        sitemap_path: Override sitemap location
        include_blogrolls: Enable LLM blogroll date extraction
        max_depth: Maximum crawl depth for spider-based discovery
        max_pages: Max pages to discover per operation
        allow_external: Follow and include links to external domains
        include_patterns: Include URL patterns
        exclude_patterns: Exclude URL patterns
        cluster_urls: Cluster discovered URLs into topics

    Returns:
        dict with discovery results
    """
    from kurt.content.map import map_url_content

    # Publish progress event - starting discovery
    DBOS.set_event("phase", "discovering")
    DBOS.set_event("url", url)

    result = map_url_content(
        url=url,
        sitemap_path=sitemap_path,
        include_blogrolls=include_blogrolls,
        max_depth=max_depth,
        max_pages=max_pages,
        allow_external=allow_external,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        dry_run=False,
        cluster_urls=cluster_urls,
        progress=None,  # No progress UI in background mode
    )

    # Publish progress event - discovery complete
    DBOS.set_event("phase", "complete")
    DBOS.set_event("total_discovered", result["total"])
    DBOS.set_event("method", result["method"])

    return result


@DBOS.workflow()
def map_url_workflow(
    url: str,
    sitemap_path: str | None = None,
    include_blogrolls: bool = False,
    max_depth: int | None = None,
    max_pages: int = 1000,
    allow_external: bool = False,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    cluster_urls: bool = False,
) -> dict[str, Any]:
    """
    Durable workflow for discovering content from a URL.

    If this crashes, DBOS will automatically resume from the last completed step.

    Args:
        url: URL to discover content from
        sitemap_path: Override sitemap location
        include_blogrolls: Enable LLM blogroll date extraction
        max_depth: Maximum crawl depth for spider-based discovery
        max_pages: Max pages to discover per operation
        allow_external: Follow and include links to external domains
        include_patterns: Include URL patterns
        exclude_patterns: Exclude URL patterns
        cluster_urls: Cluster discovered URLs into topics

    Returns:
        dict with keys:
            - url: str
            - total: int
            - new: int
            - existing: int
            - method: str
            - discovered: list
            - cluster_count: int (if clustered)
    """
    DBOS.logger.info(f"Starting map workflow for URL: {url}")

    # Publish event - workflow started
    DBOS.set_event("status", "started")
    DBOS.set_event("target_url", url)

    result = map_url_step(
        url=url,
        sitemap_path=sitemap_path,
        include_blogrolls=include_blogrolls,
        max_depth=max_depth,
        max_pages=max_pages,
        allow_external=allow_external,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        cluster_urls=cluster_urls,
    )

    DBOS.logger.info(f"Completed map workflow: {result['total']} URLs discovered")

    # Publish event - workflow completed
    DBOS.set_event("status", "completed")
    DBOS.set_event("result_total", result["total"])
    DBOS.set_event("result_new", result["new"])
    DBOS.set_event("result_existing", result["existing"])

    return {
        "url": url,
        "total": result["total"],
        "new": result["new"],
        "existing": result["existing"],
        "method": result["method"],
        "discovered": result["discovered"],
        "cluster_count": result.get("cluster_count", 0),
    }


# Priority Queue Helper Functions


def enqueue_map_with_priority(
    url: str,
    priority: int = 10,
    sitemap_path: str | None = None,
    include_blogrolls: bool = False,
    max_depth: int | None = None,
    max_pages: int = 1000,
    allow_external: bool = False,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    cluster_urls: bool = False,
) -> str:
    """
    Enqueue a map job with specific priority.

    Priority ranges from 1 (highest) to 2,147,483,647 (lowest).
    Lower number = higher priority.

    Args:
        url: URL to discover content from
        priority: Priority level (1=highest, default=10)
        sitemap_path: Override sitemap location
        include_blogrolls: Enable LLM blogroll date extraction
        max_depth: Maximum crawl depth for spider-based discovery
        max_pages: Max pages to discover per operation
        allow_external: Follow and include links to external domains
        include_patterns: Include URL patterns
        exclude_patterns: Exclude URL patterns
        cluster_urls: Cluster discovered URLs into topics

    Returns:
        Workflow ID
    """
    queue = get_map_queue()
    with SetEnqueueOptions(priority=priority):
        handle = queue.enqueue(
            map_url_workflow,
            url=url,
            sitemap_path=sitemap_path,
            include_blogrolls=include_blogrolls,
            max_depth=max_depth,
            max_pages=max_pages,
            allow_external=allow_external,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            cluster_urls=cluster_urls,
        )

    return handle.workflow_id


__all__ = [
    "map_url_workflow",
    "enqueue_map_with_priority",
    "map_queue",
]
