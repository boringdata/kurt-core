"""Fetch pipeline model.

This model fetches content from web/CMS sources, generates embeddings,
saves content to files and database, and extracts internal links.

Input: documents table (filtered by ctx.document_ids)
Output table: ingestion_fetch
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.content.document import save_document_content_and_metadata, save_document_links
from kurt.content.embeddings import generate_document_embedding
from kurt.core import (
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
)

from .utils import extract_document_links, fetch_from_cms, fetch_from_web

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class FetchConfig(ModelConfig):
    """Configuration for fetch step."""

    fetch_engine: str = ConfigParam(
        fallback="INGESTION_FETCH_ENGINE",
        default="trafilatura",
        description="Fetch engine: trafilatura, httpx, firecrawl",
    )
    embedding_max_chars: int = ConfigParam(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum characters for embedding generation",
    )


# ============================================================================
# Output Schema
# ============================================================================


class FetchRow(PipelineModelBase, table=True):
    """Records fetch operation results for a document.

    Inherits from PipelineModelBase:
    - workflow_id, created_at, updated_at, model_name, error
    """

    __tablename__ = "ingestion_fetch"

    # Primary key
    document_id: str = Field(primary_key=True)

    # Status
    status: str = Field(default="pending")  # FETCHED, ERROR

    # Content info
    content_length: int = Field(default=0)
    content_hash: Optional[str] = Field(default=None)
    content_path: Optional[str] = Field(default=None)

    # Embedding info
    embedding_dims: int = Field(default=0)

    # Links info
    links_extracted: int = Field(default=0)

    # Fetch info
    fetch_engine: Optional[str] = Field(default=None)
    public_url: Optional[str] = Field(default=None)

    # Metadata
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="ingestion.fetch",
    db_model=FetchRow,
    primary_key=["document_id"],
    write_strategy="replace",
    description="Fetch content, generate embedding, save documents, extract links",
    config_schema=FetchConfig,
)
def fetch(
    ctx: PipelineContext,
    documents=Reference(
        "documents",
        filter="id",  # SQL pushdown via ctx.document_ids
    ),
    writer: TableWriter = None,
    config: FetchConfig = None,
):
    """Fetch content, generate embedding, and save documents.

    Combined step that:
    1. Reads document metadata from documents table (source_url, cms_* fields)
    2. Fetches content via fetch_from_web() or fetch_from_cms()
    3. Generates embeddings via generate_document_embedding()
    4. Saves content to files and updates DB via save_document_content_and_metadata()
    5. Extracts and saves internal links

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        documents: Lazy reference to documents table
        writer: TableWriter for outputting result rows
        config: Configuration for fetch parameters
    """
    # Lazy load documents
    docs_df = documents.df

    if docs_df.empty:
        logger.warning("No documents to fetch")
        return {"rows_written": 0, "documents_processed": 0}

    document_records = docs_df.to_dict("records")
    logger.info(f"Fetching {len(document_records)} documents (engine: {config.fetch_engine})")

    rows = []
    successful = 0
    failed = 0

    for doc in document_records:
        doc_id = doc.get("id")
        source_url = doc.get("source_url")

        try:
            # 1. Fetch content
            public_url = None
            if doc.get("cms_platform") and doc.get("cms_instance") and doc.get("cms_document_id"):
                # CMS fetch
                content, metadata, public_url = fetch_from_cms(
                    platform=doc["cms_platform"],
                    instance=doc["cms_instance"],
                    cms_document_id=doc["cms_document_id"],
                    discovery_url=doc.get("discovery_url"),
                )
                logger.debug(f"Fetched from CMS: {doc['cms_platform']}/{doc['cms_document_id']}")
            else:
                # Web fetch
                content, metadata = fetch_from_web(
                    source_url=source_url,
                    fetch_engine=config.fetch_engine,
                )
                logger.debug(f"Fetched from web: {source_url}")

            # 2. Generate embedding
            try:
                embedding = generate_document_embedding(content, config.embedding_max_chars)
                embedding_dims = len(embedding) // 4  # bytes to float32 count
            except Exception as e:
                logger.warning(f"Embedding generation failed for {doc_id}: {e}")
                embedding = None
                embedding_dims = 0

            # 3. Save to DB + files
            save_result = save_document_content_and_metadata(
                doc_id=UUID(str(doc_id)),
                content=content,
                metadata=metadata,
                embedding=embedding,
                public_url=public_url,
            )

            # 4. Extract and save links
            links_count = 0
            try:
                # Use public_url for CMS documents, source_url for web
                link_source_url = public_url or source_url
                links = extract_document_links(content, link_source_url)
                if links:
                    links_count = save_document_links(UUID(str(doc_id)), links)
            except Exception as e:
                logger.warning(f"Link extraction failed for {doc_id}: {e}")

            # Record success
            rows.append(
                FetchRow(
                    document_id=str(doc_id),
                    status="FETCHED",
                    content_length=len(content),
                    content_hash=metadata.get("fingerprint"),
                    content_path=save_result.get("content_path"),
                    embedding_dims=embedding_dims,
                    links_extracted=links_count,
                    fetch_engine=config.fetch_engine,
                    public_url=public_url,
                    metadata_json=metadata,
                )
            )
            successful += 1
            logger.info(f"Fetched {doc_id}: {len(content)} chars, {links_count} links")

        except Exception as e:
            # Mark as error
            logger.error(f"Failed to fetch {doc_id}: {e}")
            _mark_document_as_error(doc_id, str(e))
            rows.append(
                FetchRow(
                    document_id=str(doc_id),
                    status="ERROR",
                    error=str(e),
                )
            )
            failed += 1

    logger.info(f"Fetch complete: {successful} successful, {failed} failed")

    result = writer.write(rows)
    result["documents_fetched"] = successful
    result["documents_failed"] = failed
    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _mark_document_as_error(doc_id: Any, error_message: str) -> None:
    """Mark document as ERROR in database.

    Updates the document's ingestion_status to ERROR.
    """
    from kurt.db.database import get_session
    from kurt.db.models import Document, IngestionStatus

    try:
        session = get_session()
        doc = session.get(Document, UUID(str(doc_id)))
        if doc:
            doc.ingestion_status = IngestionStatus.ERROR
            session.add(doc)
            session.commit()
            logger.debug(f"Marked document {doc_id} as ERROR")
    except Exception as e:
        logger.warning(f"Could not mark document {doc_id} as error: {e}")
