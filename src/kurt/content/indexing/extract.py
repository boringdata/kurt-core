"""Document metadata and entity extraction using DSPy.

This module contains DSPy Trace #1: IndexDocument
- Extracts document metadata (content_type, topics, tools, structure)
- Extracts entities with pre-resolution (EXISTING vs NEW)
- Extracts relationships between entities

The same DSPy signature is used for both single and batch extraction.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import dspy

from kurt.content.document import load_document_content
from kurt.content.indexing.models import (
    ClaimExtraction,
    DocumentMetadataOutput,
    EntityExtraction,
    RelationshipExtraction,
)
from kurt.db.database import get_session
from kurt.db.graph_queries import get_top_entities
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

    from kurt.db.claim_models import ClaimType
    from kurt.db.models import EntityType, RelationshipType, ResolutionStatus

    # Get descriptions from enums
    claim_type_descriptions = ClaimType.get_all_descriptions()
    claim_extraction_guidelines = ClaimType.get_extraction_guidelines()
    entity_extraction_rules = EntityType.get_extraction_rules()

    class IndexDocument(dspy.Signature):
        __doc__ = f"""Index a document: extract metadata, entities, relationships, and claims.

        This is the core indexing operation that understands a document's:

        1. Document Metadata:
           - Content Type: reference, tutorial, guide, blog, product_page, etc.
           - Title: Extract or generate concise title
           - Topics: 3-5 main topics (e.g., "ML", "Data Engineering")
           - Tools: Technologies mentioned (e.g., "PostgreSQL", "React")
           - Structure: code examples, procedures, narrative
           - Claims: Factual statements with exact source quotes and character offsets

        2. Knowledge Graph Entities:

           WHAT IS AN ENTITY?
           An entity is any distinct concept, thing, or capability that has its own identity and can be referenced.
           This includes:
           - Named things (products, companies, technologies)
           - Capabilities and features (what things can do)
           - Methods and approaches (how things work)
           - Concepts and domains (areas of knowledge)

{entity_extraction_rules}

           - For each entity provide:
             * name: The entity name as it appears in text
             * entity_type: MUST be EXACTLY one of: Product, Feature, Technology, Topic, Company, Integration
               DO NOT use any other values like Person, Event, Organization, etc.
             * quote: Exact text (50-200 chars) where entity is mentioned
             * resolution_status: MUST be EXACTLY one of: {', '.join(ResolutionStatus.get_all_values())}
               {ResolutionStatus.EXISTING.value} if matches existing_entities list, else {ResolutionStatus.NEW.value}
             * matched_entity_index: If {ResolutionStatus.EXISTING.value}, provide the 'index' value from the matching entity in existing_entities list

        3. Relationships:
           - Extract relationships between entities
           - MUST use EXACTLY one of these types: {RelationshipType.get_all_types_string()}
           - DO NOT use any other values like extends, collaborates_with, etc.
           - Provide context snippet showing the relationship

        4. Claims (Knowledge Extraction):
           - Extract ALL types of knowledge from the document
           - IMPORTANT: Look for technical instructions, explanations, and background context
           - Aim for comprehensive coverage (10-20 claims for technical documentation)

           - Claim types - MUST use one of these specific types (NO "other" option):
{claim_type_descriptions}

           IMPORTANT: You must categorize every claim into one of the above types. If unsure, choose the closest match.

