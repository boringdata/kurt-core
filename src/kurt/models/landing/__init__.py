"""
Landing layer models - Raw data ingestion.

Models:
- landing.discovery: Discover URLs from sitemap, crawl, folder, or CMS
- landing.fetch: Fetch content and generate embeddings

Table names are auto-inferred from model names:
- landing.discovery -> landing_discovery
- landing.fetch -> landing_fetch
"""

# Import models to register them
from .discovery import DiscoveryConfig, DiscoveryRow, discovery
from .fetch import FetchConfig, FetchRow, fetch

__all__ = [
    "discovery",
    "DiscoveryConfig",
    "DiscoveryRow",
    "fetch",
    "FetchConfig",
    "FetchRow",
]
