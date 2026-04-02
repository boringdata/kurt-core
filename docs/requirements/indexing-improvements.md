# Kurt Indexing Improvement Requirements

## Goals
- Preserve richer evidence during ingestion so the graph can cite exact passages.
- Reduce duplicate/ambiguous entities through better resolution inputs.
- Capture more structured signals (claims, metadata) and keep them linked to nodes/edges.
- Provide visibility into indexing status and regression risks.

## Functional Requirements
1. **Entity Evidence Preservation**
   - When linking an *existing* entity to a new document (`Stage 2`), persist the latest `DocumentEntity.context`, mention offsets, and confidence rather than only incrementing `mention_count`.
   - Maintain a history or at least the highest-confidence snippet per document/entity pair; expose it for downstream retrieval and auditing.
   - Store the `source_document_id` (or IDs if multiple) for every `EntityRelationship`, not just a free-form `context` string. This enables citations, filtering by source, and trust scoring.

2. **Expanded Candidate Pool for Resolution**
   - Replace `get_top_entities(limit=100)` with an embedding-based nearest-neighbor search across **all** entities so the LLM can resolve long-tail matches.
   - Include similarity scores + metadata (aliases, descriptions, types, doc counts) in the payload passed to the LLM.
   - Introduce configurable limits per entity type rather than a single global cap.

3. **Claim & Metadata Integration**
   - Persist all extracted claims (statement, offsets, referenced entities) and keep them linked to both the originating document and entity IDs.
   - Flag conflicts/duplicates during indexing using the existing `ClaimRelationship` schema so later validation workflows know which statements disagree.
   - Surface metadata such as `content_type`, code example flags, analytics, etc., in the KG so retrieval strategies can filter or weight sources by these attributes.

4. **Re-Indexing Hygiene**
   - When a document is re-indexed, remove obsolete `DocumentEntity` edges/relationships before inserting the new set, or mark them as superseded so historical context is explicit.
   - Track ingestion hash/commit **per entity and relationship** to detect stale links when a document changes upstream.

5. **Observability**
   - Emit indexing metrics (docs processed, entities created/merged, conflicts detected, failed resolutions) via structured logs or Prometheus counters.
   - Provide a CLI/terminal report summarizing entities/relationships/claims added per run to help operators catch regressions quickly.

## Non‑Functional Requirements
- **Deterministic Replays:** Re-running indexing on the same content should produce the same entity IDs unless the LLM explicitly changes a decision. Persist the random seeds / prompt parameters used during extraction for traceability.
- **Performance:** Ensure the new embedding lookups and evidence storage keep per-document indexing under the current SLA (target ≤ 30s per doc). Cache embeddings for frequent entity names to avoid recomputation.
- **Backfill Plan:** Ship migration scripts to populate missing relationship document IDs and snippets for existing data.
- **Extensibility:** Design the improved data model so future signals (e.g., temporal qualifiers, version tags) can be attached to both entities and relationships without yet another migration.

