"""
Unit tests for 'map' command (content discovery).

═══════════════════════════════════════════════════════════════════════════════
TEST COVERAGE
═══════════════════════════════════════════════════════════════════════════════

TestMapUrlCommand
────────────────────────────────────────────────────────────────────────────────
  ✓ test_map_url_help - Tests help text
  ✓ test_map_url_dry_run - Tests --dry-run flag
  ✓ test_map_url_with_json_output - Tests --format json


TestMapFolderCommand
────────────────────────────────────────────────────────────────────────────────
  ✓ test_map_folder_help - Tests help text
  ✓ test_map_folder_dry_run - Tests --dry-run flag
  ✓ test_map_folder_with_md_files - Tests folder scanning
  ✓ test_map_folder_nonexistent - Tests error handling
"""

import pytest
from click.testing import CliRunner

from kurt.cli import main

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def runner(mock_http_responses):
    """Create CLI runner with mocked HTTP responses."""
    return CliRunner()


# ============================================================================
# Test: map url
# ============================================================================


class TestMapUrlCommand:
    """Tests for 'map url <url>' command."""

    def test_map_url_help(self, runner):
        """Test map url help text."""
        result = runner.invoke(main, ["content", "map", "url", "--help"])
        assert result.exit_code == 0
        assert "Discover URLs from web sources" in result.output
        assert "--sitemap-path" in result.output
        assert "--include-blogrolls" in result.output
        assert "--dry-run" in result.output

    def test_map_url_dry_run(self, runner):
        """Test --dry-run flag (no DB changes)."""
        result = runner.invoke(main, ["content", "map", "url", "https://example.com", "--dry-run"])
        assert "DRY RUN" in result.output
        assert "Would discover" in result.output
        assert "https://example.com" in result.output

    def test_map_url_with_json_output(self, runner):
        """Test --format json."""
        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--dry-run", "--format", "json"]
        )
        # In dry-run, JSON output isn't generated, but we test the flag is accepted
        assert result.exit_code == 0


# ============================================================================
# Test: map folder
# ============================================================================


