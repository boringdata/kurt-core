-- Schema migrations tracking table
-- Stores which migrations have been applied

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP(6),
    description TEXT
);
