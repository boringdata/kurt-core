"""Shared types for the retrieval workflow.

This module defines the core data structures used throughout the retrieval pipeline:
- RetrievalContext: Input parameters for a retrieval request
- Citation: A reference to a source document
- GraphPayload: Nodes and edges from the knowledge graph
- RetrievalResult: The complete output from retrieval
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RetrievalContext:
    """Input context for retrieval (similar to PipelineContext for indexing).

    Attributes:
        query: The user's natural language query
        session_id: Optional session ID for context continuity
        dataset_scope: Optional list of dataset names to search
        query_type: Type of retrieval: "graph", "semantic", or "hybrid"
        deep_mode: If True, enable iterative graph expansion
        max_tokens: Maximum tokens for the context output
    """

    query: str
    session_id: Optional[str] = None
    dataset_scope: Optional[list[str]] = None
    query_type: str = "hybrid"  # graph, semantic, hybrid
    deep_mode: bool = False
    max_tokens: int = 4000


@dataclass
class Citation:
    """A citation referencing a source document.

    Attributes:
        doc_id: Document UUID
        title: Document title
        source_url: URL or path to the source
        snippet: Relevant text snippet from the document
        confidence: Confidence score (0-1) for this citation
    """

    doc_id: str
    title: str
    source_url: str
    snippet: str
    confidence: float


@dataclass
class GraphPayload:
    """Knowledge graph nodes and edges from retrieval.

    Attributes:
        nodes: List of node dicts with {id, name, type, description}
        edges: List of edge dicts with {source, target, type, context}
    """

    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)


@dataclass
class RetrievalResult:
    """Output from the retrieval pipeline.

    Attributes:
        context_text: Formatted "Nodes + Connections" text block for LLM grounding
        citations: List of Citation objects referencing source documents
        graph_payload: Raw nodes and edges from the knowledge graph
        telemetry: Metrics dict (triplets fetched, docs touched, rounds, tokens)
        suggested_prompt: Optional prompt suggestion for downstream LLM completion
    """

    context_text: str
    citations: list[Citation] = field(default_factory=list)
    graph_payload: GraphPayload = field(default_factory=GraphPayload)
    telemetry: dict = field(default_factory=dict)
    suggested_prompt: str = ""
