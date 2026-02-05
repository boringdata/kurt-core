"""Map engines module - content discovery engines.

This module provides content mapping engines that implement the BaseMapper
interface. Each engine handles a different content discovery method.

Available engines:
- SitemapEngine: Discovers URLs from sitemap.xml files
- RssEngine: Discovers URLs from RSS/Atom feeds
- CrawlEngine: Discovers URLs by recursive web crawling
- CmsEngine: Discovers content from CMS platforms
- FolderEngine: Discovers files from local folders
- ApifyEngine: Discovers content from social media via Apify

Usage:
    from kurt.tools.map.engines import SitemapEngine

    engine = SitemapEngine()
    result = engine.map("https://example.com")
    if result.count > 0:
        print(result.urls)
"""

from typing import Dict, Type

from kurt.tools.map.core import BaseMapper

# Import engine classes
from kurt.tools.map.engines.sitemap import (
    SitemapEngine,
    SitemapMapper,
    discover_from_sitemap_impl,
)
from kurt.tools.map.engines.rss import (
    RssEngine,
    RssMapper,
    discover_from_rss_impl,
)
from kurt.tools.map.engines.crawl import (
    CrawlEngine,
    CrawlMapper,
    discover_from_crawl_impl,
)
from kurt.tools.map.engines.cms import (
    CmsEngine,
    CmsMapper,
    discover_from_cms_impl,
)
from kurt.tools.map.engines.folder import (
    FolderEngine,
    FolderMapper,
    discover_from_folder_impl,
)
from kurt.tools.map.engines.apify import ApifyEngine


class EngineRegistry:
    """Registry for mapping engines."""

    _engines: Dict[str, Type[BaseMapper]] = {}

    @classmethod
    def register(cls, name: str, engine_class: Type[BaseMapper]) -> None:
        """Register an engine.

        Args:
            name: Engine name
            engine_class: Engine class (subclass of BaseMapper)
        """
        cls._engines[name] = engine_class

    @classmethod
    def get(cls, name: str) -> Type[BaseMapper]:
        """Get an engine by name.

        Args:
            name: Engine name

        Returns:
            Engine class

        Raises:
            KeyError: If engine not found
        """
        if name not in cls._engines:
            raise KeyError(f"Unknown engine: {name}")
        return cls._engines[name]

    @classmethod
    def list_engines(cls) -> list[str]:
        """List available engines.

        Returns:
            List of engine names
        """
        return list(cls._engines.keys())

    @classmethod
    def is_available(cls, name: str) -> bool:
        """Check if engine is available.

        Args:
            name: Engine name

        Returns:
            True if engine is registered
        """
        return name in cls._engines


# Register all engines
EngineRegistry.register("sitemap", SitemapEngine)
EngineRegistry.register("rss", RssEngine)
EngineRegistry.register("crawl", CrawlEngine)
EngineRegistry.register("cms", CmsEngine)
EngineRegistry.register("folder", FolderEngine)
EngineRegistry.register("apify", ApifyEngine)


__all__ = [
    # Registry
    "EngineRegistry",
    # Engine classes
    "SitemapEngine",
    "RssEngine",
    "CrawlEngine",
    "CmsEngine",
    "FolderEngine",
    "ApifyEngine",
    # Backward compatibility aliases
    "SitemapMapper",
    "RssMapper",
    "CrawlMapper",
    "CmsMapper",
    "FolderMapper",
    # Implementation functions
    "discover_from_sitemap_impl",
    "discover_from_rss_impl",
    "discover_from_crawl_impl",
    "discover_from_cms_impl",
    "discover_from_folder_impl",
]
