"""Fetch workflow - fetch content from discovered documents.

For lightweight imports (models only), use:
    from kurt.tools.fetch.models import FetchDocument, FetchStatus

For CLI commands, use:
    from kurt.tools.fetch.cli import fetch_cmd

Note: config, models, and CLI have moved to kurt.tools.fetch.
This module re-exports for backward compatibility.
"""

# Re-export from tools/ for backward compatibility
from kurt.tools.fetch.config import FetchConfig
from kurt.tools.fetch.models import FetchDocument, FetchStatus

__all__ = [
    "FetchConfig",
    "FetchDocument",
    "FetchStatus",
]
