"""
Tests for assertion helpers.

These tests verify that assertion helpers correctly validate database
state and filesystem artifacts.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from kurt.testing import (
    assert_directory_exists,
    assert_file_contains,
    assert_file_content_matches,
    assert_file_exists,
    assert_file_not_exists,
)


class TestFilesystemAssertions:
    """Tests for filesystem assertion helpers."""

    def test_assert_file_exists_success(self):
        """Test file exists assertion with existing file."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("content")
            result = assert_file_exists(path)
            assert result == path

    def test_assert_file_exists_failure(self):
        """Test file exists assertion with missing file."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.txt"
            with pytest.raises(AssertionError, match="File not found"):
                assert_file_exists(path)

    def test_assert_file_exists_directory(self):
        """Test file exists assertion with directory path."""
        with TemporaryDirectory() as tmpdir:
            with pytest.raises(AssertionError, match="not a file"):
                assert_file_exists(tmpdir)

    def test_assert_file_not_exists_success(self):
        """Test file not exists assertion with missing file."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.txt"
            # Should not raise
            assert_file_not_exists(path)

    def test_assert_file_not_exists_failure(self):
        """Test file not exists assertion with existing file."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("content")
            with pytest.raises(AssertionError, match="unexpectedly exists"):
                assert_file_not_exists(path)

    def test_assert_directory_exists_success(self):
        """Test directory exists assertion with existing directory."""
        with TemporaryDirectory() as tmpdir:
            result = assert_directory_exists(tmpdir)
            assert result == Path(tmpdir)

    def test_assert_directory_exists_failure(self):
        """Test directory exists assertion with missing directory."""
        with pytest.raises(AssertionError, match="Directory not found"):
            assert_directory_exists("/nonexistent/path")

    def test_assert_directory_exists_file(self):
        """Test directory exists assertion with file path."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("content")
            with pytest.raises(AssertionError, match="not a directory"):
                assert_directory_exists(path)

    def test_assert_file_contains_success(self):
        """Test file contains assertion with matching text."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("Hello, World!")
            # Should not raise
            assert_file_contains(path, "World")

    def test_assert_file_contains_failure(self):
        """Test file contains assertion with missing text."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("Hello, World!")
            with pytest.raises(AssertionError, match="does not contain"):
                assert_file_contains(path, "Goodbye")

    def test_assert_file_content_matches_success(self):
        """Test file content matches assertion with matching content."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("exact content")
            # Should not raise
            assert_file_content_matches(path, "exact content")

    def test_assert_file_content_matches_failure(self):
        """Test file content matches assertion with different content."""
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.txt"
            path.write_text("actual content")
            with pytest.raises(AssertionError, match="content mismatch"):
                assert_file_content_matches(path, "expected content")


class TestDatabaseAssertions:
    """Tests for database assertion helpers.

    Note: These tests require the tmp_project fixture which provides
    a real database. They are marked as integration tests.
    """

    @pytest.mark.integration
    def test_assert_map_document_exists_success(self, tmp_project_with_docs):
        """Test map document exists assertion with existing document."""
        from kurt.db import managed_session
        from kurt.testing import assert_map_document_exists

        with managed_session() as session:
            doc = assert_map_document_exists(session, "https://example.com/docs/intro")
            assert doc.title == "Introduction"

    @pytest.mark.integration
    def test_assert_map_document_exists_failure(self, tmp_project):
        """Test map document exists assertion with missing document."""
        from kurt.db import managed_session
        from kurt.testing import assert_map_document_exists

        with managed_session() as session:
            with pytest.raises(AssertionError, match="not found"):
                assert_map_document_exists(session, "https://nonexistent.example.com")

    @pytest.mark.integration
    def test_assert_map_document_count(self, tmp_project_with_docs):
        """Test map document count assertion."""
        from kurt.db import managed_session
        from kurt.testing import assert_map_document_count

        with managed_session() as session:
            # tmp_project_with_docs creates 7 map documents
            assert_map_document_count(session, 7)

    @pytest.mark.integration
    def test_assert_map_document_count_with_status(self, tmp_project_with_docs):
        """Test map document count with status filter."""
        from kurt.db import managed_session
        from kurt.testing import assert_map_document_count

        with managed_session() as session:
            # 6 SUCCESS, 1 ERROR
            assert_map_document_count(session, 6, status="SUCCESS")
            assert_map_document_count(session, 1, status="ERROR")

    @pytest.mark.integration
    def test_assert_fetch_document_exists(self, tmp_project_with_docs):
        """Test fetch document exists assertion."""
        from kurt.db import managed_session
        from kurt.testing import assert_fetch_document_exists

        with managed_session() as session:
            doc = assert_fetch_document_exists(session, "doc-4")
            assert doc.fetch_engine == "trafilatura"

    @pytest.mark.integration
    def test_assert_row_count(self, tmp_project_with_docs):
        """Test generic row count assertion."""
        from kurt.db import managed_session
        from kurt.testing import assert_row_count
        from kurt.tools.map.models import MapDocument

        with managed_session() as session:
            assert_row_count(session, MapDocument, 7)

    @pytest.mark.integration
    def test_assert_table_empty(self, tmp_project):
        """Test table empty assertion on empty table."""
        from kurt.db import managed_session
        from kurt.testing import assert_table_empty
        from kurt.tools.map.models import MapDocument

        with managed_session() as session:
            # Fresh project has empty tables
            assert_table_empty(session, MapDocument)

    @pytest.mark.integration
    def test_assert_table_not_empty(self, tmp_project_with_docs):
        """Test table not empty assertion on populated table."""
        from kurt.db import managed_session
        from kurt.testing import assert_table_not_empty
        from kurt.tools.map.models import MapDocument

        with managed_session() as session:
            assert_table_not_empty(session, MapDocument)


class TestCountHelpers:
    """Tests for count helper functions."""

    @pytest.mark.integration
    def test_count_documents_by_status(self, tmp_project_with_docs):
        """Test counting documents by status."""
        from kurt.db import managed_session
        from kurt.testing import count_documents_by_status

        with managed_session() as session:
            success_count = count_documents_by_status(session, "SUCCESS", "map")
            assert success_count == 6

            error_count = count_documents_by_status(session, "ERROR", "map")
            assert error_count == 1

    @pytest.mark.integration
    def test_count_documents_by_domain(self, tmp_project_with_docs):
        """Test counting documents by domain."""
        from kurt.db import managed_session
        from kurt.testing import count_documents_by_domain

        with managed_session() as session:
            count = count_documents_by_domain(session, "example.com")
            assert count == 7
