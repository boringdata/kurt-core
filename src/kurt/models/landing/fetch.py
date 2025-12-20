"""Fetch model - Fetch content from discovered documents.

This model fetches content from web/CMS sources, generates embeddings,
saves content to files and database, and extracts internal links.

Input: documents table (filtered by ctx.document_ids)
Output table: landing_fetch
"""

import logging
from typing import Any, Optional
from uuid import UUID

import pandas as pd
from sqlalchemy import JSON, Column
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


class FetchConfig(ModelConfig):
    """Configuration for fetch step."""

    fetch_engine: str = ConfigParam(
        fallback="INGESTION_FETCH_ENGINE",
        default="trafilatura",
        description="Fetch engine: trafilatura, httpx, firecrawl",
    )
    embedding_max_chars: int = ConfigParam(
        fallback="INGESTION_EMBEDDING_MAX_CHARS",
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

    __tablename__ = "landing_fetch"

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
    name="landing.fetch",
    primary_key=["document_id"],
    write_strategy="replace",
    description="Fetch content, generate embedding, save documents, extract links",
    config_schema=FetchConfig,
)
@table(FetchRow)
def fetch(
    ctx: PipelineContext,
    documents=Reference("documents"),
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
    """
    # Filter documents by ctx.document_ids (explicit filtering)
    query = documents.query
    if ctx.document_ids:
        query = query.filter(documents.model_class.id.in_(ctx.document_ids))
    docs_df = pd.read_sql(query.statement, documents.session.bind)

    if docs_df.empty:
        logger.warning("No documents to fetch")
        return {"rows_written": 0, "documents_processed": 0}

    logger.info(f"Fetching {len(docs_df)} documents (engine: {config.fetch_engine})")

    # Process each document using apply
    docs_df["fetch_result"] = docs_df.apply(lambda row: _fetch_document(row, config), axis=1)

    # Extract results into columns
    docs_df["status"] = docs_df["fetch_result"].apply(lambda r: r.get("status", "ERROR"))
    docs_df["content_length"] = docs_df["fetch_result"].apply(lambda r: r.get("content_length", 0))
    docs_df["content_hash"] = docs_df["fetch_result"].apply(lambda r: r.get("content_hash"))
    docs_df["content_path"] = docs_df["fetch_result"].apply(lambda r: r.get("content_path"))
    docs_df["embedding_dims"] = docs_df["fetch_result"].apply(lambda r: r.get("embedding_dims", 0))
    docs_df["links_extracted"] = docs_df["fetch_result"].apply(
        lambda r: r.get("links_extracted", 0)
    )
    docs_df["public_url"] = docs_df["fetch_result"].apply(lambda r: r.get("public_url"))
    docs_df["metadata_json"] = docs_df["fetch_result"].apply(lambda r: r.get("metadata"))
    docs_df["error"] = docs_df["fetch_result"].apply(lambda r: r.get("error"))

    # Create rows using list comprehension
    rows = [
        FetchRow(
            document_id=str(row["id"]),
            status=row["status"],
            content_length=row["content_length"],
            content_hash=row["content_hash"],
            content_path=row["content_path"],
            embedding_dims=row["embedding_dims"],
            links_extracted=row["links_extracted"],
            fetch_engine=config.fetch_engine,
            public_url=row["public_url"],
            metadata_json=row["metadata_json"],
            error=row["error"],
        )
        for row in docs_df.to_dict("records")
    ]

    # Compute stats
    successful = (docs_df["status"] == "FETCHED").sum()
    failed = (docs_df["status"] == "ERROR").sum()

    logger.info(f"Fetch complete: {successful} successful, {failed} failed")

    result = writer.write(rows)
    result["documents_fetched"] = int(successful)
    result["documents_failed"] = int(failed)
    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _fetch_document(doc: pd.Series, config: FetchConfig) -> dict:
    """Fetch a single document and return result dict.

    Returns dict with: status, content_length, content_hash, content_path,
    embedding_dims, links_extracted, public_url, metadata, error
    """
    from kurt.db.documents import save_document_content_and_metadata, save_document_links
    from kurt.integrations.cms import fetch_from_cms
    from kurt.utils.embeddings import generate_document_embedding
    from kurt.utils.fetching import extract_document_links, fetch_from_web

    doc_id = doc.get("id")
    source_url = doc.get("source_url")

    try:
        # 1. Fetch content
        public_url = None
        if doc.get("cms_platform") and doc.get("cms_instance") and doc.get("cms_document_id"):
            content, metadata, public_url = fetch_from_cms(
                platform=doc["cms_platform"],
                instance=doc["cms_instance"],
                cms_document_id=doc["cms_document_id"],
                discovery_url=doc.get("discovery_url"),
            )
        else:
            content, metadata = fetch_from_web(
                source_url=source_url,
                fetch_engine=config.fetch_engine,
            )

        # 2. Generate embedding
        embedding_dims = 0
        try:
            embedding = generate_document_embedding(content, config.embedding_max_chars)
            embedding_dims = len(embedding) // 4  # bytes to float32 count
        except Exception as e:
            logger.warning(f"Embedding generation failed for {doc_id}: {e}")
            embedding = None

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
            link_source_url = public_url or source_url
            links = extract_document_links(content, link_source_url)
            if links:
                links_count = save_document_links(UUID(str(doc_id)), links)
        except Exception as e:
            logger.warning(f"Link extraction failed for {doc_id}: {e}")

        logger.info(f"Fetched {doc_id}: {len(content)} chars, {links_count} links")

        return {
            "status": "FETCHED",
            "content_length": len(content),
            "content_hash": metadata.get("fingerprint"),
            "content_path": save_result.get("content_path"),
            "embedding_dims": embedding_dims,
            "links_extracted": links_count,
            "public_url": public_url,
            "metadata": metadata,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to fetch {doc_id}: {e}")
        _mark_document_as_error(doc_id, str(e))
        return {
            "status": "ERROR",
            "content_length": 0,
            "content_hash": None,
            "content_path": None,
            "embedding_dims": 0,
            "links_extracted": 0,
            "public_url": None,
            "metadata": None,
            "error": str(e),
        }


def _mark_document_as_error(doc_id: Any, error_message: str) -> None:
    """Mark document as ERROR in database."""
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
