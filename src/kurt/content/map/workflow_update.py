"""
DBOS Workflow for Content Map Updates

This workflow orchestrates periodic content discovery and optional auto-fetch:
1. Check configured content sources (CMS, websites)
2. Refresh content maps (discover new documents)
3. Decide whether to auto-fetch based on settings
4. Execute fetch for new documents if enabled

Use this for scheduled content updates, CI/CD pipelines, or on-demand refreshes.
"""

import logging
from typing import Any

from dbos import DBOS, Queue

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Management
# ============================================================================


@DBOS.step()
def load_content_sources_step() -> dict[str, Any]:
    """
    Load configured content sources from database and config files.

    Returns:
        dict with:
            - cms_sources: List of CMS platform/instance configs
            - website_sources: List of website URL configs with discovery settings
            - total_sources: Total number of sources
    """
    from sqlmodel import func, select

    from kurt.db.database import get_session
    from kurt.db.models import Document
    from kurt.integrations.cms.config import load_cms_config

    # Load CMS sources from config
    cms_config = load_cms_config()
    cms_sources = []

    for platform, instances in cms_config.items():
        for instance_name, instance_config in instances.items():
            # Get content type mappings
            content_types = instance_config.get("content_type_mappings", {})
            enabled_types = [k for k, v in content_types.items() if v.get("enabled")]

            cms_sources.append(
                {
                    "type": "cms",
                    "platform": platform,
                    "instance": instance_name,
                    "content_types": enabled_types,
                    "config": instance_config,
                }
            )

    # Load website sources from database (documents with discovery metadata)
    session = get_session()

    # Find unique base URLs that have been mapped (websites we've discovered content from)
    # Group by domain to identify website sources
    from sqlalchemy import case

    website_stmt = (
        select(
            func.substr(Document.source_url, 1, func.instr(Document.source_url, "/", 9)).label(
                "base_url"
            ),
            func.count(Document.id).label("doc_count"),
            func.sum(case((Document.ingestion_status == "FETCHED", 1), else_=0)).label(
                "fetched_count"
            ),
        )
        .where(Document.source_type == "URL")
        .where(Document.source_url.like("http%"))
        .group_by("base_url")
    )

    website_results = session.exec(website_stmt).all()
    website_sources = []

    for base_url, doc_count, fetched_count in website_results:
        if base_url:  # Skip empty base URLs
            website_sources.append(
                {
                    "type": "website",
                    "url": base_url,
                    "documents_mapped": doc_count or 0,
                    "documents_fetched": fetched_count or 0,
                }
            )

    session.close()

    logger.info(f"Loaded {len(cms_sources)} CMS sources and {len(website_sources)} website sources")

    return {
        "cms_sources": cms_sources,
        "website_sources": website_sources,
        "total_sources": len(cms_sources) + len(website_sources),
    }


@DBOS.step()
def get_auto_fetch_config_step() -> dict[str, Any]:
    """
    Get auto-fetch configuration settings.

    Checks:
    1. Environment variables (KURT_AUTO_FETCH_*)
    2. Config file (.kurt/update-config.json)
    3. Defaults

    Returns:
        dict with:
            - enabled: Whether auto-fetch is enabled
            - max_new_documents: Maximum new documents to auto-fetch per update
            - strategy: "all" (fetch everything) or "sample" (fetch subset)
            - priority_new: Whether to prioritize newly discovered documents
    """
    import json
    import os
    from pathlib import Path

    # Default configuration
    config = {
        "enabled": False,
        "max_new_documents": 50,
        "strategy": "sample",  # or "all"
        "priority_new": True,
    }

    # Check environment variables
    if os.getenv("KURT_AUTO_FETCH_ENABLED", "").lower() in ["true", "1", "yes"]:
        config["enabled"] = True

    if os.getenv("KURT_AUTO_FETCH_MAX_DOCUMENTS"):
        try:
            config["max_new_documents"] = int(os.getenv("KURT_AUTO_FETCH_MAX_DOCUMENTS"))
        except ValueError:
            pass

    if os.getenv("KURT_AUTO_FETCH_STRATEGY") in ["all", "sample"]:
        config["strategy"] = os.getenv("KURT_AUTO_FETCH_STRATEGY")

    # Check config file
    config_path = Path.cwd() / ".kurt" / "update-config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                file_config = json.load(f)
                # Merge file config (takes precedence over env vars)
                if "auto_fetch" in file_config:
                    config.update(file_config["auto_fetch"])
        except Exception as e:
            logger.warning(f"Could not load update config: {e}")

    logger.info(
        f"Auto-fetch config: enabled={config['enabled']}, max={config['max_new_documents']}"
    )

    return config


# ============================================================================
# Content Discovery Steps
# ============================================================================


