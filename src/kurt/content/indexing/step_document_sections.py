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
import re
from dataclasses import dataclass
from typing import Any, List, Optional

import pandas as pd
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import (
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
    table,
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
    primary_key=["document_id", "section_id"],
    write_strategy="replace",
    description="Split documents into sections for parallel processing",
    config_schema=DocumentSectionsConfig,
)
@table(DocumentSectionRow)
def document_sections(
    ctx: PipelineContext,
    documents=Reference("documents"),
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
    # Filter documents by ctx.document_ids (explicit filtering)
    query = documents.query
    if ctx.document_ids:
        query = query.filter(documents.model_class.id.in_(ctx.document_ids))
    documents_df = pd.read_sql(query.statement, documents.session.bind)

    if documents_df.empty:
        logger.warning("No documents to process")
        return {"rows_written": 0, "documents_processed": 0, "documents_skipped": 0}

    logger.info(
        f"Processing {len(documents_df)} documents for section splitting "
        f"(mode: {ctx.incremental_mode})"
    )

    # Filter out documents with errors or no content
    valid_mask = (
        ~documents_df.get("skip", pd.Series(False, index=documents_df.index)).fillna(False)
        & documents_df.get("error", pd.Series(None, index=documents_df.index)).isna()
        & documents_df["content"].notna()
        & (documents_df["content"] != "")
    )
    skipped_count = (~valid_mask).sum()
    valid_df = documents_df[valid_mask].copy()

    if valid_df.empty:
        return {"rows_written": 0, "skipped": skipped_count}

    # Split each document into sections using apply
    valid_df["sections"] = valid_df["content"].apply(
        lambda content: split_markdown_document(
            content,
            max_chars=config.max_section_chars,
            overlap_chars=config.overlap_chars,
            min_section_size=config.min_section_size,
        )
    )

    # Explode sections into rows
    sections_df = valid_df.explode("sections").reset_index(drop=True)

    # Create DocumentSectionRow objects
    rows = [
        DocumentSectionRow(
            document_id=row["document_id"],
            section_id=row["sections"].section_id,
            section_number=row["sections"].section_number,
            heading=row["sections"].heading,
            content=row["sections"].content,
            start_offset=row["sections"].start_offset,
            end_offset=row["sections"].end_offset,
            overlap_prefix=row["sections"].overlap_prefix,
            overlap_suffix=row["sections"].overlap_suffix,
            document_title=row.get("title"),
        )
        for row in sections_df.to_dict("records")
    ]

    logger.info(
        f"Generated {len(rows)} sections from {len(valid_df)} documents "
        f"(skipped {skipped_count})"
    )

    if not rows:
        return {"rows_written": 0, "skipped": skipped_count}

    result = writer.write(rows)

    # Update indexed_with_hash for successfully processed documents
    processed_docs = valid_df[["document_id", "content_hash"]].dropna(subset=["content_hash"])
    if not processed_docs.empty:
        for _, row in processed_docs.iterrows():
            writer.update_indexed_hash(row["document_id"], row["content_hash"])
        logger.info(f"Updated indexed_with_hash for {len(processed_docs)} documents")

    # Stats: documents processed and sections created
    result["documents"] = len(valid_df)
    result["sections"] = len(rows)
    # Only show skipped if there were any
    if skipped_count > 0:
        result["skipped"] = skipped_count
    return result


# ============================================================================
# Document Splitting Utilities
# ============================================================================


@dataclass
class DocumentSection:
    """Represents a section of a document for extraction."""

    section_id: str
    section_number: int
    heading: Optional[str]
    content: str
    start_offset: int
    end_offset: int
    overlap_prefix: Optional[str] = None
    overlap_suffix: Optional[str] = None


def split_markdown_document(
    content: str, max_chars: int = 5000, overlap_chars: int = 200, min_section_size: int = 500
) -> List[DocumentSection]:
    """Split a markdown document into logical sections.

    Args:
        content: The full document content
        max_chars: Maximum characters per section (default 5000 to match current limit)
        overlap_chars: Number of overlapping characters between sections for context
        min_section_size: Minimum size for a section to avoid tiny fragments

    Returns:
        List of DocumentSection objects
    """
    if len(content) <= max_chars:
        # Document fits in single section, no splitting needed
        return [
            DocumentSection(
                section_id=_generate_section_id(content, 0),
                section_number=1,
                heading=None,
                content=content,
                start_offset=0,
                end_offset=len(content),
            )
        ]

    # Find markdown headings to use as natural split points
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headings = list(heading_pattern.finditer(content))

    sections = []

    if headings:
        # Split by headings
        sections = _split_by_headings(content, headings, max_chars, overlap_chars, min_section_size)
    else:
        # No headings, split by paragraphs or size
        sections = _split_by_size(content, max_chars, overlap_chars, min_section_size)

    return sections


def _split_by_headings(
    content: str,
    headings: List[re.Match],
    max_chars: int,
    overlap_chars: int,
    min_section_size: int,
) -> List[DocumentSection]:
    """Split document using markdown headings as boundaries."""
    sections = []
    section_num = 0

    # Add implicit first section if content before first heading
    first_heading_pos = headings[0].start() if headings else len(content)
    if first_heading_pos > min_section_size:
        section_num += 1
        section_content = content[:first_heading_pos]
        sections.append(
            DocumentSection(
                section_id=_generate_section_id(section_content, 0),
                section_number=section_num,
                heading="Introduction",  # Default heading for content before first heading
                content=section_content.strip(),
                start_offset=0,
                end_offset=first_heading_pos,
            )
        )

    # Process each heading and its content
    for i, heading_match in enumerate(headings):
        heading_text = heading_match.group(2).strip()
        start_pos = heading_match.start()

        # Find end position (next heading or end of document)
        if i + 1 < len(headings):
            end_pos = headings[i + 1].start()
        else:
            end_pos = len(content)

        section_content = content[start_pos:end_pos].strip()

        # Check if section is too large and needs further splitting
        if len(section_content) > max_chars:
            # Split large section into smaller chunks
            subsections = _split_large_section(
                section_content, heading_text, start_pos, max_chars, overlap_chars, section_num
            )
            sections.extend(subsections)
            section_num += len(subsections)
        elif len(section_content) >= min_section_size:
            # Section is good size, add as is
            section_num += 1

            # Add overlap from previous section if exists
            overlap_prefix = None
            if sections and overlap_chars > 0:
                prev_content = sections[-1].content
                if len(prev_content) > overlap_chars:
                    overlap_prefix = prev_content[-overlap_chars:]

            sections.append(
                DocumentSection(
                    section_id=_generate_section_id(section_content, start_pos),
                    section_number=section_num,
                    heading=heading_text,
                    content=section_content,
                    start_offset=start_pos,
                    end_offset=end_pos,
                    overlap_prefix=overlap_prefix,
                )
            )
        elif sections:
            # Section too small, append to previous section if possible
            sections[-1].content += "\n\n" + section_content
            sections[-1].end_offset = end_pos

    # Add overlap suffixes
    for i in range(len(sections) - 1):
        if overlap_chars > 0:
            next_content = sections[i + 1].content
            if len(next_content) > overlap_chars:
                sections[i].overlap_suffix = next_content[:overlap_chars]

    return sections


def _split_large_section(
    section_content: str,
    heading_text: str,
    start_offset: int,
    max_chars: int,
    overlap_chars: int,
    section_num_offset: int,
) -> List[DocumentSection]:
    """Split a single large section into smaller chunks."""
    subsections = []
    chunks = _split_by_paragraphs(section_content, max_chars)

    for i, chunk in enumerate(chunks):
        subsection_num = section_num_offset + i + 1
        chunk_start = start_offset + chunk["start"]
        chunk_end = start_offset + chunk["end"]

        # Add overlap
        overlap_prefix = None
        overlap_suffix = None

        if i > 0 and overlap_chars > 0:
            prev_chunk = chunks[i - 1]["text"]
            if len(prev_chunk) > overlap_chars:
                overlap_prefix = prev_chunk[-overlap_chars:]

        if i < len(chunks) - 1 and overlap_chars > 0:
            next_chunk = chunks[i + 1]["text"]
            if len(next_chunk) > overlap_chars:
                overlap_suffix = next_chunk[:overlap_chars]

        subsections.append(
            DocumentSection(
                section_id=_generate_section_id(chunk["text"], chunk_start),
                section_number=subsection_num,
                heading=f"{heading_text} (Part {i+1})" if len(chunks) > 1 else heading_text,
                content=chunk["text"],
                start_offset=chunk_start,
                end_offset=chunk_end,
                overlap_prefix=overlap_prefix,
                overlap_suffix=overlap_suffix,
            )
        )

    return subsections


def _split_by_paragraphs(text: str, max_chars: int) -> List[dict]:
    """Split text by paragraphs, respecting max_chars limit."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_size = 0
    current_start = 0

    for para in paragraphs:
        para_size = len(para) + 2  # +2 for \n\n

        if current_size + para_size > max_chars and current_chunk:
            # Save current chunk
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(
                {"text": chunk_text, "start": current_start, "end": current_start + len(chunk_text)}
            )
            current_chunk = [para]
            current_size = para_size
            current_start += len(chunk_text) + 2
        else:
            current_chunk.append(para)
            current_size += para_size

    # Add remaining content
    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        chunks.append(
            {"text": chunk_text, "start": current_start, "end": current_start + len(chunk_text)}
        )

    return chunks


def _split_by_size(
    content: str, max_chars: int, overlap_chars: int, min_section_size: int
) -> List[DocumentSection]:
    """Split document by size when no headings are available."""
    sections = []
    chunks = _split_by_paragraphs(content, max_chars)

    for i, chunk in enumerate(chunks):
        section_num = i + 1

        # Add overlap
        overlap_prefix = None
        overlap_suffix = None

        if i > 0 and overlap_chars > 0:
            prev_chunk = chunks[i - 1]["text"]
            if len(prev_chunk) > overlap_chars:
                overlap_prefix = prev_chunk[-overlap_chars:]

        if i < len(chunks) - 1 and overlap_chars > 0:
            next_chunk = chunks[i + 1]["text"]
            if len(next_chunk) > overlap_chars:
                overlap_suffix = next_chunk[:overlap_chars]

        sections.append(
            DocumentSection(
                section_id=_generate_section_id(chunk["text"], chunk["start"]),
                section_number=section_num,
                heading=f"Section {section_num}",
                content=chunk["text"],
                start_offset=chunk["start"],
                end_offset=chunk["end"],
                overlap_prefix=overlap_prefix,
                overlap_suffix=overlap_suffix,
            )
        )

    return sections


def _generate_section_id(content: str, offset: int) -> str:
    """Generate a unique ID for a section based on content and position."""
    # Use first 100 chars of content + offset for uniqueness
    id_source = f"{content[:100]}_{offset}"
    return hashlib.md5(id_source.encode()).hexdigest()[:8]


def merge_overlapping_content(section: DocumentSection, include_overlap: bool = True) -> str:
    """Get the full content of a section including overlap if requested.

    Args:
        section: The document section
        include_overlap: Whether to include overlap prefix/suffix

    Returns:
        The section content with or without overlap
    """
    if not include_overlap:
        return section.content

    parts = []

    if section.overlap_prefix:
        parts.append(f"[...{section.overlap_prefix}]")

    parts.append(section.content)

    if section.overlap_suffix:
        parts.append(f"[{section.overlap_suffix}...]")

    return "\n\n".join(parts)
