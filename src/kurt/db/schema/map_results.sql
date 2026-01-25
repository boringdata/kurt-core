-- Map Results: Output from MapTool
-- Each tool run creates new rows (history preserved via run_id)

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

-- Latest view with deterministic tie-breaking
-- Uses ROW_NUMBER with (created_at DESC, run_id DESC) for stable ordering
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
