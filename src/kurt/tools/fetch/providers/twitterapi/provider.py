""" TwitterAPI.io fetch provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.fetch.engines.twitterapi import TwitterApiFetcher

__all__ = ["TwitterApiFetcher"]
