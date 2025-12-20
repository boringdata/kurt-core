"""
Indexing models - Document processing and knowledge extraction.

Models:
- staging.document_sections: Split documents into sections
- staging.extract_sections: Extract entities and claims from sections
- staging.entity_clustering: Cluster and resolve similar entities
- staging.entity_resolution: Apply entity resolution decisions
- staging.claim_clustering: Cluster and resolve similar claims
- staging.claim_resolution: Apply claim resolution decisions
"""

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
    "step_document_sections",
    "step_extract_sections",
    "step_entity_clustering",
    "step_entity_resolution",
    "step_claim_clustering",
    "step_claim_resolution",
]
