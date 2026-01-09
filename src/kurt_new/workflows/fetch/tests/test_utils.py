"""Tests for fetch utilities including content storage."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from kurt_new.workflows.fetch.models import FetchStatus
from kurt_new.workflows.fetch.workflow import _has_embedding_api_key


class TestGenerateContentPath:
    """Test suite for generate_content_path."""

    def test_generates_sharded_path(self):
        """Test that path uses 2-level hash prefix."""
        from kurt_new.workflows.fetch.utils import generate_content_path

        path = generate_content_path("doc-123")

        # Should have format: xx/yy/filename.md
        parts = path.split("/")
        assert len(parts) == 3
        assert len(parts[0]) == 2  # First hash prefix
        assert len(parts[1]) == 2  # Second hash prefix
        assert parts[2].endswith(".md")

    def test_same_id_produces_same_path(self):
        """Test deterministic path generation."""
        from kurt_new.workflows.fetch.utils import generate_content_path

        path1 = generate_content_path("document-abc")
        path2 = generate_content_path("document-abc")

        assert path1 == path2

    def test_different_ids_produce_different_paths(self):
        """Test different IDs get different paths."""
        from kurt_new.workflows.fetch.utils import generate_content_path

        path1 = generate_content_path("doc-1")
        path2 = generate_content_path("doc-2")

        assert path1 != path2

    def test_sanitizes_special_characters(self):
        """Test that special chars are replaced."""
        from kurt_new.workflows.fetch.utils import generate_content_path

        path = generate_content_path("https://example.com/page?query=1")

        # Should not contain problematic characters
        filename = path.split("/")[-1]
        assert "/" not in filename.replace(".md", "")
        assert ":" not in filename
        assert "?" not in filename

    def test_truncates_long_ids(self):
        """Test that very long IDs are truncated."""
        from kurt_new.workflows.fetch.utils import generate_content_path

        long_id = "x" * 200
        path = generate_content_path(long_id)

        filename = path.split("/")[-1]
        # Should be truncated to 100 chars + .md
        assert len(filename) <= 103  # 100 + ".md"


class TestSaveContentFile:
    """Test suite for save_content_file."""

    @patch("kurt_new.workflows.fetch.utils.load_config")
    def test_saves_content_to_file(self, mock_load_config):
        """Test content is saved to correct location."""
        from kurt_new.workflows.fetch.utils import save_content_file

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            relative_path = save_content_file("doc-123", "# Test Content\n\nHello world!")

            # Verify file was created
            full_path = Path(tmpdir) / relative_path
            assert full_path.exists()
            assert full_path.read_text() == "# Test Content\n\nHello world!"

    @patch("kurt_new.workflows.fetch.utils.load_config")
    def test_creates_directories(self, mock_load_config):
        """Test that parent directories are created."""
        from kurt_new.workflows.fetch.utils import save_content_file

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            relative_path = save_content_file("new-doc", "Content")

            full_path = Path(tmpdir) / relative_path
            assert full_path.exists()
            assert full_path.parent.exists()

    @patch("kurt_new.workflows.fetch.utils.load_config")
    def test_returns_relative_path(self, mock_load_config):
        """Test that returned path is relative."""
        from kurt_new.workflows.fetch.utils import save_content_file

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            relative_path = save_content_file("doc-456", "Content")

            # Should not be absolute
            assert not relative_path.startswith("/")
            assert not relative_path.startswith(tmpdir)

    @patch("kurt_new.workflows.fetch.utils.load_config")
    def test_handles_unicode_content(self, mock_load_config):
        """Test saving unicode content."""
        from kurt_new.workflows.fetch.utils import save_content_file

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

    @patch("kurt_new.workflows.fetch.utils.load_config")
    def test_loads_existing_file(self, mock_load_config):
        """Test loading content from existing file."""
        from kurt_new.workflows.fetch.utils import load_document_content

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

    @patch("kurt_new.workflows.fetch.utils.load_config")
    def test_returns_none_for_missing_file(self, mock_load_config):
        """Test returns None when file doesn't exist."""
        from kurt_new.workflows.fetch.utils import load_document_content

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config = MagicMock()
            mock_config.get_absolute_sources_path.return_value = Path(tmpdir)
            mock_load_config.return_value = mock_config

            content = load_document_content("nonexistent/path/file.md")

            assert content is None

    @patch("kurt_new.workflows.fetch.utils.load_config")
    def test_roundtrip_save_and_load(self, mock_load_config):
        """Test saving and loading produces same content."""
        from kurt_new.workflows.fetch.utils import load_document_content, save_content_file

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

    @patch("kurt_new.workflows.fetch.steps.save_content_file")
    def test_saves_fetched_content(self, mock_save_file):
        """Test that fetched content is saved to file."""
        from kurt_new.workflows.fetch.steps import save_content_step

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

        mock_save_file.assert_called_once_with("doc-1", "# Test Content")
        assert result[0]["content_path"] == "ab/cd/doc-1.md"
        assert "content" not in result[0]  # Content should be removed

    @patch("kurt_new.workflows.fetch.steps.save_content_file")
    def test_skips_error_documents(self, mock_save_file):
        """Test that error documents are skipped."""
        from kurt_new.workflows.fetch.steps import save_content_step

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

    @patch("kurt_new.workflows.fetch.steps.save_content_file")
    def test_dry_run_skips_saving(self, mock_save_file):
        """Test that dry_run mode doesn't save files."""
        from kurt_new.workflows.fetch.steps import save_content_step

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

    @patch("kurt_new.workflows.fetch.steps.save_content_file")
    def test_handles_multiple_documents(self, mock_save_file):
        """Test processing multiple documents."""
        from kurt_new.workflows.fetch.steps import save_content_step

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

    @patch("kurt_new.workflows.fetch.steps.save_content_file")
    def test_handles_save_error(self, mock_save_file):
        """Test that save errors are handled gracefully."""
        from kurt_new.workflows.fetch.steps import save_content_step

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

    @patch("kurt_new.workflows.fetch.steps.save_content_file")
    def test_skips_documents_without_content(self, mock_save_file):
        """Test that documents without content are skipped."""
        from kurt_new.workflows.fetch.steps import save_content_step

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

    @patch("kurt_new.workflows.fetch.steps.save_content_file")
    def test_handles_status_as_string_value(self, mock_save_file):
        """Test that save_content_step handles status as string (after serialization).

        This is critical because _serialize_rows converts FetchStatus enum to string,
        and subsequent steps receive serialized rows with string status values.
        """
        from kurt_new.workflows.fetch.steps import save_content_step

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
        mock_save_file.assert_called_once_with("doc-1", "# Test Content")
        assert result[0]["content_path"] == "ab/cd/doc-1.md"


class TestEmbeddingStepStatusHandling:
    """Tests for embedding_step status handling after serialization."""

    @patch("kurt_new.workflows.fetch.steps.load_document_content")
    @patch("kurt_new.workflows.fetch.steps.generate_embeddings")
    @patch("kurt_new.workflows.fetch.steps.embedding_to_bytes")
    def test_handles_status_as_string_value(
        self, mock_embed_bytes, mock_gen_embed, mock_load_content
    ):
        """Test that embedding_step handles status as string (after serialization).

        This is critical because _serialize_rows converts FetchStatus enum to string,
        and embedding_step receives serialized rows with string status values.
        """
        from kurt_new.workflows.fetch.steps import embedding_step

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

    @patch("kurt_new.workflows.fetch.steps.load_document_content")
    @patch("kurt_new.workflows.fetch.steps.generate_embeddings")
    def test_skips_error_status_string(self, mock_gen_embed, mock_load_content):
        """Test that embedding_step skips rows with ERROR status as string."""
        from kurt_new.workflows.fetch.steps import embedding_step

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
