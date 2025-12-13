"""DBOS workflows for document indexing.

Two main workflows:
1. extraction_workflow: Extract metadata + entities only (Stage 1)
2. complete_indexing_workflow: Extract + resolve entities (Stages 1-4)
"""

import asyncio
import logging

from dbos import DBOS

logger = logging.getLogger(__name__)


# ============================================================================
# Extraction Steps (Stage 1 only)
# ============================================================================


@DBOS.step()
def extract_document_step(document_id: str, force: bool = False) -> dict:
    """Extract metadata, entities, and claims from a single document."""
    from kurt.content.indexing import extract_document_metadata

    return extract_document_metadata(document_id, force=force)


@DBOS.step()
def extract_documents_step(document_ids: list[str], force: bool = False) -> dict:
    """Extract metadata + entities from documents."""
    from kurt.content.indexing.extract import batch_extract_document_metadata

    # Run the async batch extraction
    return asyncio.run(
        batch_extract_document_metadata(
            document_ids, max_concurrent=5, force=force, progress_callback=None
        )
    )


@DBOS.step()
def split_documents_step(document_ids: list[str]) -> list[dict]:
    """Split multiple documents into sections without creating database records.

    Returns a list of all sections from all documents.
    Each section includes document metadata for later merging.
    """
    from kurt.content.indexing.task_split_document import split_document_task

    all_sections = []
    for doc_id in document_ids:
        split_result = split_document_task(doc_id)
        if split_result.get("sections"):
            # Add document metadata to each section
            for section in split_result["sections"]:
                section["document_id"] = doc_id
                section["title"] = split_result.get("title", "Untitled")
                all_sections.append(section)
        else:
            # Small document - create single section with full content
            if split_result.get("title"):
                # Document exists but is small, treat as single section
                all_sections.append(
                    {
                        "document_id": doc_id,
                        "title": split_result["title"],
                        "section_number": 1,
                        "heading": None,
                        "content": None,  # Will be loaded during extraction
                    }
                )

    logger.info(f"Split {len(document_ids)} documents into {len(all_sections)} sections")
    return all_sections


