"""Tests for fetch utilities including content storage."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from kurt.workflows.fetch.models import FetchStatus
from kurt.workflows.fetch.utils import _deduplicate_images, _preprocess_html_for_images
from kurt.workflows.fetch.workflow import _has_embedding_api_key


class TestDeduplicateImages:
    """Test suite for _deduplicate_images."""

    def test_removes_consecutive_duplicate_images(self):
        """Test that consecutive duplicate images are removed."""
        content = """# Title

Some text.

![](https://example.com/image1.png)

![](https://example.com/image1.png)

More text."""

        result = _deduplicate_images(content)

        assert result.count("![](https://example.com/image1.png)") == 1
        assert "Some text." in result
        assert "More text." in result

    def test_keeps_different_images(self):
        """Test that different images are all kept."""
        content = """# Title

![](https://example.com/image1.png)

![](https://example.com/image2.png)

![](https://example.com/image3.png)"""

        result = _deduplicate_images(content)

        assert result.count("![](https://example.com/image1.png)") == 1
        assert result.count("![](https://example.com/image2.png)") == 1
        assert result.count("![](https://example.com/image3.png)") == 1

    def test_allows_same_image_in_different_sections(self):
        """Test that the same image can appear in different sections."""
        content = """# Section 1

![](https://example.com/image1.png)

Some text between sections.

# Section 2

![](https://example.com/image1.png)"""

        result = _deduplicate_images(content)

        # Image should appear twice because there's text between them
        assert result.count("![](https://example.com/image1.png)") == 2

    def test_handles_images_with_alt_text(self):
        """Test images with alt text are deduplicated by URL."""
        content = """![Alt 1](https://example.com/image.png)

![Alt 2](https://example.com/image.png)"""

        result = _deduplicate_images(content)

        # Only first image should remain
        assert "![Alt 1](https://example.com/image.png)" in result
        assert "![Alt 2](https://example.com/image.png)" not in result

    def test_handles_empty_content(self):
        """Test empty content is handled."""
        result = _deduplicate_images("")
        assert result == ""

    def test_handles_no_images(self):
        """Test content without images is unchanged."""
        content = """# Title

Just some text.

More text."""

        result = _deduplicate_images(content)
        assert result == content

    def test_preserves_blank_lines(self):
        """Test that blank lines are preserved."""
        content = """# Title


![](https://example.com/image.png)


Text."""

        result = _deduplicate_images(content)

        # Should preserve the blank lines structure
        assert "\n\n" in result


class TestPreprocessHtmlForImages:
    """Test suite for _preprocess_html_for_images."""

    def test_unwraps_captioned_image_container(self):
        """Test that captioned-image-container divs are unwrapped."""
        html = """<html><body>
<div class="captioned-image-container">
<figure><img src="test.png"></figure>
</div>
</body></html>"""

        result = _preprocess_html_for_images(html)

        # The figure should still be present but not wrapped in the container div
        assert "<figure>" in result
        assert "captioned-image-container" not in result

    def test_unwraps_image_container(self):
        """Test that image-container divs are unwrapped."""
        html = """<html><body>
<div class="image-container">
<img src="test.png">
</div>
</body></html>"""

        result = _preprocess_html_for_images(html)

        assert "<img" in result
        assert "image-container" not in result

    def test_unwraps_img_container(self):
        """Test that img-container divs are unwrapped."""
        html = """<html><body>
<div class="img-container">
<img src="test.png">
</div>
</body></html>"""

        result = _preprocess_html_for_images(html)

        assert "<img" in result
        assert "img-container" not in result

    def test_preserves_other_divs(self):
        """Test that other divs are not affected."""
        html = """<html><body>
<div class="content-wrapper">
<p>Hello</p>
</div>
</body></html>"""

        result = _preprocess_html_for_images(html)

        assert "content-wrapper" in result
        assert "<p>Hello</p>" in result

    def test_handles_nested_containers(self):
        """Test handling of nested container divs."""
        html = """<html><body>
<div class="captioned-image-container">
<div class="image-container">
<img src="test.png">
</div>
</div>
</body></html>"""

        result = _preprocess_html_for_images(html)

        assert "<img" in result
        assert "captioned-image-container" not in result
        assert "image-container" not in result

    def test_handles_plain_text_gracefully(self):
        """Test that plain text is handled without error."""
        html = "not valid html at all {{{"

        result = _preprocess_html_for_images(html)

        # lxml will parse even invalid HTML, just verify no error and content preserved
        assert "not valid html at all {{{" in result

    def test_handles_empty_html(self):
        """Test empty HTML is handled."""
        result = _preprocess_html_for_images("")

        # lxml may return a minimal structure or empty
        # Just verify it doesn't raise
        assert result is not None

    def test_preserves_figure_content(self):
        """Test that figure content including img is preserved."""
        html = """<html><body>
<div class="captioned-image-container">
<figure>
<a href="full.png">
<img src="thumb.png" alt="Test">
</a>
<figcaption>Caption text</figcaption>
</figure>
</div>
</body></html>"""

        result = _preprocess_html_for_images(html)

        assert "<figure>" in result
        assert 'src="thumb.png"' in result
        assert "<figcaption>" in result
        assert "Caption text" in result


class TestGenerateContentPath:
    """Test suite for generate_content_path."""

    def test_generates_sharded_path(self):
        """Test that path uses 2-level hash prefix."""
        from kurt.workflows.fetch.utils import generate_content_path

        path = generate_content_path("doc-123")

        # Should have format: xx/yy/filename.md
        parts = path.split("/")
        assert len(parts) == 3
        assert len(parts[0]) == 2  # First hash prefix
        assert len(parts[1]) == 2  # Second hash prefix
        assert parts[2].endswith(".md")

    def test_same_id_produces_same_path(self):
        """Test deterministic path generation."""
        from kurt.workflows.fetch.utils import generate_content_path

        path1 = generate_content_path("document-abc")
        path2 = generate_content_path("document-abc")

        assert path1 == path2

    def test_different_ids_produce_different_paths(self):
        """Test different IDs get different paths."""
        from kurt.workflows.fetch.utils import generate_content_path

        path1 = generate_content_path("doc-1")
        path2 = generate_content_path("doc-2")

        assert path1 != path2

    def test_sanitizes_special_characters(self):
        """Test that special chars are replaced."""
        from kurt.workflows.fetch.utils import generate_content_path

        path = generate_content_path("https://example.com/page?query=1")

        # Should not contain problematic characters
        filename = path.split("/")[-1]
        assert "/" not in filename.replace(".md", "")
        assert ":" not in filename
        assert "?" not in filename

    def test_truncates_long_ids(self):
        """Test that very long IDs are truncated."""
        from kurt.workflows.fetch.utils import generate_content_path

        long_id = "x" * 200
        path = generate_content_path(long_id)

        filename = path.split("/")[-1]
        # Should be truncated to 100 chars + .md
        assert len(filename) <= 103  # 100 + ".md"

    def test_url_based_path(self):
        """Test URL-based path generation."""
        from kurt.workflows.fetch.utils import generate_content_path

        path = generate_content_path("doc-id", "https://example.com/blog/post")
        assert path == "example.com/blog/post.md"

    def test_url_based_path_with_subdomain(self):
        """Test URL path preserves subdomain."""
        from kurt.workflows.fetch.utils import generate_content_path

        path = generate_content_path("doc-id", "https://sub.domain.com/a/b/c")
        assert path == "sub.domain.com/a/b/c.md"

    def test_url_based_path_root(self):
        """Test URL path for root URL."""
        from kurt.workflows.fetch.utils import generate_content_path

        path = generate_content_path("doc-id", "https://example.com/")
        assert path == "example.com/index.md"

    def test_url_based_path_strips_html_extension(self):
        """Test URL path strips .html extension."""
        from kurt.workflows.fetch.utils import generate_content_path

        path = generate_content_path("doc-id", "https://example.com/page.html")
        assert path == "example.com/page.md"

    def test_url_based_path_strips_query_params(self):
        """Test URL path ignores query parameters."""
        from kurt.workflows.fetch.utils import generate_content_path

        path = generate_content_path("doc-id", "https://example.com/page?q=1&x=2")
        assert path == "example.com/page.md"

    def test_url_based_path_sanitizes_special_chars(self):
        """Test URL path sanitizes special characters."""
        from kurt.workflows.fetch.utils import generate_content_path

        path = generate_content_path("doc-id", "https://example.com/path with spaces/file%20name")
        # Spaces and % become underscores
        assert "example.com/" in path
        assert path.endswith(".md")
        assert " " not in path
        assert "%" not in path


class TestSaveContentFile:
    """Test suite for save_content_file."""

    @patch("kurt.workflows.fetch.utils.load_config")
    def test_saves_content_to_file(self, mock_load_config):
        """Test content is saved to correct location."""
        from kurt.workflows.fetch.utils import save_content_file

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            relative_path = save_content_file("doc-123", "# Test Content\n\nHello world!")

            # Verify file was created
            full_path = Path(tmpdir) / relative_path
            assert full_path.exists()
            assert full_path.read_text() == "# Test Content\n\nHello world!"

    @patch("kurt.workflows.fetch.utils.load_config")
    def test_creates_directories(self, mock_load_config):
        """Test that parent directories are created."""
        from kurt.workflows.fetch.utils import save_content_file

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            relative_path = save_content_file("new-doc", "Content")

            full_path = Path(tmpdir) / relative_path
            assert full_path.exists()
            assert full_path.parent.exists()

    @patch("kurt.workflows.fetch.utils.load_config")
    def test_returns_relative_path(self, mock_load_config):
        """Test that returned path is relative."""
        from kurt.workflows.fetch.utils import save_content_file

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            relative_path = save_content_file("doc-456", "Content")

            # Should not be absolute
            assert not relative_path.startswith("/")
            assert not relative_path.startswith(tmpdir)

    @patch("kurt.workflows.fetch.utils.load_config")
    def test_handles_unicode_content(self, mock_load_config):
        """Test saving unicode content."""
        from kurt.workflows.fetch.utils import save_content_file

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            content = "# 日本語\n\nEmoji: 🎉"
            relative_path = save_content_file("unicode-doc", content)

            full_path = Path(tmpdir) / relative_path
            assert full_path.read_text(encoding="utf-8") == content


class TestLoadDocumentContent:
    """Test suite for load_document_content."""

    @patch("kurt.workflows.fetch.utils.load_config")
    def test_loads_existing_file(self, mock_load_config):
        """Test loading content from existing file."""
        from kurt.workflows.fetch.utils import load_document_content

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            # Create a file
            test_path = Path(tmpdir) / "ab" / "cd" / "test.md"
            test_path.parent.mkdir(parents=True)
            test_path.write_text("# Loaded Content")

            content = load_document_content("ab/cd/test.md")

            assert content == "# Loaded Content"

    @patch("kurt.workflows.fetch.utils.load_config")
    def test_returns_none_for_missing_file(self, mock_load_config):
        """Test returns None when file doesn't exist."""
        from kurt.workflows.fetch.utils import load_document_content

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            content = load_document_content("nonexistent/path/file.md")

            assert content is None

    @patch("kurt.workflows.fetch.utils.load_config")
    def test_roundtrip_save_and_load(self, mock_load_config):
        """Test saving and loading produces same content."""
        from kurt.workflows.fetch.utils import load_document_content, save_content_file

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            original_content = "# Test\n\nThis is a test document with multiple paragraphs."
            relative_path = save_content_file("roundtrip-doc", original_content)

            loaded_content = load_document_content(relative_path)

            assert loaded_content == original_content


class TestHasEmbeddingApiKey:
    """Test suite for _has_embedding_api_key."""

    def test_returns_true_with_openai_key(self):
        """Test returns True when OPENAI_API_KEY is set."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key"}, clear=True):
            assert _has_embedding_api_key() is True

    def test_returns_true_with_anthropic_key(self):
        """Test returns True when ANTHROPIC_API_KEY is set."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True):
            assert _has_embedding_api_key() is True

    def test_returns_true_with_cohere_key(self):
        """Test returns True when COHERE_API_KEY is set."""
        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}, clear=True):
            assert _has_embedding_api_key() is True

    def test_returns_true_with_voyage_key(self):
        """Test returns True when VOYAGE_API_KEY is set."""
        with patch.dict("os.environ", {"VOYAGE_API_KEY": "test-key"}, clear=True):
            assert _has_embedding_api_key() is True

    def test_returns_false_without_any_key(self):
        """Test returns False when no API keys are set."""
        with patch.dict("os.environ", {}, clear=True):
            assert _has_embedding_api_key() is False

    def test_returns_false_with_empty_key(self):
        """Test returns False when key is empty string."""
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=True):
            assert _has_embedding_api_key() is False

    def test_returns_true_with_multiple_keys(self):
        """Test returns True when multiple keys are set."""
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "sk-ant"},
            clear=True,
        ):
            assert _has_embedding_api_key() is True


