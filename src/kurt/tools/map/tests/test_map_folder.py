"""Tests for folder discovery functionality."""

from pathlib import Path

import pytest

from kurt.tools.map.engines.folder import (
    _extract_title,
    compute_file_hash,
    discover_from_folder_impl as discover_from_folder,
    discover_markdown_files,
)


class TestComputeFileHash:
    """Test suite for compute_file_hash function."""

    def test_computes_sha256_hash(self, tmp_path: Path):
        """Test that it computes SHA256 hash."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        file_hash = compute_file_hash(test_file)

        # SHA256 produces 64 hex characters
        assert len(file_hash) == 64
        assert all(c in "0123456789abcdef" for c in file_hash)

    def test_same_content_same_hash(self, tmp_path: Path):
        """Test that same content produces same hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        content = "Same content in both files"
        file1.write_text(content)
        file2.write_text(content)

        assert compute_file_hash(file1) == compute_file_hash(file2)

    def test_different_content_different_hash(self, tmp_path: Path):
        """Test that different content produces different hash."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content A")
        file2.write_text("Content B")

        assert compute_file_hash(file1) != compute_file_hash(file2)

    def test_handles_binary_files(self, tmp_path: Path):
        """Test that binary files can be hashed."""
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

        file_hash = compute_file_hash(binary_file)
        assert len(file_hash) == 64


class TestDiscoverMarkdownFiles:
    """Test suite for discover_markdown_files function."""

    def test_finds_md_files(self, tmp_markdown_folder: Path):
        """Test finding .md files."""
        files = discover_markdown_files(tmp_markdown_folder)

        md_files = [f for f in files if f.suffix == ".md"]
        assert len(md_files) >= 4  # intro.md, guide.md, config.md, plugins.md

    def test_finds_mdx_files(self, tmp_markdown_folder: Path):
        """Test finding .mdx files."""
        files = discover_markdown_files(tmp_markdown_folder)

        mdx_files = [f for f in files if f.suffix == ".mdx"]
        assert len(mdx_files) >= 1  # api.mdx

    def test_recursive_discovery(self, tmp_markdown_folder: Path):
        """Test that nested files are discovered."""
        files = discover_markdown_files(tmp_markdown_folder, recursive=True)

        nested_files = [f for f in files if "advanced" in str(f)]
        assert len(nested_files) >= 2  # config.md, plugins.md

    def test_non_recursive_discovery(self, tmp_markdown_folder: Path):
        """Test non-recursive discovery only finds top-level files."""
        files = discover_markdown_files(tmp_markdown_folder, recursive=False)

        nested_files = [f for f in files if "advanced" in str(f)]
        assert len(nested_files) == 0

    def test_ignores_hidden_directories(self, tmp_markdown_folder: Path):
        """Test that hidden directories are ignored."""
        files = discover_markdown_files(tmp_markdown_folder)

        hidden_files = [f for f in files if ".hidden" in str(f)]
        assert len(hidden_files) == 0

    def test_returns_sorted_paths(self, tmp_markdown_folder: Path):
        """Test that results are sorted."""
        files = discover_markdown_files(tmp_markdown_folder)

        assert files == sorted(files)

    def test_invalid_directory_raises(self, tmp_path: Path):
        """Test that invalid directory raises ValueError."""
        fake_dir = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="Not a directory"):
            discover_markdown_files(fake_dir)

    def test_file_path_raises(self, tmp_markdown_folder: Path):
        """Test that file path raises ValueError."""
        file_path = tmp_markdown_folder / "intro.md"

        with pytest.raises(ValueError, match="Not a directory"):
            discover_markdown_files(file_path)


class TestExtractTitle:
    """Test suite for _extract_title function."""

    def test_extracts_h1_title(self, tmp_path: Path):
        """Test extracting title from H1 header."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# My Great Title\n\nSome content here.")

        title = _extract_title(md_file)
        assert title == "My Great Title"

    def test_extracts_first_h1(self, tmp_path: Path):
        """Test that first H1 is used."""
        md_file = tmp_path / "test.md"
        md_file.write_text("# First Title\n\n# Second Title\n\nContent.")

        title = _extract_title(md_file)
        assert title == "First Title"

    def test_fallback_to_filename(self, tmp_path: Path):
        """Test fallback to filename when no H1."""
        md_file = tmp_path / "getting-started.md"
        md_file.write_text("No title header here.\n\nJust content.")

        title = _extract_title(md_file)
        assert title == "Getting Started"

    def test_filename_underscores(self, tmp_path: Path):
        """Test filename with underscores."""
        md_file = tmp_path / "user_guide_intro.md"
        md_file.write_text("Content without title.")

        title = _extract_title(md_file)
        assert title == "User Guide Intro"

    def test_handles_frontmatter(self, tmp_path: Path):
        """Test that H1 after frontmatter is found."""
        md_file = tmp_path / "test.md"
        content = """---
title: Frontmatter Title
---

# Actual H1 Title

Content here.
"""
        md_file.write_text(content)

        title = _extract_title(md_file)
        assert title == "Actual H1 Title"


