"""
Unit tests for discovery pipeline model.

Tests the ingestion.discovery model with mocked discovery functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.ingestion.step_discovery import (
    DiscoveryConfig,
    DiscoveryRow,
    discovery,
)
from kurt.core import PipelineContext


class TestDiscoveryModel:
    """Tests for discovery model function."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock()
        writer.write.return_value = {"rows_written": 0, "table_name": "ingestion_discovery"}
        return writer

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @pytest.fixture
    def mock_config_url(self):
        """Create config for URL discovery."""
        config = MagicMock(spec=DiscoveryConfig)
        config.source_url = "https://example.com"
        config.source_folder = None
        config.cms_platform = None
        config.cms_instance = None
        config.discovery_method = "auto"
        config.max_depth = None
        config.max_pages = 1000
        config.allow_external = False
        config.include_patterns = None
        config.exclude_patterns = None
        config.include_blogrolls = False
        return config

    @pytest.fixture
    def mock_config_folder(self):
        """Create config for folder discovery."""
        config = MagicMock(spec=DiscoveryConfig)
        config.source_url = None
        config.source_folder = "/path/to/docs"
        config.cms_platform = None
        config.cms_instance = None
        config.discovery_method = "folder"
        config.max_depth = None
        config.max_pages = 1000
        config.allow_external = False
        config.include_patterns = None
        config.exclude_patterns = None
        config.include_blogrolls = False
        return config

    @pytest.fixture
    def mock_config_cms(self):
        """Create config for CMS discovery."""
        config = MagicMock(spec=DiscoveryConfig)
        config.source_url = None
        config.source_folder = None
        config.cms_platform = "sanity"
        config.cms_instance = "prod"
        config.discovery_method = "cms"
        config.max_depth = None
        config.max_pages = 1000
        config.allow_external = False
        config.include_patterns = None
        config.exclude_patterns = None
        config.include_blogrolls = False
        return config

    @patch("kurt.content.ingestion.step_discovery._discover_from_url")
    def test_discovery_url_sitemap_success(
        self,
        mock_discover,
        mock_writer,
        mock_ctx,
        mock_config_url,
    ):
        """Test successful URL discovery via sitemap."""
        # Mock discovery results
        mock_discover.return_value = {
            "discovered": [
                {"doc_id": "doc-1", "url": "https://example.com/page1", "created": True},
                {"doc_id": "doc-2", "url": "https://example.com/page2", "created": True},
                {"doc_id": "doc-3", "url": "https://example.com/page3", "created": False},
            ],
            "method": "sitemap",
            "total": 3,
            "new": 2,
            "existing": 1,
        }

        mock_writer.write.return_value = {"rows_written": 3, "table_name": "ingestion_discovery"}

        result = discovery(
            ctx=mock_ctx,
            writer=mock_writer,
            config=mock_config_url,
        )

        # Verify results
        assert result["documents_discovered"] == 2
        assert result["documents_existing"] == 1
        assert result["documents_errors"] == 0
        assert result["discovery_method"] == "sitemap"

        # Verify rows written
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3

        # Check row statuses
        new_rows = [r for r in rows if r.status == "DISCOVERED"]
        existing_rows = [r for r in rows if r.status == "EXISTING"]
        assert len(new_rows) == 2
        assert len(existing_rows) == 1

    @patch("kurt.content.ingestion.step_discovery._discover_from_url")
    def test_discovery_url_crawl_fallback(
        self,
        mock_discover,
        mock_writer,
        mock_ctx,
        mock_config_url,
    ):
        """Test URL discovery with crawl fallback."""
        mock_discover.return_value = {
            "discovered": [
                {"doc_id": "doc-1", "url": "https://example.com/page1", "created": True},
            ],
            "method": "crawl",  # Fallback to crawl
            "total": 1,
            "new": 1,
            "existing": 0,
        }

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "ingestion_discovery"}

        result = discovery(
            ctx=mock_ctx,
            writer=mock_writer,
            config=mock_config_url,
        )

        assert result["documents_discovered"] == 1
        assert result["discovery_method"] == "crawl"

    @patch("kurt.content.ingestion.step_discovery._discover_from_folder")
    def test_discovery_folder_success(
        self,
        mock_discover,
        mock_writer,
        mock_ctx,
        mock_config_folder,
    ):
        """Test successful folder discovery."""
        mock_discover.return_value = {
            "discovered": [
                {"doc_id": "doc-1", "path": "/path/to/docs/file1.md", "created": True},
                {"doc_id": "doc-2", "path": "/path/to/docs/file2.md", "created": True},
            ],
            "total": 2,
            "new": 2,
            "existing": 0,
        }

        mock_writer.write.return_value = {"rows_written": 2, "table_name": "ingestion_discovery"}

        result = discovery(
            ctx=mock_ctx,
            writer=mock_writer,
            config=mock_config_folder,
        )

        assert result["documents_discovered"] == 2
        assert result["documents_existing"] == 0
        assert result["discovery_method"] == "folder"

        # Verify source_type is "file" for folder discovery
        rows = mock_writer.write.call_args[0][0]
        assert all(r.source_type == "file" for r in rows)

    @patch("kurt.content.ingestion.step_discovery._discover_from_cms")
    def test_discovery_cms_success(
        self,
        mock_discover,
        mock_writer,
        mock_ctx,
        mock_config_cms,
    ):
        """Test successful CMS discovery."""
        mock_discover.return_value = {
            "discovered": [
                {
                    "document_id": "doc-1",
                    "url": "sanity/prod/article/post-1",
                    "created": True,
                    "title": "Blog Post 1",
                },
                {
                    "document_id": "doc-2",
                    "url": "sanity/prod/article/post-2",
                    "created": True,
                    "title": "Blog Post 2",
                },
            ],
            "total": 2,
            "new": 2,
            "existing": 0,
        }

        mock_writer.write.return_value = {"rows_written": 2, "table_name": "ingestion_discovery"}

        result = discovery(
            ctx=mock_ctx,
            writer=mock_writer,
            config=mock_config_cms,
        )

        assert result["documents_discovered"] == 2
        assert result["discovery_method"] == "cms"

        # Verify source_type is "cms" for CMS discovery
        rows = mock_writer.write.call_args[0][0]
        assert all(r.source_type == "cms" for r in rows)

    def test_discovery_no_source_raises_error(
        self,
        mock_writer,
        mock_ctx,
    ):
        """Test that missing source configuration raises error."""
        config = MagicMock(spec=DiscoveryConfig)
        config.source_url = None
        config.source_folder = None
        config.cms_platform = None
        config.cms_instance = None
        config.include_patterns = None
        config.exclude_patterns = None

        with pytest.raises(ValueError, match="Must specify"):
            discovery(
                ctx=mock_ctx,
                writer=mock_writer,
                config=config,
            )

    @patch("kurt.content.ingestion.step_discovery._discover_from_url")
    def test_discovery_with_errors(
        self,
        mock_discover,
        mock_writer,
        mock_ctx,
        mock_config_url,
    ):
        """Test discovery with some errors."""
        mock_discover.return_value = {
            "discovered": [
                {"doc_id": "doc-1", "url": "https://example.com/page1", "created": True},
                {"doc_id": "doc-2", "url": "https://example.com/page2", "error": "Failed"},
            ],
            "method": "sitemap",
            "total": 2,
            "new": 1,
            "existing": 0,
        }

        mock_writer.write.return_value = {"rows_written": 2, "table_name": "ingestion_discovery"}

        result = discovery(
            ctx=mock_ctx,
            writer=mock_writer,
            config=mock_config_url,
        )

        assert result["documents_discovered"] == 1
        assert result["documents_errors"] == 1

        # Verify error row
        rows = mock_writer.write.call_args[0][0]
        error_rows = [r for r in rows if r.status == "ERROR"]
        assert len(error_rows) == 1
        assert error_rows[0].error == "Failed"

    @patch("kurt.content.ingestion.step_discovery._discover_from_url")
    def test_discovery_with_patterns(
        self,
        mock_discover,
        mock_writer,
        mock_ctx,
    ):
        """Test discovery with include/exclude patterns."""
        config = MagicMock(spec=DiscoveryConfig)
        config.source_url = "https://example.com"
        config.source_folder = None
        config.cms_platform = None
        config.cms_instance = None
        config.discovery_method = "auto"
        config.max_depth = None
        config.max_pages = 1000
        config.allow_external = False
        config.include_patterns = "*/docs/*,*/api/*"
        config.exclude_patterns = "*/internal/*"
        config.include_blogrolls = False

        mock_discover.return_value = {
            "discovered": [
                {"doc_id": "doc-1", "url": "https://example.com/docs/guide", "created": True},
            ],
            "method": "sitemap",
            "total": 1,
            "new": 1,
            "existing": 0,
        }

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "ingestion_discovery"}

        discovery(
            ctx=mock_ctx,
            writer=mock_writer,
            config=config,
        )

        # Verify patterns were parsed and passed
        call_kwargs = mock_discover.call_args[1]
        assert call_kwargs["include_patterns"] == ("*/docs/*", "*/api/*")
        assert call_kwargs["exclude_patterns"] == ("*/internal/*",)

    @patch("kurt.content.ingestion.step_discovery._discover_from_url")
    def test_discovery_empty(
        self,
        mock_discover,
        mock_writer,
        mock_ctx,
        mock_config_url,
    ):
        """Test discovery when nothing is discovered."""
        mock_discover.return_value = {
            "discovered": [],
            "method": "sitemap",
            "total": 0,
            "new": 0,
            "existing": 0,
        }

        mock_writer.write.return_value = {"rows_written": 0, "table_name": "ingestion_discovery"}

        result = discovery(
            ctx=mock_ctx,
            writer=mock_writer,
            config=mock_config_url,
        )

        assert result["documents_discovered"] == 0
        assert result["documents_existing"] == 0
        assert result["documents_errors"] == 0


