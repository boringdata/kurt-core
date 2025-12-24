"""Test fixtures for retrieval tests."""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
from sqlmodel import SQLModel

from kurt.db.database import get_session
from kurt.db.models import (
    ContentType,
    Document,
    DocumentEntity,
    Entity,
    EntityRelationship,
    EntityType,
    IngestionStatus,
    SourceType,
)


def create_embedding(seed: int, dim: int = 512) -> bytes:
    """Create a deterministic embedding vector for testing.

    Args:
        seed: Seed for random number generation (makes embeddings deterministic)
        dim: Embedding dimensions (default 512 as per schema)

    Returns:
        Embedding as bytes (float32 array)
    """
    rng = np.random.RandomState(seed)
    # Generate normalized vector
    vec = rng.randn(dim).astype(np.float32)
    vec = vec / np.linalg.norm(vec)  # Normalize to unit length
    return vec.tobytes()


@pytest.fixture
def minimal_retrieval_fixture(tmp_project):
    """
    Create a minimal Kurt project with fake data for retrieval testing.

    This fixture sets up:
    - 5 documents about DuckDB/MotherDuck
    - 10 entities (technologies, features, companies)
    - Document-entity links
    - Entity relationships
    - Source files for the documents

    Returns:
        dict: Contains document_ids, entity_ids, and other metadata
    """
    session = get_session()

    # Ensure all tables exist
    SQLModel.metadata.create_all(session.bind)

    # Create source directory
    sources_dir = Path(".kurt/sources")
    sources_dir.mkdir(parents=True, exist_ok=True)

    # --- Documents ---
    docs_data = [
        {
            "id": uuid4(),
            "title": "DuckDB Introduction",
            "source_url": "https://duckdb.org/docs/intro",
            "content": """# DuckDB Introduction

DuckDB is an in-process SQL OLAP database management system.
It is designed to support analytical query workloads (OLAP).
DuckDB supports both SQL and Python APIs.

Key features:
- Fast analytical queries
- Embedded database (no server needed)
- Supports Parquet, CSV, JSON
- Compatible with pandas DataFrames
""",
            "content_type": ContentType.GUIDE,
        },
        {
            "id": uuid4(),
            "title": "MotherDuck Overview",
            "source_url": "https://motherduck.com/docs/overview",
            "content": """# MotherDuck Overview

MotherDuck is a serverless analytics platform built on DuckDB.
It extends DuckDB with cloud storage, sharing, and collaboration.

Features:
- Serverless DuckDB in the cloud
- Data sharing across teams
- Compatible with local DuckDB
- Supports S3, Parquet, CSV
""",
            "content_type": ContentType.PRODUCT_PAGE,
        },
        {
            "id": uuid4(),
            "title": "Parquet File Format Guide",
            "source_url": "https://example.com/parquet-guide",
            "content": """# Parquet File Format

Parquet is a columnar storage format optimized for analytical workloads.
It provides efficient compression and encoding schemes.

Benefits:
- Column-oriented storage
- Efficient compression
- Fast reads for analytics
- Works great with DuckDB and MotherDuck
""",
            "content_type": ContentType.GUIDE,
        },
        {
            "id": uuid4(),
            "title": "SQL Analytics Tutorial",
            "source_url": "https://example.com/sql-tutorial",
            "content": """# SQL Analytics Tutorial

Learn how to perform analytics with SQL.
Use DuckDB for fast local analytics.

Topics:
- GROUP BY queries
- Window functions
- JOIN operations
- Aggregations
""",
            "content_type": ContentType.TUTORIAL,
        },
        {
            "id": uuid4(),
            "title": "Cloud Data Warehouses Comparison",
            "source_url": "https://example.com/warehouses",
            "content": """# Cloud Data Warehouses

Comparing different cloud data warehouse solutions.
MotherDuck offers a serverless approach based on DuckDB.

Comparison:
- MotherDuck: Serverless, DuckDB-compatible
- Snowflake: Separate storage and compute
- BigQuery: Google Cloud native
""",
            "content_type": ContentType.BLOG,
        },
    ]

    documents = []
    for i, doc_data in enumerate(docs_data):
        # Create document with embedding
        doc = Document(
            id=doc_data["id"],
            title=doc_data["title"],
            source_url=doc_data["source_url"],
            source_type=SourceType.URL,
            ingestion_status=IngestionStatus.FETCHED,
            content_type=doc_data["content_type"],
            content_path=f"doc_{i}.md",
            embedding=create_embedding(seed=1000 + i),  # Deterministic embeddings
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(doc)
        documents.append(doc)

        # Write source file
        source_file = sources_dir / f"doc_{i}.md"
        source_file.write_text(doc_data["content"])

    session.commit()

    # --- Entities ---
    entities_data = [
        {"name": "DuckDB", "type": EntityType.TECHNOLOGY, "description": "In-process SQL OLAP database"},
        {"name": "MotherDuck", "type": EntityType.COMPANY, "description": "Serverless analytics platform"},
        {"name": "Parquet", "type": EntityType.TECHNOLOGY, "description": "Columnar storage format"},
        {"name": "SQL", "type": EntityType.TECHNOLOGY, "description": "Structured Query Language"},
        {"name": "OLAP", "type": EntityType.TOPIC, "description": "Online Analytical Processing"},
        {"name": "Serverless", "type": EntityType.FEATURE, "description": "Cloud computing model"},
        {"name": "Cloud Storage", "type": EntityType.FEATURE, "description": "Remote data storage"},
        {"name": "Analytics", "type": EntityType.TOPIC, "description": "Data analysis"},
        {"name": "Pandas", "type": EntityType.TECHNOLOGY, "description": "Python data analysis library"},
        {"name": "S3", "type": EntityType.TECHNOLOGY, "description": "Amazon Simple Storage Service"},
    ]

    entities = []
    for idx, ent_data in enumerate(entities_data):
        entity = Entity(
            id=uuid4(),
            name=ent_data["name"],
            canonical_name=ent_data["name"],
            entity_type=ent_data["type"].value,
            description=ent_data["description"],
            confidence_score=0.95,
            source_mentions=1,
            embedding=create_embedding(seed=2000 + idx),  # Deterministic embeddings
            created_at=datetime.utcnow(),
        )
        session.add(entity)
        entities.append(entity)

    session.commit()

    # --- Document-Entity Links ---
    # Doc 0 (DuckDB Intro): DuckDB, SQL, OLAP, Parquet, Pandas
    for entity in [entities[0], entities[3], entities[4], entities[2], entities[8]]:
        session.add(DocumentEntity(
            document_id=documents[0].id,
            entity_id=entity.id,
            mention_count=2,
            confidence=0.9,
            created_at=datetime.utcnow(),
        ))

    # Doc 1 (MotherDuck): MotherDuck, DuckDB, Serverless, Cloud Storage, S3, Parquet
    for entity in [entities[1], entities[0], entities[5], entities[6], entities[9], entities[2]]:
        session.add(DocumentEntity(
            document_id=documents[1].id,
            entity_id=entity.id,
            mention_count=2,
            confidence=0.9,
            created_at=datetime.utcnow(),
        ))

    # Doc 2 (Parquet): Parquet, DuckDB, MotherDuck, Analytics
    for entity in [entities[2], entities[0], entities[1], entities[7]]:
        session.add(DocumentEntity(
            document_id=documents[2].id,
            entity_id=entity.id,
            mention_count=2,
            confidence=0.9,
            created_at=datetime.utcnow(),
        ))

    # Doc 3 (SQL Tutorial): SQL, DuckDB, Analytics
    for entity in [entities[3], entities[0], entities[7]]:
        session.add(DocumentEntity(
            document_id=documents[3].id,
            entity_id=entity.id,
            mention_count=2,
            confidence=0.9,
            created_at=datetime.utcnow(),
        ))

    # Doc 4 (Cloud Warehouses): MotherDuck, DuckDB, Serverless
    for entity in [entities[1], entities[0], entities[5]]:
        session.add(DocumentEntity(
            document_id=documents[4].id,
            entity_id=entity.id,
            mention_count=2,
            confidence=0.9,
            created_at=datetime.utcnow(),
        ))

    session.commit()

    # --- Entity Relationships ---
    relationships_data = [
        # MotherDuck is built on DuckDB
        {"source": entities[1], "target": entities[0], "type": "BUILT_ON",
         "context": "MotherDuck is built on DuckDB"},
        # DuckDB supports Parquet
        {"source": entities[0], "target": entities[2], "type": "SUPPORTS",
         "context": "DuckDB supports Parquet format"},
        # MotherDuck supports S3
        {"source": entities[1], "target": entities[9], "type": "INTEGRATES_WITH",
         "context": "MotherDuck integrates with S3"},
        # DuckDB supports SQL
        {"source": entities[0], "target": entities[3], "type": "IMPLEMENTS",
         "context": "DuckDB implements SQL"},
        # DuckDB supports Pandas
        {"source": entities[0], "target": entities[8], "type": "INTEGRATES_WITH",
         "context": "DuckDB integrates with Pandas"},
    ]

    for rel_data in relationships_data:
        relationship = EntityRelationship(
            id=uuid4(),
            source_entity_id=rel_data["source"].id,
            target_entity_id=rel_data["target"].id,
            relationship_type=rel_data["type"],
            confidence=0.9,
            evidence_count=1,
            context=rel_data["context"],
            created_at=datetime.utcnow(),
        )
        session.add(relationship)

    session.commit()

    # Extract IDs before closing session
    document_ids = [str(doc.id) for doc in documents]
    entity_ids = [str(ent.id) for ent in entities]
    entity_names = [ent.name for ent in entities]

    session.close()

    # Return fixture data
    return {
        "document_ids": document_ids,
        "entity_ids": entity_ids,
        "entity_names": entity_names,
        "documents": documents,
        "entities": entities,
        "sources_dir": sources_dir,
    }
