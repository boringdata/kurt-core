"""CMS-based content mapping engine."""

from __future__ import annotations

import logging
from typing import Optional

from kurt.tools.map.core import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.models import DocType

logger = logging.getLogger(__name__)


class CmsMapperConfig(MapperConfig):
    """Configuration for CMS mapper.

    Attributes:
        platform: CMS platform name (e.g., "sanity")
        instance: CMS instance identifier
        content_type: Filter by content type
        status: Filter by document status (e.g., "published", "draft")
    """

    platform: Optional[str] = None
    instance: Optional[str] = None
    content_type: Optional[str] = None
    status: Optional[str] = None


class CmsEngine(BaseMapper):
    """Maps content by discovering documents from CMS platforms.

    Supports CMS platforms like Sanity, with content type and status filtering.
    """

    def __init__(self, config: Optional[CmsMapperConfig] = None):
        """Initialize CMS mapper.

        Args:
            config: CMS mapper configuration
        """
        super().__init__(config or CmsMapperConfig())
        self._config: CmsMapperConfig = self.config  # type: ignore

    def map(
        self,
        source: str,
        doc_type: DocType = DocType.DOC,
    ) -> MapperResult:
        """Map documents from a CMS platform.

        Args:
            source: CMS source in format "platform/instance" or just instance
                   if platform is set in config
            doc_type: Type of documents to map

        Returns:
            MapperResult with discovered document URLs
        """
        # Parse source to get platform and instance
        platform = self._config.platform
        instance = self._config.instance

        if "/" in source:
            parts = source.split("/", 1)
            platform = parts[0]
            instance = parts[1]
        elif not instance:
            instance = source

        if not platform or not instance:
            return MapperResult(
                urls=[],
                count=0,
                errors=["CMS platform and instance are required"],
                metadata={"engine": "cms"},
            )

        try:
            result = discover_from_cms_impl(
                platform=platform,
                instance=instance,
                content_type=self._config.content_type,
                status=self._config.status,
                limit=self._config.max_urls,
            )

            urls = [item["url"] for item in result.get("discovered", [])]

            return MapperResult(
                urls=urls,
                count=len(urls),
                metadata={
                    "engine": "cms",
                    "platform": platform,
                    "instance": instance,
                    "method": "cms",
                },
            )

        except Exception as e:
            logger.error("CMS mapping failed: %s", e)
            return MapperResult(
                urls=[],
                count=0,
                errors=[str(e)],
                metadata={"engine": "cms", "platform": platform, "instance": instance},
            )


def discover_from_cms_impl(
    platform: str,
    instance: str,
    *,
    content_type: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict:
    """
    Discover documents from a CMS platform without persisting them.

    This is the core implementation used by both CmsEngine and the
    backward-compatible discover_from_cms() function.

    Args:
        platform: CMS platform name (e.g., "sanity")
        instance: CMS instance identifier
        content_type: Filter by content type
        status: Filter by document status
        limit: Maximum number of documents to return

    Returns:
        Dict with discovered documents and metadata
    """
    from kurt.integrations.cms import get_adapter
    from kurt.integrations.cms.config import get_platform_config

    cms_config = get_platform_config(platform, instance)
    adapter = get_adapter(platform, cms_config)

    try:
        cms_documents = adapter.list_all(
            content_type=content_type,
            status=status,
            limit=limit,
        )
    except Exception as exc:
        logger.error("CMS discovery failed: %s", exc)
        raise ValueError(f"Failed to discover documents from {platform}/{instance}: {exc}")

    results = []
    for doc_meta in cms_documents:
        schema = doc_meta.get("content_type")
        slug = doc_meta.get("slug", "untitled")
        cms_doc_id = doc_meta.get("id")

        source_url = f"{platform}/{instance}/{schema}/{slug}"

        results.append(
            {
                "url": source_url,
                "title": doc_meta.get("title"),
                "cms_id": cms_doc_id,
                "schema": schema,
                "slug": slug,
                "metadata": {
                    **doc_meta,
                    "cms_platform": platform,
                    "cms_instance": instance,
                    "cms_id": cms_doc_id,
                },
                "created": True,
            }
        )

    return {
        "discovered": results,
        "total": len(results),
        "method": "cms",
    }


# Backward compatibility alias
CmsMapper = CmsEngine
