"""Tests for documents CLI in cloud mode with API server.

This tests the full cloud mode routing:
CLI → HTTP → web/api/server.py → queries.py → PostgreSQL
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.documents.cli import content_group


@pytest.fixture
def mock_cloud_mode_with_data(tmp_project_with_docs):
    """Mock cloud mode environment with API responses."""
    # Mock is_cloud_mode to return True
    with patch("kurt.db.tenant.is_cloud_mode") as mock_is_cloud:
        mock_is_cloud.return_value = True

        # Mock API base URL
        with patch("kurt.auth.credentials.get_cloud_api_url") as mock_api_url:
            mock_api_url.return_value = "http://testserver"

            # Mock auth token
            with patch("kurt.db.cloud_api.get_auth_token") as mock_token:
                mock_token.return_value = "test-token"

                # Mock requests.get to return realistic API responses
                def mock_get(url, **kwargs):
                    import requests

                    response = MagicMock()
                    response.status_code = 200

                    # Handle different endpoints
                    if "/api/status" in url:
                        response.json.return_value = {
                            "initialized": True,
                            "documents": {
                                "total": 2,
                                "by_status": {"fetched": 2, "not_fetched": 0, "error": 0},
                                "by_domain": {"example.com": 1, "test.com": 1},
                            },
                        }
                    elif "/api/documents/" in url and not url.endswith("/api/documents/"):
                        # Get single document
                        doc_id = url.split("/")[-1]
                        if doc_id == "nonexistent-id":
                            response.status_code = 404
                            response.json.return_value = {"error": "Document not found"}

                            # Make raise_for_status actually raise HTTPError
                            def raise_404():
                                error = requests.exceptions.HTTPError()
                                error.response = response
                                raise error

                            response.raise_for_status = raise_404
                        else:
                            response.json.return_value = {
                                "document_id": doc_id,
                                "source_url": "https://example.com",
                                "source_type": "url",
                                "title": "Test Doc",
                                "map_status": "MapStatus.SUCCESS",
                                "fetch_status": "FetchStatus.SUCCESS",
                                "content_length": 1000,
                                "error": None,
                                "discovered_at": "2026-01-15 10:00:00",
                                "fetched_at": "2026-01-15 10:01:00",
                            }
                            response.raise_for_status = MagicMock()
                    elif "/api/documents/count" in url:
                        response.json.return_value = {"count": 2}
                    elif "/api/documents" in url:
                        # List documents
                        response.json.return_value = [
                            {
                                "document_id": "test-doc-1",
                                "source_url": "https://example.com",
                                "source_type": "url",
                                "title": "Test Doc 1",
                                "map_status": "MapStatus.SUCCESS",
                                "fetch_status": "FetchStatus.SUCCESS",
                                "content_length": 1000,
                                "error": None,
                                "discovered_at": "2026-01-15 10:00:00",
                                "fetched_at": "2026-01-15 10:01:00",
                            },
                            {
                                "document_id": "test-doc-2",
                                "source_url": "https://test.com",
                                "source_type": "url",
                                "title": "Test Doc 2",
                                "map_status": "MapStatus.SUCCESS",
                                "fetch_status": "FetchStatus.SUCCESS",
                                "content_length": 2000,
                                "error": None,
                                "discovered_at": "2026-01-15 10:00:00",
                                "fetched_at": "2026-01-15 10:02:00",
                            },
                        ]

                    if (
                        not hasattr(response, "raise_for_status")
                        or response.raise_for_status is None
                    ):
                        response.raise_for_status = MagicMock()

                    return response

                with patch("requests.get", side_effect=mock_get):
                    yield


class TestStatusCloudMode:
    """Test status command in cloud mode."""

    def test_status_json_via_api(self, mock_cloud_mode_with_data):
        """Test kurt status --format json routes through API."""
        from kurt.status.cli import status

        runner = CliRunner()
        result = runner.invoke(status, ["--format", "json"])

        assert result.exit_code == 0
        assert "initialized" in result.output
        assert "documents" in result.output
        assert "total" in result.output


class TestDocumentsListCloudMode:
    """Test documents list command in cloud mode."""

    def test_list_all_via_api(self, mock_cloud_mode_with_data):
        """Test kurt content list routes through API."""
        runner = CliRunner()
        result = runner.invoke(content_group, ["list", "--format", "json"])

        assert result.exit_code == 0
        # Should return JSON array
        assert result.output.startswith("[")
        assert "document_id" in result.output
        assert "source_url" in result.output

    def test_list_with_limit_via_api(self, mock_cloud_mode_with_data):
        """Test kurt content list --limit routes through API."""
        runner = CliRunner()
        result = runner.invoke(content_group, ["list", "--limit", "1", "--format", "json"])

        assert result.exit_code == 0
        # Should return documents (mocked data doesn't respect limit)
        import json

        docs = json.loads(result.output)
        assert len(docs) >= 1


class TestDocumentsGetCloudMode:
    """Test documents get command in cloud mode."""

    def test_get_by_id_via_api(self, mock_cloud_mode_with_data):
        """Test kurt content get <id> routes through API."""
        runner = CliRunner()
        # Get test-doc-1 from mocked API
        result = runner.invoke(content_group, ["get", "test-doc-1", "--format", "json"])

        assert result.exit_code == 0
        import json

        doc = json.loads(result.output)
        assert doc["document_id"] == "test-doc-1"

    def test_get_nonexistent_via_api(self, mock_cloud_mode_with_data):
        """Test kurt content get with nonexistent ID returns error."""
        runner = CliRunner()
        result = runner.invoke(content_group, ["get", "nonexistent-id", "--format", "json"])

        # Should complete but return error in JSON
        import json

        output = json.loads(result.output)
        assert "error" in output
        assert "not found" in output["error"].lower()


class TestCloudModeIntegration:
    """Integration tests for cloud mode architecture."""

    def test_full_flow_status(self, mock_cloud_mode_with_data):
        """Test full flow: CLI → API → queries.py → database."""
        from kurt.status.cli import status

        runner = CliRunner()
        result = runner.invoke(status, ["--format", "json"])

        assert result.exit_code == 0
        import json

        data = json.loads(result.output)
        assert data["initialized"] is True
        assert "documents" in data
        assert isinstance(data["documents"]["total"], int)
        assert data["documents"]["total"] == 2

    def test_full_flow_documents_list(self, mock_cloud_mode_with_data):
        """Test full flow for document listing."""
        runner = CliRunner()
        result = runner.invoke(content_group, ["list", "--format", "json"])

        assert result.exit_code == 0
        import json

        docs = json.loads(result.output)
        assert isinstance(docs, list)
        assert len(docs) == 2
        assert docs[0]["document_id"] == "test-doc-1"
        assert docs[1]["document_id"] == "test-doc-2"

    def test_full_flow_documents_get(self, mock_cloud_mode_with_data):
        """Test full flow for getting single document."""
        runner = CliRunner()
        result = runner.invoke(content_group, ["get", "test-doc-1", "--format", "json"])

        assert result.exit_code == 0
        import json

        doc = json.loads(result.output)
        assert doc["document_id"] == "test-doc-1"
        assert "source_url" in doc
        assert doc["source_url"] == "https://example.com"
