"""Conftest for indexing tests - fixtures for mocking LLM boundaries.

Test Strategy:
- Use tmp_project fixture for real database isolation
- Mock DSPy at the run_batch_sync boundary (LLM interface)
- Mock embeddings at generate_embeddings boundary
- Let the framework and model logic run with real code paths

The helpers in kurt.core.testing provide:
- mock_run_batch(): Mock DSPy batch execution
- mock_embeddings(): Mock embedding generation
- create_extraction_response_factory(): Generate predictable extraction responses
"""

import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Re-export the core testing utilities for convenience
from kurt.core.dspy_helpers import DSPyResult
from kurt.core.testing import (
    create_extraction_response_factory,
    mock_embeddings,
    mock_run_batch,
)

# Import fixtures from main test suite (re-export for this package's tests)
from tests.conftest import (
    reset_dbos_state,  # noqa: F401
    tmp_project,  # noqa: F401, F811
)


@pytest.fixture
def add_test_documents(tmp_project):  # noqa: F811
    """Fixture to add test documents to the database.

    Usage:
        def test_something(tmp_project, add_test_documents):
            doc_ids = add_test_documents([
                {"title": "Test Doc", "content": "Test content", "source_url": "https://example.com"}
            ])
            # doc_ids is a list of created document IDs
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

            # If content is provided, create the content file
            if "content" in doc:
                session = get_session()
                db_doc = session.get(Document, doc_id)
                if db_doc:
                    # Create content file
                    content_path = f"test_doc_{i}_{uuid4().hex[:8]}.md"
                    test_file = sources_path / content_path
                    test_file.parent.mkdir(parents=True, exist_ok=True)
                    test_file.write_text(doc["content"])

                    # Update document
                    db_doc.content_path = content_path
                    db_doc.ingestion_status = IngestionStatus.FETCHED
                    if "description" in doc:
                        db_doc.description = doc["description"]
                    session.commit()
                session.close()

        return doc_ids

    return _add_documents


# Directory containing test fixtures
_FIXTURES_DIR = Path(__file__).parent


def _load_json_fixture(filename: str) -> dict:
    """Load a JSON fixture file from the tests directory.

    Args:
        filename: Name of the JSON file (with extension)

    Returns:
        Parsed JSON content as dict

    Raises:
        FileNotFoundError: If fixture file doesn't exist
    """
    # Try root tests directory first (larger file), then fixtures subdirectory
    fixtures_path = _FIXTURES_DIR / filename
    if not fixtures_path.exists():
        fixtures_path = _FIXTURES_DIR / "fixtures" / filename

    if not fixtures_path.exists():
        # Return empty embeddings dict as fallback
        return {"embeddings": {}}

    with open(fixtures_path) as f:
        return json.load(f)


def make_embedding_mock(embeddings: dict):
    """Create a mock for embedding generation that returns pre-computed embeddings.

    DEPRECATED: Use mock_embeddings() context manager from kurt.core.testing instead.

    Args:
        embeddings: Dict mapping text -> embedding vector

    Returns:
        Mock function that returns embeddings for given texts
    """
    import random

    def mock_generate_embeddings(texts):
        """Return pre-computed embeddings for texts, or unique random ones for unknown texts.

        Uses lowercase normalization to simulate real embedding behavior where
        case differences produce identical embeddings.
        """
        results = []
        for text in texts:
            if text in embeddings:
                results.append(embeddings[text])
            else:
                # Normalize to lowercase to match real embedding behavior
                # (real embeddings are case-insensitive)
                normalized = text.lower().strip()
                # Generate deterministic but distinct embedding based on normalized text hash
                # Use the hash as seed for random to get reproducible but varied embeddings
                rng = random.Random(hash(normalized))
                results.append([rng.random() for _ in range(1536)])
        return results

    return mock_generate_embeddings


def content_aware_response_factory(items: List[Dict[str, Any]]) -> List[DSPyResult]:
    """
    Create extraction responses based on document content.

    This factory analyzes the document content and generates appropriate
    entities and claims, simulating what the LLM would extract.
    """
    results = []
    for item in items:
        content = item.get("document_content", "")

        entities = []
        claims = []

        # Extract entities based on content keywords
        if "PostgreSQL" in content or "postgresql" in content.lower():
            entities.append(
                {
                    "name": "PostgreSQL",
                    "entity_type": "Technology",
                    "description": "A powerful open-source relational database",
                    "aliases": ["Postgres", "PG"],
                    "confidence": 0.95,
                    "resolution_status": "NEW",
                    "quote": "PostgreSQL is a powerful database",
                }
            )
            claims.append(
                {
                    "statement": "PostgreSQL is a powerful database",
                    "claim_type": "capability",
                    "entity_indices": [len(entities) - 1],
                    "source_quote": "PostgreSQL is a powerful database that supports JSON",
                    "quote_start_offset": 0,
                    "quote_end_offset": 50,
                    "confidence": 0.9,
                }
            )

        if "Python" in content:
            entities.append(
                {
                    "name": "Python",
                    "entity_type": "Technology",
                    "description": "A high-level programming language",
                    "aliases": [],
                    "confidence": 0.9,
                    "resolution_status": "NEW",
                    "quote": "Python integrates well",
                }
            )

        if "Docker" in content:
            entities.append(
                {
                    "name": "Docker",
                    "entity_type": "Technology",
                    "description": "Container platform for deployment",
                    "aliases": [],
                    "confidence": 0.85,
                    "resolution_status": "NEW",
                    "quote": "Docker is useful for deploying",
                }
            )

        if "DuckDB" in content or "duckdb" in content.lower():
            entities.append(
                {
                    "name": "DuckDB",
                    "entity_type": "Technology",
                    "description": "An in-process SQL OLAP database",
                    "aliases": [],
                    "confidence": 0.9,
                    "resolution_status": "NEW",
                    "quote": "DuckDB is an in-process database",
                }
            )

        if "MotherDuck" in content:
            entities.append(
                {
                    "name": "MotherDuck",
                    "entity_type": "Product",
                    "description": "Cloud service for DuckDB",
                    "aliases": [],
                    "confidence": 0.85,
                    "resolution_status": "NEW",
                    "quote": "MotherDuck extends DuckDB",
                }
            )

        # Check for document number patterns (for batch tests)
        for i in range(10):
            if f"Document {i}" in content or f"technology {i}" in content:
                entities.append(
                    {
                        "name": f"Technology{i}",
                        "entity_type": "Technology",
                        "description": f"Technology number {i}",
                        "aliases": [],
                        "confidence": 0.8,
                        "resolution_status": "NEW",
                        "quote": f"Document {i} about technology {i}",
                    }
                )
                claims.append(
                    {
                        "statement": f"Technology {i} is useful",
                        "claim_type": "capability",
                        "entity_indices": [len(entities) - 1],
                        "source_quote": f"technology {i}",
                        "quote_start_offset": 0,
                        "quote_end_offset": 20,
                        "confidence": 0.8,
                    }
                )
                break

        # Default entity if nothing matches
        if not entities:
            entities.append(
                {
                    "name": "Unknown",
                    "entity_type": "Topic",
                    "description": "Unknown topic",
                    "aliases": [],
                    "confidence": 0.5,
                    "resolution_status": "NEW",
                    "quote": content[:100] if content else "No content",
                }
            )

        # Create mock result
        mock_result = MagicMock()
        mock_result.metadata = {
            "content_type": "reference",
            "has_code_examples": False,
            "has_step_by_step_procedures": False,
            "has_narrative_structure": False,
        }
        mock_result.entities = entities
        mock_result.relationships = []
        mock_result.claims = claims

        results.append(
            DSPyResult(
                payload=item,
                result=mock_result,
                error=None,
                telemetry={"tokens_prompt": 100, "tokens_completion": 50},
            )
        )

    return results


@pytest.fixture
def mock_llm_boundary():
    """
    Mock the LLM boundary (DSPy + embeddings) for indexing tests.

    This fixture mocks only the expensive nondeterministic LLM calls,
    allowing the framework and model logic to exercise their real code paths.

    Usage:
        def test_something(tmp_project, mock_llm_boundary):
            # DSPy and embeddings are mocked, framework runs real code
            result = run_pipeline(...)
    """
    with mock_run_batch(content_aware_response_factory), mock_embeddings():
        yield


@pytest.fixture
def mock_llm_with_factory():
    """
    Mock the LLM boundary with a simple predictable factory.

    Use this when you want consistent, predictable entities/claims
    rather than content-aware extraction.

    Usage:
        def test_something(tmp_project, mock_llm_with_factory):
            # Each section gets 2 entities, 1 claim with predictable names
            result = run_pipeline(...)
    """
    factory = create_extraction_response_factory(
        entities_per_section=2,
        claims_per_section=1,
        entity_prefix="TestEntity",
    )
    with mock_run_batch(factory), mock_embeddings():
        yield