class TestMapFolderCommand:
    """Tests for 'map folder <path>' command."""

    def test_map_folder_help(self, runner):
        """Test map folder help text."""
        result = runner.invoke(main, ["content", "map", "folder", "--help"])
        assert result.exit_code == 0
        assert "Discover markdown files from local folder" in result.output
        assert "--include" in result.output
        assert "--exclude" in result.output
        assert "--dry-run" in result.output

    def test_map_folder_nonexistent(self, runner):
        """Test error handling for nonexistent folder."""
        result = runner.invoke(main, ["content", "map", "folder", "/nonexistent/path"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_map_folder_dry_run(self, runner, tmp_path):
        """Test --dry-run flag."""
        # Create a temp folder with some markdown files
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("# Test 1")
        (test_dir / "file2.md").write_text("# Test 2")

        result = runner.invoke(main, ["content", "map", "folder", str(test_dir), "--dry-run"])
        assert "DRY RUN" in result.output
        assert "Would discover" in result.output or "Discovering content from" in result.output

    def test_map_folder_with_md_files(self, runner, tmp_path):
        """Test folder scanning for .md files."""
        # Create a temp folder with markdown files
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("# Test 1")
        (test_dir / "file2.mdx").write_text("# Test 2")
        (test_dir / "readme.txt").write_text("Not markdown")

        result = runner.invoke(main, ["content", "map", "folder", str(test_dir), "--dry-run"])
        assert result.exit_code == 0
        # Should find the .md and .mdx files
        assert "file" in result.output.lower() or "found" in result.output.lower()


"""
Tests for 'map' commands with mocked HTTP responses.

These tests use mocked responses to avoid network calls.
"""


class TestMapUrlWithMockedResponses:
    """Tests for map url command with mocked HTTP responses."""

    def test_map_url_with_mocked_sitemap(self, isolated_cli_runner_with_mocks):
        """Test map url command with mocked sitemap response."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Run map url command (mocks are already active)
        result = runner.invoke(main, ["content", "map", "url", "https://example.com"])

        # Check command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Discovered" in result.output or "pages" in result.output

        # Verify discovery was called
        assert mocks["mock_sitemap"].called

        # Verify documents were created
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()
        assert len(docs) > 0, "Should have created documents"

    def test_map_url_dry_run_no_db_changes(self, isolated_cli_runner_with_mocks):
        """Test that --dry-run makes no database changes."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Get initial doc count
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        initial_count = session.query(Document).count()

        # Run map with --dry-run
        result = runner.invoke(main, ["content", "map", "url", "https://example.com", "--dry-run"])

        # Check command succeeded
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

        # Verify NO documents were created
        final_count = session.query(Document).count()
        assert final_count == initial_count, "Dry run should not create documents"

    def test_map_url_with_include_pattern_mocked(self, isolated_cli_runner_with_mocks):
        """Test map url with --include pattern."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Customize mock to return mixed URLs
        mocks["mock_sitemap"].return_value = [
            "https://example.com/docs/page1",
            "https://example.com/docs/page2",
            "https://example.com/api/reference",  # Should be filtered out
            "https://example.com/blog/post",  # Should be filtered out
        ]

        # Run map with include pattern
        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--include", "*/docs/*"]
        )

        # Check command succeeded
        assert result.exit_code == 0

        # Verify only matching URLs were added
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()

        # Should have only docs matching pattern
        doc_urls = [doc.source_url for doc in docs]
        assert len(doc_urls) > 0, "Should have at least one document"
        assert all(
            "/docs/" in url for url in doc_urls
        ), f"All docs should match /docs/ pattern, got: {doc_urls}"

    def test_map_url_with_max_pages_limit(self, isolated_cli_runner_with_mocks):
        """Test map url respects --max-pages limit."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Mock many URLs
        many_urls = [f"https://example.com/page{i}" for i in range(100)]
        mocks["mock_sitemap"].return_value = many_urls

        # Run map with max-pages=10
        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--max-pages", "10"]
        )

        # Check command succeeded
        assert result.exit_code == 0

        # Verify only max-pages documents were created
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()
        assert len(docs) <= 10, f"Should have at most 10 docs, got {len(docs)}"


class TestMapFolderIntegration:
    """Integration tests for map folder command."""

    def test_map_folder_discovers_markdown_files(self, isolated_cli_runner, tmp_path):
        """Test map folder discovers .md and .mdx files."""
        runner, project_dir = isolated_cli_runner

        # Create test markdown files
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("# File 1")
        (test_dir / "file2.mdx").write_text("# File 2")
        (test_dir / "file3.md").write_text("# File 3")
        (test_dir / "readme.txt").write_text("Not markdown")  # Should be ignored

        # Run map folder
        result = runner.invoke(main, ["content", "map", "folder", str(test_dir)])

        # Check command succeeded
        assert result.exit_code == 0
        assert "Discovered" in result.output or "found" in result.output.lower()

        # Verify only .md and .mdx files were added
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()
        assert len(docs) == 3, f"Should have 3 markdown files, got {len(docs)}"

        # Verify .txt file was not added
        doc_paths = [doc.source_url for doc in docs]
        assert not any("readme.txt" in path for path in doc_paths if path)

    def test_map_folder_with_include_pattern(self, isolated_cli_runner, tmp_path):
        """Test map folder with --include pattern."""
        runner, project_dir = isolated_cli_runner

        # Create test files
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()
        (test_dir / "tutorial.md").write_text("# Tutorial")
        (test_dir / "guide.md").write_text("# Guide")
        (test_dir / "api.md").write_text("# API")

        # Run map folder with pattern
        result = runner.invoke(
            main, ["content", "map", "folder", str(test_dir), "--include", "*tutorial*"]
        )

        # Check command succeeded
        assert result.exit_code == 0

        # Verify only matching file was added
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()
        assert len(docs) == 1, f"Should have 1 matching file, got {len(docs)}"
        assert "tutorial" in (docs[0].source_url or docs[0].content_path or "")

    def test_map_folder_dry_run_no_db_changes(self, isolated_cli_runner, tmp_path):
        """Test that map folder --dry-run makes no database changes."""
        runner, project_dir = isolated_cli_runner

        # Create test file
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("# File 1")

        # Get initial doc count
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        initial_count = session.query(Document).count()

        # Run map folder with --dry-run
        result = runner.invoke(main, ["content", "map", "folder", str(test_dir), "--dry-run"])

        # Check command succeeded
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

        # Verify NO documents were created
        final_count = session.query(Document).count()
        assert final_count == initial_count, "Dry run should not create documents"


# ============================================================================
# Test: URL Mapping with Exclude Patterns
# ============================================================================


class TestMapUrlWithExcludePatterns:
    """Tests for map url command with --exclude option."""

    def test_map_url_with_exclude_patterns(self, isolated_cli_runner_with_mocks):
        """Test --exclude option filters URLs correctly."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Customize mock with mixed URLs
        mocks["mock_sitemap"].return_value = [
            "https://example.com/docs/page1",
            "https://example.com/docs/page2",
            "https://example.com/api/reference",
            "https://example.com/api/guide",
            "https://example.com/blog/post1",
        ]

        # Run map with exclude pattern
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--exclude",
                "*/api/*",
                "--exclude",
                "*/blog/*",
            ],
        )

        # Check command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify only non-matching URLs were added
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()

        # Should only have docs NOT matching exclude patterns
        doc_urls = [doc.source_url for doc in docs]
        assert len(doc_urls) > 0, "Should have at least one document"
        assert all(
            "/docs/" in url for url in doc_urls
        ), f"All docs should match /docs/ pattern, got: {doc_urls}"
        assert not any("/api/" in url for url in doc_urls), "Should not have /api/ URLs"
        assert not any("/blog/" in url for url in doc_urls), "Should not have /blog/ URLs"

    def test_map_url_with_multiple_exclude_patterns(self, isolated_cli_runner_with_mocks):
        """Test multiple --exclude patterns work together."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Customize mock with various URLs
        mocks["mock_sitemap"].return_value = [
            "https://example.com/docs/tutorial.html",
            "https://example.com/docs/reference.html",
            "https://example.com/api/v1/endpoints.html",
            "https://example.com/api/v2/endpoints.html",
            "https://example.com/draft/work-in-progress.html",
            "https://example.com/internal/private.html",
        ]

        # Run map with multiple exclude patterns
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--exclude",
                "*/api/*",
                "--exclude",
                "*/draft/*",
                "--exclude",
                "*/internal/*",
            ],
        )

        # Check command succeeded
        assert result.exit_code == 0

        # Verify only /docs/ URLs were added
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()

        doc_urls = [doc.source_url for doc in docs]
        assert len(doc_urls) == 2, f"Should have 2 docs, got {len(doc_urls)}"
        assert all("/docs/" in url for url in doc_urls)