@DBOS.step()
def refresh_cms_source_step(
    platform: str,
    instance: str,
    content_types: list[str] | None = None,
) -> dict[str, Any]:
    """
    Refresh content map for a single CMS source.

    Args:
        platform: CMS platform (sanity, contentful, etc)
        instance: Instance name (prod, staging, default)
        content_types: Optional list of content types to discover

    Returns:
        dict with discovery results (total, new, existing)
    """
    from kurt.content.map.cms import map_cms_content

    logger.info(f"Refreshing CMS: {platform}/{instance}")

    result = map_cms_content(
        platform=platform,
        instance=instance,
        content_type=None,  # Discover all types
        status="published",  # Only published content
        limit=None,  # No limit
        cluster_urls=False,  # Don't cluster during discovery
        dry_run=False,
        progress=None,
    )

    DBOS.set_event(f"cms_{platform}_{instance}_total", result["total"])
    DBOS.set_event(f"cms_{platform}_{instance}_new", result["new"])

    return {
        "source_type": "cms",
        "platform": platform,
        "instance": instance,
        "total": result["total"],
        "new": result["new"],
        "existing": result["existing"],
        "method": result["method"],
    }


@DBOS.step()
def refresh_website_source_step(
    url: str,
    sitemap_path: str | None = None,
    max_pages: int = 1000,
) -> dict[str, Any]:
    """
    Refresh content map for a single website source.

    Args:
        url: Website base URL
        sitemap_path: Optional sitemap location
        max_pages: Maximum pages to discover

    Returns:
        dict with discovery results (total, new, existing)
    """
    from kurt.content.map import map_url_content

    logger.info(f"Refreshing website: {url}")

    result = map_url_content(
        url=url,
        sitemap_path=sitemap_path,
        include_blogrolls=False,  # Don't use LLM for discovery
        max_depth=None,
        max_pages=max_pages,
        allow_external=False,
        include_patterns=(),
        exclude_patterns=(),
        dry_run=False,
        cluster_urls=False,  # Don't cluster during discovery
        progress=None,
    )

    DBOS.set_event(f"website_{url}_total", result["total"])
    DBOS.set_event(f"website_{url}_new", result["new"])

    return {
        "source_type": "website",
        "url": url,
        "total": result["total"],
        "new": result["new"],
        "existing": result["existing"],
        "method": result["method"],
    }


@DBOS.step()
def select_documents_to_fetch_step(
    max_documents: int = 50,
    strategy: str = "sample",
) -> list[str]:
    """
    Select documents to auto-fetch based on configuration.

    Args:
        max_documents: Maximum documents to select
        strategy: "all" or "sample"

    Returns:
        List of document IDs to fetch
    """
    from sqlmodel import select

    from kurt.db.database import get_session
    from kurt.db.models import Document, IngestionStatus

    session = get_session()

    # Query for NOT_FETCHED documents
    query = (
        select(Document.id)
        .where(Document.ingestion_status == IngestionStatus.NOT_FETCHED)
        .order_by(Document.created_at.desc())  # Prioritize recent discoveries
    )

    if strategy == "sample":
        query = query.limit(max_documents)

    results = session.exec(query).all()
    document_ids = [str(doc_id) for doc_id in results]

    session.close()

    logger.info(f"Selected {len(document_ids)} documents to fetch (strategy={strategy})")

    return document_ids


# ============================================================================
# Main Workflow
# ============================================================================


