"""Document section splitting model for the indexing pipeline.

This model splits documents into logical sections for parallel processing,
ensuring full document coverage beyond the 5000 char limit.

This is the FIRST model in the pipeline:
- It reads from the `documents` table with `load_content=True`
- The Reference automatically loads file content into the DataFrame

Input: documents table (with content loaded from files)
Output table: indexing_document_sections
"""

import hashlib
import logging
from typing import Any, Optional

from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.content.indexing.utils import split_markdown_document
from kurt.core import (
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class DocumentSectionsConfig(ModelConfig):
    """Configuration for document section splitting."""

    max_section_chars: int = ConfigParam(
        default=5000,
        ge=500,
        le=20000,
        description="Maximum characters per section (matches extraction limit)",
    )
    overlap_chars: int = ConfigParam(
        default=200,
        ge=0,
        le=1000,
        description="Context overlap between sections",
    )
    min_section_size: int = ConfigParam(
        default=500,
        ge=100,
        le=2000,
        description="Minimum size to avoid tiny fragments",
    )


# ============================================================================
# Output Model
# ============================================================================


class DocumentSectionRow(PipelineModelBase, table=True):
    """Schema for document sections table.

    Inherits from PipelineModelBase:
    - workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = "indexing_document_sections"

    # Primary key fields
    document_id: str = Field(primary_key=True)
    section_id: str = Field(primary_key=True)

    # Core fields
    section_number: int
    heading: Optional[str] = Field(default=None)
    content: str
    start_offset: int
    end_offset: int
    overlap_prefix: Optional[str] = Field(default=None)
    overlap_suffix: Optional[str] = Field(default=None)
    section_hash: str = Field(default="")

    # Document metadata (from source)
    document_title: Optional[str] = Field(default=None)

    # Model-specific fields
    is_active: bool = Field(default=True)
    token_count: Optional[int] = Field(default=None)

    def __init__(self, **data: Any):
        """Compute section_hash from content and offsets if not provided.

        Note: Using __init__ instead of model_validator because SQLModel
        with table=True doesn't properly support Pydantic v2 model_validator.
        """
        if "section_hash" not in data or not data.get("section_hash"):
            content = data.get("content", "")
            start = data.get("start_offset", 0)
            end = data.get("end_offset", 0)
            data["section_hash"] = hashlib.sha256(f"{content}{start}{end}".encode()).hexdigest()
        super().__init__(**data)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="indexing.document_sections",
    db_model=DocumentSectionRow,
    primary_key=["document_id", "section_id"],
    write_strategy="replace",
    description="Split documents into sections for parallel processing",
    config_schema=DocumentSectionsConfig,
)
def document_sections(
    ctx: PipelineContext,
    documents=Reference(
        "documents",
        load_content={"document_id_column": "document_id"},
        # Use string filter "id" for SQL-level filtering via ctx.document_ids
        # TableReader._load_documents_with_content() now applies all DocumentFilters
        # including with_status, include_pattern, limit, etc. from ctx.filters
        filter="id",
    ),
    writer: TableWriter = None,
    config: DocumentSectionsConfig = None,
):
    """Split documents into sections for parallel processing.

    This model reads from the documents table with content loaded from files,
    then splits each document into smaller sections for parallel extraction.

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        documents: Lazy reference to documents table (loads content from files)
        writer: TableWriter for outputting section rows
        config: Configuration for section splitting parameters
    """
    # Lazy load - data fetched here when we access .df
    documents_df = documents.df

    if documents_df.empty:
        logger.warning("No documents to process")
        return {"rows_written": 0, "documents_processed": 0, "documents_skipped": 0}

    document_records = documents_df.to_dict("records")
    logger.info(
        f"Processing {len(document_records)} documents for section splitting "
        f"(mode: {ctx.incremental_mode})"
    )

    rows = []
    skipped_count = 0
    # Track successfully processed documents for indexed_hash update
    processed_docs = []  # List of (document_id, content_hash) tuples

    for doc in document_records:
        # Skip if document has error or no content
        if doc.get("skip", False) or doc.get("error"):
            skipped_count += 1
            continue

        document_id = doc["document_id"]
        content = doc.get("content", "")

        if not content:
            logger.warning(f"Document {document_id} has no content, skipping")
            skipped_count += 1
            continue

        # Split the document into sections
        sections = split_markdown_document(
            content,
            max_chars=config.max_section_chars,
            overlap_chars=config.overlap_chars,
            min_section_size=config.min_section_size,
        )

        # Create rows - __init__ handles hash computation
        rows.extend(
            DocumentSectionRow(
                document_id=document_id,
                section_id=section.section_id,
                section_number=section.section_number,
                heading=section.heading,
                content=section.content,
                start_offset=section.start_offset,
                end_offset=section.end_offset,
                overlap_prefix=section.overlap_prefix,
                overlap_suffix=section.overlap_suffix,
                document_title=doc.get("title"),
            )
            for section in sections
        )

        # Track this document for indexed_hash update
        content_hash = doc.get("content_hash")
        if content_hash:
            processed_docs.append((document_id, content_hash))

    logger.info(
        f"Generated {len(rows)} sections from {len(document_records) - skipped_count} documents "
        f"(skipped {skipped_count})"
    )

    if not rows:
        # All documents were skipped - only show skipped count
        return {
            "rows_written": 0,
            "skipped": skipped_count,
        }

    result = writer.write(rows)

    # Update indexed_with_hash for successfully processed documents
    # This enables incremental mode to skip unchanged documents in future runs
    if processed_docs:
        for document_id, content_hash in processed_docs:
            writer.update_indexed_hash(document_id, content_hash)
        logger.info(f"Updated indexed_with_hash for {len(processed_docs)} documents")

    # Stats: documents processed and sections created
    processed_count = len(document_records) - skipped_count
    result["documents"] = processed_count
    result["sections"] = len(rows)
    # Only show skipped if there were any
    if skipped_count > 0:
        result["skipped"] = skipped_count
    return result
