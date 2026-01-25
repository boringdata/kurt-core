-- Dolt schema for observability and document tables
-- kurt-core-24c.1: Observability schema for workflow runs, step logs, and events
-- kurt-core-24c.6: Documents table for map/fetch metadata
--
-- These tables track workflow execution in Dolt for:
-- - Workflow lifecycle (pending -> running -> completed/failed)
-- - Step-level summaries (one row per step)
-- - Append-only event stream for progress tracking
-- - Document metadata for map/fetch workflows
--
-- Streaming: step_events uses monotonic `id` for cursor-based streaming
-- (ORDER BY id ASC), not created_at (which has no ordering guarantee).

-- =============================================================================
-- workflow_runs: One row per workflow execution
-- =============================================================================
CREATE TABLE IF NOT EXISTS workflow_runs (
    id VARCHAR(36) PRIMARY KEY,
    workflow VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- pending|running|completed|failed|canceling|canceled
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error TEXT,
    inputs JSON,
    metadata JSON,
    INDEX idx_workflow_runs_status (status),
    INDEX idx_workflow_runs_started (started_at DESC)
);

-- =============================================================================
-- step_logs: Summary row per step (updated in place)
-- =============================================================================
CREATE TABLE IF NOT EXISTS step_logs (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) NOT NULL,
    step_id VARCHAR(255) NOT NULL,
    tool VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- pending|running|completed|failed|canceled
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    input_count INT,
    output_count INT,
    error_count INT DEFAULT 0,
    errors JSON,                   -- [{row_idx, error_type, message}]
    metadata JSON,
    INDEX idx_step_logs_run_step (run_id, step_id),
    UNIQUE KEY uq_step_logs_run_step (run_id, step_id),
    CONSTRAINT fk_step_logs_run FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
);

-- =============================================================================
-- step_events: Append-only event stream for progress
-- =============================================================================
-- id is BIGINT AUTO_INCREMENT for monotonic ordering (streaming cursor).
-- created_at is for display only - no ordering guarantees.
CREATE TABLE IF NOT EXISTS step_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    run_id VARCHAR(36) NOT NULL,
    step_id VARCHAR(255) NOT NULL,
    substep VARCHAR(255),
    status VARCHAR(20) NOT NULL,  -- running|progress|completed|failed
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    current INT,
    total INT,
    message TEXT,
    metadata JSON,
    INDEX idx_step_events_run_id (run_id, id)
);

-- =============================================================================
-- TOOL-OWNED TABLES (new architecture: 1 table per tool)
-- =============================================================================
-- See spec: kurt-core-5v6 "Tool-Owned Tables with Pydantic Schemas"
-- Each tool owns its table. History preserved via (document_id, run_id) key.
-- Unified `documents` VIEW joins all tool tables via document_registry.

-- =============================================================================
-- schema_migrations: Track applied migrations
-- =============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    description TEXT
);

-- =============================================================================
-- document_registry: Central registry of all known documents
-- =============================================================================
-- Populated by any tool that discovers new documents.
-- CRITICAL: url_hash MUST use same canonicalization as document_id
CREATE TABLE IF NOT EXISTS document_registry (
    document_id VARCHAR(12) PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    url_hash VARCHAR(64) NOT NULL,  -- SHA256 of canonicalized URL
    source_type VARCHAR(20) NOT NULL,  -- url|file|cms
    first_seen_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY idx_registry_url_hash (url_hash),
    INDEX idx_registry_url (url(255))
);

-- =============================================================================
-- map_results: Output from MapTool
-- =============================================================================
CREATE TABLE IF NOT EXISTS map_results (
    document_id VARCHAR(12) NOT NULL,
    run_id VARCHAR(36) NOT NULL,
    url TEXT NOT NULL,
    source_type VARCHAR(20) DEFAULT 'url',
    discovery_method VARCHAR(50) NOT NULL,
    discovery_url TEXT,
    title TEXT,
    status VARCHAR(20) DEFAULT 'success',
    error TEXT,
    metadata JSON,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (document_id, run_id),
    INDEX idx_map_created (created_at),
    INDEX idx_map_status (status)
);

-- =============================================================================
-- fetch_results: Output from FetchTool
-- =============================================================================
CREATE TABLE IF NOT EXISTS fetch_results (
    document_id VARCHAR(12) NOT NULL,
    run_id VARCHAR(36) NOT NULL,
    url TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,  -- success|error|skipped
    content_path TEXT,
    content_hash VARCHAR(64),
    content_length INT,
    fetch_engine VARCHAR(50),
    error TEXT,
    metadata JSON,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (document_id, run_id),
    INDEX idx_fetch_created (created_at),
    INDEX idx_fetch_status (status)
);

