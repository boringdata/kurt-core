"""
Ingestion pipeline - dbt-style models for content discovery and fetching.

This module provides:
- ingestion.discovery: Discover URLs/files and create document records
- ingestion.fetch: Fetch content, generate embeddings, save to DB

Usage:
    from kurt.core import run_pipeline_workflow
    from kurt.content.filtering import DocumentFilters

    # Discover content
    result = await run_pipeline_workflow(
        target="ingestion.discovery",
        config={"source_url": "https://example.com"},
    )

    # Fetch content
    result = await run_pipeline_workflow(
        target="ingestion.fetch",
        filters=DocumentFilters(ids="doc-id-1,doc-id-2"),
    )

Or programmatically:
    from kurt.content.ingestion import INGESTION_PIPELINE
    from kurt.core import run_pipeline, PipelineContext

    ctx = PipelineContext(filters=DocumentFilters(ids="..."), workflow_id="...")
    result = await run_pipeline(INGESTION_PIPELINE, ctx)
"""

from kurt.core import get_pipeline

# Import models to register them
from .step_discovery import DiscoveryConfig, DiscoveryRow, discovery
from .step_fetch import FetchConfig, FetchRow, fetch

# Get pipeline for all ingestion models
INGESTION_PIPELINE = get_pipeline("ingestion")

__all__ = [
    # Pipeline
    "INGESTION_PIPELINE",
    # Discovery model
    "discovery",
    "DiscoveryConfig",
    "DiscoveryRow",
    # Fetch model
    "fetch",
    "FetchConfig",
    "FetchRow",
]