# ============================================================================
# Test: Folder Mapping with Exclude Patterns
# ============================================================================


class TestMapFolderWithExcludePatterns:
    """Tests for map folder command with --exclude option."""

    def test_map_folder_with_exclude_patterns(self, isolated_cli_runner, tmp_path):
        """Test --exclude option filters files correctly."""
        runner, project_dir = isolated_cli_runner

        # Create test files
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()
        (test_dir / "tutorial.md").write_text("# Tutorial")
        (test_dir / "guide.md").write_text("# Guide")
        (test_dir / "draft-notes.md").write_text("# Draft")
        (test_dir / "wip-feature.md").write_text("# WIP")

        # Run map folder with exclude pattern
        result = runner.invoke(
            main,
            ["content", "map", "folder", str(test_dir), "--exclude", "draft*", "--exclude", "wip*"],
        )

        # Check command succeeded
        assert result.exit_code == 0

        # Verify only non-matching files were added
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()

        assert len(docs) == 2, f"Should have 2 files, got {len(docs)}"

        # Get file names from source URLs
        doc_paths = [doc.source_url or doc.content_path or "" for doc in docs]
        assert any("tutorial" in path for path in doc_paths)
        assert any("guide" in path for path in doc_paths)
        assert not any("draft" in path for path in doc_paths)
        assert not any("wip" in path for path in doc_paths)

    def test_map_folder_with_nested_exclude_patterns(self, isolated_cli_runner, tmp_path):
        """Test --exclude patterns work with nested directories."""
        runner, project_dir = isolated_cli_runner

        # Create nested directory structure
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()

        public_dir = test_dir / "public"
        public_dir.mkdir()
        (public_dir / "doc1.md").write_text("# Doc 1")
        (public_dir / "doc2.md").write_text("# Doc 2")

        private_dir = test_dir / "private"
        private_dir.mkdir()
        (private_dir / "secret1.md").write_text("# Secret 1")
        (private_dir / "secret2.md").write_text("# Secret 2")

        draft_dir = test_dir / "draft"
        draft_dir.mkdir()
        (draft_dir / "wip.md").write_text("# WIP")

        # Run map folder excluding private and draft directories
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "folder",
                str(test_dir),
                "--exclude",
                "private/*",
                "--exclude",
                "draft/*",
            ],
        )

        # Check command succeeded
        assert result.exit_code == 0

        # Verify only public files were added
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()

        assert len(docs) == 2, f"Should have 2 public files, got {len(docs)}"

        doc_paths = [doc.source_url or doc.content_path or "" for doc in docs]
        assert all("public" in path for path in doc_paths)


