"""Tests for file-based content ingestion."""

from unittest.mock import MagicMock, Mock, create_autospec, patch
from uuid import UUID

import pytest

from kurt.config import KurtConfig
from kurt.ingestion.add_files import (
    add_directory,
    add_single_file,
    compute_file_hash,
    copy_file_to_sources,
    should_confirm_file_batch,
)


class TestComputeFileHash:
    """Test file hashing functionality."""

    def test_computes_sha256_hash(self, tmp_path):
        # Create test file with known content
        test_file = tmp_path / "test.md"
        test_file.write_text("# Hello World\n\nThis is a test.")

        hash_result = compute_file_hash(test_file)

        # Should return hex string
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA256 produces 64 hex chars
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_same_content_produces_same_hash(self, tmp_path):
        # Create two files with identical content
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        content = "# Test\n\nSame content"

        file1.write_text(content)
        file2.write_text(content)

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)

        assert hash1 == hash2

    def test_different_content_produces_different_hash(self, tmp_path):
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"

        file1.write_text("# File 1")
        file2.write_text("# File 2")

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)

        assert hash1 != hash2

    def test_handles_large_files(self, tmp_path):
        # Create large file (> 4096 bytes to test chunking)
        large_file = tmp_path / "large.md"
        large_content = "# Large File\n" + ("test content " * 1000)
        large_file.write_text(large_content)

        hash_result = compute_file_hash(large_file)

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64


class TestCopyFileToSources:
    """Test file copying to sources directory."""

    @patch("kurt.ingestion.add_files.load_config")
    def test_copies_file_with_relative_path(self, mock_config, tmp_path):
        # Setup
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        # Create source file
        source_file = tmp_path / "original" / "test.md"
        source_file.parent.mkdir()
        source_file.write_text("# Test")

        # Copy with relative path
        result = copy_file_to_sources(source_file, relative_path="subdir/test.md")

        # Check file was copied
        target_file = sources_dir / "subdir" / "test.md"
        assert target_file.exists()
        assert target_file.read_text() == "# Test"
        assert result == "subdir/test.md"

    @patch("kurt.ingestion.add_files.load_config")
    def test_copies_file_without_relative_path(self, mock_config, tmp_path):
        # Setup
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        # Create source file
        source_file = tmp_path / "test.md"
        source_file.write_text("# Test")

        # Copy without relative path
        result = copy_file_to_sources(source_file)

        # Should use just filename
        target_file = sources_dir / "test.md"
        assert target_file.exists()
        assert result == "test.md"

    @patch("kurt.ingestion.add_files.load_config")
    def test_creates_nested_directories(self, mock_config, tmp_path):
        # Setup
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        # Create source file
        source_file = tmp_path / "test.md"
        source_file.write_text("# Test")

        # Copy to deeply nested path
        copy_file_to_sources(source_file, relative_path="a/b/c/test.md")

        # Should create all parent directories
        target_file = sources_dir / "a" / "b" / "c" / "test.md"
        assert target_file.exists()


class TestAddSingleFile:
    """Test adding a single file."""

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    @patch("kurt.ingestion.add_files.extract_document_metadata")
    def test_adds_new_file_successfully(self, mock_extract, mock_config, mock_session, tmp_path):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = None  # No existing doc
        mock_session.return_value = mock_db

        mock_extract.return_value = {"content_type": "article", "topics": ["test", "python"]}

        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Article\n\nContent here.")

        # Add file
        result = add_single_file(test_file, index=True)

        # Verify result
        assert result["created"] is True
        assert result["indexed"] is True
        assert "doc_id" in result
        assert result["title"] == "Test Article"
        assert result["content_length"] == len("# Test Article\n\nContent here.")
        assert "index_result" in result

        # Verify document was added to session
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    def test_skips_duplicate_content(self, mock_config, mock_session, tmp_path):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        # Mock existing document with same hash
        existing_doc = Mock()
        existing_doc.id = UUID("12345678-1234-5678-1234-567812345678")

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = existing_doc
        mock_session.return_value = mock_db

        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Add file
        result = add_single_file(test_file, index=False)

        # Should skip
        assert result["created"] is False
        assert result["indexed"] is False
        assert result["skipped"] is True
        assert result["reason"] == "Content already exists"

        # Should not add to session
        mock_db.add.assert_not_called()

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    def test_extracts_title_from_filename_if_no_heading(self, mock_config, mock_session, tmp_path):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = None
        mock_session.return_value = mock_db

        # Create file without heading
        test_file = tmp_path / "my-test-file.md"
        test_file.write_text("Just some content without a heading.")

        # Add file
        result = add_single_file(test_file, index=False)

        # Should derive title from filename
        assert result["title"] == "My Test File"

    def test_rejects_invalid_extension(self, tmp_path):
        # Create non-markdown file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Not markdown")

        # Should raise ValueError
        with pytest.raises(ValueError, match="Unsupported file type"):
            add_single_file(test_file, index=False)

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    @patch("kurt.ingestion.add_files.extract_document_metadata")
    def test_handles_indexing_error_gracefully(
        self, mock_extract, mock_config, mock_session, tmp_path
    ):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = None
        mock_session.return_value = mock_db

        # Mock indexing failure
        mock_extract.side_effect = Exception("LLM API error")

        # Create test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        # Add file with indexing
        result = add_single_file(test_file, index=True)

        # Should still create document but mark indexing as failed
        assert result["created"] is True
        assert result["indexed"] is False
        assert "index_error" in result
        assert "LLM API error" in result["index_error"]