class TestDiscoverFromFolder:
    """Test suite for discover_from_folder function."""

    def test_returns_expected_structure(self, tmp_markdown_folder: Path):
        """Test return structure."""
        result = discover_from_folder(str(tmp_markdown_folder))

        assert "discovered" in result
        assert "total" in result
        assert "method" in result
        assert result["method"] == "folder"

    def test_discovers_all_files(self, tmp_markdown_folder: Path):
        """Test all markdown files are discovered."""
        result = discover_from_folder(str(tmp_markdown_folder))

        # 5 files: intro.md, guide.md, api.mdx, advanced/config.md, advanced/plugins.md
        assert result["total"] >= 5
        assert len(result["discovered"]) >= 5

    def test_discovered_items_have_path(self, tmp_markdown_folder: Path):
        """Test discovered items have path field."""
        result = discover_from_folder(str(tmp_markdown_folder))

        for item in result["discovered"]:
            assert "path" in item
            assert item["path"].endswith((".md", ".mdx"))

    def test_discovered_items_have_title(self, tmp_markdown_folder: Path):
        """Test discovered items have title field."""
        result = discover_from_folder(str(tmp_markdown_folder))

        for item in result["discovered"]:
            assert "title" in item
            assert item["title"] is not None

    def test_discovered_items_have_content_hash(self, tmp_markdown_folder: Path):
        """Test discovered items have content_hash field."""
        result = discover_from_folder(str(tmp_markdown_folder))

        for item in result["discovered"]:
            if "error" not in item:
                assert "content_hash" in item
                assert len(item["content_hash"]) == 64  # SHA256 hex length

    def test_include_patterns(self, tmp_markdown_folder: Path):
        """Test include patterns filter results."""
        result = discover_from_folder(
            str(tmp_markdown_folder),
            include_patterns=("*.mdx",),
        )

        # Only api.mdx should match
        assert result["total"] == 1
        assert result["discovered"][0]["path"].endswith(".mdx")

    def test_exclude_patterns(self, tmp_markdown_folder: Path):
        """Test exclude patterns filter results."""
        result = discover_from_folder(
            str(tmp_markdown_folder),
            exclude_patterns=("advanced/*",),
        )

        # Should exclude config.md and plugins.md from advanced/
        for item in result["discovered"]:
            assert "advanced" not in item["path"]

    def test_error_handling(self, tmp_path: Path):
        """Test error handling for unreadable files."""
        docs = tmp_path / "docs"
        docs.mkdir()

        # Create a file that will cause an error in title extraction
        bad_file = docs / "bad.md"
        bad_file.write_bytes(b"\x80\x81\x82")  # Invalid UTF-8

        result = discover_from_folder(str(docs))

        # Should have an error entry
        assert result["total"] == 1
        assert "error" in result["discovered"][0]
