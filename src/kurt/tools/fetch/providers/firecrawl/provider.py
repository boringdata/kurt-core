""" Firecrawl fetch provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.fetch.engines.firecrawl import FirecrawlFetcher

__all__ = ["FirecrawlFetcher"]