# ============================================================================
# Test: JSON Output Format
# ============================================================================


class TestMapJsonOutputFormat:
    """Tests for map commands with --format json option."""

    def test_map_url_json_output_format(self, isolated_cli_runner_with_mocks):
        """Test --format json produces valid JSON output."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Run map with JSON format
        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--format", "json"]
        )

        # Check command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Extract JSON from output (may have text before JSON)
        import json
        import re

        # Find JSON in output (starts with { or [)
        json_match = re.search(r"(\{.*\}|\[.*\])", result.output, re.DOTALL)
        if not json_match:
            pytest.fail(f"No JSON found in output: {result.output}")

        json_str = json_match.group(1)

        try:
            output_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nJSON string: {json_str}")

        # Verify JSON structure
        assert "total" in output_data, "JSON should have 'total' field"
        assert "new" in output_data, "JSON should have 'new' field"
        assert "existing" in output_data, "JSON should have 'existing' field"
        assert "method" in output_data, "JSON should have 'method' field"
        assert "discovered" in output_data, "JSON should have 'discovered' field"

        # Verify counts
        assert output_data["total"] == 3
        assert output_data["new"] == 3
        assert output_data["existing"] == 0
        assert output_data["method"] == "sitemap"

        # Verify discovered list structure
        assert isinstance(output_data["discovered"], list)
        assert len(output_data["discovered"]) == 3

    def test_map_folder_json_output_format(self, isolated_cli_runner, tmp_path):
        """Test map folder --format json produces valid JSON output."""
        runner, project_dir = isolated_cli_runner

        # Create test files
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("# File 1")
        (test_dir / "file2.md").write_text("# File 2")

        # Run map folder with JSON format and wider terminal to avoid line wrapping
        result = runner.invoke(
            main,
            ["content", "map", "folder", str(test_dir), "--format", "json"],
            env={"COLUMNS": "500"},
        )  # Set wide terminal width to prevent line wrapping

        # Check command succeeded
        assert result.exit_code == 0

        # Extract JSON from output
        import json
        import re

        # Find the start of JSON (first { or [)
        json_start = -1
        for i, char in enumerate(result.output):
            if char in ["{", "["]:
                json_start = i
                break

        if json_start == -1:
            pytest.fail(f"No JSON found in output: {result.output}")

        # Get everything from the JSON start to the end
        json_str = result.output[json_start:]

        # Remove ANSI color codes and other escape sequences
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        json_str = ansi_escape.sub("", json_str)

        try:
            output_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\nJSON string: {json_str[:500]}")

        # Verify JSON structure
        assert "total" in output_data
        assert "new" in output_data
        assert "existing" in output_data
        assert "discovered" in output_data

        # Verify counts
        assert output_data["total"] == 2
        assert output_data["new"] == 2

        # Verify discovered list
        assert isinstance(output_data["discovered"], list)
        assert len(output_data["discovered"]) == 2

    def test_map_url_json_output_with_existing_docs(self, isolated_cli_runner_with_mocks):
        """Test JSON output correctly reports new vs existing documents."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # First run - all new
        result1 = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--format", "json"]
        )
        assert result1.exit_code == 0

        import json
        import re

        # Extract JSON from first run
        json_match1 = re.search(r"(\{.*\}|\[.*\])", result1.output, re.DOTALL)
        assert json_match1, f"No JSON in first output: {result1.output}"
        output1 = json.loads(json_match1.group(1))

        assert output1["new"] == 3
        assert output1["existing"] == 0

        # Second run - all existing
        result2 = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--format", "json"]
        )
        assert result2.exit_code == 0

        # Extract JSON from second run
        json_match2 = re.search(r"(\{.*\}|\[.*\])", result2.output, re.DOTALL)
        assert json_match2, f"No JSON in second output: {result2.output}"
        output2 = json.loads(json_match2.group(1))

        assert output2["new"] == 0
        assert output2["existing"] == 3
        assert output2["total"] == 3


