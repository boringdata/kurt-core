"""
Staging layer models - Transformed and enriched data.

Subpackages:
- staging.indexing: Document processing and knowledge extraction models
- staging.clustering: Entity, claim, and topic clustering models

Table names are auto-inferred from model names:
- staging.document_sections -> staging_document_sections
"""

from kurt.core import TableReader, TableWriter, model

# Import subpackages to register models
from . import clustering, indexing

# Re-export step modules for backwards compatibility
from .clustering import (
    step_claim_clustering,
    step_claim_resolution,
    step_entity_clustering,
    step_entity_resolution,
    step_topic_clustering,
)
from .indexing import (
    step_document_sections,
    step_extract_sections,
)

__all__ = [
    "model",
    "TableReader",
    "TableWriter",
    "indexing",
    "clustering",
    # Step modules (re-exported for backwards compatibility)
    "step_document_sections",
    "step_extract_sections",
    "step_entity_clustering",
    "step_entity_resolution",
    "step_claim_clustering",
    "step_claim_resolution",
    "step_topic_clustering",
]
