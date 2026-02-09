""" Apify map provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.map.engines.apify import ApifyEngine

__all__ = ["ApifyEngine"]
