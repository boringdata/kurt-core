-- Document Registry: Central registry of all known documents
-- Populated by any tool that discovers new documents
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
