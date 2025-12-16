"""
Document section splitting model for the indexing pipeline.

This model splits documents into logical sections for parallel processing,
ensuring full document coverage beyond the 5000 char limit.
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, SQLModel

from kurt.config import ConfigParam, ModelConfig
from kurt.content.indexing.splitting import split_markdown_document
from kurt.content.indexing_new.framework import PipelineContext, TableReader, TableWriter, model

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


class DocumentSectionRow(SQLModel, table=True):
    """Schema for document sections table."""

    __tablename__ = "indexing_document_sections"

    # Primary key fields
    document_id: str = Field(primary_key=True, description="Document UUID")
    section_id: str = Field(primary_key=True, description="Unique section identifier")

    # Core fields
    section_number: int = Field(description="Section order number")
    heading: Optional[str] = Field(default=None, description="Section heading or title")
    content: str = Field(description="Section content")
    start_offset: int = Field(description="Starting character offset in original document")
    end_offset: int = Field(description="Ending character offset in original document")
    overlap_prefix: Optional[str] = Field(default=None, description="Overlap from previous section")
    overlap_suffix: Optional[str] = Field(default=None, description="Overlap to next section")
    section_hash: str = Field(description="Hash of section content for change detection")

    # Model-specific fields
    is_active: bool = Field(default=True, description="Whether this section is active")

    # Workflow tracking (managed by TableWriter)
    workflow_id: Optional[str] = Field(default=None, description="Workflow that created this row")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Update timestamp")
    model_name: Optional[str] = Field(default=None, description="Model that created this row")

    # Token telemetry (populated later by extraction models)
    token_count: Optional[int] = Field(default=None, description="Token count for this section")


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
    reader: TableReader,  # Required by decorator but unused - documents come via payloads
    writer: TableWriter,
    payloads: List[dict],
    config: DocumentSectionsConfig = None,
):
    """
    Split documents into sections for parallel processing.

    This model takes document payloads and splits them into logical sections based on
    markdown headings and size constraints, enabling parallel extraction while
    maintaining context through overlapping regions.

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        reader: Table reader (required by framework but unused - documents come via payloads)
        writer: Table writer for persisting results
        payloads: List of document payloads from workflow (with document_id, content, skip, etc.)

    Returns:
        Write statistics from the table writer
    """
    logger.info(
        f"Processing {len(payloads)} documents for section splitting (mode: {ctx.incremental_mode})"
    )

    rows = []
    skipped_count = 0

    for doc in payloads:
        # Skip if document hasn't changed (in delta mode)
        if doc.get("skip", False):
            skipped_count += 1
            logger.debug(f"Skipping unchanged document: {doc['document_id']}")
            continue

        document_id = doc["document_id"]
        content = doc.get("content", "")

        if not content:
            logger.warning(f"Document {document_id} has no content, skipping")
            continue

        # Split the document into sections using config parameters
        max_chars = config.max_section_chars if config else 5000
        overlap_chars = config.overlap_chars if config else 200
        min_section_size = config.min_section_size if config else 500

        sections = split_markdown_document(
            content,
            max_chars=max_chars,
            overlap_chars=overlap_chars,
            min_section_size=min_section_size,
        )

        logger.debug(f"Document {document_id} split into {len(sections)} sections")

        # Create rows for each section
        for section in sections:
            # Generate a stable section hash for change detection
            section_hash = hashlib.sha256(
                f"{section.content}{section.start_offset}{section.end_offset}".encode()
            ).hexdigest()

            # Only include core fields - let TableWriter handle metadata
            row = {
                # Core fields
                "document_id": document_id,
                "section_id": section.section_id,
                "section_number": section.section_number,
                "heading": section.heading,
                "content": section.content,
                "start_offset": section.start_offset,
                "end_offset": section.end_offset,
                "overlap_prefix": section.overlap_prefix,
                "overlap_suffix": section.overlap_suffix,
                "section_hash": section_hash,
                # Model-specific fields (not handled by TableWriter)
                "is_active": True,
                "token_count": None,  # Will be populated by extraction models
            }

            rows.append(row)

    logger.info(
        f"Generated {len(rows)} sections from {len(payloads) - skipped_count} documents "
        f"(skipped {skipped_count} unchanged)"
    )

    # Write all rows to the table with the SQLModel schema
    if rows:
        # Add model_name to all rows for tracking
        for row in rows:
            row["model_name"] = "indexing.document_sections"

        return writer.write(
            rows,
            table_schema=DocumentSectionRow,
            primary_keys=["document_id", "section_id"],
            write_strategy="replace",
        )
    else:
        return {"rows_written": 0, "rows_deduplicated": 0}
