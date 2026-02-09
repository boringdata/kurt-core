""" RSS map provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.map.engines.rss import RssEngine

__all__ = ["RssEngine"]