async def merge_section_results(results: list[dict]) -> list[dict]:
    """Merge section results back to parent documents.

    This function identifies section documents and merges them back to their parent,
    deduplicating entities, relationships, and claims.
    """
    from collections import defaultdict

    # Group results by parent document
    parent_groups = defaultdict(list)
    standalone_results = []

    for result in results:
        doc_id = result.get("document_id", "")
        # Check if this is a section document by looking at extraction metadata
        if result.get("metadata", {}).get("is_section"):
            # Get parent ID from metadata
            parent_id = result["metadata"].get("parent_document_id")
            if parent_id:
                parent_groups[parent_id].append(result)
            else:
                # Section without parent, treat as standalone
                standalone_results.append(result)
        else:
            # Not a section document
            standalone_results.append(result)

    # Merge section results for each parent
    for parent_id, section_results in parent_groups.items():
        if len(section_results) == 1:
            # Only one section, just use it as is
            standalone_results.append(section_results[0])
            continue

        # Merge multiple sections
        merged = {
            "document_id": parent_id,
            "title": section_results[0]
            .get("title", "")
            .rsplit(" - ", 1)[0],  # Remove section suffix
            "content_type": section_results[0].get("content_type"),
            "topics": [],
            "tools": [],
            "kg_data": {"existing_entities": [], "new_entities": [], "relationships": []},
            "claims_data": {"extracted_claims": [], "conflicts": []},
        }

        # Merge topics and tools (deduplicated)
        seen_topics = set()
        seen_tools = set()

        for result in section_results:
            for topic in result.get("topics", []):
                if topic not in seen_topics:
                    merged["topics"].append(topic)
                    seen_topics.add(topic)

            for tool in result.get("tools", []):
                if tool not in seen_tools:
                    merged["tools"].append(tool)
                    seen_tools.add(tool)

        # Merge KG data
        seen_entities = set()
        seen_relationships = set()

        for result in section_results:
            kg_data = result.get("kg_data", {})

            # Merge existing entities
            for entity_id in kg_data.get("existing_entities", []):
                if entity_id not in seen_entities:
                    merged["kg_data"]["existing_entities"].append(entity_id)
                    seen_entities.add(entity_id)

            # Merge new entities (deduplicate by name)
            for entity in kg_data.get("new_entities", []):
                entity_key = entity.get("name")
                if entity_key and entity_key not in seen_entities:
                    merged["kg_data"]["new_entities"].append(entity)
                    seen_entities.add(entity_key)

            # Merge relationships (deduplicate by source+target+type)
            for rel in kg_data.get("relationships", []):
                rel_key = (
                    rel.get("source_entity"),
                    rel.get("target_entity"),
                    rel.get("relationship_type"),
                )
                if all(rel_key) and rel_key not in seen_relationships:
                    merged["kg_data"]["relationships"].append(rel)
                    seen_relationships.add(rel_key)

        # Merge claims
        seen_claims = set()
        for result in section_results:
            claims_data = result.get("claims_data", {})

            # Merge extracted claims (deduplicate by statement)
            for claim in claims_data.get("extracted_claims", []):
                claim_key = claim.get("statement")
                if claim_key and claim_key not in seen_claims:
                    # Add section info to claim
                    section_id = result.get("document_id", "").split("_section_")[-1]
                    claim["source_section"] = f"Section {section_id}"
                    merged["claims_data"]["extracted_claims"].append(claim)
                    seen_claims.add(claim_key)

            # Merge conflicts
            merged["claims_data"]["conflicts"].extend(claims_data.get("conflicts", []))

        standalone_results.append(merged)
        logger.info(f"Merged {len(section_results)} sections for document {str(parent_id)[:8]}")

    return standalone_results


