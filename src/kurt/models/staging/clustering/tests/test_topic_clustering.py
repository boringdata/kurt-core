"""Tests for topic clustering step.

Tests the step_topic_clustering module which:
1. Discovers/refines topic clusters from documents
2. Classifies document content types
3. Assigns documents to clusters
"""

import json
from unittest.mock import MagicMock, patch

import pandas as pd

from kurt.models.staging.clustering.step_topic_clustering import (
    ClassifyAndAssignDocument,
    DiscoverTopicClusters,
    TopicClusteringConfig,
    TopicClusteringRow,
    _discover_clusters,
    _fetch_existing_clusters,
    _normalize_cluster_name,
    _normalize_content_type,
)


class TestNormalizeContentType:
    """Test content type normalization."""

    def test_valid_content_types(self):
        """Test that valid content types pass through."""
        assert _normalize_content_type("tutorial") == "tutorial"
        assert _normalize_content_type("guide") == "guide"
        assert _normalize_content_type("blog") == "blog"
        assert _normalize_content_type("reference") == "reference"

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert _normalize_content_type("TUTORIAL") == "tutorial"
        assert _normalize_content_type("Guide") == "guide"
        assert _normalize_content_type("BLOG") == "blog"

    def test_type_mapping(self):
        """Test that common variations are mapped correctly."""
        assert _normalize_content_type("example") == "tutorial"
        assert _normalize_content_type("examples") == "tutorial"
        assert _normalize_content_type("documentation") == "reference"
        assert _normalize_content_type("doc") == "reference"
        assert _normalize_content_type("docs") == "reference"
        assert _normalize_content_type("article") == "blog"
        assert _normalize_content_type("post") == "blog"

    def test_invalid_defaults_to_other(self):
        """Test that invalid types default to 'other'."""
        assert _normalize_content_type("invalid_type") == "other"
        assert _normalize_content_type("random") == "other"

    def test_empty_or_none(self):
        """Test empty or None values."""
        assert _normalize_content_type("") == "other"
        assert _normalize_content_type(None) == "other"


class TestNormalizeClusterName:
    """Test cluster name normalization."""

    def test_valid_cluster_names(self):
        """Test that valid names pass through."""
        assert _normalize_cluster_name("Tutorials") == "Tutorials"
        assert _normalize_cluster_name("Documentation") == "Documentation"

    def test_null_variations(self):
        """Test that null variations return None."""
        assert _normalize_cluster_name("null") is None
        assert _normalize_cluster_name("NULL") is None
        assert _normalize_cluster_name("none") is None
        assert _normalize_cluster_name("None") is None
        assert _normalize_cluster_name("") is None

    def test_none_value(self):
        """Test None value."""
        assert _normalize_cluster_name(None) is None


class TestTopicClusteringConfig:
    """Test configuration loading."""

    def test_default_values(self):
        """Test default configuration values."""
        # Instantiate config to get defaults
        config = TopicClusteringConfig()

        assert config.batch_size == 200
        assert config.max_concurrent == 1
        assert config.force_fresh is False


class TestTopicClusteringRow:
    """Test output row model."""

    def test_row_creation(self):
        """Test creating output rows."""
        row = TopicClusteringRow(
            document_id="doc-123",
            workflow_id="wf-456",
            source_url="https://example.com/page",
            title="Test Page",
            cluster_name="Tutorials",
            cluster_description="Step-by-step guides",
            content_type="tutorial",
            reasoning="This is a tutorial because...",
        )

        assert row.document_id == "doc-123"
        assert row.workflow_id == "wf-456"
        assert row.cluster_name == "Tutorials"
        assert row.content_type == "tutorial"

    def test_row_with_nulls(self):
        """Test row with optional fields as None."""
        row = TopicClusteringRow(
            document_id="doc-123",
            workflow_id="wf-456",
        )

        assert row.document_id == "doc-123"
        assert row.cluster_name is None
        assert row.content_type is None


