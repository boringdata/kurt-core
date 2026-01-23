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
-- documents: Map/fetch document metadata
-- =============================================================================
-- Used by MapTool and FetchTool to persist discovered/fetched document metadata.
-- - MapTool: INSERT with source_type, fetch_status='pending'
-- - FetchTool: UPDATE with content_path, content_hash, fetch_status='success'
-- - EmbedTool: UPDATE with embedding
--
-- Deduplication:
-- - url is UNIQUE
-- - Map skips existing URLs (upsert with no-op on conflict)
-- - Fetch skips already-fetched (check fetch_status='success')
CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(20),          -- url|file|cms
    content_path TEXT,                -- path to content file on disk
    content_hash VARCHAR(64),         -- SHA256 of content
    embedding BLOB,                   -- vector embedding (optional)
    fetch_status VARCHAR(20),         -- pending|fetching|success|error
    error TEXT,
    metadata JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(fetch_status);

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
