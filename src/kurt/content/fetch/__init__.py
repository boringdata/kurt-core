"""
Fetch module - Business logic and workflows for content fetching.

This module contains:
- content.py: Pure fetching logic (Network I/O)
- filtering.py: Pure filter building logic (no DB)
- links.py: Pure link extraction logic (regex parsing)
- utils.py: Configuration utilities
- workflow.py: DBOS workflows for fetching (DB operations + orchestration)

Pattern:
- Business logic (pure): content.py, filtering.py, links.py (NO DB operations)
- Workflow (DB ops): workflow.py (orchestration with DBOS)
- CLI (entry point): commands/content/fetch.py calls workflows
"""

# Business logic exports
from kurt.content.document import add_document, resolve_or_create_document
from kurt.content.fetch.content import fetch_batch_from_cms, fetch_from_cms, fetch_from_web
from kurt.content.fetch.filtering import (
    DocumentFetchFilters,
    build_document_filters,
    estimate_fetch_cost,
    select_documents_for_fetch,
)
from kurt.content.fetch.links import extract_document_links
from kurt.content.fetch.utils import _get_fetch_engine

# NOTE: Workflow exports are NOT included here to avoid circular imports.
# Import workflows directly from workflow.py:
#     from kurt.content.fetch.workflow import fetch_document_workflow, ...
#
# The workflow module has dependencies on filtering.py which creates a circular import
# when loaded eagerly through __init__.py.

__all__ = [
    # Content fetching (pure - Network I/O)
    "fetch_from_cms",
    "fetch_batch_from_cms",
    "fetch_from_web",
    # Filtering (pure - no DB)
    "DocumentFetchFilters",
    "build_document_filters",
    "estimate_fetch_cost",
    # Link extraction (pure - regex)
    "extract_document_links",
    # Utilities
    "_get_fetch_engine",
    "select_documents_for_fetch",
    # Document CRUD (re-exported from document.py for backward compatibility)
    "add_document",
    "resolve_or_create_document",
]