class TestDiscoveryRow:
    """Tests for DiscoveryRow schema."""

    def test_default_values(self):
        """Test default values for DiscoveryRow."""
        row = DiscoveryRow(document_id="test-id")

        assert row.document_id == "test-id"
        assert row.source_url == ""
        assert row.source_type == "url"
        assert row.discovery_method == ""
        assert row.discovery_url is None
        assert row.status == "DISCOVERED"
        assert row.is_new is True
        assert row.title is None
        assert row.metadata_json is None

    def test_all_fields(self):
        """Test DiscoveryRow with all fields."""
        row = DiscoveryRow(
            document_id="test-id",
            source_url="https://example.com/page",
            source_type="url",
            discovery_method="sitemap",
            discovery_url="https://example.com",
            status="DISCOVERED",
            is_new=True,
            title="Test Page",
            metadata_json={"key": "value"},
        )

        assert row.document_id == "test-id"
        assert row.source_url == "https://example.com/page"
        assert row.discovery_method == "sitemap"
        assert row.title == "Test Page"
        assert row.metadata_json == {"key": "value"}


class TestDiscoveryConfig:
    """Tests for DiscoveryConfig schema."""

    def test_explicit_values(self):
        """Test explicit values for DiscoveryConfig."""
        # ConfigParam doesn't resolve defaults on direct instantiation
        # Test with explicit values instead
        config = DiscoveryConfig(
            source_url=None,
            source_folder=None,
            cms_platform=None,
            cms_instance=None,
            discovery_method="auto",
            max_depth=None,
            max_pages=1000,
            allow_external=False,
            include_blogrolls=False,
        )

        assert config.source_url is None
        assert config.source_folder is None
        assert config.cms_platform is None
        assert config.cms_instance is None
        assert config.discovery_method == "auto"
        assert config.max_depth is None
        assert config.max_pages == 1000
        assert config.allow_external is False
        assert config.include_blogrolls is False

    def test_url_config(self):
        """Test URL configuration."""
        config = DiscoveryConfig(
            source_url="https://example.com",
            max_depth=2,
            max_pages=500,
        )

        assert config.source_url == "https://example.com"
        assert config.max_depth == 2
        assert config.max_pages == 500

    def test_folder_config(self):
        """Test folder configuration."""
        config = DiscoveryConfig(
            source_folder="/path/to/docs",
            include_patterns="*.md",
        )

        assert config.source_folder == "/path/to/docs"
        assert config.include_patterns == "*.md"

    def test_cms_config(self):
        """Test CMS configuration."""
        config = DiscoveryConfig(
            cms_platform="sanity",
            cms_instance="prod",
        )

        assert config.cms_platform == "sanity"
        assert config.cms_instance == "prod"
