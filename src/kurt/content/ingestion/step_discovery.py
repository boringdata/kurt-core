"""Discovery pipeline model.

This model discovers URLs from various sources (sitemap, crawl, folder, CMS)
and creates document records with NOT_FETCHED status.

Input: URL or folder path (via config)
Output table: ingestion_discovery
"""

import logging
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import (
    PipelineContext,
    PipelineModelBase,
    TableWriter,
    model,
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


# ============================================================================
# Output Schema
# ============================================================================


class DiscoveryRow(PipelineModelBase, table=True):
    """Records discovery operation results for discovered documents.

    Inherits from PipelineModelBase:
    - workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = "ingestion_discovery"

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
    name="ingestion.discovery",
    db_model=DiscoveryRow,
    primary_key=["document_id"],
    write_strategy="replace",
    description="Discover URLs/files and create document records",
    config_schema=DiscoveryConfig,
)
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

    Args:
        ctx: Pipeline context with workflow_id
        writer: TableWriter for outputting result rows
        config: Configuration for discovery parameters
    """
    # Parse patterns from comma-separated strings
    include_patterns = tuple(
        p.strip() for p in (config.include_patterns or "").split(",") if p.strip()
    )
    exclude_patterns = tuple(
        p.strip() for p in (config.exclude_patterns or "").split(",") if p.strip()
    )

    rows = []
    discovered = 0
    existing = 0
    errors = 0

    # Determine discovery method
    if config.source_folder:
        # Folder discovery
        result = _discover_from_folder(
            folder_path=config.source_folder,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
        discovery_method = "folder"
        discovery_url = config.source_folder

    elif config.cms_platform and config.cms_instance:
        # CMS discovery
        result = _discover_from_cms(
            platform=config.cms_platform,
            instance=config.cms_instance,
        )
        discovery_method = "cms"
        discovery_url = f"{config.cms_platform}/{config.cms_instance}"

    elif config.source_url:
        # URL discovery (sitemap or crawl)
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
        discovery_method = result.get("method", "sitemap")
        discovery_url = config.source_url

    else:
        raise ValueError("Must specify source_url, source_folder, or cms_platform+cms_instance")

    # Process results
    for doc in result.get("discovered", []):
        doc_id = doc.get("doc_id") or doc.get("document_id")
        is_new = doc.get("created", False)

        if doc.get("error"):
            status = "ERROR"
            errors += 1
        elif is_new:
            status = "DISCOVERED"
            discovered += 1
        else:
            status = "EXISTING"
            existing += 1

        rows.append(
            DiscoveryRow(
                document_id=str(doc_id) if doc_id else "",
                source_url=doc.get("url") or doc.get("path") or "",
                source_type=_get_source_type(discovery_method),
                discovery_method=discovery_method,
                discovery_url=discovery_url,
                status=status,
                is_new=is_new,
                title=doc.get("title"),
                error=doc.get("error"),
            )
        )

    logger.info(
        f"Map complete: {discovered} new, {existing} existing, {errors} errors "
        f"(method: {discovery_method})"
    )

    result = writer.write(rows)
    result["documents_discovered"] = discovered
    result["documents_existing"] = existing
    result["documents_errors"] = errors
    result["discovery_method"] = discovery_method
    return result


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
    from .utils.map import discover_from_url

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
    from .utils.map import discover_from_folder

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
    from .utils.map import discover_from_cms

    return discover_from_cms(
        platform=platform,
        instance=instance,
    )


def _get_source_type(discovery_method: str) -> str:
    """Map discovery method to source type."""
    if discovery_method == "folder":
        return "file"
    elif discovery_method == "cms":
        return "cms"
    else:
        return "url"