{claim_extraction_guidelines}

           - CRITICAL: entity_indices must reference YOUR OUTPUT entities list
           - Include ALL entities: product AND its capabilities/features/types
           - Provide exact quote (50-500 chars) with character offsets
           - Include confidence score (0.0-1.0)

        Be accurate - only list prominently discussed topics/tools/entities/claims.
        Always include exact quotes from the document for entities, relationships, and claims.
        """

        document_content: str = dspy.InputField(desc="Markdown document content (first 5000 chars)")
        existing_entities: list[dict] = dspy.InputField(
            default=[],
            desc="Known entities: [{index, name, type, description, aliases}, ...] where index is the position in this list",
        )

        # Outputs
        metadata: DocumentMetadataOutput = dspy.OutputField(
            desc="Document metadata (content_type, title, structure flags)"
        )
        entities: list[EntityExtraction] = dspy.OutputField(
            desc="All meaningful entities: products, companies, technologies, features, and concepts. Include both main entities (proper nouns) and their capabilities/features as separate entities."
        )
        relationships: list[RelationshipExtraction] = dspy.OutputField(
            desc="Relationships between entities"
        )
        claims: list[ClaimExtraction] = dspy.OutputField(
            desc="Factual claims extracted from the document, linked to entities by their indices in YOUR entities output list (0-based indexing)"
        )

    return IndexDocument


# ============================================================================
# Single Document Extraction
# ============================================================================


def _validate_and_transform_claims(extracted_claims: list, entities: list) -> tuple[list, int]:
    """
    Validate and transform extracted claims to ensure entity references are valid.

    Args:
        extracted_claims: List of ClaimExtraction objects from LLM
        entities: List of EntityExtraction objects from LLM

    Returns:
        Tuple of (valid_claims_list, invalid_count)
    """
    # Create mapping of entity indices to names
    entity_index_to_name = {i: entity.name for i, entity in enumerate(entities)}
    max_valid_index = len(entities) - 1 if entities else -1

    valid_claims = []
    invalid_count = 0

    for claim in extracted_claims:
        # Skip claims without entity references
        if not claim.entity_indices:
            logger.debug(f"Skipping claim without entity references: {claim.statement[:100]}")
            invalid_count += 1
            continue

        # Validate primary entity index
        primary_idx = claim.entity_indices[0]
        if primary_idx > max_valid_index or primary_idx not in entity_index_to_name:
            logger.warning(
                f"Invalid primary entity index {primary_idx} (max: {max_valid_index}) "
                f"for claim: {claim.statement[:100]}"
            )
            invalid_count += 1
            continue

        # Map indices to entity names
        primary_entity = entity_index_to_name[primary_idx]
        referenced_entities = [
            entity_index_to_name[idx]
            for idx in claim.entity_indices[1:]
            if idx in entity_index_to_name
        ]

        # Transform to dictionary format
        valid_claims.append(
            {
                "statement": claim.statement,
                "claim_type": claim.claim_type,
                "primary_entity": primary_entity,
                "referenced_entities": referenced_entities,
                "source_quote": claim.source_quote,
                "quote_start_offset": claim.quote_start_offset,
                "quote_end_offset": claim.quote_end_offset,
                "temporal_qualifier": getattr(claim, "temporal_qualifier", None),
                "version_info": getattr(claim, "version_info", None),
                "extraction_confidence": claim.confidence,
                "source_context": claim.source_quote,
            }
        )

    return valid_claims, invalid_count


def extract_document_metadata(
    document_id: str, extractor=None, force: bool = False, activity_callback: callable = None
) -> dict:
    """
    Index a document: extract metadata, entities, relationships, and claims.

    This is the core indexing operation that extracts:
    - Document metadata (content type, topics, tools, structure)
    - Knowledge graph entities (products, technologies, concepts)
    - Relationships between entities
    - Claims from the document content

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
            - claims_data: dict with (included by default):
                - extracted_claims: list[dict] (claims extracted)
                - conflicts: list[dict] (detected conflicts)

    Raises:
        ValueError: If document not found or not FETCHED
    """
    from uuid import UUID

    from sqlmodel import select

    from kurt.config import get_config_or_default
    from kurt.db.models import Document, ResolutionStatus

    # Get session first (use same session throughout to avoid attachment issues)
    session = get_session()

    # Resolve document ID using this session
    try:
        doc_uuid = UUID(document_id)
        # Use text-based comparison to avoid UUID type conversion issues
        uuid_str = str(doc_uuid).replace("-", "").lower()
        stmt = select(Document)
        all_docs = session.exec(stmt).all()
        doc = None
        for d in all_docs:
            if str(d.id).replace("-", "").lower() == uuid_str:
                doc = d
                break
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
        doc_uuid = doc.id  # Store the resolved full UUID (already a UUID object from the DB)

    # Use resolved UUID string consistently throughout
    resolved_doc_id = str(doc_uuid)

    if doc.ingestion_status.value != "FETCHED":
        raise ValueError(
            f"Document {doc.id} has not been fetched yet (status: {doc.ingestion_status.value})"
        )

    # Load content - check if this is a section document
    if doc.metadata and doc.metadata.get("is_section"):
        # Section document stores content in metadata
        content = doc.metadata.get("section_content", "")
        logger.debug(f"Loading section content from metadata for {doc.id}")
    else:
        # Regular document loads from filesystem
        content = load_document_content(doc)

    # Calculate current content hash
    current_content_hash = calculate_content_hash(content, algorithm="sha256")

    # Skip if content hasn't changed (unless --force)
    if not force and doc.indexed_with_hash == current_content_hash:
        logger.info(
            f"Skipping document {doc.id} - content unchanged (hash: {current_content_hash[:8]}...)"
        )
        # Get all entities from knowledge graph
        from kurt.db.graph_queries import get_document_entities

        all_entities = get_document_entities(doc.id, names_only=False, session=session)
        # Convert to entity dicts matching the format from extraction
        entities = [{"name": name, "type": etype} for name, etype in all_entities]

        return {
            "document_id": resolved_doc_id,
            "title": doc.title,
            "content_type": doc.content_type.value if doc.content_type else None,
            "entities": entities,
            "skipped": True,
            "skip_reason": "content unchanged",
        }

    logger.info(f"Indexing document {doc.id} ({len(content)} chars)")
    logger.info("  → Loading existing entities for resolution...")

    # Report activity: loading entities
    if activity_callback:
        activity_callback("Loading existing entities...")

    # Get existing entities for resolution
    existing_entities_raw = get_top_entities(limit=100, session=session)
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

    # Configure extractor if not provided (shared for both paths)
    if extractor is None:
        llm_config = get_config_or_default()
        try:
            current_lm = dspy.settings.lm
            if current_lm is None:
                max_tokens = 4000 if "haiku" in llm_config.INDEXING_LLM_MODEL.lower() else 8000
                lm = dspy.LM(llm_config.INDEXING_LLM_MODEL, max_tokens=max_tokens)
                dspy.configure(lm=lm)
        except (AttributeError, RuntimeError):
            max_tokens = 4000 if "haiku" in llm_config.INDEXING_LLM_MODEL.lower() else 8000
            lm = dspy.LM(llm_config.INDEXING_LLM_MODEL, max_tokens=max_tokens)
            dspy.configure(lm=lm)

        index_document_sig = _get_index_document_signature()
        extractor = dspy.ChainOfThought(index_document_sig)

    # Check if we should use section-based extraction for large documents
    if len(content) > 5000:
        logger.info(
            f"  → Document is large ({len(content)} chars), using section-based extraction..."
        )

        # Report activity
        if activity_callback:
            activity_callback("Processing document in sections...")

        # Use section-based extraction for large documents
        from kurt.content.indexing.section_extraction import (
            SectionExtractionResult,
            _merge_section_results,
        )
        from kurt.content.indexing.splitting import split_markdown_document

        # Split document into sections
        sections = split_markdown_document(content, max_chars=5000, overlap_chars=200)
        logger.info(f"  → Split into {len(sections)} sections")

        # Import threading utilities for parallel processing
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Process sections in parallel
        MAX_WORKERS = 3  # Limit concurrent LLM calls
        section_results = [None] * len(sections)  # Pre-allocate results list to maintain order

        def process_section(idx, section):
            """Process a single section (runs in thread)."""
            try:
                # Thread-local logging
                logger.info(
                    f"  → Processing section {idx+1}/{len(sections)}: {section.heading or 'No heading'}"
                )

                # Add context to section
                section_content = section.content
                if section.overlap_prefix:
                    section_content = f"[...{section.overlap_prefix[-100:]}]\n\n{section_content}"
                if section.overlap_suffix:
                    section_content = f"{section_content}\n\n[{section.overlap_suffix[:100]}...]"

                # REUSE THE SAME EXTRACTION CALL
                # Note: Each thread needs proper DSPy configuration
                # Copy the LM config to thread-local context
                with dspy.context(lm=dspy.settings.lm):  # Pass the LM to thread context
                    result = extractor(
                        document_content=section_content[:5000],
                        existing_entities=existing_entities_for_llm,
                    )

                # The result attributes should be JSON strings
                # Parse them into Python objects for the section result
                metadata_dict = {}
                entities_list = []
                relationships_list = []
                claims_list = []

                try:
                    # DSPy should return JSON strings for all outputs
                    # Parse them into dictionaries/lists
                    if hasattr(result, "metadata") and result.metadata:
                        metadata_dict = (
                            json.loads(result.metadata) if isinstance(result.metadata, str) else {}
                        )

                    if hasattr(result, "entities") and result.entities:
                        entities_list = (
                            json.loads(result.entities) if isinstance(result.entities, str) else []
                        )

                    if hasattr(result, "relationships") and result.relationships:
                        relationships_list = (
                            json.loads(result.relationships)
                            if isinstance(result.relationships, str)
                            else []
                        )

                    if hasattr(result, "claims") and result.claims:
                        claims_list = (
                            json.loads(result.claims) if isinstance(result.claims, str) else []
                        )

                except (json.JSONDecodeError, TypeError, AttributeError) as e:
                    logger.debug(f"  → Section {idx+1} extraction note: {str(e)[:100]}")
                    # Use defaults set above

                return idx, SectionExtractionResult(
                    section_id=section.section_id,
                    section_number=section.section_number,
                    metadata=metadata_dict,
                    entities=entities_list,
                    relationships=relationships_list,
                    claims=claims_list,
                )

            except Exception as e:
                logger.error(f"  → Error processing section {idx+1}: {e}")
                return idx, SectionExtractionResult(
                    section_id=section.section_id,
                    section_number=section.section_number,
                    error=str(e),
                )

        logger.info(
            f"  → Processing {len(sections)} sections in parallel (max {MAX_WORKERS} workers)..."
        )

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            futures = {
                executor.submit(process_section, i, section): i
                for i, section in enumerate(sections)
            }

            # Collect results as they complete
            for future in as_completed(futures):
                idx, result = future.result()
                section_results[idx] = result

                # Update activity callback
                if activity_callback:
                    completed = sum(1 for r in section_results if r is not None)
                    activity_callback(f"Processed {completed} of {len(sections)} sections...")

        # Merge all section results
        logger.info("  → Merging section results...")
        merged = _merge_section_results(section_results)

        # Convert merged result to expected format
        metadata_output = json.dumps(merged.metadata)
        entities_output = json.dumps(merged.entities)
        relationships_output = json.dumps(merged.relationships)
        claims_output = json.dumps(merged.claims)

    else:
        # Small document, use single extraction
        logger.info("  → Calling LLM to extract metadata + entities...")

        # Report activity: calling LLM
        if activity_callback:
            activity_callback("Calling LLM to extract metadata...")

        # Use the same configured extractor (already configured above)
        try:
            result = extractor(
                document_content=content[:5000],  # Limit to first 5000 chars
                existing_entities=existing_entities_for_llm,
            )
            metadata_output = result.metadata
            entities_output = result.entities
            relationships_output = result.relationships
            claims_output = result.claims if hasattr(result, "claims") else "[]"
        except Exception as e:
            # If DSPy parsing fails, log warning but continue
            logger.warning(f"DSPy parsing warning (will retry with JSON mode): {str(e)[:100]}")
            # Try again with explicit JSON configuration
            result = extractor(
                document_content=content[:5000],
                existing_entities=existing_entities_for_llm,
            )
            metadata_output = result.metadata
            entities_output = result.entities
            relationships_output = result.relationships
            claims_output = result.claims if hasattr(result, "claims") else "[]"

    # For section-based extraction, we already have JSON strings
    # For single extraction, we need to get outputs from result object
    if len(content) <= 5000 and "result" in locals():
        # Single extraction - get outputs from result
        entities_output = result.entities if hasattr(result, "entities") else "[]"
        relationships_output = result.relationships if hasattr(result, "relationships") else "[]"
        claims_output = result.claims if hasattr(result, "claims") else "[]"

    # SECOND PASS: Review and verify entity-claim linking (only for single extraction)
    if (
        len(content) <= 5000
        and hasattr(result, "claims")
        and result.claims
        and hasattr(result, "entities")
        and result.entities
    ):
        from kurt.content.indexing.entity_linking_verification import verify_and_fix_entity_linking

        result.claims, result.entities = verify_and_fix_entity_linking(
            result.claims, result.entities, logger=logger
        )

    # Track token usage
    token_usage = {}
    total_tokens = 0
    try:
        if hasattr(dspy.settings, "lm") and hasattr(dspy.settings.lm, "history"):
            if dspy.settings.lm.history:
                # Sum tokens from all LLM calls (first pass + second pass)
                for call in dspy.settings.lm.history[-2:]:  # Get last 2 calls
                    if isinstance(call, dict) and "usage" in call:
                        usage = call["usage"]
                        total_tokens += usage.get("total_tokens", 0)

                if total_tokens > 0:
                    logger.info(f"  → Total token usage: {total_tokens} tokens (both passes)")
    except Exception:
        pass  # Token tracking is optional

    logger.info("  ✓ LLM extraction completed")

    # Parse metadata if it's a JSON string
    if isinstance(metadata_output, str):
        metadata_dict = json.loads(metadata_output)
        logger.info(f"  → Extracted: type={metadata_dict.get('content_type', 'unknown')}")
    else:
        logger.info(f"  → Extracted: type={metadata_output.content_type.value}")
        metadata_dict = None

    # Get claims from the result (now a separate output)
    if isinstance(claims_output, str):
        extracted_claims = json.loads(claims_output) if claims_output else []
    else:
        extracted_claims = result.claims if hasattr(result, "claims") else []
    if extracted_claims:
        logger.info(f"  → Extracted {len(extracted_claims)} claims")

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

    # Handle both JSON string (section-based) and object (single extraction) metadata
    if isinstance(metadata_output, str):
        # Section-based extraction - metadata is JSON string
        metadata = json.loads(metadata_output)
        if not doc.cms_platform and "content_type" in metadata:
            doc.content_type = metadata["content_type"]
        doc.has_code_examples = metadata.get("has_code_examples", False)
        doc.has_step_by_step_procedures = metadata.get("has_step_by_step_procedures", False)
        doc.has_narrative_structure = metadata.get("has_narrative_structure", False)
        if metadata.get("extracted_title") and not doc.title:
            doc.title = metadata["extracted_title"]
    else:
        # Single extraction - metadata is an object
        if not doc.cms_platform:
            doc.content_type = metadata_output.content_type
        doc.has_code_examples = metadata_output.has_code_examples
        doc.has_step_by_step_procedures = metadata_output.has_step_by_step_procedures
        doc.has_narrative_structure = metadata_output.has_narrative_structure
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
        if (
            e.resolution_status == ResolutionStatus.EXISTING.value
            and e.matched_entity_index is not None
        ):
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
            "type": e.entity_type.value,  # Convert enum to string
            "description": e.description,
            "aliases": e.aliases,
            "confidence": e.confidence,
            "quote": e.quote,  # Store the exact quote from the document
        }
        for e in result.entities
        if e.resolution_status == ResolutionStatus.NEW.value
    ]
    relationships = [
        {
            "source_entity": r.source_entity,
            "target_entity": r.target_entity,
            "relationship_type": r.relationship_type.value,  # Convert enum to string
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

    # Build complete list of all extracted entities (both existing and new)
    all_extracted_entities = []

    # Add existing entities (need to get their details from the extraction result)
    for e in result.entities:
        entity_dict = {
            "name": e.name,
            "type": e.entity_type.value,
            "description": e.description,
            "aliases": e.aliases,
            "confidence": e.confidence,
            "quote": e.quote,
        }
        all_extracted_entities.append(entity_dict)

    # Handle both string (section-based) and object (single extraction) metadata
    if isinstance(metadata_output, str):
        # Section-based extraction returns JSON string
        content_type_value = metadata_dict.get("content_type", "unknown")
    else:
        # Single extraction returns object
        content_type_value = metadata_output.content_type.value

    result_dict = {
        "document_id": resolved_doc_id,
        "title": doc.title,
        "content_type": content_type_value,
        "entities": all_extracted_entities,  # ALL entities extracted (existing + new)
        "skipped": False,
        # Include document metadata for section detection
        "metadata": doc.metadata if doc.metadata else {},
        # Knowledge graph data
        "kg_data": {
            "existing_entities": existing_entity_ids,
            "new_entities": new_entities,
            "relationships": relationships,
        },
    }

    # Add claims data if extracted
    if extracted_claims:
        valid_claims, invalid_count = _validate_and_transform_claims(
            extracted_claims, result.entities
        )

        logger.info(
            f"  → Extracted {len(result.entities)} entities, {len(extracted_claims)} claims"
        )
        if invalid_count > 0:
            logger.warning(f"  → Filtered out {invalid_count} invalid claims")

        result_dict["claims_data"] = {
            "extracted_claims": valid_claims,
            "conflicts": [],  # Will be populated during claim resolution workflow
        }

    return result_dict


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
            lm = dspy.LM(model_name, max_tokens=8000)
            dspy.configure(lm=lm)
    except (AttributeError, RuntimeError):
        lm = dspy.LM(model_name, max_tokens=8000)
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

    # Cleanup executor - wait for threads to complete
    executor.shutdown(wait=True)

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
