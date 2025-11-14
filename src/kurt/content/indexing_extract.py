"""Document metadata and entity extraction using DSPy.

This module contains DSPy Trace #1: IndexDocument
- Extracts document metadata (content_type, topics, tools, structure)
- Extracts entities with pre-resolution (EXISTING vs NEW)
- Extracts relationships between entities

The same DSPy signature is used for both single and batch extraction.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

import dspy

from kurt.content.indexing_helpers import (
    _get_top_entities,
    _load_document_content,
)
from kurt.content.indexing_models import (
    DocumentMetadataOutput,
    EntityExtraction,
    RelationshipExtraction,
)
from kurt.db.database import get_session
from kurt.utils import calculate_content_hash, get_git_commit_hash

logger = logging.getLogger(__name__)


# ============================================================================
# DSPy Trace #1: IndexDocument
# ============================================================================


def _get_index_document_signature():
    """Get the IndexDocument DSPy signature class.

    This is defined as a function to ensure it's created fresh in each thread,
    avoiding DSPy threading issues.
    """
    import dspy

    class IndexDocument(dspy.Signature):
        """Index a document: extract metadata, entities, and relationships.

        This is the core indexing operation that understands a document's:

        1. Document Metadata:
           - Content Type: reference, tutorial, guide, blog, product_page, etc.
           - Title: Extract or generate concise title
           - Topics: 3-5 main topics (e.g., "ML", "Data Engineering")
           - Tools: Technologies mentioned (e.g., "PostgreSQL", "React")
           - Structure: code examples, procedures, narrative

        2. Knowledge Graph Entities:
           - Extract meaningful entities (Products, Technologies, Features, etc.)
           - For each entity, provide an exact quote (50-200 chars) from the document where it's mentioned
           - Check if it matches existing entities
           - Mark as EXISTING if confident match (>80% similar), provide matched_entity_index (the index number from existing_entities list)
           - Mark as NEW if novel or unsure

        3. Relationships:
           - Extract relationships between entities
           - Types: mentions, part_of, integrates_with, enables, related_to, etc.
           - Provide context snippet showing the relationship

        Be accurate - only list prominently discussed topics/tools/entities.
        Always include exact quotes from the document for entities and relationships.
        """

        document_content: str = dspy.InputField(desc="Markdown document content (first 5000 chars)")
        existing_entities: list[dict] = dspy.InputField(
            default=[],
            desc="Known entities: [{index, name, type, description, aliases}, ...] where index is the position in this list",
        )

        # Outputs
        metadata: DocumentMetadataOutput = dspy.OutputField(
            desc="Document metadata (content_type, topics, tools, structure)"
        )
        entities: list[EntityExtraction] = dspy.OutputField(
            desc="Extracted entities with resolution status (EXISTING or NEW) and exact quotes from document"
        )
        relationships: list[RelationshipExtraction] = dspy.OutputField(
            desc="Relationships between entities"
        )

    return IndexDocument


# ============================================================================
# Single Document Extraction
# ============================================================================


def extract_document_metadata(
    document_id: str, extractor=None, force: bool = False, activity_callback: callable = None
) -> dict:
    """
    Index a document: extract metadata, entities, and relationships.

    This is the core indexing operation that extracts:
    - Document metadata (content type, topics, tools, structure)
    - Knowledge graph entities (products, technologies, concepts)
    - Relationships between entities

    Args:
        document_id: Document UUID (full or partial)
        extractor: Optional pre-configured DSPy extractor (for batch processing)
        force: If True, re-index even if content hasn't changed
        activity_callback: Optional callback(activity: str) for progress updates

    Returns:
        Dictionary with extraction results:
            - document_id: str
            - title: str
            - content_type: str
            - topics: list[str]
            - tools: list[str]
            - skipped: bool (True if skipped due to unchanged content)
            - kg_data: dict with:
                - existing_entities: list[str] (entity IDs to link)
                - new_entities: list[dict] (entities to resolve)
                - relationships: list[dict] (relationships to create)

    Raises:
        ValueError: If document not found or not FETCHED
    """
    from uuid import UUID

    from sqlmodel import select

    from kurt.config import get_config_or_default
    from kurt.db.models import Document

    # Get session first (use same session throughout to avoid attachment issues)
    session = get_session()

    # Resolve document ID using this session
    try:
        doc_uuid = UUID(document_id)
        doc = session.get(Document, doc_uuid)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
    except ValueError:
        # Try partial UUID match
        if len(document_id) < 8:
            raise ValueError(f"Document ID too short (minimum 8 characters): {document_id}")

        stmt = select(Document)
        docs = session.exec(stmt).all()
        partial_lower = document_id.lower().replace("-", "")
        matches = [d for d in docs if str(d.id).replace("-", "").startswith(partial_lower)]

        if len(matches) == 0:
            raise ValueError(f"Document not found: {document_id}")
        elif len(matches) > 1:
            raise ValueError(
                f"Ambiguous document ID '{document_id}' matches {len(matches)} documents. "
                f"Please provide more characters."
            )

        doc = matches[0]
        doc_uuid = doc.id  # Store the resolved full UUID

    # Use resolved UUID string consistently throughout
    resolved_doc_id = str(doc_uuid)

    if doc.ingestion_status.value != "FETCHED":
        raise ValueError(
            f"Document {doc.id} has not been fetched yet (status: {doc.ingestion_status.value})"
        )

    # Load content from filesystem
    content = _load_document_content(doc)

    # Calculate current content hash
    current_content_hash = calculate_content_hash(content, algorithm="sha256")

    # Skip if content hasn't changed (unless --force)
    if not force and doc.indexed_with_hash == current_content_hash:
        logger.info(
            f"Skipping document {doc.id} - content unchanged (hash: {current_content_hash[:8]}...)"
        )
        return {
            "document_id": resolved_doc_id,
            "title": doc.title,
            "content_type": doc.content_type.value if doc.content_type else None,
            "topics": doc.primary_topics or [],
            "tools": doc.tools_technologies or [],
            "skipped": True,
            "skip_reason": "content unchanged",
        }

    logger.info(f"Indexing document {doc.id} ({len(content)} chars)")
    logger.info("  → Loading existing entities for resolution...")

    # Report activity: loading entities
    if activity_callback:
        activity_callback("Loading existing entities...")

    # Get existing entities for resolution
    existing_entities_raw = _get_top_entities(session, limit=100)
    logger.info(f"  → Loaded {len(existing_entities_raw)} existing entities")

    # Create index-to-UUID mapping for efficient LLM processing
    # Instead of passing full UUIDs to LLM, we pass simple indices (0, 1, 2, ...)
    entity_index_to_uuid = {i: e["id"] for i, e in enumerate(existing_entities_raw)}

    # Prepare entities for LLM with index instead of UUID
    existing_entities_for_llm = [
        {
            "index": i,  # Simple number instead of UUID
            "name": e["name"],
            "type": e["type"],
            "description": e["description"],
            "aliases": e["aliases"],
        }
        for i, e in enumerate(existing_entities_raw)
    ]

    logger.info("  → Calling LLM to extract metadata + entities...")

    # Report activity: calling LLM
    if activity_callback:
        activity_callback("Calling LLM to extract metadata...")

    # Extract metadata + entities using unified DSPy signature
    if extractor is None:
        # Single document mode - configure DSPy here
        llm_config = get_config_or_default()

        # Check if DSPy is already configured
        try:
            current_lm = dspy.settings.lm
            if current_lm is None:
                # Not configured yet, configure it
                lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
                dspy.configure(lm=lm)
        except (AttributeError, RuntimeError):
            # DSPy not configured yet, configure it
            lm = dspy.LM(llm_config.INDEXING_LLM_MODEL)
            dspy.configure(lm=lm)

        index_document_sig = _get_index_document_signature()
        extractor = dspy.ChainOfThought(index_document_sig)

    result = extractor(
        document_content=content[:5000],  # Limit to first 5000 chars
        existing_entities=existing_entities_for_llm,
    )
    metadata_output = result.metadata

    logger.info("  ✓ LLM call completed")
    logger.info(
        f"  → Extracted: type={metadata_output.content_type.value}, "
        f"topics={len(metadata_output.primary_topics)}, "
        f"tools={len(metadata_output.tools_technologies)}"
    )
    logger.info("  → Updating document in database...")

    # Report activity: updating database
    if activity_callback:
        activity_callback("Updating database...")

    # Get git commit hash for content_file
    from kurt.config import load_config

    config = load_config()
    source_base = config.get_absolute_sources_path()
    content_file = source_base / doc.content_path
    git_commit_hash = get_git_commit_hash(content_file)

    # Update document with extracted metadata (session already obtained at start of function)
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

    logger.info("  ✓ Database updated")
    logger.info("  → Writing frontmatter to file...")

    # Sync frontmatter to file after database update
    from kurt.db.metadata_sync import write_frontmatter_to_file

    write_frontmatter_to_file(doc)
    logger.info("  ✓ Frontmatter synced")

    # Separate entities by resolution status
    # Map entity indices back to UUIDs
    existing_entity_ids = []
    for e in result.entities:
        if e.resolution_status == "EXISTING" and e.matched_entity_index is not None:
            # Validate index is in range
            if 0 <= e.matched_entity_index < len(entity_index_to_uuid):
                uuid = entity_index_to_uuid[e.matched_entity_index]
                existing_entity_ids.append(uuid)
            else:
                logger.warning(
                    f"Entity '{e.name}' has invalid index {e.matched_entity_index} "
                    f"(max: {len(entity_index_to_uuid)-1}), skipping"
                )
    new_entities = [
        {
            "name": e.name,
            "type": e.entity_type,
            "description": e.description,
            "aliases": e.aliases,
            "confidence": e.confidence,
            "quote": e.quote,  # Store the exact quote from the document
        }
        for e in result.entities
        if e.resolution_status == "NEW"
    ]
    relationships = [
        {
            "source_entity": r.source_entity,
            "target_entity": r.target_entity,
            "relationship_type": r.relationship_type,
            "context": r.context,
            "confidence": r.confidence,
        }
        for r in result.relationships
    ]

    logger.info(
        f"  → Found: {len(existing_entity_ids)} existing entities, "
        f"{len(new_entities)} new entities, {len(relationships)} relationships"
    )
    logger.info("  ✓ Indexing complete")

    return {
        "document_id": resolved_doc_id,
        "title": doc.title,
        "content_type": metadata_output.content_type.value,
        "topics": metadata_output.primary_topics,
        "tools": metadata_output.tools_technologies,
        "skipped": False,
        # Knowledge graph data
        "kg_data": {
            "existing_entities": existing_entity_ids,
            "new_entities": new_entities,
            "relationships": relationships,
        },
    }


# ============================================================================
# Batch Document Extraction
# ============================================================================


async def batch_extract_document_metadata(
    document_ids: list[str],
    max_concurrent: int = 5,
    force: bool = False,
    progress_callback=None,
) -> dict:
    """
    Extract metadata for multiple documents in parallel.

    Each worker thread configures its own DSPy instance to avoid threading issues.
    DSPy configuration and signature classes are created fresh in each thread.

    Args:
        document_ids: List of document UUIDs (full or partial)
        max_concurrent: Maximum number of concurrent extraction tasks (default: 5)
        force: If True, re-index even if content hasn't changed
        progress_callback: Optional callback function(doc_id, title, status, activity=None)
                          - Called with activity during processing (e.g., "Loading entities...")
                          - Called with final status on completion (activity=None)

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

    from kurt.config import get_config_or_default

    # Get model name for worker threads
    llm_config = get_config_or_default()
    model_name = llm_config.INDEXING_LLM_MODEL

    # Configure DSPy once in the main thread before parallel processing
    try:
        current_lm = dspy.settings.lm
        if current_lm is None:
            lm = dspy.LM(model_name)
            dspy.configure(lm=lm)
    except (AttributeError, RuntimeError):
        lm = dspy.LM(model_name)
        dspy.configure(lm=lm)

    # Get the signature and extractor in main thread
    index_document_sig = _get_index_document_signature()
    extractor = dspy.ChainOfThought(index_document_sig)

    # Create worker that uses dspy.context() for thread safety
    def worker_with_context(doc_id: str) -> tuple[str, dict | Exception]:
        """Worker that uses DSPy context for thread safety."""
        try:
            # Use dspy.context() to ensure proper thread initialization
            with dspy.context():
                logger.info(f"[{doc_id[:8]}] Starting indexing...")

                # Create activity callback wrapper that reports to progress_callback
                def activity_wrapper(activity: str):
                    if progress_callback:
                        # Report activity for timing tracking (status doesn't matter for activity updates)
                        progress_callback(doc_id, "", "", activity, None)

                result = extract_document_metadata(
                    doc_id, extractor=extractor, force=force, activity_callback=activity_wrapper
                )

                status = "skipped" if result.get("skipped") else "success"
                title = result.get("title", "Untitled")
                skip_reason = result.get("skip_reason")

                # Get the resolved document_id from result (handles partial UUID resolution)
                resolved_doc_id = result.get("document_id") or doc_id
                # Ensure resolved_doc_id is not empty/whitespace (fallback to input doc_id)
                if not resolved_doc_id.strip():
                    logger.warning(f"Empty document_id in result for {doc_id}, using input doc_id")
                    resolved_doc_id = doc_id

                if progress_callback:
                    # Report completion with timing info
                    progress_callback(resolved_doc_id, title, status, None, skip_reason)

                if result.get("skipped"):
                    logger.info(f"[{doc_id[:8]}] Skipped (content unchanged)")
                else:
                    logger.info(f"[{doc_id[:8]}] ✓ Indexed: {title}")
                return (resolved_doc_id, result)
        except Exception as e:
            logger.error(f"[{doc_id[:8]}] ✗ Failed: {e}")
            if progress_callback:
                progress_callback(doc_id, str(e), "error", None)
            return (doc_id, e)

    semaphore = asyncio.Semaphore(max_concurrent)
    loop = asyncio.get_event_loop()

    # Create explicit thread pool with max_concurrent threads for true parallelism
    executor = ThreadPoolExecutor(max_workers=max_concurrent)

    async def extract_with_semaphore(doc_id: str) -> tuple[str, dict | Exception]:
        """Extract metadata with semaphore to limit concurrency."""
        async with semaphore:
            # Run in executor with DSPy context
            return await loop.run_in_executor(executor, worker_with_context, doc_id)

    # Run all extractions concurrently
    tasks = [extract_with_semaphore(doc_id) for doc_id in document_ids]
    completed = await asyncio.gather(*tasks, return_exceptions=False)

    # Cleanup executor
    executor.shutdown(wait=False)

    # Separate successful results from errors
    results = []
    errors = []
    skipped_count = 0

    for doc_id, outcome in completed:
        if isinstance(outcome, Exception):
            errors.append(
                {
                    "document_id": doc_id,
                    "error": str(outcome),
                }
            )
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
