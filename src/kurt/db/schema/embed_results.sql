-- Embed Results: Output from EmbedTool
-- PK includes embedding_model to support multiple models per run
-- File path: sources/embeddings/<document_id>/<run_id>/<embedding_model>.npy

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

-- Latest view per document per model (deterministic tie-breaking)
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
