""" Trafilatura fetch provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher

__all__ = ["TrafilaturaFetcher"]