@DBOS.workflow()
async def content_map_update_workflow(
    refresh_cms: bool = True,
    refresh_websites: bool = True,
    auto_fetch: bool | None = None,  # None = use config
    max_concurrent_fetch: int = 5,
) -> dict[str, Any]:
    """
    Orchestrate content map updates and optional auto-fetch.

    Steps:
    1. Load content sources (CMS + websites)
    2. Load auto-fetch configuration
    3. Refresh each source's content map (discover new documents)
    4. Decide whether to auto-fetch based on config
    5. Execute fetch for new documents if enabled

    Args:
        refresh_cms: Whether to refresh CMS sources
        refresh_websites: Whether to refresh website sources
        auto_fetch: Override auto-fetch config (True/False/None)
        max_concurrent_fetch: Max concurrent fetch operations

    Returns:
        dict with:
            - sources_checked: Number of sources checked
            - cms_results: List of CMS discovery results
            - website_results: List of website discovery results
            - total_discovered: Total documents discovered
            - total_new: Total new documents
            - auto_fetch_enabled: Whether auto-fetch ran
            - documents_fetched: Number of documents fetched (if auto-fetch enabled)
    """

    logger.info("Starting content map update workflow")

    # Publish workflow start event
    DBOS.set_event("workflow_status", "started")
    DBOS.set_event("workflow_phase", "loading_sources")

    # Step 1: Load content sources
    sources_info = load_content_sources_step()
    cms_sources = sources_info["cms_sources"]
    website_sources = sources_info["website_sources"]

    DBOS.set_event("total_sources", sources_info["total_sources"])
    DBOS.set_event("cms_sources_count", len(cms_sources))
    DBOS.set_event("website_sources_count", len(website_sources))

    # Step 2: Load auto-fetch config
    auto_fetch_config = get_auto_fetch_config_step()

    # Override with parameter if provided
    if auto_fetch is not None:
        auto_fetch_config["enabled"] = auto_fetch

    DBOS.set_event("auto_fetch_enabled", auto_fetch_config["enabled"])

    # Step 3: Refresh content maps
    DBOS.set_event("workflow_phase", "refreshing_maps")

    cms_results = []
    website_results = []

    # Refresh CMS sources
    if refresh_cms and cms_sources:
        logger.info(f"Refreshing {len(cms_sources)} CMS sources")

        for source in cms_sources:
            try:
                result = refresh_cms_source_step(
                    platform=source["platform"],
                    instance=source["instance"],
                    content_types=source.get("content_types"),
                )
                cms_results.append(result)
            except Exception as e:
                logger.error(f"Failed to refresh {source['platform']}/{source['instance']}: {e}")
                cms_results.append(
                    {
                        "source_type": "cms",
                        "platform": source["platform"],
                        "instance": source["instance"],
                        "error": str(e),
                        "total": 0,
                        "new": 0,
                        "existing": 0,
                    }
                )

    # Refresh website sources
    if refresh_websites and website_sources:
        logger.info(f"Refreshing {len(website_sources)} website sources")

        for source in website_sources:
            try:
                result = refresh_website_source_step(
                    url=source["url"],
                    max_pages=1000,
                )
                website_results.append(result)
            except Exception as e:
                logger.error(f"Failed to refresh {source['url']}: {e}")
                website_results.append(
                    {
                        "source_type": "website",
                        "url": source["url"],
                        "error": str(e),
                        "total": 0,
                        "new": 0,
                        "existing": 0,
                    }
                )

    # Calculate totals
    total_discovered = sum(r.get("total", 0) for r in cms_results + website_results)
    total_new = sum(r.get("new", 0) for r in cms_results + website_results)

    DBOS.set_event("total_discovered", total_discovered)
    DBOS.set_event("total_new", total_new)

    # Step 4: Decide whether to auto-fetch
    DBOS.set_event("workflow_phase", "deciding_fetch")

    should_fetch = auto_fetch_config["enabled"] and total_new > 0
    documents_fetched = 0

    if should_fetch:
        logger.info(
            f"Auto-fetch enabled, selecting documents (max={auto_fetch_config['max_new_documents']})"
        )

        # Step 5: Execute fetch
        DBOS.set_event("workflow_phase", "fetching")

        # Select documents to fetch
        document_ids = select_documents_to_fetch_step(
            max_documents=auto_fetch_config["max_new_documents"],
            strategy=auto_fetch_config["strategy"],
        )

        if document_ids:
            # Import fetch workflow
            from kurt.content.fetch.workflow import fetch_workflow

            logger.info(f"Fetching {len(document_ids)} documents")
            DBOS.set_event("documents_to_fetch", len(document_ids))

            # Execute fetch workflow (batch mode)
            fetch_result = await fetch_workflow(
                identifiers=document_ids,
                max_concurrent=max_concurrent_fetch,
            )

            documents_fetched = fetch_result.get("successful", 0)
            DBOS.set_event("documents_fetched", documents_fetched)

            logger.info(f"Auto-fetch complete: {documents_fetched}/{len(document_ids)} successful")
    else:
        logger.info("Auto-fetch disabled or no new documents")

    # Workflow complete
    DBOS.set_event("workflow_phase", "completed")
    DBOS.set_event("workflow_status", "completed")

    result = {
        "sources_checked": len(cms_sources) + len(website_sources),
        "cms_results": cms_results,
        "website_results": website_results,
        "total_discovered": total_discovered,
        "total_new": total_new,
        "auto_fetch_enabled": auto_fetch_config["enabled"],
        "documents_fetched": documents_fetched,
    }

    logger.info(f"Content map update complete: {total_new} new documents discovered")
    if should_fetch:
        logger.info(f"Auto-fetched {documents_fetched} documents")

    return result


# ============================================================================
# Queue for Background Execution
# ============================================================================

# Create queue for content updates (priority-enabled for urgent updates)
update_queue = Queue("update_queue", priority_enabled=True, concurrency=1)


def enqueue_content_update(
    refresh_cms: bool = True,
    refresh_websites: bool = True,
    auto_fetch: bool | None = None,
    priority: int = 10,
) -> str:
    """
    Enqueue content update workflow for background execution.

    Args:
        refresh_cms: Whether to refresh CMS sources
        refresh_websites: Whether to refresh website sources
        auto_fetch: Override auto-fetch config
        priority: Queue priority (1=highest, 10=default)

    Returns:
        Workflow ID
    """
    from dbos import SetEnqueueOptions

    with SetEnqueueOptions(priority=priority):
        handle = update_queue.enqueue(
            content_map_update_workflow,
            refresh_cms=refresh_cms,
            refresh_websites=refresh_websites,
            auto_fetch=auto_fetch,
        )

    return handle.workflow_id


__all__ = [
    "content_map_update_workflow",
    "enqueue_content_update",
    "load_content_sources_step",
    "get_auto_fetch_config_step",
    "refresh_cms_source_step",
    "refresh_website_source_step",
    "select_documents_to_fetch_step",
    "update_queue",
]
