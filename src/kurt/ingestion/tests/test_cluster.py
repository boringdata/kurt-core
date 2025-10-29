"""
Tests for topic clustering functionality.

═══════════════════════════════════════════════════════════════════════════════
TEST COVERAGE (3 tests)
═══════════════════════════════════════════════════════════════════════════════

TestComputeTopicClusters (3 tests)
────────────────────────────────────────────────────────────────────────────────
  ✓ test_compute_clusters_success
      → Verifies clustering creates TopicCluster and DocumentClusterEdge records

  ✓ test_compute_clusters_url_normalization
      → Verifies URL normalization handles trailing slashes and case differences

  ✓ test_compute_clusters_no_documents
      → Verifies error when no documents match filter criteria

═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from kurt.ingestion.cluster import TopicClusterOutput, compute_topic_clusters


class MockDSpyResult:
    """Mock DSPy result object."""

    def __init__(self, clusters):
        self.clusters = clusters


@pytest.fixture
def mock_documents():
    """Create mock documents for testing."""
    from kurt.db.models import Document, SourceType

    return [
        Document(
            id=uuid4(),
            title="Machine Learning Basics",
            source_url="https://example.com/blog/ml-basics",
            description="Introduction to ML",
            source_type=SourceType.URL,
        ),
        Document(
            id=uuid4(),
            title="Deep Learning Tutorial",
            source_url="https://example.com/blog/deep-learning/",  # Trailing slash
            description="Learn deep learning",
            source_type=SourceType.URL,
        ),
        Document(
            id=uuid4(),
            title="Data Engineering Guide",
            source_url="https://Example.com/blog/data-eng",  # Different case
            description="Guide to data pipelines",
            source_type=SourceType.URL,
        ),
    ]


@pytest.fixture
def mock_clusters():
    """Create mock clustering results."""
    return [
        TopicClusterOutput(
            name="Machine Learning",
            description="Articles about ML and deep learning",
            example_urls=[
                "https://example.com/blog/ml-basics",
                "https://example.com/blog/deep-learning",  # No trailing slash
            ],
        ),
        TopicClusterOutput(
            name="Data Engineering",
            description="Content about data pipelines",
            example_urls=["https://example.com/blog/data-eng"],
        ),
    ]


@patch("kurt.db.database.get_session")
@patch("kurt.document.list_documents")
@patch("dspy.ChainOfThought")
@patch("dspy.configure")
@patch("dspy.LM")
@patch("kurt.config.get_config_or_default")
def test_compute_clusters_success(
    mock_config,
    mock_lm,
    mock_configure,
    mock_cot,
    mock_list_docs,
    mock_session,
    mock_documents,
    mock_clusters,
):
    """Test successful cluster computation."""
    # Setup mocks
    mock_config.return_value.INDEXING_LLM_MODEL = "openai/gpt-4o-mini"
    mock_list_docs.return_value = mock_documents

    # Mock DSPy clustering
    mock_clusterer = MagicMock()
    mock_clusterer.return_value = MockDSpyResult(clusters=mock_clusters)
    mock_cot.return_value = mock_clusterer

    # Mock database session
    mock_db_session = MagicMock()
    mock_session.return_value = mock_db_session

    # Run clustering
    result = compute_topic_clusters(url_prefix="https://example.com/blog/")

    # Verify results
    assert result["total_pages"] == 3
    assert len(result["clusters"]) == 2
    assert result["clusters"][0]["name"] == "Machine Learning"
    assert result["clusters"][1]["name"] == "Data Engineering"
    assert result["edges_created"] == 3  # All 3 example URLs matched

    # Verify database operations
    assert mock_db_session.add.call_count >= 2  # At least 2 clusters added
    mock_db_session.commit.assert_called_once()


@patch("kurt.db.database.get_session")
@patch("kurt.document.list_documents")
@patch("dspy.ChainOfThought")
@patch("dspy.configure")
@patch("dspy.LM")
@patch("kurt.config.get_config_or_default")
def test_compute_clusters_url_normalization(
    mock_config,
    mock_lm,
    mock_configure,
    mock_cot,
    mock_list_docs,
    mock_session,
    mock_documents,
    mock_clusters,
):
    """Test URL normalization handles case and trailing slashes."""
    # Setup mocks
    mock_config.return_value.INDEXING_LLM_MODEL = "openai/gpt-4o-mini"
    mock_list_docs.return_value = mock_documents

    # Mock DSPy clustering with URLs that need normalization
    normalized_clusters = [
        TopicClusterOutput(
            name="Test Cluster",
            description="Test normalization",
            example_urls=[
                "https://EXAMPLE.com/blog/ml-basics/",  # Different case + trailing slash
                "https://example.com/blog/deep-learning/",  # Trailing slash matches
                "https://example.com/BLOG/data-eng",  # Different case
            ],
        ),
    ]

    mock_clusterer = MagicMock()
    mock_clusterer.return_value = MockDSpyResult(clusters=normalized_clusters)
    mock_cot.return_value = mock_clusterer

    # Mock database session
    mock_db_session = MagicMock()
    mock_session.return_value = mock_db_session

    # Run clustering
    result = compute_topic_clusters(url_prefix="https://example.com/blog/")

    # Verify all URLs matched despite normalization needs
    assert result["edges_created"] == 3


@patch("kurt.document.list_documents")
def test_compute_clusters_no_documents(mock_list_docs):
    """Test error when no documents found."""
    # Setup mock to return empty list
    mock_list_docs.return_value = []

    # Verify error raised
    with pytest.raises(ValueError, match="No documents found matching criteria"):
        compute_topic_clusters(url_prefix="https://nonexistent.com/")
