"""DBOS task for splitting documents into sections.

This task splits a large document into sections without creating database records.
Sections exist only in memory for processing.
"""

import logging
from typing import Any, Dict
from uuid import UUID

from dbos import DBOS

logger = logging.getLogger(__name__)


@DBOS.step()
def split_document_task(document_id: str) -> Dict[str, Any]:
    """Split a document into sections without creating database records.

    Args:
        document_id: The document ID to split

    Returns:
        Dictionary containing:
        - document_id: The original document ID
        - title: Document title
        - source_url: Document source URL
        - sections: List of section dictionaries with content and metadata
    """
    from kurt.content.document import load_document_content
    from kurt.content.indexing.splitting import split_markdown_document
    from kurt.db import get_session
    from kurt.db.models import Document

    logger.info(f"Splitting document {document_id[:8]}...")

    # Convert string ID to UUID if needed
    if isinstance(document_id, str):
        document_uuid = UUID(document_id)
    else:
        document_uuid = document_id

    with get_session() as session:
        doc = session.get(Document, document_uuid)
        if not doc:
            logger.warning(f"Document {document_id} not found")
            return {"document_id": document_id, "sections": []}

        # Load document content
        content = load_document_content(doc)
        if not content:
            logger.warning(f"No content for document {document_id}")
            return {"document_id": document_id, "sections": []}

        # Check if splitting is needed
        if len(content) <= 5000:
            # Small document, return as single section
            logger.info(
                f"Document {document_id[:8]} is small ({len(content)} chars), no split needed"
            )
            return {
                "document_id": document_id,
                "title": doc.title,
                "source_url": doc.source_url,
                "sections": [
                    {
                        "section_number": 1,
                        "heading": None,
                        "content": content,
                        "start_offset": 0,
                        "end_offset": len(content),
                    }
                ],
            }

        # Split the document
        sections = split_markdown_document(content, max_chars=5000, overlap_chars=200)

        logger.info(f"Split document {document_id[:8]} into {len(sections)} sections")

        # Convert section objects to dictionaries
        section_data = []
        for section in sections:
            section_data.append(
                {
                    "section_number": section.section_number,
                    "heading": section.heading,
                    "content": section.content,
                    "start_offset": section.start_offset,
                    "end_offset": section.end_offset,
                    "overlap_prefix": section.overlap_prefix,
                    "overlap_suffix": section.overlap_suffix,
                }
            )

        return {
            "document_id": document_id,
            "title": doc.title,
            "source_url": doc.source_url,
            "sections": section_data,
        }