class TestSaveContentStep:
    """Test suite for save_content_step."""

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_saves_fetched_content(self, mock_save_file):
        """Test that fetched content is saved to file."""
        from kurt.workflows.fetch.steps import save_content_step

        mock_save_file.return_value = "ab/cd/doc-1.md"

        rows = [
            {
                "document_id": "doc-1",
                "status": FetchStatus.SUCCESS,
                "content": "# Test Content",
            }
        ]
        config = {"dry_run": False, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        mock_save_file.assert_called_once_with("doc-1", "# Test Content", None)
        assert result[0]["content_path"] == "ab/cd/doc-1.md"
        assert "content" not in result[0]  # Content should be removed

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_skips_error_documents(self, mock_save_file):
        """Test that error documents are skipped."""
        from kurt.workflows.fetch.steps import save_content_step

        rows = [
            {
                "document_id": "doc-error",
                "status": FetchStatus.ERROR,
                "content": None,
                "error": "Failed to fetch",
            }
        ]
        config = {"dry_run": False, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        mock_save_file.assert_not_called()
        assert result[0]["content_path"] is None

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_dry_run_skips_saving(self, mock_save_file):
        """Test that dry_run mode doesn't save files."""
        from kurt.workflows.fetch.steps import save_content_step

        rows = [
            {
                "document_id": "doc-1",
                "status": FetchStatus.SUCCESS,
                "content": "# Test Content",
            }
        ]
        config = {"dry_run": True, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        mock_save_file.assert_not_called()
        assert result[0]["content_path"] is None
        # Content should still be present in dry_run for inspection
        assert result[0].get("content") == "# Test Content"

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_handles_multiple_documents(self, mock_save_file):
        """Test processing multiple documents."""
        from kurt.workflows.fetch.steps import save_content_step

        mock_save_file.side_effect = ["ab/cd/doc-1.md", "ef/gh/doc-2.md"]

        rows = [
            {
                "document_id": "doc-1",
                "status": FetchStatus.SUCCESS,
                "content": "Content 1",
            },
            {
                "document_id": "doc-2",
                "status": FetchStatus.SUCCESS,
                "content": "Content 2",
            },
        ]
        config = {"dry_run": False, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        assert len(result) == 2
        assert result[0]["content_path"] == "ab/cd/doc-1.md"
        assert result[1]["content_path"] == "ef/gh/doc-2.md"

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_handles_save_error(self, mock_save_file):
        """Test that save errors are handled gracefully."""
        from kurt.workflows.fetch.steps import save_content_step

        mock_save_file.side_effect = IOError("Disk full")

        rows = [
            {
                "document_id": "doc-1",
                "status": FetchStatus.SUCCESS,
                "content": "# Test Content",
            }
        ]
        config = {"dry_run": False, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        # Should not raise, but content_path should be None
        assert result[0]["content_path"] is None
        assert "content" not in result[0]

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_skips_documents_without_content(self, mock_save_file):
        """Test that documents without content are skipped."""
        from kurt.workflows.fetch.steps import save_content_step

        rows = [
            {
                "document_id": "doc-empty",
                "status": FetchStatus.SUCCESS,
                "content": None,
            },
            {
                "document_id": "doc-empty-string",
                "status": FetchStatus.SUCCESS,
                "content": "",
            },
        ]
        config = {"dry_run": False, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        mock_save_file.assert_not_called()
        assert result[0]["content_path"] is None
        assert result[1]["content_path"] is None

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_handles_status_as_string_value(self, mock_save_file):
        """Test that save_content_step handles status as string (after serialization).

        This is critical because _serialize_rows converts FetchStatus enum to string,
        and subsequent steps receive serialized rows with string status values.
        """
        from kurt.workflows.fetch.steps import save_content_step

        mock_save_file.return_value = "ab/cd/doc-1.md"

        # Status is string "SUCCESS" instead of FetchStatus.SUCCESS
        rows = [
            {
                "document_id": "doc-1",
                "status": "SUCCESS",  # String, not enum
                "content": "# Test Content",
            }
        ]
        config = {"dry_run": False, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        # Should still save content because "SUCCESS" == FetchStatus.SUCCESS.value
        mock_save_file.assert_called_once_with("doc-1", "# Test Content", None)
        assert result[0]["content_path"] == "ab/cd/doc-1.md"


class TestEmbeddingStepStatusHandling:
    """Tests for embedding_step status handling after serialization."""

    @patch("kurt.workflows.fetch.steps.load_document_content")
    @patch("kurt.workflows.fetch.steps.generate_embeddings")
    @patch("kurt.workflows.fetch.steps.embedding_to_bytes")
    def test_handles_status_as_string_value(
        self, mock_embed_bytes, mock_gen_embed, mock_load_content
    ):
        """Test that embedding_step handles status as string (after serialization).

        This is critical because _serialize_rows converts FetchStatus enum to string,
        and embedding_step receives serialized rows with string status values.
        """
        from kurt.workflows.fetch.steps import embedding_step

        mock_load_content.return_value = "Test content for embedding"
        mock_gen_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_embed_bytes.return_value = b"embedding_bytes"

        # Status is string "SUCCESS" instead of FetchStatus.SUCCESS
        rows = [
            {
                "document_id": "doc-1",
                "status": "SUCCESS",  # String, not enum
                "content_path": "ab/cd/doc-1.md",
            }
        ]
        config = {"embedding_max_chars": 1000, "embedding_batch_size": 100}

        result = embedding_step(rows, config)

        # Should generate embeddings because "SUCCESS" == FetchStatus.SUCCESS.value
        mock_load_content.assert_called_once()
        mock_gen_embed.assert_called_once()
        assert result[0]["embedding"] == b"embedding_bytes"

    @patch("kurt.workflows.fetch.steps.load_document_content")
    @patch("kurt.workflows.fetch.steps.generate_embeddings")
    def test_skips_error_status_string(self, mock_gen_embed, mock_load_content):
        """Test that embedding_step skips rows with ERROR status as string."""
        from kurt.workflows.fetch.steps import embedding_step

        rows = [
            {
                "document_id": "doc-error",
                "status": "ERROR",  # String ERROR status
                "content_path": None,
            }
        ]
        config = {"embedding_max_chars": 1000, "embedding_batch_size": 100}

        result = embedding_step(rows, config)

        # Should not generate embeddings for error rows
        mock_load_content.assert_not_called()
        mock_gen_embed.assert_not_called()
        assert result[0]["embedding"] is None


class TestFetchSingleDocument:
    """Tests for _fetch_single_document including source_url passthrough."""

    @patch("kurt.workflows.fetch.steps.fetch_from_web")
    def test_returns_source_url_on_success(self, mock_fetch_web):
        """Test that source_url is included in success response."""
        from kurt.workflows.fetch.config import FetchConfig
        from kurt.workflows.fetch.steps import _fetch_single_document

        mock_fetch_web.return_value = {
            "https://example.com/page": ("# Content", {"fingerprint": "abc123"})
        }

        doc = {
            "document_id": "doc-1",
            "source_url": "https://example.com/page",
            "source_type": "url",
        }
        config = FetchConfig(fetch_engine="trafilatura")

        result = _fetch_single_document(doc, config)

        assert result["source_url"] == "https://example.com/page"
        assert result["status"] == FetchStatus.SUCCESS

    @patch("kurt.workflows.fetch.steps.fetch_from_web")
    def test_returns_source_url_on_error(self, mock_fetch_web):
        """Test that source_url is included in error response."""
        from kurt.workflows.fetch.config import FetchConfig
        from kurt.workflows.fetch.steps import _fetch_single_document

        mock_fetch_web.return_value = {
            "https://example.com/broken": ValueError("Connection failed")
        }

        doc = {
            "document_id": "doc-1",
            "source_url": "https://example.com/broken",
            "source_type": "url",
        }
        config = FetchConfig(fetch_engine="trafilatura")

        result = _fetch_single_document(doc, config)

        assert result["source_url"] == "https://example.com/broken"
        assert result["status"] == FetchStatus.ERROR


class TestFetchBatchWebDocuments:
    """Tests for _fetch_batch_web_documents including source_url passthrough."""

    @patch("kurt.workflows.fetch.steps.DBOS")
    @patch("kurt.workflows.fetch.steps.fetch_from_web")
    def test_returns_source_url_on_success(self, mock_fetch_web, mock_dbos):
        """Test that source_url is included in batch success responses."""
        from kurt.workflows.fetch.config import FetchConfig
        from kurt.workflows.fetch.steps import _fetch_batch_web_documents

        mock_fetch_web.return_value = {
            "https://example.com/page1": ("# Page 1", {"fingerprint": "abc"}),
            "https://example.com/page2": ("# Page 2", {"fingerprint": "def"}),
        }

        docs = [
            {"document_id": "doc-1", "source_url": "https://example.com/page1"},
            {"document_id": "doc-2", "source_url": "https://example.com/page2"},
        ]
        config = FetchConfig(fetch_engine="trafilatura")

        results = _fetch_batch_web_documents(docs, config)

        assert len(results) == 2
        # Find results by document_id
        result1 = next(r for r in results if r["document_id"] == "doc-1")
        result2 = next(r for r in results if r["document_id"] == "doc-2")

        assert result1["source_url"] == "https://example.com/page1"
        assert result1["status"] == FetchStatus.SUCCESS
        assert result2["source_url"] == "https://example.com/page2"
        assert result2["status"] == FetchStatus.SUCCESS

    @patch("kurt.workflows.fetch.steps.DBOS")
    @patch("kurt.workflows.fetch.steps.fetch_from_web")
    def test_returns_source_url_on_error(self, mock_fetch_web, mock_dbos):
        """Test that source_url is included in batch error responses."""
        from kurt.workflows.fetch.config import FetchConfig
        from kurt.workflows.fetch.steps import _fetch_batch_web_documents

        mock_fetch_web.return_value = {
            "https://example.com/good": ("# Content", {"fingerprint": "abc"}),
            "https://example.com/broken": ValueError("Failed"),
        }

        docs = [
            {"document_id": "doc-1", "source_url": "https://example.com/good"},
            {"document_id": "doc-2", "source_url": "https://example.com/broken"},
        ]
        config = FetchConfig(fetch_engine="trafilatura")

        results = _fetch_batch_web_documents(docs, config)

        assert len(results) == 2
        result1 = next(r for r in results if r["document_id"] == "doc-1")
        result2 = next(r for r in results if r["document_id"] == "doc-2")

        assert result1["source_url"] == "https://example.com/good"
        assert result1["status"] == FetchStatus.SUCCESS
        assert result2["source_url"] == "https://example.com/broken"
        assert result2["status"] == FetchStatus.ERROR


class TestSaveContentStepWithSourceUrl:
    """Tests for save_content_step with source_url passthrough for URL-based paths."""

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_passes_source_url_to_save(self, mock_save_file):
        """Test that source_url is passed to save_content_file for URL-based paths."""
        from kurt.workflows.fetch.steps import save_content_step

        mock_save_file.return_value = "example.com/blog/post.md"

        rows = [
            {
                "document_id": "doc-1",
                "source_url": "https://example.com/blog/post",
                "status": FetchStatus.SUCCESS,
                "content": "# Blog Post Content",
            }
        ]
        config = {"dry_run": False, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        # Verify source_url was passed to save_content_file
        mock_save_file.assert_called_once_with(
            "doc-1", "# Blog Post Content", "https://example.com/blog/post"
        )
        assert result[0]["content_path"] == "example.com/blog/post.md"

    @patch("kurt.workflows.fetch.steps.save_content_file")
    def test_handles_missing_source_url(self, mock_save_file):
        """Test graceful handling when source_url is missing (legacy data)."""
        from kurt.workflows.fetch.steps import save_content_step

        mock_save_file.return_value = "ab/cd/doc-1.md"

        rows = [
            {
                "document_id": "doc-1",
                # No source_url key
                "status": FetchStatus.SUCCESS,
                "content": "# Content",
            }
        ]
        config = {"dry_run": False, "fetch_engine": "trafilatura"}

        result = save_content_step(rows, config)

        # Should still work, passing None as source_url
        mock_save_file.assert_called_once_with("doc-1", "# Content", None)
        assert result[0]["content_path"] == "ab/cd/doc-1.md"


class TestPersistFetchDocumentsFiltering:
    """Tests for persist_fetch_documents filtering non-model fields.

    These tests verify that source_url and content fields are filtered out
    before persisting to FetchDocument, since those fields are not in the model.
    """

    def test_filters_out_source_url_field(self):
        """Test that source_url is filtered out before persisting to FetchDocument."""
        from kurt.workflows.fetch.models import FetchDocument

        row = {
            "document_id": "doc-1",
            "source_url": "https://example.com/page",  # Not in FetchDocument model
            "status": FetchStatus.SUCCESS,
            "content_length": 100,
            "content_hash": "abc123",
            "content_path": "example.com/page.md",
            "fetch_engine": "trafilatura",
        }

        # Same filtering logic used in persist_fetch_documents
        non_model_fields = {"source_url", "content"}
        db_row = {k: v for k, v in row.items() if k not in non_model_fields}

        # Should not raise - source_url filtered out before creating FetchDocument
        doc = FetchDocument(**db_row)
        assert doc.document_id == "doc-1"
        assert doc.content_path == "example.com/page.md"

    def test_filters_out_content_field(self):
        """Test that content is filtered out before persisting (should already be saved to file)."""
        from kurt.workflows.fetch.models import FetchDocument

        row = {
            "document_id": "doc-2",
            "content": "# Some markdown content",  # Not in FetchDocument model
            "status": FetchStatus.SUCCESS,
            "content_length": 22,
            "content_hash": "def456",
            "content_path": "example.com/other.md",
            "fetch_engine": "tavily",
        }

        # Same filtering logic used in persist_fetch_documents
        non_model_fields = {"source_url", "content"}
        db_row = {k: v for k, v in row.items() if k not in non_model_fields}

        # Should not raise - content filtered out before creating FetchDocument
        doc = FetchDocument(**db_row)
        assert doc.document_id == "doc-2"
        assert doc.content_length == 22
