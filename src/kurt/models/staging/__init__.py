"""
Staging layer models - Transformed and enriched data.

Models:
- staging.document_sections: Split documents into sections
- staging.extract_sections: Extract entities and claims from sections
- staging.entity_clustering: Cluster similar entities
- staging.entity_resolution: Resolve entity clusters
- staging.claim_clustering: Cluster similar claims
- staging.claim_resolution: Resolve claim clusters

Table names are auto-inferred from model names:
- staging.document_sections -> staging_document_sections
"""

from kurt.core import TableReader, TableWriter, model

# Import step models to register them
from . import (
    step_claim_clustering,
    step_claim_resolution,
    step_document_sections,
    step_entity_clustering,
    step_entity_resolution,
    step_extract_sections,
)

__all__ = [
    "model",
    "TableReader",
    "TableWriter",
    # Step modules
    "step_document_sections",
    "step_extract_sections",
    "step_entity_clustering",
    "step_entity_resolution",
    "step_claim_clustering",
    "step_claim_resolution",
]
