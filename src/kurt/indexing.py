"""Document indexing logic using DSPy."""

import asyncio
import logging
from typing import Optional

import dspy
from pydantic import BaseModel

from kurt.models.models import ContentType

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class DocumentMetadataOutput(BaseModel):
    """Metadata extracted from document content."""

    content_type: ContentType
    extracted_title: Optional[str] = None
    primary_topics: list[str] = []
    tools_technologies: list[str] = []
    has_code_examples: bool = False
    has_step_by_step_procedures: bool = False
    has_narrative_structure: bool = False


# ============================================================================
# DSPy Signature
# ============================================================================


class ExtractMetadata(dspy.Signature):
    """Extract structured metadata from markdown document content.

    Analyze and extract:
    - Content Type: reference, tutorial, guide, blog, product_page, etc.
    - Title: Extract or generate concise title
    - Topics: 3-5 main topics (e.g., "ML", "Data Engineering")
    - Tools: Technologies mentioned (e.g., "PostgreSQL", "React")
    - Structure: code examples, procedures, narrative

    Be accurate - only list prominently discussed topics/tools.
    """

    document_content: str = dspy.InputField(description="Markdown document content")
    metadata: DocumentMetadataOutput = dspy.OutputField(description="Extracted metadata")


# ============================================================================
# Business Logic
# ============================================================================


def extract_document_metadata(document_id: str, extractor=None, force: bool = False) -> dict:
    """
    Extract and persist metadata for a document.

    Args:
        document_id: Document UUID (full or partial)
        extractor: Optional pre-configured DSPy extractor (for batch processing)
        force: If True, re-index even if content hasn't changed

    Returns:
        Dictionary with extraction results:
            - document_id: str
            - title: str
            - content_type: str
            - topics: list[str]
            - tools: list[str]
            - skipped: bool (True if skipped due to unchanged content)

    Raises:
        ValueError: If document not found or not FETCHED
    """
    from kurt.config import get_config_or_default, load_config
    from kurt.database import get_session
    from kurt.document import get_document
    from kurt.utils import calculate_content_hash, get_git_commit_hash

    # Get document
    doc = get_document(document_id)

    if doc.ingestion_status.value != "FETCHED":
        raise ValueError(
            f"Document {doc.id} has not been fetched yet (status: {doc.ingestion_status.value})"
        )

    # Load content from filesystem
    if not doc.content_path:
        raise ValueError(f"Document {doc.id} has no content_path")

    config = load_config()
    source_base = config.get_absolute_source_path()
    content_file = source_base / doc.content_path

    if not content_file.exists():
        raise ValueError(f"Content file not found: {content_file}")

    content = content_file.read_text(encoding="utf-8")

    if not content.strip():
        raise ValueError(f"Document {doc.id} has empty content")

    # Calculate current content hash
    current_content_hash = calculate_content_hash(content, algorithm="sha256")

    # Skip if content hasn't changed (unless --force)
    if not force and doc.indexed_with_hash == current_content_hash:
        logger.info(
            f"Skipping document {doc.id} - content unchanged (hash: {current_content_hash[:8]}...)"
        )
        return {
            "document_id": str(doc.id),
            "title": doc.title,
            "content_type": doc.content_type.value if doc.content_type else None,
            "topics": doc.primary_topics or [],
            "tools": doc.tools_technologies or [],
            "skipped": True,
        }

    logger.info(f"Extracting metadata for document {doc.id} ({len(content)} chars)")

    # Extract metadata using DSPy
    if extractor is None:
        # Single document mode - configure DSPy here
        llm_config = get_config_or_default()
        lm = dspy.LM(llm_config.LLM_MODEL_DOC_PROCESSING)
        dspy.configure(lm=lm)
        extractor = dspy.ChainOfThought(ExtractMetadata)

    result = extractor(document_content=content)
    metadata_output = result.metadata

    logger.info(
        f"Extracted: type={metadata_output.content_type.value}, "
        f"topics={len(metadata_output.primary_topics)}, "
        f"tools={len(metadata_output.tools_technologies)}"
    )

    # Get git commit hash for content_file
    git_commit_hash = get_git_commit_hash(content_file)

    # Update document with extracted metadata
    session = get_session()
    doc.indexed_with_hash = current_content_hash
    doc.indexed_with_git_commit = git_commit_hash
    doc.content_type = metadata_output.content_type
    doc.primary_topics = metadata_output.primary_topics
    doc.tools_technologies = metadata_output.tools_technologies
    doc.has_code_examples = metadata_output.has_code_examples
    doc.has_step_by_step_procedures = metadata_output.has_step_by_step_procedures
    doc.has_narrative_structure = metadata_output.has_narrative_structure

    # Update title if extracted and not already set
    if metadata_output.extracted_title and not doc.title:
        doc.title = metadata_output.extracted_title

    session.add(doc)
    session.commit()
    session.refresh(doc)

    logger.info(f"Updated document {doc.id} with extracted metadata")

    return {
        "document_id": str(doc.id),
        "title": doc.title,
        "content_type": metadata_output.content_type.value,
        "topics": metadata_output.primary_topics,
        "tools": metadata_output.tools_technologies,
        "skipped": False,
    }


