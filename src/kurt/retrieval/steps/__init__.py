"""Retrieval pipeline steps.

Each step is a @model-decorated function that reads from upstream tables
and writes to its own output table.

Steps:
- cag_retrieve: CAG retrieval (single embedding + SQL context loading)
- rag_retrieve: Unified RAG (multi-signal search with RRF fusion)

Note: Step implementations are in kurt.models.staging.retrieval
"""

from kurt.models.staging.retrieval.step_cag import cag_retrieve
from kurt.models.staging.retrieval.step_rag import rag_retrieve

__all__ = [
    "cag_retrieve",
    "rag_retrieve",
]
