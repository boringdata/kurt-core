"""Retrieval pipeline configuration.

Defines retrieval pipelines using PipelineConfig pattern.

Pipelines:
- CAG_PIPELINE: Single step - entity routing + SQL context loading
- RAG_PIPELINE: Single step - multi-signal search with RRF fusion
"""

from kurt.core.pipeline import PipelineConfig

# CAG: Fast, deterministic retrieval for agent sessions
CAG_PIPELINE = PipelineConfig(
    name="retrieval_cag",
    models=[
        "retrieval.cag",  # Single step: embed → entity routing → SQL load → format
    ],
)

# RAG: Unified multi-signal search with RRF fusion
RAG_PIPELINE = PipelineConfig(
    name="retrieval_rag",
    models=[
        "retrieval.rag",  # Single step: embed → parallel searches → RRF → format
    ],
)

# Legacy alias for backward compatibility
RETRIEVAL_PIPELINE = RAG_PIPELINE
