"""
Indexing models - Document processing and knowledge extraction.

Models:
- staging.document_sections: Split documents into sections
- staging.extract_sections: Extract entities and claims from sections
"""

# Import step models to register them
from . import (
    step_document_sections,
    step_extract_sections,
)

__all__ = [
    "step_document_sections",
    "step_extract_sections",
]