# ============================================================================
# Test: Blogroll Extraction (with LLM mocking)
# ============================================================================


class TestMapUrlWithBlogrollExtraction:
    """Tests for map url command with --include-blogrolls option."""

    def test_map_url_with_include_blogrolls_extraction(self, isolated_cli_runner_with_mocks):
        """Test actual blogroll extraction (with mocked LLM)."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Customize mocks for blogroll scenario
        sitemap_urls = [
            "https://example.com/blog",
            "https://example.com/blog/post1",
            "https://example.com/blog/post2",
        ]
        mocks["mock_sitemap"].return_value = sitemap_urls

        # Mock identify_blogroll_candidates to return blog index
        blogroll_candidates = [
            {
                "url": "https://example.com/blog",
                "type": "blog_index",
                "priority": 10,
                "reasoning": "Main blog index",
            }
        ]
        mocks["mock_blogroll"].return_value = blogroll_candidates

        # Mock extract_chronological_content to return blog posts
        from datetime import datetime

        extracted_posts = [
            {
                "url": "https://example.com/blog/post-from-blogroll-1",
                "title": "Post 1 from Blogroll",
                "date": datetime(2024, 1, 1),
                "excerpt": "First post excerpt",
            },
            {
                "url": "https://example.com/blog/post-from-blogroll-2",
                "title": "Post 2 from Blogroll",
                "date": datetime(2024, 1, 2),
                "excerpt": "Second post excerpt",
            },
        ]
        mocks["mock_extract"].return_value = extracted_posts

        # Run map with blogroll extraction enabled
        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--include-blogrolls"]
        )

        # Check command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify LLM functions were called
        assert mocks["mock_blogroll"].called, "Should call identify_blogroll_candidates"
        assert mocks["mock_extract"].called, "Should call extract_chronological_content"

        # Verify documents were created (sitemap + blogroll posts)
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()

        # Should have sitemap docs (3) + blogroll-extracted posts (2)
        assert len(docs) >= 2, f"Should have at least 2 blogroll-extracted posts, got {len(docs)}"

        # Check that some docs have blogroll discovery metadata
        blogroll_docs = [doc for doc in docs if doc.discovery_method == "blogroll"]
        assert len(blogroll_docs) >= 2, "Should have at least 2 docs discovered via blogroll"

        # Verify chronological flag is set
        assert any(
            doc.is_chronological for doc in blogroll_docs
        ), "Blogroll docs should have is_chronological=True"

    def test_map_url_blogroll_extraction_with_json_output(self, isolated_cli_runner_with_mocks):
        """Test blogroll extraction with JSON output format."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        sitemap_urls = ["https://example.com/blog"]
        mocks["mock_sitemap"].return_value = sitemap_urls

        blogroll_candidates = [
            {
                "url": "https://example.com/blog",
                "type": "blog_index",
                "priority": 10,
                "reasoning": "Main blog index",
            }
        ]
        mocks["mock_blogroll"].return_value = blogroll_candidates

        from datetime import datetime

        extracted_posts = [
            {
                "url": "https://example.com/blog/extracted-post",
                "title": "Extracted Post",
                "date": datetime(2024, 1, 1),
                "excerpt": "Post excerpt",
            },
        ]
        mocks["mock_extract"].return_value = extracted_posts

        # Run with JSON output and blogroll extraction
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--include-blogrolls",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0

        # Extract JSON from output
        import json
        import re

        json_match = re.search(r"(\{.*\}|\[.*\])", result.output, re.DOTALL)
        assert json_match, f"No JSON found in output: {result.output}"
        output_data = json.loads(json_match.group(1))

        assert "total" in output_data
        assert "discovered" in output_data
        assert isinstance(output_data["discovered"], list)

        # Should have both sitemap and blogroll-extracted docs
        assert output_data["total"] >= 1

    def test_map_url_blogroll_no_candidates_found(self, isolated_cli_runner_with_mocks):
        """Test blogroll extraction when no candidates are found."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        sitemap_urls = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]
        mocks["mock_sitemap"].return_value = sitemap_urls
        mocks["mock_blogroll"].return_value = []  # No candidates found

        # Run with blogroll extraction
        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--include-blogrolls"]
        )

        # Should still succeed, just without blogroll extraction
        assert result.exit_code == 0

        # Verify only sitemap docs were created
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()
        assert len(docs) == 2


# ============================================================================
# Test: Edge Cases and Error Handling
# ============================================================================


class TestMapEdgeCases:
    """Tests for edge cases and error handling in map commands."""

    def test_map_url_with_conflicting_include_exclude(self, isolated_cli_runner_with_mocks):
        """Test behavior when include and exclude patterns conflict."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        mocks["mock_sitemap"].return_value = [
            "https://example.com/docs/api/reference",
            "https://example.com/docs/guide",
            "https://example.com/blog/post",
        ]

        # Include */docs/* but exclude */api/*
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--include",
                "*/docs/*",
                "--exclude",
                "*/api/*",
            ],
        )

        assert result.exit_code == 0

        # Should only have /docs/ URLs that don't match /api/
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()

        doc_urls = [doc.source_url for doc in docs]
        assert len(doc_urls) == 1, f"Should have 1 doc, got {len(doc_urls)}: {doc_urls}"
        assert "guide" in doc_urls[0]

    def test_map_folder_with_no_matching_files(self, isolated_cli_runner, tmp_path):
        """Test map folder when no files match the patterns."""
        runner, project_dir = isolated_cli_runner

        # Create test files
        test_dir = tmp_path / "test_docs"
        test_dir.mkdir()
        (test_dir / "file1.md").write_text("# File 1")
        (test_dir / "file2.md").write_text("# File 2")

        # Use include pattern that matches nothing
        result = runner.invoke(
            main, ["content", "map", "folder", str(test_dir), "--include", "nonexistent*"]
        )

        # Should succeed but find no files
        assert result.exit_code == 0

        # Verify no documents were created
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()
        assert len(docs) == 0, "Should have no documents"

    def test_map_url_empty_sitemap_response(self, isolated_cli_runner_with_mocks):
        """Test map url when sitemap returns no URLs."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        mocks["mock_sitemap"].return_value = []  # Empty sitemap

        result = runner.invoke(main, ["content", "map", "url", "https://example.com"])

        # Should succeed but find no pages
        assert result.exit_code == 0

        # Verify no documents were created
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        docs = session.query(Document).all()
        assert len(docs) == 0


# ============================================================================
# Test: New CLI options (--max-depth, --allow-external, --sitemap-path)
# ============================================================================


class TestMapNewOptions:
    """Tests for newly implemented CLI options."""

    def test_map_url_max_depth_option_accepted(self, runner):
        """Test that --max-depth option is accepted by CLI."""
        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--max-depth", "3", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_map_url_allow_external_option_accepted(self, runner):
        """Test that --allow-external option is accepted by CLI."""
        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--allow-external", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_map_url_sitemap_path_option_accepted(self, runner):
        """Test that --sitemap-path option is accepted by CLI."""
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--sitemap-path",
                "/custom-sitemap.xml",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_map_url_combined_options(self, runner):
        """Test multiple new options together."""
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--max-depth",
                "5",
                "--allow-external",
                "--sitemap-path",
                "/sitemap.xml",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_map_url_help_shows_new_options(self, runner):
        """Test that help text includes new options."""
        result = runner.invoke(main, ["content", "map", "url", "--help"])
        assert result.exit_code == 0
        assert "--max-depth" in result.output
        assert "--allow-external" in result.output
        assert "--sitemap-path" in result.output


# ============================================================================
# Test: Crawling functionality with mocked responses
# ============================================================================


class TestMapCrawlingFunctionality:
    """Tests for web crawling with --max-depth and --allow-external."""

    def test_crawl_fallback_when_no_sitemap(self, isolated_cli_runner_with_mocks):
        """Test that crawler is used as fallback when sitemap fails and max_depth is specified."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Mock sitemap to fail
        mocks["mock_sitemap"].side_effect = ValueError("No sitemap found")
        mocks["mock_crawler"].return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--max-depth", "2", "--dry-run"]
        )

        # Should succeed using crawler
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Would discover 3" in result.output or "3" in result.output

        # Verify crawler was called
        mocks["mock_crawler"].assert_called_once()
        call_kwargs = mocks["mock_crawler"].call_args[1]
        assert call_kwargs["homepage"] == "https://example.com"
        assert call_kwargs["max_depth"] == 2

    def test_crawl_respects_max_depth(self, isolated_cli_runner_with_mocks):
        """Test that max_depth parameter is passed to crawler correctly."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        mocks["mock_sitemap"].side_effect = ValueError("No sitemap found")
        mocks["mock_crawler"].return_value = ["https://example.com/page1"]

        result = runner.invoke(
            main, ["content", "map", "url", "https://example.com", "--max-depth", "5", "--dry-run"]
        )

        assert result.exit_code == 0

        # Verify max_depth was passed correctly
        call_kwargs = mocks["mock_crawler"].call_args[1]
        assert call_kwargs["max_depth"] == 5

    def test_crawl_respects_allow_external(self, isolated_cli_runner_with_mocks):
        """Test that allow_external parameter filters external links."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        mocks["mock_sitemap"].side_effect = ValueError("No sitemap found")
        mocks["mock_crawler"].return_value = [
            "https://example.com/page1",
            "https://external.com/page2",  # External
        ]

        # Test with allow_external=True
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--max-depth",
                "2",
                "--allow-external",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

        # Verify allow_external was passed
        call_kwargs = mocks["mock_crawler"].call_args[1]
        assert call_kwargs["allow_external"] is True

    def test_crawl_without_max_depth_falls_back_to_single_url(self, isolated_cli_runner_with_mocks):
        """Test that without max_depth, sitemap failure falls back to single URL (no crawler)."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        mocks["mock_sitemap"].side_effect = ValueError("No sitemap found")
        mocks["mock_crawler"].return_value = []

        # Without --max-depth, should fall back to single URL
        result = runner.invoke(main, ["content", "map", "url", "https://example.com", "--dry-run"])

        # Should succeed with single URL fallback
        assert result.exit_code == 0
        assert "Would discover: 1 page(s)" in result.output or "1 pages" in result.output

        # Crawler should NOT have been called (no max_depth)
        mocks["mock_crawler"].assert_not_called()

    def test_crawl_applies_include_exclude_patterns(self, isolated_cli_runner_with_mocks):
        """Test that include/exclude patterns are passed to crawler."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        mocks["mock_sitemap"].side_effect = ValueError("No sitemap found")
        mocks["mock_crawler"].return_value = ["https://example.com/docs/page1"]

        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--max-depth",
                "2",
                "--include",
                "*/docs/*",
                "--exclude",
                "*/api/*",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

        # Verify patterns were passed
        call_kwargs = mocks["mock_crawler"].call_args[1]
        assert "*/docs/*" in call_kwargs["include_patterns"]
        assert "*/api/*" in call_kwargs["exclude_patterns"]

    def test_sitemap_preferred_over_crawling(self, isolated_cli_runner_with_mocks):
        """Test that sitemap is tried first, crawler only used on failure."""
        runner, project_dir, mocks = isolated_cli_runner_with_mocks

        # Sitemap succeeds (default mock already returns URLs)
        result = runner.invoke(
            main,
            [
                "content",
                "map",
                "url",
                "https://example.com",
                "--max-depth",
                "2",  # max_depth provided but shouldn't be used
                "--dry-run",
            ],
        )

        assert result.exit_code == 0

        # Sitemap should have been called
        mocks["mock_sitemap"].assert_called_once()

        # Crawler should NOT have been called (sitemap succeeded)
        mocks["mock_crawler"].assert_not_called()
