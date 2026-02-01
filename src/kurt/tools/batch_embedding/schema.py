"""
Pydantic schema for batch_embedding_results table.

Used for VALIDATION ONLY - not DDL generation.
Actual table schema defined in src/kurt/db/schema/embed_results.sql

File path convention:
  sources/embeddings/<document_id>/<run_id>/<embedding_model>.npy
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BatchEmbeddingResult(BaseModel):
    """Validation schema for BatchEmbeddingTool output."""

    model_config = ConfigDict(extra="forbid")  # Strict - no extra fields

    document_id: str = Field(description="Document ID (12-char hex) - JOIN key")
    run_id: str = Field(description="Run/batch ID (UUID) for versioning")
    embedding_model: str = Field(description="Model name (e.g. text-embedding-3-small)")
    embedding_path: str = Field(
        description="Path to embedding file: sources/embeddings/<doc_id>/<run_id>/<model>.npy"
    )
    vector_size: int = Field(description="Dimension of embedding vector")
    # NOTE: created_at NOT included - DB handles it with CURRENT_TIMESTAMP(6)
