""" Crawl map provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.map.engines.crawl import CrawlEngine

__all__ = ["CrawlEngine"]
