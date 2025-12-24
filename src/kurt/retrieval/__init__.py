"""Kurt Retrieval Module.

This module provides retrieval pipelines:
- CAG: Fast, deterministic retrieval using entity similarity routing + SQL context loading
- RAG: Multi-signal search with embedding similarity and RRF fusion

Usage:
    from kurt.retrieval import retrieve, RetrievalContext

    ctx = RetrievalContext(
        query="What integrations does Segment support?",
        query_type="hybrid",
    )
    result = await retrieve(ctx)
    print(result.context_text)
"""

import json
import logging
from uuid import uuid4

from kurt.core.model_runner import PipelineContext, run_pipeline
from kurt.core.table_io import TableReader
from kurt.utils.filtering import DocumentFilters

from .config import RetrievalConfig
from .pipeline import CAG_PIPELINE, RAG_PIPELINE, RETRIEVAL_PIPELINE
from .types import Citation, GraphPayload, RetrievalContext, RetrievalResult

logger = logging.getLogger(__name__)

__all__ = [
    # Main API
    "retrieve",
    "RetrievalContext",
    "RetrievalResult",
    # Types
    "Citation",
    "GraphPayload",
    # Config
    "RetrievalConfig",
    # Pipelines
    "CAG_PIPELINE",
    "RAG_PIPELINE",
    "RETRIEVAL_PIPELINE",  # Alias for RAG_PIPELINE
]


async def retrieve(ctx: RetrievalContext) -> RetrievalResult:
    """Execute the retrieval pipeline for a given query.

    This is the main entry point for the retrieval module. It:
    1. Converts RetrievalContext to PipelineContext
    2. Runs the RAG pipeline (single step with multi-signal search)
    3. Reads the final context from the output table
    4. Returns a RetrievalResult

    Args:
        ctx: RetrievalContext with the query and options

    Returns:
        RetrievalResult with context_text, citations, graph_payload, and telemetry

    Example:
        ctx = RetrievalContext(
            query="What integrations does Segment support?",
            query_type="hybrid",
            deep_mode=False,
        )
        result = await retrieve(ctx)
        print(result.context_text)
    """
    # Register steps with ModelRegistry (lazy import to avoid circular deps)
    _register_steps()

    # Generate workflow ID from session_id or create new
    workflow_id = ctx.session_id or str(uuid4())

    logger.info(f"Starting retrieval for query: {ctx.query[:100]}...")

    # Convert RetrievalContext to PipelineContext
    pipeline_ctx = PipelineContext(
        filters=DocumentFilters(),
        workflow_id=workflow_id,
        metadata={
            "query": ctx.query,
            "query_type": ctx.query_type,
            "deep_mode": ctx.deep_mode,
            "session_context": "",  # TODO: Load from session store
        },
    )

    # Run the retrieval pipeline
    result = await run_pipeline(RETRIEVAL_PIPELINE, pipeline_ctx)

    # Check for errors
    if result.get("errors"):
        logger.error(f"Retrieval pipeline errors: {result['errors']}")

    # Read the final context from the output table
    reader = TableReader()

    try:
        context_df = reader.load(
            "retrieval_rag_context",
            where={"query_id": workflow_id},
        )

        if context_df.empty:
            logger.warning("No context results found")
            return RetrievalResult(
                context_text="No results found.",
                telemetry={"error": "no_results", **result},
            )

        # Extract from first row
        row = context_df.iloc[0]

        # Parse JSON fields
        entities = json.loads(row.get("entities", "[]"))
        citations_data = json.loads(row.get("citations", "[]"))
        telemetry = json.loads(row.get("telemetry", "{}"))

        # Build Citation objects
        citations = [
            Citation(
                doc_id=c["doc_id"],
                title=c.get("title", ""),
                source_url=c.get("url", ""),
                snippet="",
                confidence=c.get("score", 0.0),
            )
            for c in citations_data
        ]

        # Build GraphPayload
        graph_payload = GraphPayload(
            nodes=[{"name": e} for e in entities],
            edges=[],
        )

        # Add pipeline results to telemetry
        telemetry["pipeline"] = {
            "models_executed": result.get("models_executed", []),
            "errors": result.get("errors", {}),
        }

        return RetrievalResult(
            context_text=row.get("context_text", ""),
            citations=citations,
            graph_payload=graph_payload,
            telemetry=telemetry,
            suggested_prompt=f"Based on the following context, answer: {ctx.query}",
        )

    except Exception as e:
        logger.error(f"Error reading retrieval results: {e}")
        return RetrievalResult(
            context_text=f"Error: {e}",
            telemetry={"error": str(e), **result},
        )


def _register_steps():
    """Lazy import to register steps with ModelRegistry.

    This avoids circular import by not importing at module load time.
    Call this before running the pipeline.
    """
    from . import steps  # noqa: F401

    return steps
