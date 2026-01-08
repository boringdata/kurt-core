"""
Document lifecycle management for kurt_new.

Provides a unified view of documents across all workflow stages.
DocumentView is a virtual aggregation - not a persisted table.
"""

from kurt_new.documents.filtering import DocumentFilters
from kurt_new.documents.models import DocumentView
from kurt_new.documents.registry import DocumentRegistry

__all__ = [
    "DocumentView",
    "DocumentRegistry",
    "DocumentFilters",
]
