# Cognee Internal Retrieval Overview

## High-Level Architecture
- **ECL Pipelines:** Cognee ingests data via Extract → Cognify → Load stages, turning documents, conversations, and media into graph nodes/edges plus vector collections (e.g., `DocumentChunk_text`, `Entity_name`, `Event_name`).
- **Search Orchestration:** `cognee.search()` (in `cognee/modules/search/methods/search.py`) logs the query, selects a `SearchType`, executes the associated retriever(s) per dataset, and formats responses via `prepare_search_result`.
- **Retriever Abstraction:** Each search type maps to one or two callables (`get_completion`, `get_context`) defined in `get_search_type_tools.py`, enabling modes like graph completion, summaries, code search, temporal queries, and natural-language-to-Cypher.

## Graph Retrieval Flow
1. **Triplet Retrieval**
   - `GraphCompletionRetriever.get_triplets` calls `brute_force_triplet_search`, which:
     - Projects a temporary `CogneeGraph` with relevant node/edge properties.
     - Runs vector searches against multiple collections (`Entity_name`, `TextSummary_text`, etc.).
     - Maps vector distances back onto graph nodes/edges and ranks triplets by importance.
2. **Context Resolution**
   - Retrieved edges are transformed into human-readable text through `resolve_edges_to_text`, producing a “Nodes” section (with summaries) and a “Connections” section (relationship statements).
3. **Completion Generation**
   - `generate_completion` or `generate_structured_completion` feeds the context to the configured LLM, optionally prepending serialized conversation history when session caching is enabled.
4. **Extensions**
   - **Context Extension:** `GraphCompletionContextExtensionRetriever` iteratively generates hypotheses → fetches new triplets → merges results until saturation.
   - **Chain-of-Thought:** `GraphCompletionCotRetriever` performs multiple reasoning rounds, validates answers, and issues follow-up queries.
   - **Summaries:** `GraphSummaryCompletionRetriever` auto-summarizes edges before passing them to the LLM.

## Additional Retrieval Modes
- **Vector / RAG:** `CompletionRetriever` and `ChunksRetriever` query vector collections directly (document chunks, summaries).
- **Lexical:** `JaccardChunksRetriever` performs token-based similarity with configurable stop words.
- **Code:** `CodeRetriever` interprets the query via LLM to extract filenames/source code spans, runs vector search over code collections, then reads actual files for context.
- **Temporal:** `TemporalRetriever` extracts time windows via LLM, filters events in the graph, and ranks them by semantic similarity.
- **Natural Language to Cypher:** `NaturalLanguageRetriever` introspects the schema, generates Cypher queries through LLM prompting, retries on errors, and returns raw query results.
- **Cypher Search:** Allows direct Cypher execution for power users.
- **Feedback & Coding Rules:** Specialized retrievers to record user feedback or fetch coding standards stored as graph nodes.

## Result Formatting & Caching
- `prepare_search_result` converts `(result, context, datasets)` tuples into:
  - `graphs`: node/edge lists for visualization (when context/result are `Edge` objects).
  - `context`: text per dataset (raw strings or newline-joined lists).
  - `result`: either the LLM answer or structured output.
- **Session Cache:** `session_cache.py` stores summarized context and answers keyed by user/session, enabling conversational continuity and providing history to prompts.
- **Interaction Logging:** `GraphCompletionRetriever.save_qa` (behind `save_interaction`) persists Q&A pairs plus the triplets used, forming a provenance trail for later analysis or feedback weighting.

