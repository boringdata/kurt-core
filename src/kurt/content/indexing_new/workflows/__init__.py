"""
Pipeline configurations for indexing workflows.

Pipelines are discovered automatically from registered models.
Models declare their namespace via their name prefix (e.g., "indexing.document_sections").

Usage:
    from kurt.content.indexing_new.framework import run_workflow
    from kurt.content.indexing_new.workflows import INDEXING_PIPELINE

    result = await run_workflow(
        pipeline=INDEXING_PIPELINE,
        filters=DocumentFilters(ids="doc1,doc2"),
    )
"""

# Import models to trigger @model decorator registration
import kurt.content.indexing_new.models  # noqa: F401
from kurt.content.indexing_new.framework import get_pipeline

# Discover the indexing pipeline from registered models
# Models are found by their "indexing.*" name prefix
INDEXING_PIPELINE = get_pipeline("indexing")

__all__ = [
    "INDEXING_PIPELINE",
]
