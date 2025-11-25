# MotherDuck Project Dump

Real-world dump from the kurt-demo project containing MotherDuck-related documentation and content.

## Contents

- **874 documents**: Documentation, blog posts, and articles about MotherDuck
- **371 entities**: Knowledge graph entities extracted from content
- **1,667 document-entity links**: Connections between documents and entities
- **126 entity relationships**: Relationships between entities

## Use Cases

This dump is useful for testing:
- Document import scenarios
- Large-scale content ingestion
- Knowledge graph construction
- Entity extraction and resolution
- Real-world URL patterns
- GraphRAG queries on actual data

## Source

Exported from `/Users/julien/Documents/wik/wikumeo/projects/kurt-demo` on 2025-11-25.

## Schema

### Documents
- id
- source_url
- title
- content_path
- ingestion_status
- content_type

### Entities
- id
- name
- entity_type
- canonical_name
- description
- confidence_score
- source_mentions
- created_at

### Document-Entity Links
- document_id
- entity_id
- evidence_text
- relevance_score

### Entity Relationships
- source_entity_id
- target_entity_id
- relationship_type
- description
- strength