-- =============================================================================
-- embed_results: Output from EmbedTool
-- =============================================================================
-- PK includes embedding_model to support multiple models per run
CREATE TABLE IF NOT EXISTS embed_results (
    document_id VARCHAR(12) NOT NULL,
    run_id VARCHAR(36) NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,
    embedding_path TEXT NOT NULL,
    vector_size INT NOT NULL,
    created_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (document_id, run_id, embedding_model),
    INDEX idx_embed_created (created_at),
    INDEX idx_embed_model (embedding_model)
);

-- =============================================================================
-- LATEST VIEWS: Deterministic tie-breaking with ROW_NUMBER
-- =============================================================================

CREATE OR REPLACE VIEW map_results_latest AS
SELECT document_id, run_id, url, source_type, discovery_method,
       discovery_url, title, status, error, metadata, created_at
FROM (
    SELECT m.*,
           ROW_NUMBER() OVER (
               PARTITION BY m.document_id
               ORDER BY m.created_at DESC, m.run_id DESC
           ) AS rn
    FROM map_results m
) ranked
WHERE rn = 1;

CREATE OR REPLACE VIEW fetch_results_latest AS
SELECT document_id, run_id, url, status, content_path, content_hash,
       content_length, fetch_engine, error, metadata, created_at
FROM (
    SELECT f.*,
           ROW_NUMBER() OVER (
               PARTITION BY f.document_id
               ORDER BY f.created_at DESC, f.run_id DESC
           ) AS rn
    FROM fetch_results f
) ranked
WHERE rn = 1;

CREATE OR REPLACE VIEW embed_results_latest AS
SELECT document_id, run_id, embedding_model, embedding_path,
       vector_size, created_at
FROM (
    SELECT e.*,
           ROW_NUMBER() OVER (
               PARTITION BY e.document_id, e.embedding_model
               ORDER BY e.created_at DESC, e.run_id DESC
           ) AS rn
    FROM embed_results e
) ranked
WHERE rn = 1;

-- =============================================================================
-- documents VIEW: Unified view joining all tool tables
-- =============================================================================
CREATE OR REPLACE VIEW documents AS
SELECT
    r.document_id,
    r.document_id AS id,  -- Alias for backward compatibility
    r.url,
    r.source_type,
    r.first_seen_at,
    -- Map data (latest)
    ml.discovery_method,
    ml.title,
    ml.status AS map_status,
    ml.created_at AS mapped_at,
    -- Fetch data (latest)
    fl.status AS fetch_status,
    fl.content_path,
    fl.content_hash,
    fl.content_length,
    fl.fetch_engine,
    fl.created_at AS fetched_at,
    -- Embed data (latest)
    el.embedding_model,
    el.vector_size,
    el.created_at AS embedded_at,
    -- Computed fields for backward compatibility
    COALESCE(fl.created_at, ml.created_at, r.first_seen_at) AS created_at,
    COALESCE(fl.created_at, ml.created_at, r.first_seen_at) AS updated_at,
    fl.error AS error,
    ml.metadata AS metadata
FROM document_registry r
LEFT JOIN map_results_latest ml ON r.document_id = ml.document_id
LEFT JOIN fetch_results_latest fl ON r.document_id = fl.document_id
LEFT JOIN embed_results_latest el ON r.document_id = el.document_id;

-- =============================================================================
-- llm_traces: LLM call traces for cost/token tracking
-- =============================================================================
-- Stores individual LLM API calls for observability and cost analysis.
-- Used by TracingHooks to record token usage and costs.
--
-- Storage format:
-- - prompt: raw text as sent to API
-- - response: raw text from API
-- - structured_output: parsed JSON if output_schema was used
-- - cost_usd: computed from token counts + model pricing
CREATE TABLE IF NOT EXISTS llm_traces (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36),
    step_id VARCHAR(255),
    model VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,           -- openai|anthropic|cohere
    prompt TEXT,
    response TEXT,
    structured_output JSON,                  -- if output_schema used
    tokens_in INT NOT NULL,
    tokens_out INT NOT NULL,
    cost_usd DECIMAL(10,6),
    latency_ms INT,
    error TEXT,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    INDEX idx_llm_traces_run (run_id),
    INDEX idx_llm_traces_created (created_at DESC),
    INDEX idx_llm_traces_model (model)
);
