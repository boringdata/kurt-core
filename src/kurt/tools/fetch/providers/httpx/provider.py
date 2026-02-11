""" HTTPX fetch provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.fetch.engines.httpx import HttpxFetcher

__all__ = ["HttpxFetcher"]
