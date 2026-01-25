-- Fetch Results: Output from FetchTool
-- Each tool run creates new rows (history preserved via run_id)

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

-- Latest view with deterministic tie-breaking
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
