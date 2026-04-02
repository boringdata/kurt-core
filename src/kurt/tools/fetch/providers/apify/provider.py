""" Apify fetch provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.fetch.engines.apify import ApifyFetcher

__all__ = ["ApifyFetcher"]
