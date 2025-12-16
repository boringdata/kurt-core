"""
Shared fixtures for indexing models tests.

This module provides:
- Precomputed embeddings for deterministic clustering tests
- LLM resolution patterns for mocking DSPy calls
- Extraction samples for integration tests
- Common mocks and fixtures
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.framework import PipelineContext, TableWriter

# Import fixtures from main test suite
from tests.conftest import reset_dbos_state, tmp_project  # noqa: F401

# ============================================================================
# Data Loading
# ============================================================================

DATA_DIR = Path(__file__).parent.parent.parent / "framework" / "tests" / "data"


def _load_json_fixture(filename: str) -> dict:
    """Load a JSON fixture file from the data directory."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Fixture file not found: {filepath}")
    with open(filepath) as f:
        return json.load(f)


# ============================================================================
# Embedding Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def claim_embeddings() -> dict:
    """Load precomputed claim embeddings for clustering tests."""
    return _load_json_fixture("test_embeddings.json")["embeddings"]


@pytest.fixture(scope="module")
def entity_embeddings() -> dict:
    """Load precomputed entity embeddings for similarity tests."""
    return _load_json_fixture("test_entity_similarities.json")["embeddings"]


@pytest.fixture(scope="module")
def all_embeddings() -> dict:
    """Unified embeddings from both claim and entity fixtures."""
    claim_data = _load_json_fixture("test_embeddings.json")["embeddings"]
    entity_data = _load_json_fixture("test_entity_similarities.json")["embeddings"]
    # Merge with entity embeddings taking precedence for conflicts
    return {**claim_data, **entity_data}


# ============================================================================
# Mock Embedding Generators
# ============================================================================


def make_embedding_mock(embeddings: dict, default_dim: int = 8):
    """Create a mock function for generate_embeddings using precomputed data.

    Args:
        embeddings: Dict mapping text -> embedding vector
        default_dim: Dimension for default embedding (for unknown texts)

    Returns:
        Mock function that takes list of texts and returns list of embeddings
    """
    # Create a default embedding (uniform distribution)
    default_embedding = [1.0 / default_dim] * default_dim

    def mock_generate_embeddings(texts):
        result = []
        for text in texts:
            normalized = text.lower().strip()
            if normalized in embeddings:
                result.append(embeddings[normalized])
            else:
                result.append(default_embedding)
        return result

    return mock_generate_embeddings


@pytest.fixture
def mock_claim_embeddings(claim_embeddings):
    """Provide a mock function for claim embedding generation."""
    return make_embedding_mock(claim_embeddings)


@pytest.fixture
def mock_entity_embeddings(entity_embeddings):
    """Provide a mock function for entity embedding generation."""
    return make_embedding_mock(entity_embeddings)


# ============================================================================
# LLM Resolution Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def llm_resolution_patterns() -> dict:
    """Load precomputed LLM resolution patterns."""
    return _load_json_fixture("test_llm_resolutions.json")["resolution_patterns"]


# ============================================================================
# Extraction Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def extraction_samples() -> dict:
    """Load sample extraction results for testing."""
    return _load_json_fixture("test_extraction_results.json")["extraction_samples"]


@pytest.fixture(scope="module")
def existing_entities_context() -> dict:
    """Load existing entities context for testing resolution."""
    return _load_json_fixture("test_extraction_results.json")["existing_entities_context"]


# ============================================================================
# Common Mocks
# ============================================================================


@pytest.fixture
def mock_writer():
    """Create a mock TableWriter."""
    writer = MagicMock(spec=TableWriter)
    writer.write.return_value = {"rows_written": 0, "table_name": "mock_table"}
    return writer


@pytest.fixture
def mock_ctx():
    """Create a mock PipelineContext."""
    return PipelineContext(
        filters=DocumentFilters(),
        workflow_id="test-workflow",
        incremental_mode="full",
    )


@pytest.fixture
def mock_ctx_with_filters():
    """Create a mock PipelineContext with document filters."""

    def _create_ctx(document_ids=None, project_id=None, workflow_id="test-workflow"):
        filters = DocumentFilters(
            document_ids=document_ids,
            project_id=project_id,
        )
        return PipelineContext(
            filters=filters,
            workflow_id=workflow_id,
            incremental_mode="incremental" if document_ids else "full",
        )

    return _create_ctx
