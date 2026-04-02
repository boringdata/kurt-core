"""Fetch engines module - content extraction engines.

This module provides content fetching engines that implement the BaseFetcher
interface. Each engine handles a different data source or extraction method.

Available engines:
- TrafilaturaFetcher: Free, local HTML extraction using trafilatura library
- HttpxFetcher: HTTPX + trafilatura extraction (proxy-friendly)
- TavilyFetcher: Tavily API-based content extraction
- FirecrawlFetcher: Firecrawl API-based content extraction (handles JS rendering)
- ApifyFetcher: Apify-based social media content extraction
- TwitterApiFetcher: TwitterAPI.io-based Twitter/X content extraction (pay-as-you-go)

Usage:
    from kurt.tools.fetch.engines import TrafilaturaFetcher

    fetcher = TrafilaturaFetcher()
    result = fetcher.fetch("https://example.com")
    if result.success:
        print(result.content)
"""

from typing import Dict, Type

from kurt.tools.fetch.core import BaseFetcher
from kurt.tools.fetch.engines.apify import ApifyEngine, ApifyFetcher
from kurt.tools.fetch.engines.firecrawl import FirecrawlEngine, FirecrawlFetcher
from kurt.tools.fetch.engines.httpx import HttpxEngine, HttpxFetcher
from kurt.tools.fetch.engines.tavily import TavilyEngine, TavilyFetcher

# Import engine classes for easy access
# Primary names are *Fetcher, *Engine aliases exist for backward compatibility
from kurt.tools.fetch.engines.trafilatura import TrafilaturaEngine, TrafilaturaFetcher
from kurt.tools.fetch.engines.twitterapi import TwitterApiEngine, TwitterApiFetcher


class EngineRegistry:
    """Registry for fetching engines."""

    _engines: Dict[str, Type[BaseFetcher]] = {}

    @classmethod
    def register(cls, name: str, engine_class: Type[BaseFetcher]) -> None:
        """Register an engine.

        Args:
            name: Engine name
            engine_class: Engine class (subclass of BaseFetcher)
        """
        cls._engines[name] = engine_class

    @classmethod
    def get(cls, name: str) -> Type[BaseFetcher]:
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
EngineRegistry.register("trafilatura", TrafilaturaFetcher)
EngineRegistry.register("httpx", HttpxFetcher)
EngineRegistry.register("tavily", TavilyFetcher)
EngineRegistry.register("firecrawl", FirecrawlFetcher)
EngineRegistry.register("apify", ApifyFetcher)
EngineRegistry.register("twitterapi", TwitterApiFetcher)


__all__ = [
    # Registry
    "EngineRegistry",
    # Engine classes (primary *Fetcher names)
    "TrafilaturaFetcher",
    "HttpxFetcher",
    "TavilyFetcher",
    "FirecrawlFetcher",
    "ApifyFetcher",
    "TwitterApiFetcher",
    # Backward compatibility aliases (*Engine names)
    "TrafilaturaEngine",
    "HttpxEngine",
    "TavilyEngine",
    "FirecrawlEngine",
    "ApifyEngine",
    "TwitterApiEngine",
]