class TestFetchExistingClusters:
    """Test fetching existing clusters."""

    def test_empty_when_no_clusters(self):
        """Test returns empty list when no clusters exist."""
        from uuid import uuid4

        doc_id_1, doc_id_2 = str(uuid4()), str(uuid4())
        docs_df = pd.DataFrame({"id": [doc_id_1, doc_id_2]})

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query

        result = _fetch_existing_clusters(docs_df, mock_session)
        assert result == []

    def test_returns_cluster_data(self):
        """Test returns cluster data when clusters exist."""
        from uuid import uuid4

        doc_id_1, doc_id_2 = str(uuid4()), str(uuid4())
        docs_df = pd.DataFrame({"id": [doc_id_1, doc_id_2]})

        mock_cluster_1 = MagicMock()
        mock_cluster_1.name = "Tutorials"
        mock_cluster_1.description = "Step-by-step guides"

        mock_cluster_2 = MagicMock()
        mock_cluster_2.name = "Documentation"
        mock_cluster_2.description = "API reference docs"

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = [mock_cluster_1, mock_cluster_2]
        mock_session.query.return_value = mock_query

        result = _fetch_existing_clusters(docs_df, mock_session)

        assert len(result) == 2
        assert result[0]["name"] == "Tutorials"
        assert result[0]["description"] == "Step-by-step guides"
        assert result[1]["name"] == "Documentation"


class TestDiscoverClusters:
    """Test cluster discovery."""

    def test_discover_clusters_single_batch(self):
        """Test cluster discovery with single batch."""
        docs_df = pd.DataFrame(
            {
                "source_url": ["https://example.com/tutorial", "https://example.com/guide"],
                "title": ["Tutorial 1", "Guide 1"],
                "description": ["Learn how to...", "Best practices for..."],
            }
        )

        mock_result = MagicMock()
        mock_result.clusters_json = json.dumps(
            [
                {"name": "Tutorials", "description": "Step-by-step guides"},
                {"name": "Guides", "description": "Best practices"},
            ]
        )

        mock_chain_instance = MagicMock(return_value=mock_result)

        with (
            patch(
                "kurt.models.staging.clustering.step_topic_clustering.dspy.ChainOfThought",
                return_value=mock_chain_instance,
            ),
            patch("kurt.core.dspy_helpers.configure_dspy_model") as mock_configure,
        ):
            # Create config with explicit values (bypass ConfigParam)
            config = MagicMock()
            config.batch_size = 200
            config.llm_model = "claude-3-5-haiku-latest"

            clusters = _discover_clusters(docs_df, existing_clusters=[], config=config)

            assert len(clusters) == 2
            assert clusters[0]["name"] == "Tutorials"
            assert clusters[1]["name"] == "Guides"
            mock_configure.assert_called_once()

    def test_discover_clusters_json_error(self):
        """Test graceful handling of JSON parse error."""
        docs_df = pd.DataFrame(
            {
                "source_url": ["https://example.com/page"],
                "title": ["Page"],
                "description": ["Description"],
            }
        )

        existing = [{"name": "Existing", "description": "Keep this"}]

        mock_result = MagicMock()
        mock_result.clusters_json = "invalid json {{"
        mock_chain_instance = MagicMock(return_value=mock_result)

        with (
            patch(
                "kurt.models.staging.clustering.step_topic_clustering.dspy.ChainOfThought",
                return_value=mock_chain_instance,
            ),
            patch("kurt.core.dspy_helpers.configure_dspy_model"),
        ):
            config = MagicMock()
            config.batch_size = 200
            config.llm_model = "claude-3-5-haiku-latest"

            clusters = _discover_clusters(docs_df, existing_clusters=existing, config=config)

            # Should keep existing clusters on JSON error
            assert clusters == existing


class TestDSPySignatures:
    """Test DSPy signature definitions."""

    def test_classify_signature_fields(self):
        """Test ClassifyAndAssignDocument has required fields."""
        # Check model_fields for DSPy signatures
        fields = ClassifyAndAssignDocument.model_fields

        # Input fields
        assert "url" in fields
        assert "title" in fields
        assert "description" in fields
        assert "available_clusters" in fields

        # Output fields
        assert "content_type" in fields
        assert "cluster_name" in fields
        assert "reasoning" in fields

    def test_discover_signature_fields(self):
        """Test DiscoverTopicClusters has required fields."""
        fields = DiscoverTopicClusters.model_fields

        # Input fields
        assert "documents_json" in fields
        assert "existing_clusters_json" in fields

        # Output fields
        assert "clusters_json" in fields
