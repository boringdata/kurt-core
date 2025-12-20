"""Discovery model - Discover URLs from various sources.

This model discovers URLs from various sources (sitemap, crawl, folder, CMS)
and creates document records with NOT_FETCHED status.

Input: URL or folder path (via config)
Output table: landing_discovery
"""

import logging
from typing import Optional

import pandas as pd
from sqlalchemy import JSON, Column
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import (
    PipelineContext,
    PipelineModelBase,
    TableWriter,
    model,
    table,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class DiscoveryConfig(ModelConfig):
    """Configuration for discovery step."""

    # Source configuration
    source_url: Optional[str] = ConfigParam(
        default=None,
        description="URL to discover content from (sitemap or crawl)",
    )
    source_folder: Optional[str] = ConfigParam(
        default=None,
        description="Local folder path to scan for markdown files",
    )
    cms_platform: Optional[str] = ConfigParam(
        default=None,
        description="CMS platform to discover from (e.g., sanity)",
    )
    cms_instance: Optional[str] = ConfigParam(
        default=None,
        description="CMS instance name",
    )

    # Discovery options
    discovery_method: str = ConfigParam(
        default="auto",
        description="Discovery method: auto, sitemap, crawl, folder, cms",
    )
    max_depth: Optional[int] = ConfigParam(
        default=None,
        ge=1,
        le=5,
        description="Max crawl depth (1-5) for crawler fallback",
    )
    max_pages: int = ConfigParam(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum pages to discover",
    )

    # Filtering
    include_patterns: Optional[str] = ConfigParam(
        default=None,
        description="Comma-separated glob patterns to include",
    )
    exclude_patterns: Optional[str] = ConfigParam(
        default=None,
        description="Comma-separated glob patterns to exclude",
    )

    # Advanced options
    allow_external: bool = ConfigParam(
        default=False,
        description="Allow following external domain links",
    )
    include_blogrolls: bool = ConfigParam(
        default=False,
        description="Enable LLM-powered blogroll/changelog discovery",
    )
    dry_run: bool = ConfigParam(
        default=False,
        description="Preview discovery without creating database records",
    )


# ============================================================================
# Output Schema
# ============================================================================


class DiscoveryRow(PipelineModelBase, table=True):
    """Records discovery operation results for discovered documents.

    Inherits from PipelineModelBase:
    - workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = "landing_discovery"

    # Primary key
    document_id: str = Field(primary_key=True)

    # Source info
    source_url: str = Field(default="")
    source_type: str = Field(default="url")  # url, file, cms

    # Discovery info
    discovery_method: str = Field(default="")  # sitemap, crawl, folder, cms
    discovery_url: Optional[str] = Field(default=None)

    # Status
    status: str = Field(default="DISCOVERED")  # DISCOVERED, EXISTING, ERROR
    is_new: bool = Field(default=True)

    # Metadata
    title: Optional[str] = Field(default=None)
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="landing.discovery",
    primary_key=["document_id"],
    write_strategy="replace",
    description="Discover URLs/files and create document records",
    config_schema=DiscoveryConfig,
)
@table(DiscoveryRow)
def discovery(
    ctx: PipelineContext,
    writer: TableWriter = None,
    config: DiscoveryConfig = None,
):
    """Discover content sources and create document records.

    Discovers content from:
    1. URL sources (sitemap or crawl)
    2. Local folders (markdown files)
    3. CMS platforms (API discovery)

    Creates documents with NOT_FETCHED status (or FETCHED for local files).
    """
    # Parse patterns from comma-separated strings
    include_patterns = _parse_patterns(config.include_patterns)
    exclude_patterns = _parse_patterns(config.exclude_patterns)

    # Run discovery based on source type
    discovery_result, discovery_method, discovery_url = _run_discovery(
        config, include_patterns, exclude_patterns
    )

    # Convert results to DataFrame for processing
    discovered_docs = discovery_result.get("discovered", [])
    if not discovered_docs:
        logger.info("No documents discovered")
        return {"rows_written": 0, "documents_discovered": 0}

    df = pd.DataFrame(discovered_docs)

    # Compute status using vectorized operations
    df["document_id"] = df.apply(
        lambda r: str(r.get("doc_id") or r.get("document_id") or ""), axis=1
    )
    df["is_new"] = df.get("created", pd.Series(False)).fillna(False)
    df["status"] = df.apply(_compute_status, axis=1)
    df["source_url"] = df.apply(lambda r: r.get("url") or r.get("path") or "", axis=1)
    df["source_type"] = _get_source_type(discovery_method)
    df["discovery_method"] = discovery_method
    df["discovery_url"] = discovery_url
    df["title"] = df.get("title", pd.Series(None))

    # Create rows using list comprehension
    rows = [
        DiscoveryRow(
            document_id=row["document_id"],
            source_url=row["source_url"],
            source_type=row["source_type"],
            discovery_method=row["discovery_method"],
            discovery_url=row["discovery_url"],
            status=row["status"],
            is_new=row["is_new"],
            title=row.get("title"),
            error=row.get("error"),
        )
        for row in df.to_dict("records")
    ]

    # Compute stats
    discovered = (df["status"] == "DISCOVERED").sum()
    existing = (df["status"] == "EXISTING").sum()
    errors = (df["status"] == "ERROR").sum()

    logger.info(
        f"Discovery complete: {discovered} new, {existing} existing, {errors} errors "
        f"(method: {discovery_method})"
    )

    # Dry run mode: return preview without writing to database
    if config.dry_run:
        return {
            "rows_written": 0,
            "documents_discovered": int(discovered),
            "documents_existing": int(existing),
            "documents_errors": int(errors),
            "discovery_method": discovery_method,
            "dry_run": True,
            "discovered_urls": df["source_url"].tolist(),
        }

    # Normal mode: write to database
    result = writer.write(rows)
    result["documents_discovered"] = int(discovered)
    result["documents_existing"] = int(existing)
    result["documents_errors"] = int(errors)
    result["discovery_method"] = discovery_method
    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_patterns(patterns_str: Optional[str]) -> tuple:
    """Parse comma-separated patterns into tuple."""
    if not patterns_str:
        return ()
    return tuple(p.strip() for p in patterns_str.split(",") if p.strip())


def _compute_status(row) -> str:
    """Compute status from discovery result row."""
    if row.get("error"):
        return "ERROR"
    elif row.get("created", False):
        return "DISCOVERED"
    return "EXISTING"


def _get_source_type(discovery_method: str) -> str:
    """Map discovery method to source type."""
    return {"folder": "file", "cms": "cms"}.get(discovery_method, "url")


def _run_discovery(
    config: DiscoveryConfig,
    include_patterns: tuple,
    exclude_patterns: tuple,
) -> tuple:
    """Run discovery and return (result, method, url)."""
    if config.source_folder:
        result = _discover_from_folder(
            folder_path=config.source_folder,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
        return result, "folder", config.source_folder

    if config.cms_platform and config.cms_instance:
        result = _discover_from_cms(
            platform=config.cms_platform,
            instance=config.cms_instance,
        )
        return result, "cms", f"{config.cms_platform}/{config.cms_instance}"

    if config.source_url:
        result = _discover_from_url(
            url=config.source_url,
            discovery_method=config.discovery_method,
            max_depth=config.max_depth,
            max_pages=config.max_pages,
            allow_external=config.allow_external,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            include_blogrolls=config.include_blogrolls,
        )
        return result, result.get("method", "sitemap"), config.source_url

    raise ValueError("Must specify source_url, source_folder, or cms_platform+cms_instance")


# ============================================================================
# Discovery Functions
# ============================================================================


def _discover_from_url(
    url: str,
    discovery_method: str = "auto",
    max_depth: Optional[int] = None,
    max_pages: int = 1000,
    allow_external: bool = False,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    include_blogrolls: bool = False,
) -> dict:
    """Discover URLs from web source (sitemap or crawl)."""
    from kurt.utils.discovery import discover_from_url

    return discover_from_url(
        url=url,
        max_depth=max_depth,
        max_pages=max_pages,
        allow_external=allow_external,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )


def _discover_from_folder(
    folder_path: str,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
) -> dict:
    """Discover markdown files from local folder."""
    from kurt.utils.discovery import discover_from_folder

    return discover_from_folder(
        folder_path=folder_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )


def _discover_from_cms(
    platform: str,
    instance: str,
) -> dict:
    """Discover documents from CMS platform."""
    from kurt.utils.discovery import discover_from_cms

    return discover_from_cms(
        platform=platform,
        instance=instance,
    )
