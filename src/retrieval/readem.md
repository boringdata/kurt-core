# Retrieval System Plan

## Purpose
Deliver a prompt-driven retrieval subsystem that mirrors Cognee’s GraphRAG ergonomics while remaining idiomatic to Kurt’s CLI/API. Every user input (prompt or follow-up question) must deterministically flow through retriever selection, graph lookups, context synthesis, and structured outputs so LLM calls are always grounded.

## Architecture Overview
- **Entry Points:** CLI (`kurt answer`, `kurt context`), Python SDK, and future agent hooks call a unified `RetrievalOrchestrator` that accepts `{prompt, query_type, dataset_scope, session_id, output_mode}`.
- **Retriever Registry:** Pluggable factory that returns one of the supported retrievers (GraphRAG, Semantic Chunk, Summary, Claim Search, CoT Validation). Configurable defaults live in `kurt.config`.
- **Graph/Data Access Layer:** Reuse existing DB helpers for datasets & workspaces. Provide convenience clients for nodes, edges, claims, summaries, and vector chunks so retrievers stay focused on strategy.
- **Context Builder:** Shared utility that converts raw nodes/documents into `Nodes + Connections` text, machine-readable payloads, optional Summaries, and citation bundles.
- **Session & Cache Store:** Lightweight persistence (SQLite or Redis abstraction) keyed by `session_id` containing recent prompts, contexts, answers, and citation metadata.
- **Observability Hooks:** Emit structured logs/events for each stage (retriever input, graph queries, iterations, token use) enabling CLI progress updates and later analytics.

## Phased Implementation
### Phase 0 – Foundations
1. Audit and document current retrieval path (GraphRAG baseline, DB helpers, CLI flags).
2. Extract shared DTOs (PromptContext, RetrieverResponse, Citation) for reuse.
3. Define new config keys (`DEFAULT_QUERY_TYPE`, `MAX_CONTEXT_TOKENS`, `MAX_GRAPH_ITERATIONS`, etc.).

### Phase 1 – Prompt → Graph Context (MVP)
1. Implement `RetrievalOrchestrator` shell with retriever registry and validator.
2. Build `GraphContextTransformation` utility per requirements (header metadata, deterministic text, JSON payload, citation tuples).
3. Wire CLI & SDK to call orchestrator when answering/contexting, preserving backwards compatibility with a feature flag.
4. Add regression tests comparing old vs. new default outputs to guarantee parity.

### Phase 2 – Iterative Graph Expansion & CoT
1. Create `GraphContextExtension` retriever that loops hypothesis → graph query until cap or no new edges, deduplicating nodes/edges each round.
2. Surface iteration telemetry in responses and stream progress via CLI logs.
3. Implement `GraphCompletionCotRetriever` (initial answer, validation prompt, follow-up questions) including optional claim verification re-queries.
4. Introduce configurable latency/accuracy trade-offs (e.g., `--fast`, `--deep`).

### Phase 3 – Alternate Search Types
1. **Chunk Semantic Search:** expose chunk store, vector similarity, lexical fallback, plus combined results into context builder.
2. **Summary Retrieval:** index and query pre-generated dataset summaries; ensure prompt oven view returns quickly.
3. **Claim Search:** fetch claims tied to entities with quote + confidence, optionally scoring by prompt overlap.
4. Extend CLI/API with `--query-type` flag and Python enums; update docs/examples.

### Phase 4 – Dataset Scoping, Sessions, Citations
1. Implement multi-dataset orchestration: run targeted retrieval per dataset, aggregate, and provide per-dataset stats.
2. Add session cache with CRUD, TTL, and `--session-id` flag default sourced from config/env.
3. Persist session summaries so follow-up prompts can reuse context/citations.
4. Enhance citation payloads with rationale snippets and ensure JSON output mirrors Cognee’s `CombinedSearchResult`.

### Phase 5 – Observability & Testing
1. Instrument retrieval stack with structured logs (triplets fetched, docs touched, cache hits) and expose via CLI verbose flag.
2. Build regression suite covering each query type, ensuring citations resolve to actual graph rows.
3. Add load tests for latency SLOs (graph-only ≤3s) and streaming telemetry validation for iterative modes.
4. Document troubleshooting playbooks and config examples in `docs/`.

## Dependencies & Risks
- Need parity with Cognee prompts (e.g., `resolve_edges_to_text`, `summarize_graph_context`)—clone or re-author to avoid licensing conflicts.
- Vector store performance must support fast chunk search; consider indexing tasks before enabling by default.
- Session storage introduces privacy considerations; confirm encryption/scoping before enabling multi-tenant deployments.

## Success Criteria
- Any user prompt can specify `--query-type` and `--session-id`, receive structured context + citations matching doc requirements.
- Retrieval latency and accuracy meet SLAs, validated via automated tests and manual parity checks with Cognee reference runs.
- Documentation and observability allow operators to debug why a prompt produced a given context without re-running manually.
