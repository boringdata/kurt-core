-- Unified Documents VIEW
-- Joins document_registry with all *_latest views
-- IMPORTANT: All *_latest views must be created BEFORE this view

CREATE OR REPLACE VIEW documents AS
SELECT
    r.document_id,
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
    -- Embed data (latest, one per model but showing most recent)
    el.embedding_model,
    el.vector_size,
    el.created_at AS embedded_at
FROM document_registry r
LEFT JOIN map_results_latest ml ON r.document_id = ml.document_id
LEFT JOIN fetch_results_latest fl ON r.document_id = fl.document_id
LEFT JOIN embed_results_latest el ON r.document_id = el.document_id;
