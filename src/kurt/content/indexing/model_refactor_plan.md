# Indexing Pipeline Refactor Plan

This document tracks the migration from the legacy DBOS tasks to the new model-based pipeline under `src/kurt/content/indexing_new/`.

## Stage 1 – Framework & Document Splitting (Completed)
- ✅ Framework foundation (decorator, registry, ModelContext/run_models, TableReader/TableWriter using SQLModel, DSPy helpers, DBOS integration).
- ✅ Document loader: loads documents once per workflow run, honors incremental mode, and passes payloads downstream.
- ✅ `step_document_sections.py`: splits documents with the existing logic, emits per-section rows with section hashes and metadata.
- ✅ `workflow_indexing_new.py`: DBOS workflow that loads documents once, runs models via `run_models`, and emits batch status events.

## Stage 2 – Section Extraction (In Progress)
- Copy `IndexDocumentSignature` from legacy `indexing/models.py` into `step_extract_sections.py` (static class definition).
- Create SQLModel schema `SectionExtractionRow` with columns:
  - `document_id`, `section_id`, `section_number`, `section_title`
  - `metadata_json`, `entities_json`, `relationships_json`, `claims_json`
  - `error`, `tokens_prompt`, `tokens_completion`, `model_name`, `workflow_id`, `created_at`, `updated_at`
- Implement `@model(name="indexing.section_extractions", ...)` that consumes section payloads, runs DSPy via `run_batch`, normalizes outputs, captures telemetry, and writes rows (write_strategy="replace").
- Add unit tests (`models/tests/test_step_extract_sections.py`) covering success/error paths and telemetry.
- Update `workflow_indexing_new.py` to append the new model after section splitting and include its results.

## Stage 3 – Document Merge (Next)
- Port logic from `task_gather_sections.py` into `step_document_extractions.py`.
- Schema: per-document row containing merged metadata/topics/entities/relationships/claims, sections_processed/failed, and telemetry.
- Deduplicate entities/claims the same way as the current gather step.
- Tests verifying multiple sections merge into one document row.

## Stage 4 – Entity Resolution (Pending)
- Implement three models:
  1. `step_entity_resolution_stage2_links` – desired document→entity links (feeds existing link transaction).
  2. `step_entity_resolution_stage3_groups` – clustering + similarity fetch + DSPy resolution (store prep + decisions in one table).
  3. `step_entity_resolution_stage4_upserts` – emit entity/relationship upsert tables consumed by transactions.
- Reuse existing helpers (graph similarity, clustering, ResolveEntityGroup signature).

## Stage 5 – Claim Resolution (Pending)
- Implement models mirroring the entity pipeline:
  1. `step_claim_resolution_stage1_groups`
  2. `step_claim_resolution_stage2_llm`
  3. `step_claim_resolution_stage3_finalize`
- Ensure conflict/confidence data is emitted for the existing transactions.

## Testing & CLI Integration
- Each `step_*.py` model must have end-to-end unit tests using mock DSPy responses/embeddings.
- `tests/indexing_new/test_workflow_indexing_new.py` should validate the workflow runs the registered models in order.
- DBOS events (`emit_batch_status`) keep the CLI informed; final workflow should expose a feature flag to switch from legacy to new pipeline.

