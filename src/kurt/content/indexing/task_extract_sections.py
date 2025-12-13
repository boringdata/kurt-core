"""DBOS task for extracting metadata from multiple sections.

This task processes a batch of sections (potentially from different documents)
and extracts entities, relationships, and claims in parallel.
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import dspy
from dbos import DBOS

logger = logging.getLogger(__name__)


@DBOS.step()
def extract_sections_task(sections_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract metadata from multiple sections in parallel.

    Args:
        sections_batch: List of section dictionaries, each containing:
            - document_id: Parent document ID
            - title: Document title
            - section_number: Section number
            - heading: Section heading (optional)
            - content: Section content
            - overlap_prefix: Previous section overlap (optional)
            - overlap_suffix: Next section overlap (optional)

    Returns:
        List of extraction results, one per section, each containing:
        - document_id: Parent document ID
        - section_number: Section number
        - metadata: Extracted metadata
        - entities: List of extracted entities
        - relationships: List of extracted relationships
        - claims: List of extracted claims
        - error: Error message if extraction failed
    """
    from kurt.db import get_session
    from kurt.db.models import Entity

    logger.info(f"Extracting {len(sections_batch)} sections in parallel...")

    # Configure DSPy once in the main thread before parallel processing
    # Check if already configured to avoid conflicts in async contexts
    try:
        current_lm = dspy.settings.lm
        if current_lm is None:
            from kurt.config import get_config_or_default

            llm_config = get_config_or_default()
            max_tokens = 4000 if "haiku" in llm_config.INDEXING_LLM_MODEL.lower() else 8000
            lm = dspy.LM(llm_config.INDEXING_LLM_MODEL, max_tokens=max_tokens)
            dspy.configure(lm=lm)
            logger.info(f"Configured DSPy with model {llm_config.INDEXING_LLM_MODEL}")
        else:
            logger.info(
                f"DSPy already configured with {current_lm.model_name if hasattr(current_lm, 'model_name') else 'unknown model'}"
            )
    except (AttributeError, RuntimeError) as e:
        # If we can't check or configure, it might already be configured in an async context
        logger.info(f"DSPy configuration check: {e}")

    # Load existing entities once for all sections
    with get_session() as session:
        entities = session.query(Entity).limit(100).all()
        existing_entities = [
            {
                "id": str(entity.id),
                "name": entity.name,
                "type": entity.entity_type,
                "description": entity.description,
            }
            for entity in entities
        ]

    # Process sections in parallel
    results = []
    logger.info("Starting ThreadPoolExecutor with max_workers=3...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all extraction tasks
        futures = {}
        for section_data in sections_batch:
            logger.info(
                f"Submitting extraction for document {section_data['document_id'][:8]} section {section_data['section_number']}"
            )
            future = executor.submit(_extract_single_section, section_data, existing_entities)
            futures[future] = section_data

        # Collect results as they complete
        for future in as_completed(futures):
            section_data = futures[future]
            try:
                result = future.result(timeout=60)
                results.append(result)
                logger.info(
                    f"Completed extraction for document {section_data['document_id'][:8]} "
                    f"section {section_data['section_number']}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to extract document {section_data['document_id'][:8]} "
                    f"section {section_data['section_number']}: {e}"
                )
                results.append(
                    {
                        "document_id": section_data["document_id"],
                        "section_number": section_data["section_number"],
                        "section_heading": section_data.get("heading"),
                        "error": str(e),
                    }
                )

    logger.info(f"Extracted {len(results)} sections")
    return results


def _extract_single_section(
    section_data: Dict[str, Any], existing_entities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Extract metadata from a single section (runs in thread).

    Args:
        section_data: Section data dictionary
        existing_entities: List of existing entities for context

    Returns:
        Extraction result dictionary
    """
    from uuid import UUID

    from kurt.content.document import load_document_content
    from kurt.content.indexing.extract import _get_index_document_signature
    from kurt.db import get_session
    from kurt.db.models import Document

    document_id = section_data["document_id"]
    section_number = section_data["section_number"]

    logger.info(f"Starting extraction for section {section_number} of document {document_id[:8]}")

    # Get section content
    section_content = section_data.get("content")

    # If content is None, we need to load it from the document (small doc case)
    if section_content is None:
        with get_session() as session:
            doc_uuid = UUID(document_id) if isinstance(document_id, str) else document_id
            doc = session.get(Document, doc_uuid)
            if doc:
                section_content = load_document_content(doc)
            else:
                logger.warning(f"Document {document_id} not found")
                return {
                    "document_id": document_id,
                    "section_number": section_number,
                    "error": f"Document {document_id} not found",
                }

    if not section_content:
        logger.warning(f"No content for document {document_id} section {section_number}")
        return {
            "document_id": document_id,
            "section_number": section_number,
            "error": "No content available",
        }

    # Build section content with overlap context
    if section_data.get("overlap_prefix"):
        section_content = f"[...{section_data['overlap_prefix']}]\n\n{section_content}"
    if section_data.get("overlap_suffix"):
        section_content = f"{section_content}\n\n[{section_data['overlap_suffix']}...]"

    # DSPy is already configured in the main thread
    try:
        logger.info(f"Section {section_number}: Starting extraction...")

        # Create the extraction prompt with proper signature
        index_document_sig = _get_index_document_signature()
        extractor = dspy.ChainOfThought(index_document_sig)

        # Build title with section info
        title = section_data["title"]
        if section_data.get("heading"):
            title = f"{title} - {section_data['heading']}"
        else:
            title = f"{title} - Section {section_number}"

        # Build context with existing entities
        existing_str = json.dumps(existing_entities[:20]) if existing_entities else "[]"

        logger.info(f"Section {section_number}: Running LLM extraction...")
        # Run extraction
        result = extractor(
            document_title=title, document_content=section_content, existing_entities=existing_str
        )
        logger.info(f"Section {section_number}: LLM extraction complete")

        # Parse results - handle both string and object returns
        def parse_result_field(field, field_name):
            """Safely parse a result field that might be string or object."""
            if field is None:
                return {} if field_name == "metadata" else []
            if isinstance(field, str):
                try:
                    return json.loads(field)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse {field_name} as JSON: {field[:100]}")
                    return {} if field_name == "metadata" else []
            # Check if it's a Pydantic model with model_dump
            if hasattr(field, "model_dump"):
                return field.model_dump()
            # Already a dict/list
            return field

        metadata = parse_result_field(result.metadata, "metadata")
        entities = parse_result_field(result.entities, "entities")
        relationships = parse_result_field(result.relationships, "relationships")
        claims = parse_result_field(result.claims, "claims")

        # Ensure entities are converted to dicts if they are Pydantic models
        if entities and hasattr(entities[0] if entities else None, "model_dump"):
            entities = [e.model_dump() if hasattr(e, "model_dump") else e for e in entities]
        if relationships and hasattr(relationships[0] if relationships else None, "model_dump"):
            relationships = [
                r.model_dump() if hasattr(r, "model_dump") else r for r in relationships
            ]
        if claims and hasattr(claims[0] if claims else None, "model_dump"):
            claims = [c.model_dump() if hasattr(c, "model_dump") else c for c in claims]

        # Log extraction results
        logger.debug(
            f"Section {section_number} extracted: "
            f"{len(entities)} entities, {len(relationships)} relationships, {len(claims)} claims"
        )

        return {
            "document_id": document_id,
            "section_number": section_number,
            "section_heading": section_data.get("heading"),
            "metadata": metadata,
            "entities": entities,
            "relationships": relationships,
            "claims": claims,
            "error": None,
        }

    except Exception as e:
        import traceback

        logger.error(f"Error extracting section {section_number}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "document_id": document_id,
            "section_number": section_number,
            "section_heading": section_data.get("heading"),
            "metadata": {},
            "entities": [],
            "relationships": [],
            "claims": [],
            "error": str(e),
        }
