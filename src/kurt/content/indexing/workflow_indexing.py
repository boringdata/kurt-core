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
    """Extract metadata + entities from a single document."""
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


@DBOS.workflow()
async def complete_indexing_workflow(
    document_ids: list[str], force: bool = False, enable_kg: bool = True, max_concurrent: int = 5
) -> dict:
    """Complete end-to-end indexing workflow with granular events (Stages 1-4)."""
    from kurt.content.indexing.workflow_entity_resolution import (
        complete_entity_resolution_workflow,
    )

    logger.info(f"Starting complete indexing workflow for {len(document_ids)} documents")

    # Emit batch start events
    total = len(document_ids)
    DBOS.set_event("batch_total", total)
    DBOS.set_event("batch_status", "extracting")

    # STAGE 1: Extract metadata + entities with events
    semaphore = asyncio.Semaphore(max_concurrent)
    loop = asyncio.get_event_loop()

    async def extract_with_semaphore(document_id: str, index: int):
        """Extract one document with semaphore control and streaming progress."""
        import time

        from kurt.commands.content._live_display import format_display_timestamp

        key = f"doc_{index}"
        doc_id_short = document_id[:8] if len(document_id) > 8 else document_id

        async with semaphore:
            try:
                # Stream: Started
                DBOS.write_stream(
                    f"{key}_progress",
                    {
                        "message": f"{format_display_timestamp()}⠋ Extracting [{doc_id_short}]...",
                        "style": "dim cyan",
                    },
                )

                # Extract metadata + entities
                extract_start = time.time()
                result = await loop.run_in_executor(
                    None, lambda: extract_document_step(document_id, force=force)
                )
                extract_duration = time.time() - extract_start
                duration_ms = int(extract_duration * 1000)

                # Stream: Completion event
                if result.get("skipped"):
                    reason = result.get("skip_reason", "")
                    reason_short = reason[:40] if len(reason) > 40 else reason
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "message": f"{format_display_timestamp()}○ Skipped [{doc_id_short}] {reason_short} ({duration_ms}ms)",
                            "style": "dim yellow",
                            "advance_progress": True,
                        },
                    )
                    DBOS.close_stream(f"{key}_progress")
                elif "error" in result:
                    error = result.get("error", "Unknown error")
                    error_short = error[:60] + "..." if len(error) > 60 else error
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "message": f"{format_display_timestamp()}✗ Error [{doc_id_short}] {error_short} ({duration_ms}ms)",
                            "style": "dim red",
                            "advance_progress": True,
                        },
                    )
                    DBOS.close_stream(f"{key}_progress")
                else:
                    title = result.get("title", "Untitled")
                    title_short = title[:40] if len(title) > 40 else title
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "message": f"{format_display_timestamp()}✓ Indexed [{doc_id_short}] {title_short} ({duration_ms}ms)",
                            "style": "dim green",
                            "advance_progress": True,
                        },
                    )
                    DBOS.close_stream(f"{key}_progress")

                return result

            except Exception as e:
                error_msg = str(e)
                error_short = error_msg[:60] + "..." if len(error_msg) > 60 else error_msg
                DBOS.write_stream(
                    f"{key}_progress",
                    {
                        "message": f"{format_display_timestamp()}✗ Error [{doc_id_short}] {error_short}",
                        "style": "dim red",
                        "advance_progress": True,
                    },
                )
                DBOS.close_stream(f"{key}_progress")
                return {"document_id": document_id, "error": error_msg}

    # Run parallel extraction with events
    results = await asyncio.gather(
        *[extract_with_semaphore(doc_id, i) for i, doc_id in enumerate(document_ids)]
    )

    # Process results
    successful_results = [r for r in results if not r.get("error") and not r.get("skipped")]
    skipped = [r for r in results if r.get("skipped")]
    errors = [r for r in results if r.get("error")]

    extract_results = {
        "results": successful_results,
        "errors": errors,
        "total": total,
        "succeeded": len(successful_results),
        "failed": len(errors),
        "skipped": len(skipped),
    }

    logger.info(
        f"Stage 1 complete: {extract_results['succeeded']} succeeded, "
        f"{extract_results['failed']} failed, {extract_results['skipped']} skipped"
    )

    # Emit extraction completion
    DBOS.set_event("batch_extracted", len(successful_results))
    DBOS.set_event("batch_status", "resolving_entities")

    # STAGES 2-4: Finalize knowledge graph (checkpointed)
    kg_stats = None
    if enable_kg and successful_results:
        logger.info("Stages 2-4: Finalizing knowledge graph...")
        kg_stats = await loop.run_in_executor(
            None, lambda: complete_entity_resolution_workflow(successful_results)
        )
        logger.info(
            f"Knowledge graph complete: {kg_stats.get('entities_created', 0)} created, "
            f"{kg_stats.get('entities_merged', 0)} merged, "
            f"{kg_stats.get('entities_linked_existing', 0)} linked"
        )

    # Emit final completion
    DBOS.set_event("batch_status", "completed")
    DBOS.set_event("workflow_done", True)  # Signal completion for CLI polling

    return {
        "extract_results": extract_results,
        "kg_stats": kg_stats,
        "workflow_id": DBOS.workflow_id,
    }
