# Kurt Retrieval Improvement Requirements

## Retrieval System Overview
The goal is to accept an arbitrary natural-language prompt or follow-up question, discover the most relevant facts from the knowledge graph plus any auxiliary corpora, then format that context so a downstream LLM can ground its answer. The happy path mirrors Cognee’s GraphRAG flow:
1. Normalize and disambiguate the prompt (spell-check, entity detection, dataset scope, user/session metadata).
2. Run the selected retriever (graph-only, semantic chunk, summaries, etc.) and capture the graph nodes, edges, and raw documents.
3. Transform the retrieved artifacts into a deterministic text block (nodes + connections + citations) plus a machine-readable payload for auditing.
4. Optionally iterate (graph expansion, validation chain-of-thought, claim verification) until confidence thresholds or budget caps are met.
5. Return the final context, reasoning trace, citations, and a suggested completion prompt so callers can immediately ask LLMs for answers.

This document lists the capabilities needed so the system behaves like Cognee’s retrieval pipeline while fitting Kurt’s config, CLI, and API surfaces.

## Objectives
- Close the gap with Cognee’s retrieval stack by supporting richer graph context, multiple search modes, and traceable answers for prompt-driven workflows.
- Reduce failure cases where entity-only search misses relevant context by iteratively expanding the graph until no novel edges appear.
- Provide structured outputs (summaries, citations, graphs) tailored to different consumers (CLI, API, agents) so callers can plug them directly into completions.

## Functional Requirements
1. **Graph Context Transformation**
   - After fetching entities/relationships/documents, convert them into a normalized “Nodes + Connections” text block similar to Cognee’s `resolve_edges_to_text`, ensuring each edge lists participating node names, relationship type, and source doc IDs.
   - Include a header that echoes the original user prompt, selected dataset(s), retriever name, and session ID to make the context self-describing for downstream models.
   - Optionally summarize the context when it exceeds a configurable token budget using a dedicated prompt (e.g., `summarize_graph_context.txt`).

2. **Iterative Context Expansion**
   - Implement a `GraphContextExtension` mode that alternates between generating a hypothesis and re-querying the KG with that hypothesis until no new triplets are returned or a round cap is reached.
   - Deduplicate nodes/edges between rounds and expose stats (rounds run, triplets added) in the response.
   - Provide guardrails so multi-round expansions respect latency/token budgets (stop when marginal gains fall below a configurable ratio).

3. **Chain-of-Thought & Validation Mode**
   - Add a retriever that performs multi-step reasoning: initial answer, validation prompt, and follow-up question generation, similar to Cognee’s `GraphCompletionCotRetriever`.
   - Allow structured outputs (Pydantic models/JSON) for automation scenarios and attach the raw reasoning trace for auditability.
   - Support optional “claim verification” passes that re-query the KG for each assertion before finalizing the response.

4. **Alternate Search Types**
   - Provide at least three additional query types beyond current GraphRAG:
     1. **Chunk Semantic Search:** direct document chunk retrieval via vector similarity (with optional lexical fallback).
     2. **Summary Retrieval:** query pre-generated summaries to answer “overview” questions quickly.
     3. **Claim Search:** retrieve and rank claims linked to entities, returning their quotes and confidence.
   - Expose these via CLI flags and the Python API so downstream tools can choose the right mode.

5. **Dataset / Context Scoping**
   - Support searching across multiple datasets or workspaces by reusing the existing DB switching helpers; report per-dataset context and offer an optional combined context run (aggregate edges, then perform one completion).
   - Surface dataset-level relevance scores so orchestration layers can decide whether to keep or drop a corpus before prompting the LLM.

6. **Session Awareness**
   - Cache recent Q&A pairs (question, context summary, answer) keyed by user/session so follow-up questions can reuse context and so answers can reference previous citations.
   - Provide a `--session-id` flag on CLI commands and an API parameter to opt in/out.
   - Persist lightweight session summaries (intent, selected retriever, datasets touched) allowing the system to bias retrieval for clarifying questions.

7. **Citations & Graph Output**
   - Return machine-readable citations in addition to the textual answer: list of `(doc_id, title, content_path, snippet_start)` tuples plus the subset of graph edges used.
   - Offer a JSON mode that mirrors Cognee’s `CombinedSearchResult` (`result`, `context_texts`, `graphs`, `datasets`).
   - Include a short explanation of how each citation supported the final answer for easier review in UI layers.

## Non‑Functional Requirements
- **Latency:** Graph-only retrieval should remain within current SLA (≈2–3 s) for typical questions; iterative modes may take longer but must stream progress events/logs.
- **Configurability:** Make new retrievers pluggable so power users can set defaults in `kurt.config` (e.g., `DEFAULT_QUERY_TYPE`, max tokens per context, max rounds).
- **Observability:** Log retrieval stats (triplets fetched, documents touched, cache hits) and expose them for debugging.
- **Prompt & Context Traceability:** Persist every prompt + retriever configuration + resulting context blob for replay/debug, matching Cognee’s “reconstruction log”.
- **Backward Compatibility:** Maintain the current `kurt answer`/`kurt context` interface while defaulting to improved context formatting behind the scenes. Allow users to opt into new modes gradually.
- **Testing:** Add regression suites comparing answers vs. known corpora for each search mode and verifying that citations match the graph database contents.
