"""Tests for source type detection utilities."""

from pathlib import Path

import pytest

from kurt.ingestion.source_detection import (
    detect_source_type,
    discover_markdown_files,
    get_relative_path_from_source,
    validate_file_extension,
)


class TestDetectSourceType:
    """Test source type detection."""

    def test_detects_http_url(self):
        assert detect_source_type("http://example.com") == "url"

    def test_detects_https_url(self):
        assert detect_source_type("https://example.com/blog") == "url"

    def test_detects_ftp_url(self):
        assert detect_source_type("ftp://files.example.com") == "url"

    def test_detects_existing_file(self, tmp_path):
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        assert detect_source_type(str(test_file)) == "file"

    def test_detects_existing_directory(self, tmp_path):
        # Use existing tmp_path directory
        assert detect_source_type(str(tmp_path)) == "directory"

    def test_non_existent_path_defaults_to_url(self):
        # Non-existent paths are assumed to be URLs (will fail gracefully later)
        assert detect_source_type("/non/existent/path.md") == "url"

    def test_relative_file_path(self, tmp_path, monkeypatch):
        # Change to tmp directory
        monkeypatch.chdir(tmp_path)

        # Create relative file
        test_file = tmp_path / "article.md"
        test_file.write_text("# Article")

        assert detect_source_type("article.md") == "file"

    def test_relative_directory_path(self, tmp_path, monkeypatch):
        # Change to parent of tmp_path
        monkeypatch.chdir(tmp_path.parent)

        # Use relative path to tmp_path
        relative_path = tmp_path.name
        assert detect_source_type(relative_path) == "directory"


class TestDiscoverMarkdownFiles:
    """Test markdown file discovery."""

    def test_discovers_md_files_in_directory(self, tmp_path):
        # Create markdown files
        (tmp_path / "file1.md").write_text("# File 1")
        (tmp_path / "file2.md").write_text("# File 2")
        (tmp_path / "readme.txt").write_text("Not markdown")

        files = discover_markdown_files(tmp_path, recursive=False)

        assert len(files) == 2
        assert all(f.suffix == ".md" for f in files)
        assert {f.name for f in files} == {"file1.md", "file2.md"}

    def test_recursive_discovery(self, tmp_path):
        # Create nested structure
        (tmp_path / "root.md").write_text("# Root")

        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.md").write_text("# Nested")

        deep_dir = subdir / "deep"
        deep_dir.mkdir()
        (deep_dir / "deep.md").write_text("# Deep")

        # Non-recursive
        files_non_recursive = discover_markdown_files(tmp_path, recursive=False)
        assert len(files_non_recursive) == 1
        assert files_non_recursive[0].name == "root.md"

        # Recursive
        files_recursive = discover_markdown_files(tmp_path, recursive=True)
        assert len(files_recursive) == 3
        assert {f.name for f in files_recursive} == {"root.md", "nested.md", "deep.md"}

    def test_ignores_hidden_files(self, tmp_path):
        # Create regular and hidden files
        (tmp_path / "visible.md").write_text("# Visible")
        (tmp_path / ".hidden.md").write_text("# Hidden")

        # Create hidden directory
        hidden_dir = tmp_path / ".git"
        hidden_dir.mkdir()
        (hidden_dir / "config.md").write_text("# Git config")

        files = discover_markdown_files(tmp_path, recursive=True)

        # Should only find visible.md
        assert len(files) == 1
        assert files[0].name == "visible.md"

    def test_empty_directory(self, tmp_path):
        files = discover_markdown_files(tmp_path, recursive=True)
        assert len(files) == 0

    def test_raises_on_non_directory(self, tmp_path):
        test_file = tmp_path / "file.md"
        test_file.write_text("# Test")

        with pytest.raises(ValueError, match="Not a directory"):
            discover_markdown_files(test_file, recursive=False)

    def test_sorts_files_alphabetically(self, tmp_path):
        # Create files in random order
        (tmp_path / "zebra.md").write_text("# Z")
        (tmp_path / "apple.md").write_text("# A")
        (tmp_path / "mango.md").write_text("# M")

        files = discover_markdown_files(tmp_path, recursive=False)

        # Should be sorted
        assert [f.name for f in files] == ["apple.md", "mango.md", "zebra.md"]


class TestValidateFileExtension:
    """Test file extension validation."""

    def test_valid_md_file(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        is_valid, error = validate_file_extension(test_file)

        assert is_valid is True
        assert error == ""

    def test_case_insensitive_extension(self, tmp_path):
        test_file = tmp_path / "test.MD"
        test_file.write_text("# Test")

        is_valid, error = validate_file_extension(test_file)

        assert is_valid is True
        assert error == ""

    def test_invalid_extension_txt(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")

        is_valid, error = validate_file_extension(test_file)

        assert is_valid is False
        assert "Unsupported file type" in error
        assert ".txt" in error

    def test_invalid_extension_pdf(self, tmp_path):
        test_file = tmp_path / "test.pdf"
        test_file.write_text("Fake PDF")

        is_valid, error = validate_file_extension(test_file)

        assert is_valid is False
        assert "Unsupported file type" in error
        assert ".pdf" in error

    def test_file_not_found(self):
        non_existent = Path("/non/existent/file.md")

        is_valid, error = validate_file_extension(non_existent)

        assert is_valid is False
        assert "File not found" in error

    def test_directory_not_file(self, tmp_path):
        is_valid, error = validate_file_extension(tmp_path)

        assert is_valid is False
        assert "Not a file" in error


class TestGetRelativePathFromSource:
    """Test relative path calculation."""

    def test_relative_path_from_source_root(self, tmp_path):
        source_root = tmp_path
        file_path = tmp_path / "subdir" / "file.md"

        relative = get_relative_path_from_source(file_path, source_root)

        assert relative == "subdir/file.md"

    def test_file_in_source_root(self, tmp_path):
        source_root = tmp_path
        file_path = tmp_path / "file.md"

        relative = get_relative_path_from_source(file_path, source_root)

        assert relative == "file.md"

    def test_file_outside_source_root(self, tmp_path):
        source_root = tmp_path / "subdir"
        source_root.mkdir()
        file_path = tmp_path / "file.md"  # Outside subdir

        relative = get_relative_path_from_source(file_path, source_root)

        # Should return absolute path when not relative
        assert str(file_path) in relative

    def test_deeply_nested_path(self, tmp_path):
        source_root = tmp_path
        file_path = tmp_path / "a" / "b" / "c" / "file.md"

        relative = get_relative_path_from_source(file_path, source_root)

        assert relative == "a/b/c/file.md"