def _extract_document_metadata_worker(document_id: str, extractor, force: bool = False) -> dict:
    """
    Worker function for async batch processing.

    This function is called in thread pool executors and expects
    extractor to be already configured (avoids dspy.configure() in threads).

    Args:
        document_id: Document UUID (full or partial)
        extractor: Pre-configured DSPy extractor
        force: If True, re-index even if content hasn't changed

    Returns:
        Dictionary with extraction results (same as extract_document_metadata)
    """
    return extract_document_metadata(document_id, extractor=extractor, force=force)


async def batch_extract_document_metadata(
    document_ids: list[str],
    max_concurrent: int = 5,
    force: bool = False,
) -> dict:
    """
    Extract metadata for multiple documents in parallel.

    Configures DSPy once in the main thread, then runs extractions in parallel
    using thread pool executors (avoids dspy.configure() threading issues).

    Args:
        document_ids: List of document UUIDs (full or partial)
        max_concurrent: Maximum number of concurrent extraction tasks (default: 5)
        force: If True, re-index even if content hasn't changed

    Returns:
        Dictionary with batch results:
            - results: list of successful extraction results
            - errors: list of errors with document_id and error message
            - total: total documents processed
            - succeeded: number of successful extractions
            - failed: number of failed extractions
            - skipped: number of skipped documents (unchanged content)

    Example:
        document_ids = ["abc123", "def456", "ghi789"]
        result = await batch_extract_document_metadata(document_ids, max_concurrent=3)

        print(f"Succeeded: {result['succeeded']}/{result['total']}")
        for res in result['results']:
            print(f"  {res['title']}: {res['content_type']}")
    """
    from functools import partial

    from kurt.config import get_config_or_default

    # Configure DSPy once in main thread (before spawning workers)
    llm_config = get_config_or_default()
    lm = dspy.LM(llm_config.LLM_MODEL_DOC_PROCESSING)
    dspy.configure(lm=lm)
    extractor = dspy.ChainOfThought(ExtractMetadata)

    # Create worker function with extractor pre-bound
    worker = partial(_extract_document_metadata_worker, extractor=extractor, force=force)

    semaphore = asyncio.Semaphore(max_concurrent)
    loop = asyncio.get_event_loop()

    async def extract_with_semaphore(doc_id: str) -> tuple[str, dict | Exception]:
        """Extract metadata with semaphore to limit concurrency."""
        async with semaphore:
            try:
                logger.info(f"Starting extraction for document {doc_id}")
                result = await loop.run_in_executor(None, worker, doc_id)
                logger.info(f"Completed extraction for document {doc_id}")
                return (doc_id, result)
            except Exception as e:
                logger.error(f"Failed to extract metadata for {doc_id}: {e}")
                return (doc_id, e)

    # Run all extractions concurrently
    tasks = [extract_with_semaphore(doc_id) for doc_id in document_ids]
    completed = await asyncio.gather(*tasks, return_exceptions=False)

    # Separate successful results from errors
    results = []
    errors = []
    skipped_count = 0

    for doc_id, outcome in completed:
        if isinstance(outcome, Exception):
            errors.append({
                "document_id": doc_id,
                "error": str(outcome),
            })
        else:
            if outcome.get("skipped", False):
                skipped_count += 1
            results.append(outcome)

    return {
        "results": results,
        "errors": errors,
        "total": len(document_ids),
        "succeeded": len(results),
        "failed": len(errors),
        "skipped": skipped_count,
    }
