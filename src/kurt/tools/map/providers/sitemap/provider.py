""" Sitemap map provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.map.engines.sitemap import SitemapEngine

__all__ = ["SitemapEngine"]
