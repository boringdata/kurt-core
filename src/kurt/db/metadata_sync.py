"""Metadata synchronization between database and files.

This module handles syncing document metadata from the database to markdown files
as YAML frontmatter.
"""

import logging
import re
from datetime import datetime
from typing import Optional

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class MetadataFrontmatter(BaseModel):
    """Pydantic model for metadata written to file frontmatter.

    This defines all fields that can be written to markdown file frontmatter.
    """

    title: Optional[str] = None
    content_type: Optional[str] = None
    topics: Optional[list[str]] = None
    tools: Optional[list[str]] = None
    description: Optional[str] = None
    author: Optional[list[str]] = None
    published_date: Optional[str] = None
    source_url: Optional[str] = None
    indexed_at: str
    content_hash: Optional[str] = None
    has_code_examples: Optional[bool] = None
    has_step_by_step: Optional[bool] = None
    has_narrative: Optional[bool] = None


# ============================================================================
# Frontmatter Sync Functions
# ============================================================================


def write_frontmatter_to_file(doc, session=None) -> None:
    """
    Write document metadata as YAML frontmatter to the markdown file.

    Also cleans up any pending sync queue entries for this document to prevent
    duplicate syncs.

    Args:
        doc: Document instance with metadata to write
        session: Optional SQLModel session (for testing/batch operations)
    """
    from sqlmodel import delete

    from kurt.db.database import get_session
    from kurt.db.models import IngestionStatus, MetadataSyncQueue

    # Skip if no content path
    if not doc.content_path:
        return

    # Skip if not fetched
    if doc.ingestion_status != IngestionStatus.FETCHED:
        return

    # Skip if no metadata to write
    if not any([doc.content_type, doc.primary_topics, doc.tools_technologies]):
        return

    try:
        # Load config to get sources path
        from kurt.config import load_config

        config = load_config()
        source_base = config.get_absolute_sources_path()
        content_file = source_base / doc.content_path

        if not content_file.exists():
            logger.warning(f"Content file not found for document {doc.id}: {content_file}")
            return

        # Read current content
        content = content_file.read_text(encoding="utf-8")

        # Remove existing frontmatter if present
        content_without_frontmatter = remove_frontmatter(content)

        # Build frontmatter model
        frontmatter = MetadataFrontmatter(
            title=doc.title,
            content_type=doc.content_type.value if doc.content_type else None,
            topics=doc.primary_topics,
            tools=doc.tools_technologies,
            description=doc.description,
            author=doc.author,
            published_date=doc.published_date.isoformat() if doc.published_date else None,
            source_url=doc.source_url,
            indexed_at=datetime.utcnow().isoformat(),
            content_hash=doc.indexed_with_hash[:16] if doc.indexed_with_hash else None,
            has_code_examples=doc.has_code_examples if doc.has_code_examples else None,
            has_step_by_step=doc.has_step_by_step_procedures
            if doc.has_step_by_step_procedures
            else None,
            has_narrative=doc.has_narrative_structure if doc.has_narrative_structure else None,
        )

        # Convert to dict and remove None values
        frontmatter_dict = frontmatter.model_dump(exclude_none=True)

        # Write frontmatter + content
        frontmatter_yaml = yaml.dump(frontmatter_dict, sort_keys=False, allow_unicode=True)
        new_content = f"---\n{frontmatter_yaml}---\n\n{content_without_frontmatter}"

        content_file.write_text(new_content, encoding="utf-8")
        logger.info(f"Updated frontmatter for document {doc.id} at {content_file}")

        # Clean up any pending queue entries for this document
        # (Silently skip if table doesn't exist - for backwards compatibility)
        try:
            # Use provided session or create new one
            cleanup_session = session if session is not None else get_session()
            close_session = session is None  # Only close if we created it

            stmt = delete(MetadataSyncQueue).where(MetadataSyncQueue.document_id == doc.id)
            result = cleanup_session.exec(stmt)
            if result.rowcount > 0:
                cleanup_session.commit()
                logger.debug(f"Cleaned up {result.rowcount} queue entries for document {doc.id}")

            if close_session:
                cleanup_session.close()
        except Exception as queue_error:
            # Silently ignore if table doesn't exist (older databases)
            if "no such table" not in str(queue_error).lower():
                logger.warning(f"Failed to clean up sync queue for {doc.id}: {queue_error}")
            if close_session:
                try:
                    cleanup_session.close()
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"Failed to write frontmatter for document {doc.id}: {e}")


def remove_frontmatter(content: str) -> str:
    """
    Remove YAML frontmatter from markdown content.

    Args:
        content: Markdown content that may contain frontmatter

    Returns:
        Content without frontmatter
    """
    # Check if content starts with ---
    if not content.startswith("---"):
        return content

    # Find the closing ---
    match = re.match(r"^---\s*\n(.*?\n)---\s*\n", content, re.DOTALL)
    if match:
        # Return content after frontmatter
        return content[match.end() :]

    return content


def process_metadata_sync_queue(session=None) -> dict:
    """
    Process the metadata sync queue.

    Reads all pending documents from the queue, syncs their frontmatter,
    and clears the queue.

    Args:
        session: Optional SQLModel session (for testing/batch operations)

    Returns:
        dict with:
            - processed: number of documents processed
            - errors: list of errors
    """
    from sqlmodel import select

    from kurt.db.database import get_session
    from kurt.db.models import Document, MetadataSyncQueue

    # Use provided session or create new one
    process_session = session if session is not None else get_session()
    close_session = session is None

    try:
        # Get all pending syncs
        # (Silently return if table doesn't exist - for backwards compatibility)
        try:
            stmt = select(MetadataSyncQueue)
            queue_items = process_session.exec(stmt).all()
        except Exception as e:
            if "no such table" in str(e).lower():
                logger.debug("metadata_sync_queue table does not exist, skipping")
                return {"processed": 0, "errors": []}
            raise

        if not queue_items:
            return {"processed": 0, "errors": []}

        processed = 0
        errors = []

        # Get unique document IDs
        doc_ids = list(set(item.document_id for item in queue_items))

        for doc_id in doc_ids:
            try:
                # Get document
                doc = process_session.get(Document, doc_id)
                if doc:
                    # Note: write_frontmatter_to_file() already cleans up the queue,
                    # so we don't need to delete items manually afterward
                    write_frontmatter_to_file(doc, session=process_session)
                    processed += 1
            except Exception as e:
                logger.error(f"Failed to sync frontmatter for {doc_id}: {e}")
                errors.append({"document_id": str(doc_id), "error": str(e)})

        # Queue should already be cleaned up by write_frontmatter_to_file()
        # But commit any remaining changes
        process_session.commit()

        return {"processed": processed, "errors": errors}

    finally:
        if close_session:
            process_session.close()
