"""Conftest for retrieval tests - fixtures for mocking LLM and embedding boundaries.

Test Strategy:
- Use tmp_project fixture for real database isolation
- Mock DSPy at the run_batch_sync boundary (LLM interface)
- Mock embeddings at generate_embeddings boundary
- Mock DBOS step decorator to avoid async wrapping issues
- Pre-populate database with test documents, entities, and claims
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from sqlalchemy import text

# Fixtures tmp_project and reset_dbos_state are auto-discovered from src/kurt/conftest.py
from kurt.core.dspy_helpers import DSPyResult
from kurt.db.database import get_session


@pytest.fixture
def add_test_documents(tmp_project):
    """Fixture to add test documents to the database.

    Usage:
        def test_something(tmp_project, add_test_documents):
            doc_ids = add_test_documents([
                {"title": "Test Doc", "content": "Test content", "source_url": "https://example.com"}
            ])
    """
    from kurt.config import load_config
    from kurt.db.database import get_session
    from kurt.db.documents import add_document
    from kurt.db.models import Document, IngestionStatus

    def _add_documents(documents: List[Dict[str, Any]]) -> List[str]:
        config = load_config()
        sources_path = config.get_absolute_sources_path()

        doc_ids = []
        for i, doc in enumerate(documents):
            url = doc.get("source_url", f"https://example.com/{uuid4()}")
            title = doc.get("title", "Test Document")

            doc_id = add_document(url=url, title=title)
            doc_ids.append(str(doc_id))

            # Create content file if content provided
            if "content" in doc:
                session = get_session()
                db_doc = session.get(Document, doc_id)
                if db_doc:
                    content_path = f"test_doc_{i}_{uuid4().hex[:8]}.md"
                    test_file = sources_path / content_path
                    test_file.parent.mkdir(parents=True, exist_ok=True)
                    test_file.write_text(doc["content"])

                    db_doc.content_path = content_path
                    db_doc.ingestion_status = IngestionStatus.FETCHED
                    if "description" in doc:
                        db_doc.description = doc["description"]

                    # Add embedding if provided
                    if "embedding" in doc:
                        db_doc.embedding = np.array(doc["embedding"], dtype=np.float32).tobytes()

                    session.commit()
                session.close()

        return doc_ids

    return _add_documents


@pytest.fixture
def add_test_entities(tmp_project):
    """Fixture to add test entities to the database.

    Usage:
        def test_something(tmp_project, add_test_entities):
            entity_ids = add_test_entities([
                {"name": "Segment", "entity_type": "Product", "description": "Customer data platform"}
            ])
    """
    from kurt.db.database import get_session
    from kurt.db.models import Entity, EntityType

    def _add_entities(entities: List[Dict[str, Any]]) -> List[str]:
        session = get_session()
        entity_ids = []

        for entity_data in entities:
            entity = Entity(
                name=entity_data.get("name", "Test Entity"),
                entity_type=entity_data.get("entity_type", EntityType.TOPIC),
                description=entity_data.get("description"),
                aliases=entity_data.get("aliases", []),
            )
            session.add(entity)
            session.commit()
            entity_ids.append(str(entity.id))

        session.close()
        return entity_ids

    return _add_entities


@pytest.fixture
def add_test_claims(tmp_project, add_test_documents, add_test_entities):
    """Fixture to add test claims to the database.

    Usage:
        def test_something(tmp_project, add_test_claims):
            claim_ids = add_test_claims([
                {
                    "statement": "Segment supports 300+ integrations",
                    "claim_type": "capability",
                    "source_quote": "Segment offers 300+ integrations",
                    "doc_index": 0,
                    "entity_index": 0,
                }
            ], doc_ids=["..."], entity_ids=["..."])
    """
    from uuid import UUID

    from kurt.db.claim_models import Claim, ClaimType
    from kurt.db.database import get_session

    def _add_claims(
        claims: List[Dict[str, Any]],
        doc_ids: List[str],
        entity_ids: List[str],
    ) -> List[str]:
        session = get_session()
        claim_ids = []

        for claim_data in claims:
            doc_idx = claim_data.get("doc_index", 0)
            entity_idx = claim_data.get("entity_index", 0)

            claim = Claim(
                statement=claim_data.get("statement", "Test claim"),
                claim_type=claim_data.get("claim_type", ClaimType.CAPABILITY),
                source_quote=claim_data.get("source_quote", "Test quote"),
                source_document_id=UUID(doc_ids[doc_idx]) if doc_ids else None,
                subject_entity_id=UUID(entity_ids[entity_idx]) if entity_ids else None,
                source_location_start=claim_data.get("source_location_start", 0),
                source_location_end=claim_data.get("source_location_end", 100),
                extraction_confidence=claim_data.get("extraction_confidence", 0.9),
                overall_confidence=claim_data.get("overall_confidence", 0.85),
            )
            session.add(claim)
            session.commit()
            claim_ids.append(str(claim.id))

        session.close()
        return claim_ids

    return _add_claims


@pytest.fixture
def add_test_sections(tmp_project, add_test_documents):
    """Fixture to add test sections to staging_document_sections.

    Usage:
        def test_something(tmp_project, add_test_sections):
            add_test_sections(doc_ids, [
                {"heading": "Introduction", "content": "This is the intro..."}
            ])
    """
    from sqlalchemy import text

    from kurt.db.database import get_session

    def _add_sections(doc_ids: List[str], sections: List[Dict[str, Any]]) -> List[str]:
        session = get_session()
        section_ids = []

        # Create staging table if it doesn't exist
        session.execute(
            text("""
                CREATE TABLE IF NOT EXISTS staging_document_sections (
                    document_id TEXT NOT NULL,
                    section_id TEXT NOT NULL,
                    section_number INTEGER NOT NULL,
                    heading TEXT,
                    content TEXT,
                    start_offset INTEGER DEFAULT 0,
                    end_offset INTEGER DEFAULT 0,
                    workflow_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (document_id, section_id)
                )
            """)
        )
        session.commit()

        for i, section_data in enumerate(sections):
            doc_id = doc_ids[i % len(doc_ids)] if doc_ids else str(uuid4())
            section_id = uuid4().hex[:8]

            # Insert directly into staging table
            session.execute(
                text("""
                    INSERT INTO staging_document_sections
                    (document_id, section_id, section_number, heading, content, start_offset, end_offset, workflow_id)
                    VALUES (:doc_id, :section_id, :section_num, :heading, :content, 0, :end_offset, 'test')
                """),
                {
                    "doc_id": doc_id,
                    "section_id": section_id,
                    "section_num": i + 1,
                    "heading": section_data.get("heading", f"Section {i+1}"),
                    "content": section_data.get("content", "Test section content"),
                    "end_offset": len(section_data.get("content", "")),
                },
            )
            section_ids.append(section_id)

        session.commit()
        session.close()
        return section_ids

    return _add_sections


def query_analysis_response_factory(items: List[Dict[str, Any]]) -> List[DSPyResult]:
    """Factory for query analysis mock responses."""
    results = []
    for item in items:
        query = item.get("query", "")

        # Extract entities from query (simple keyword matching)
        entities = []
        keywords = []

        if "segment" in query.lower():
            entities.append("Segment")
        if "integration" in query.lower():
            keywords.append("integration")
        if "customer" in query.lower():
            keywords.append("customer data")

        # Determine intent
        intent = "factual"
        if "how" in query.lower():
            intent = "how-to"
        elif "what is" in query.lower() or "overview" in query.lower():
            intent = "overview"
        elif "compare" in query.lower() or "vs" in query.lower():
            intent = "comparison"

        mock_result = MagicMock()
        mock_result.intent = intent
        mock_result.entities = entities or ["default_entity"]
        mock_result.keywords = keywords or ["default_keyword"]

        results.append(
            DSPyResult(
                payload=item,
                result=mock_result,
                error=None,
                telemetry={"tokens_prompt": 50, "tokens_completion": 20},
            )
        )

    return results


@pytest.fixture
def mock_retrieval_llm():
    """Mock the LLM boundary for retrieval tests.

    Mocks DSPy query analysis, embeddings, and DBOS step decorator.
    Also patches embeddings at specific step module locations.
    """
    import asyncio
    import random

    def mock_generate(texts):
        """Generate deterministic embeddings based on text hash."""
        results = []
        for txt in texts:
            rng = random.Random(hash(txt.lower().strip()))
            results.append([rng.random() for _ in range(1536)])
        return results

    def make_dbos_step_decorator(**step_kwargs):
        """Return a decorator that mimics DBOS.step() behavior.

        If the decorated function is already async, return it unchanged.
        If it's sync, wrap it in an async wrapper.
        """

        def decorator(fn):
            if asyncio.iscoroutinefunction(fn):
                # Already async, return as-is
                return fn
            else:
                # Sync function, wrap it to be awaitable
                async def async_wrapper(*args, **kwargs):
                    return fn(*args, **kwargs)

                return async_wrapper

        return decorator

    # Create mock_run_batch_sync to patch directly at step module level
    def mock_run_batch_sync(
        *,
        signature,
        items,
        max_concurrent=1,
        context=None,
        timeout=None,
        on_progress=None,
        llm_model=None,
    ):
        """Mock implementation of run_batch_sync."""
        results = query_analysis_response_factory(items)
        if on_progress:
            for i, result in enumerate(results, 1):
                try:
                    on_progress(i, len(items), result)
                except Exception:
                    pass
        return results

    with patch("kurt.core.model_runner.DBOS") as mock_dbos:
        # Make DBOS.step return a decorator that handles both sync and async
        mock_dbos.step = make_dbos_step_decorator

        # Patch embeddings at step module locations
        with (
            patch("kurt.utils.embeddings.generate_embeddings", side_effect=mock_generate),
            patch(
                "kurt.models.staging.retrieval.step_cag.generate_embeddings",
                side_effect=mock_generate,
            ),
            patch(
                "kurt.models.staging.retrieval.step_rag.generate_embeddings",
                side_effect=mock_generate,
            ),
            patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync),
        ):
            yield


@pytest.fixture
def sample_retrieval_data(
    tmp_project, add_test_documents, add_test_entities, add_test_claims, add_test_sections
):
    """Create a complete sample dataset for retrieval testing.

    Returns dict with doc_ids, entity_ids, claim_ids, section_ids.
    """
    # Add documents
    docs = [
        {
            "title": "Segment Overview",
            "content": "# Segment\n\nSegment is a customer data platform that offers 300+ integrations.",
            "description": "Customer data platform with integrations",
            "source_url": "https://segment.com/docs/overview",
            "embedding": [0.1] * 1536,
        },
        {
            "title": "Segment API Reference",
            "content": "# API Reference\n\nThe Segment API allows programmatic access to customer data.",
            "description": "API documentation for Segment",
            "source_url": "https://segment.com/docs/api",
            "embedding": [0.2] * 1536,
        },
    ]
    doc_ids = add_test_documents(docs)

    # Add entities
    entities = [
        {"name": "Segment", "entity_type": "Product", "description": "Customer data platform"},
        {"name": "Customer Data", "entity_type": "Topic", "description": "Data about customers"},
    ]
    entity_ids = add_test_entities(entities)

    # Add sections
    sections = [
        {"heading": "Overview", "content": "Segment is a customer data platform."},
        {"heading": "Integrations", "content": "Segment offers 300+ integrations with tools."},
    ]
    section_ids = add_test_sections(doc_ids, sections)

    # Add claims
    claims = [
        {
            "statement": "Segment offers 300+ integrations",
            "claim_type": "capability",
            "source_quote": "Segment offers 300+ integrations with tools",
            "doc_index": 0,
            "entity_index": 0,
        },
    ]
    claim_ids = add_test_claims(claims, doc_ids, entity_ids)

    return {
        "doc_ids": doc_ids,
        "entity_ids": entity_ids,
        "claim_ids": claim_ids,
        "section_ids": section_ids,
    }


# ============================================================================
# Fixtures for retrieval integration tests
# ============================================================================


@pytest.fixture
def motherduck_project(tmp_project):
    """
    Load the MotherDuck mock project into a temporary Kurt project.

    This fixture:
    - Uses tmp_project to create isolated test environment
    - Loads documents, entities, and relationships from motherduck dump
    - Returns the project directory path

    Usage:
        def test_retrieval(motherduck_project):
            # Database is populated with motherduck data
            result = await retrieve("DuckDB embeddings")
    """
    # Path to mock project dump (relative to project root)
    # Go up from src/kurt/models/staging/retrieval/tests/ to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent.parent.parent
    dump_dir = project_root / "eval" / "mock" / "projects" / "motherduck" / "database"

    if not dump_dir.exists():
        pytest.skip(f"MotherDuck dump not found at {dump_dir}")

    # Tables to load in dependency order
    tables = [
        "documents",
        "entities",
        "document_entities",
        "entity_relationships",
    ]

    session = get_session()

    try:
        for table_name in tables:
            input_file = dump_dir / f"{table_name}.jsonl"

            if not input_file.exists():
                continue

            # Get valid columns for this table
            pragma_query = text(f"PRAGMA table_info({table_name})")
            table_columns_info = session.execute(pragma_query).fetchall()
            valid_columns = {col[1] for col in table_columns_info}

            # Read and insert records
            count = 0
            with open(input_file, "r") as f:
                for line in f:
                    record = json.loads(line)

                    # Filter to valid columns only
                    filtered_record = {k: v for k, v in record.items() if k in valid_columns}

                    if not filtered_record:
                        continue

                    # Build INSERT statement
                    columns = list(filtered_record.keys())
                    placeholders = [f":{col}" for col in columns]

                    insert_sql = text(
                        f"INSERT OR REPLACE INTO {table_name} "
                        f"({', '.join(columns)}) "
                        f"VALUES ({', '.join(placeholders)})"
                    )

                    session.execute(insert_sql, filtered_record)
                    count += 1

            session.commit()

        yield tmp_project

    finally:
        session.close()
