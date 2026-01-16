"""Fetch workflow - fetch content from discovered documents.

For lightweight imports (models only), use:
    from kurt.workflows.fetch.models import FetchDocument, FetchStatus

For workflow execution (requires [workflows] extras):
    from kurt.workflows.fetch.workflow import fetch_workflow, run_fetch
"""

from .config import FetchConfig
from .models import FetchDocument, FetchStatus

# NOTE: workflow and steps not imported here to avoid heavy dependencies
# Import directly when needed: from kurt.workflows.fetch.workflow import fetch_workflow

__all__ = [
    "FetchConfig",
    "FetchDocument",
    "FetchStatus",
]
