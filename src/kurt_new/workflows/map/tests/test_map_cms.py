"""Tests for CMS discovery functionality."""

from unittest.mock import MagicMock, patch

import pytest

from kurt_new.workflows.map.map_cms import discover_from_cms


class TestDiscoverFromCms:
    """Test suite for discover_from_cms function."""

    def test_returns_expected_structure(self):
        """Test return structure."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = [
            {
                "id": "doc-1",
                "title": "Test Document",
                "slug": "test-document",
                "content_type": "page",
                "status": "published",
            }
        ]

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                result = discover_from_cms("sanity", "prod")

        assert "discovered" in result
        assert "total" in result
        assert "method" in result
        assert result["method"] == "cms"

    def test_discovers_documents(self):
        """Test that documents are discovered from CMS."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = [
            {
                "id": "doc-1",
                "title": "First Document",
                "slug": "first-doc",
                "content_type": "page",
                "status": "published",
            },
            {
                "id": "doc-2",
                "title": "Second Document",
                "slug": "second-doc",
                "content_type": "post",
                "status": "draft",
            },
        ]

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                result = discover_from_cms("sanity", "prod")

        assert result["total"] == 2
        assert len(result["discovered"]) == 2

    def test_discovered_items_have_expected_fields(self):
        """Test discovered items have required fields."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = [
            {
                "id": "doc-1",
                "title": "Test Document",
                "slug": "test-doc",
                "content_type": "page",
                "status": "published",
            }
        ]

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                result = discover_from_cms("sanity", "prod")

        item = result["discovered"][0]
        assert "url" in item
        assert "title" in item
        assert "cms_id" in item
        assert "schema" in item
        assert "slug" in item
        assert "metadata" in item

    def test_builds_source_url(self):
        """Test source URL is built correctly."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = [
            {
                "id": "doc-1",
                "title": "Test",
                "slug": "test-slug",
                "content_type": "page",
            }
        ]

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                result = discover_from_cms("sanity", "prod")

        item = result["discovered"][0]
        assert item["url"] == "sanity/prod/page/test-slug"

    def test_passes_content_type_filter(self):
        """Test content_type filter is passed to adapter."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = []

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                discover_from_cms("sanity", "prod", content_type="page")

        mock_adapter.list_all.assert_called_once_with(
            content_type="page",
            status=None,
            limit=None,
        )

    def test_passes_status_filter(self):
        """Test status filter is passed to adapter."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = []

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                discover_from_cms("sanity", "prod", status="published")

        mock_adapter.list_all.assert_called_once_with(
            content_type=None,
            status="published",
            limit=None,
        )

    def test_passes_limit(self):
        """Test limit is passed to adapter."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = []

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                discover_from_cms("sanity", "prod", limit=10)

        mock_adapter.list_all.assert_called_once_with(
            content_type=None,
            status=None,
            limit=10,
        )

    def test_handles_adapter_error(self):
        """Test error handling when adapter fails."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.side_effect = Exception("API error")

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                with pytest.raises(ValueError, match="Failed to discover documents"):
                    discover_from_cms("sanity", "prod")

    def test_handles_empty_result(self):
        """Test handling when no documents found."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = []

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                result = discover_from_cms("sanity", "prod")

        assert result["total"] == 0
        assert result["discovered"] == []

    def test_uses_untitled_for_missing_slug(self):
        """Test fallback to 'untitled' when slug is missing."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = [
            {
                "id": "doc-1",
                "title": "Test",
                "content_type": "page",
                # No slug
            }
        ]

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                result = discover_from_cms("sanity", "prod")

        item = result["discovered"][0]
        assert "untitled" in item["url"]

    def test_preserves_metadata(self):
        """Test that full metadata is preserved."""
        mock_adapter = MagicMock()
        mock_adapter.list_all.return_value = [
            {
                "id": "doc-1",
                "title": "Test",
                "slug": "test",
                "content_type": "page",
                "extra_field": "extra_value",
                "nested": {"key": "value"},
            }
        ]

        with patch("kurt_new.integrations.cms.config.get_platform_config", return_value={}):
            with patch("kurt_new.integrations.cms.get_adapter", return_value=mock_adapter):
                result = discover_from_cms("sanity", "prod")

        metadata = result["discovered"][0]["metadata"]
        assert metadata["extra_field"] == "extra_value"
        assert metadata["nested"]["key"] == "value"