class TestAddDirectory:
    """Test adding directory of files."""

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    @patch("kurt.ingestion.add_files.asyncio.run")
    def test_adds_multiple_files_from_directory(
        self, mock_async_run, mock_config, mock_session, tmp_path
    ):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = None
        mock_session.return_value = mock_db

        # Mock batch indexing
        mock_async_run.return_value = {"succeeded": 3, "failed": 0}

        # Create test directory with files
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("# File 1")
        (test_dir / "file2.md").write_text("# File 2")
        (test_dir / "file3.md").write_text("# File 3")

        # Add directory
        result = add_directory(test_dir, recursive=False, index=True)

        # Verify results
        assert result["total"] == 3
        assert result["created"] == 3
        assert result["skipped"] == 0
        assert result["indexed"] == 3
        assert result["errors"] == 0
        assert len(result["files"]) == 3

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    def test_handles_empty_directory(self, mock_config, mock_session, tmp_path):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        # Create empty directory
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        # Add directory
        result = add_directory(test_dir, recursive=False, index=False)

        # Should return empty results
        assert result["total"] == 0
        assert result["created"] == 0
        assert result["files"] == []

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    def test_recursive_vs_non_recursive(self, mock_config, mock_session, tmp_path):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = None
        mock_session.return_value = mock_db

        # Create nested structure
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "root.md").write_text("# Root")

        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.md").write_text("# Nested")

        # Non-recursive
        result_non_recursive = add_directory(test_dir, recursive=False, index=False)
        assert result_non_recursive["total"] == 1
        assert result_non_recursive["files"][0]["relative_path"] == "root.md"

        # Reset mock
        mock_db.reset_mock()

        # Recursive
        result_recursive = add_directory(test_dir, recursive=True, index=False)
        assert result_recursive["total"] == 2
        relative_paths = [f["relative_path"] for f in result_recursive["files"]]
        assert "root.md" in relative_paths
        assert "subdir/nested.md" in relative_paths

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    def test_handles_file_errors_gracefully(self, mock_config, mock_session, tmp_path):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        mock_db = MagicMock()
        mock_db.exec.return_value.first.return_value = None
        mock_session.return_value = mock_db

        # Create test directory
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "good.md").write_text("# Good File")
        (test_dir / "bad.md").write_text("# Bad File")

        # Mock add_single_file to fail on one file
        with patch("kurt.ingestion.add_files.add_single_file") as mock_add:

            def side_effect(path, **kwargs):
                if "bad.md" in str(path):
                    raise Exception("File processing error")
                return {"doc_id": "test-id", "created": True, "title": "Good File"}

            mock_add.side_effect = side_effect

            # Add directory
            result = add_directory(test_dir, recursive=False, index=False)

            # Should handle error gracefully
            assert result["total"] == 2
            assert result["created"] == 1
            assert result["errors"] == 1

            # Check error is recorded
            error_file = [f for f in result["files"] if "error" in f][0]
            assert "bad.md" in error_file["path"]
            assert "File processing error" in error_file["error"]

    @patch("kurt.ingestion.add_files.get_session")
    @patch("kurt.ingestion.add_files.load_config")
    def test_skips_duplicate_files(self, mock_config, mock_session, tmp_path):
        # Setup mocks
        sources_dir = tmp_path / "sources"
        sources_dir.mkdir()

        mock_config_obj = create_autospec(KurtConfig, instance=True)
        mock_config_obj.get_absolute_sources_path.return_value = sources_dir
        mock_config.return_value = mock_config_obj

        # Mock one file existing, one new
        def mock_exec_side_effect(stmt):
            result = MagicMock()
            # Return existing doc for first file, None for second
            call_count = mock_exec_side_effect.call_count
            if call_count % 2 == 1:  # Odd calls = existing
                result.first.return_value = Mock(id=UUID("12345678-1234-5678-1234-567812345678"))
            else:  # Even calls = new
                result.first.return_value = None
            return result

        mock_exec_side_effect.call_count = 0

        mock_db = MagicMock()
        mock_db.exec.side_effect = lambda stmt: (
            setattr(mock_exec_side_effect, "call_count", mock_exec_side_effect.call_count + 1),
            mock_exec_side_effect(stmt),
        )[1]
        mock_session.return_value = mock_db

        # Create test directory
        test_dir = tmp_path / "docs"
        test_dir.mkdir()
        (test_dir / "existing.md").write_text("# Existing")
        (test_dir / "new.md").write_text("# New")

        # Add directory
        result = add_directory(test_dir, recursive=False, index=False)

        # Should show 1 created, 1 skipped
        assert result["total"] == 2
        assert result["created"] == 1
        assert result["skipped"] == 1


class TestShouldConfirmFileBatch:
    """Test batch confirmation logic."""

    def test_no_confirmation_for_small_batch(self):
        assert should_confirm_file_batch(10) is False
        assert should_confirm_file_batch(20) is False

    def test_confirmation_for_large_batch(self):
        assert should_confirm_file_batch(21) is True
        assert should_confirm_file_batch(100) is True

    def test_force_flag_skips_confirmation(self):
        assert should_confirm_file_batch(100, force=True) is False
        assert should_confirm_file_batch(1000, force=True) is False

    def test_threshold_boundary(self):
        # At exactly threshold (20)
        assert should_confirm_file_batch(20) is False
        # One above threshold
        assert should_confirm_file_batch(21) is True