@DBOS.workflow()
async def complete_indexing_workflow(
    document_ids: list[str], force: bool = False, enable_kg: bool = True, max_concurrent: int = 5
) -> dict:
    """Complete end-to-end indexing workflow with granular events (Stages 1-6).

    Stages:
    1. Split large documents into sections (if needed)
    2. Extract metadata, entities, and claims
    3. Link existing entities
    4. Resolve new entities
    5. Create entities and relationships
    6. Resolve and store claims
    """
    from kurt.content.indexing.workflow_claim_resolution import (
        claim_resolution_workflow,
    )
    from kurt.content.indexing.workflow_entity_resolution import (
        complete_entity_resolution_workflow,
    )

    logger.info(f"Starting complete indexing workflow for {len(document_ids)} documents")

    # STAGE 1: Split large documents into sections (without creating DB records)
    logger.info("Stage 1: Splitting documents into sections...")
    all_sections = split_documents_step(document_ids)

    # Check if we have sections to process
    if all_sections:
        total_sections = len(all_sections)
        logger.info(f"Split {len(document_ids)} documents into {total_sections} sections")
    else:
        # No sections created (all docs don't exist or have no content)
        logger.warning("No sections created from documents")
        total_sections = 0

    # If no sections, return early
    if not all_sections:
        return {
            "extract_results": {
                "results": [],
                "errors": [],
                "total": len(document_ids),
                "succeeded": 0,
                "failed": 0,
                "skipped": len(document_ids),
            },
            "kg_stats": None,
            "claim_stats": None,
            "workflow_id": DBOS.workflow_id,
        }

    # Emit batch start events
    DBOS.set_event("batch_total", len(document_ids))
    DBOS.set_event("batch_status", "extracting")

    # STAGE 2: Extract metadata from sections using new DBOS task
    from kurt.content.indexing.task_extract_sections import extract_sections_task

    logger.info(f"Stage 2: Extracting {total_sections} sections...")
    section_extraction_results = extract_sections_task(all_sections)

    # STAGE 3: Gather and merge section results by document
    from kurt.content.indexing.task_gather_sections import gather_sections_task

    logger.info("Stage 3: Gathering and merging section results...")
    merged_results = gather_sections_task(section_extraction_results)

    # Process extraction results
    successful_results = [r for r in merged_results if not r.get("error")]
    errors = [r for r in merged_results if r.get("error")]

    # Count sections that were processed/failed
    total_sections_processed = sum(r.get("sections_processed", 0) for r in merged_results)
    total_sections_failed = sum(r.get("sections_failed", 0) for r in merged_results)

    extract_results = {
        "results": successful_results,
        "errors": errors,
        "total": len(document_ids),
        "succeeded": len(successful_results),
        "failed": len(errors),
        "skipped": 0,  # Handle skipped documents differently
        "sections_processed": total_sections_processed,
        "sections_failed": total_sections_failed,
    }

    logger.info(
        f"Stages 2-3 complete: {extract_results['succeeded']} documents indexed, "
        f"{extract_results['sections_processed']} sections processed, "
        f"{extract_results['sections_failed']} sections failed"
    )

    # Emit extraction completion
    DBOS.set_event("batch_extracted", len(successful_results))
    DBOS.set_event("batch_status", "resolving_entities")

    # STAGES 4-6: Finalize knowledge graph (checkpointed)
    kg_stats = None
    if enable_kg and successful_results:
        logger.info("Stages 4-6: Finalizing knowledge graph...")

        loop = asyncio.get_event_loop()
        from concurrent.futures import ThreadPoolExecutor

        executor = ThreadPoolExecutor(max_workers=max_concurrent)

        kg_stats = await loop.run_in_executor(
            executor, lambda: complete_entity_resolution_workflow(successful_results)
        )
        logger.info(
            f"Knowledge graph complete: {kg_stats.get('entities_created', 0)} created, "
            f"{kg_stats.get('entities_merged', 0)} merged, "
            f"{kg_stats.get('entities_linked_existing', 0)} linked"
        )

    # STAGE 7: Claim Resolution
    claim_stats = None
    if successful_results:
        # Check if any results have claims_data
        has_claims = any(r.get("claims_data") for r in successful_results)
        if has_claims:
            logger.info("Stage 6: Resolving and storing claims...")

            claim_results = []
            for result in successful_results:
                if result.get("claims_data"):
                    # Run claim resolution for each document with claims
                    claim_result = await claim_resolution_workflow(
                        document_id=result["document_id"],
                        claims_data=result["claims_data"],
                        entity_resolution_results=kg_stats or {},
                        git_commit=None,
                    )
                    claim_results.append(claim_result)

            # Aggregate claim statistics
            total_claims = sum(r.get("claims_processed", 0) for r in claim_results)
            total_conflicts = sum(r.get("conflicts_detected", 0) for r in claim_results)
            total_duplicates = sum(r.get("duplicates_skipped", 0) for r in claim_results)

            claim_stats = {
                "claims_processed": total_claims,
                "conflicts_detected": total_conflicts,
                "duplicates_skipped": total_duplicates,
                "documents_with_claims": len(claim_results),
            }

            logger.info(
                f"Stage 6 complete: {claim_stats['claims_processed']} claims processed, "
                f"{claim_stats['conflicts_detected']} conflicts detected, "
                f"{claim_stats['duplicates_skipped']} duplicates skipped"
            )

    # Emit final completion
    DBOS.set_event("batch_status", "completed")
    DBOS.set_event("workflow_done", True)  # Signal completion for CLI polling

    # Note: Do NOT shutdown the executor here to avoid "cannot schedule new futures after shutdown"
    # The executor will be cleaned up by Python's garbage collector when the workflow completes
    # or by the cleanup code in index.py's finally block

    return {
        "extract_results": extract_results,
        "kg_stats": kg_stats,
        "claim_stats": claim_stats,
        "workflow_id": DBOS.workflow_id,
    }
