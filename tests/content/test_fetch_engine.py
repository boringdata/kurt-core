"""
Tests for fetch engine selection and behavior.

This module tests:
- Engine selection based on config and environment
- Override behavior with --fetch-engine flag
- Fallback to Trafilatura when Firecrawl is unavailable
- Error handling for invalid configurations
"""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from kurt.content.fetch import _get_fetch_engine


class TestFetchEngineSelection:
    """Tests for _get_fetch_engine() function."""

    def test_default_to_trafilatura_no_config(self, monkeypatch):
        """Test that Trafilatura is used when no config is available."""
        # Remove any FIRECRAWL_API_KEY
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        # Mock load_config to raise exception (config not found)
        with patch("kurt.content.fetch.load_config", side_effect=FileNotFoundError):
            engine = _get_fetch_engine()
            assert engine == "trafilatura"

    def test_default_to_trafilatura_no_api_key(self, monkeypatch, tmp_path):
        """Test that Trafilatura is used when Firecrawl config is set but no API key."""
        # Remove any FIRECRAWL_API_KEY
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        # Mock config with firecrawl engine
        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "firecrawl"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine()
            assert engine == "trafilatura"

    def test_default_to_trafilatura_placeholder_api_key(self, monkeypatch):
        """Test that Trafilatura is used when API key is placeholder."""
        # Set placeholder API key
        monkeypatch.setenv("FIRECRAWL_API_KEY", "your_firecrawl_api_key_here")

        # Mock config with firecrawl engine
        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "firecrawl"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine()
            assert engine == "trafilatura"

    def test_use_firecrawl_with_valid_api_key(self, monkeypatch):
        """Test that Firecrawl is used when config and valid API key are set."""
        # Set valid API key
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-valid-key-12345")

        # Mock config with firecrawl engine
        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "firecrawl"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine()
            assert engine == "firecrawl"

    def test_use_trafilatura_when_config_says_so(self, monkeypatch):
        """Test that Trafilatura is used when explicitly set in config."""
        # Remove any API key
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        # Mock config with trafilatura engine
        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "trafilatura"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine()
            assert engine == "trafilatura"


class TestFetchEngineOverride:
    """Tests for override parameter in _get_fetch_engine()."""

    def test_override_with_trafilatura(self, monkeypatch):
        """Test that override='trafilatura' works regardless of config."""
        # Set valid API key and firecrawl config
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-valid-key-12345")

        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "firecrawl"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine(override="trafilatura")
            assert engine == "trafilatura"

    def test_override_with_firecrawl_valid_key(self, monkeypatch):
        """Test that override='firecrawl' works with valid API key."""
        # Set valid API key
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-valid-key-12345")

        # Config says trafilatura, but override should win
        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "trafilatura"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine(override="firecrawl")
            assert engine == "firecrawl"

    def test_override_with_firecrawl_no_key_raises_error(self, monkeypatch):
        """Test that override='firecrawl' without API key raises ValueError."""
        # Remove any API key
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        with pytest.raises(ValueError, match="Cannot use Firecrawl: FIRECRAWL_API_KEY not set"):
            _get_fetch_engine(override="firecrawl")

    def test_override_with_firecrawl_placeholder_key_raises_error(self, monkeypatch):
        """Test that override='firecrawl' with placeholder API key raises ValueError."""
        # Set placeholder API key
        monkeypatch.setenv("FIRECRAWL_API_KEY", "your_firecrawl_api_key_here")

        with pytest.raises(ValueError, match="Cannot use Firecrawl: FIRECRAWL_API_KEY not set"):
            _get_fetch_engine(override="firecrawl")

    def test_override_with_invalid_engine_raises_error(self):
        """Test that invalid engine name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid fetch engine: invalid"):
            _get_fetch_engine(override="invalid")

    def test_override_case_insensitive(self, monkeypatch):
        """Test that override parameter is case-insensitive."""
        # Test uppercase
        engine = _get_fetch_engine(override="TRAFILATURA")
        assert engine == "trafilatura"

        # Test mixed case
        engine = _get_fetch_engine(override="Trafilatura")
        assert engine == "trafilatura"

        # Test Firecrawl with valid key
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-valid-key-12345")
        engine = _get_fetch_engine(override="FIRECRAWL")
        assert engine == "firecrawl"


class TestFetchDocumentWithEngine:
    """Tests for fetch_document() with fetch_engine parameter."""

    def test_fetch_document_uses_default_engine(self, monkeypatch):
        """Test that fetch_document uses default engine when no override."""
        from kurt.content.fetch import fetch_document

        # Mock the entire fetch flow
        with (
            patch("kurt.content.fetch.get_session") as mock_session,
            patch("kurt.content.fetch.load_config") as mock_config,
        ):
            with patch("kurt.content.fetch._get_fetch_engine") as mock_get_engine:
                with patch("kurt.content.fetch.fetch_with_trafilatura") as mock_fetch:
                    # Mock config
                    mock_cfg = MagicMock()
                    mock_cfg.INGESTION_FETCH_ENGINE = "trafilatura"
                    mock_config.return_value = mock_cfg

                    mock_get_engine.return_value = "trafilatura"
                    mock_fetch.return_value = ("Test content", {"title": "Test"})

                    # Mock session and document
                    mock_doc = MagicMock()
                    mock_doc.id = UUID("550e8400-e29b-41d4-a716-446655440000")
                    mock_doc.source_url = "https://example.com"
                    mock_doc.ingestion_status = "NOT_FETCHED"
                    mock_doc.source_type = "URL"
                    mock_doc.cms_platform = None
                    mock_doc.cms_instance = None
                    mock_doc.cms_document_id = None
                    mock_session.return_value.get.return_value = mock_doc

                    # Call fetch_document
                    fetch_document(mock_doc.id)

                    # Verify _get_fetch_engine was called with no override
                    mock_get_engine.assert_called_once_with(override=None)

    def test_fetch_document_uses_override_engine(self, monkeypatch):
        """Test that fetch_document respects fetch_engine parameter."""
        from kurt.content.fetch import fetch_document

        # Mock the entire fetch flow
        with (
            patch("kurt.content.fetch.get_session") as mock_session,
            patch("kurt.content.fetch.load_config") as mock_config,
        ):
            with patch("kurt.content.fetch._get_fetch_engine") as mock_get_engine:
                with patch("kurt.content.fetch.fetch_with_firecrawl") as mock_fetch:
                    # Mock config
                    mock_cfg = MagicMock()
                    mock_cfg.INGESTION_FETCH_ENGINE = "firecrawl"
                    mock_config.return_value = mock_cfg

                    mock_get_engine.return_value = "firecrawl"
                    mock_fetch.return_value = ("Test content", {"title": "Test"})

                    # Mock session and document
                    mock_doc = MagicMock()
                    mock_doc.id = UUID("550e8400-e29b-41d4-a716-446655440000")
                    mock_doc.source_url = "https://example.com"
                    mock_doc.ingestion_status = "NOT_FETCHED"
                    mock_doc.source_type = "URL"
                    mock_doc.cms_platform = None
                    mock_doc.cms_instance = None
                    mock_doc.cms_document_id = None
                    mock_session.return_value.get.return_value = mock_doc

                    # Call fetch_document with engine override
                    fetch_document(mock_doc.id, fetch_engine="firecrawl")

                    # Verify _get_fetch_engine was called with override
                    mock_get_engine.assert_called_once_with(override="firecrawl")


class TestFetchDocumentsBatchWithEngine:
    """Tests for fetch_documents_batch() with fetch_engine parameter."""

    def test_batch_fetch_uses_default_engine(self):
        """Test that batch fetch uses default engine when no override."""
        from kurt.content.fetch import fetch_documents_batch

        with patch("kurt.content.fetch._get_fetch_engine") as mock_get_engine:
            mock_get_engine.return_value = "trafilatura"

            # Mock asyncio.run to avoid actually running async code
            with patch("kurt.content.fetch.asyncio.run") as mock_run:
                # Properly consume the coroutine to avoid RuntimeWarning
                mock_run.side_effect = lambda coro: (coro.close(), [])[1]

                fetch_documents_batch(["doc1", "doc2"])

                # Verify _get_fetch_engine was called with no override
                mock_get_engine.assert_called_once_with(override=None)

    def test_batch_fetch_uses_override_engine(self):
        """Test that batch fetch respects fetch_engine parameter."""
        from kurt.content.fetch import fetch_documents_batch

        with patch("kurt.content.fetch._get_fetch_engine") as mock_get_engine:
            mock_get_engine.return_value = "firecrawl"

            # Mock asyncio.run to avoid actually running async code
            with patch("kurt.content.fetch.asyncio.run") as mock_run:
                # Properly consume the coroutine to avoid RuntimeWarning
                mock_run.side_effect = lambda coro: (coro.close(), [])[1]

                fetch_documents_batch(["doc1", "doc2"], fetch_engine="firecrawl")

                # Verify _get_fetch_engine was called with override
                mock_get_engine.assert_called_once_with(override="firecrawl")

    def test_batch_fetch_shows_warning_for_large_trafilatura_batch(self, capsys):
        """Test that warning is shown for large batches with Trafilatura."""
        from kurt.content.fetch import fetch_documents_batch

        with patch("kurt.content.fetch._get_fetch_engine") as mock_get_engine:
            mock_get_engine.return_value = "trafilatura"

            # Mock asyncio.run to avoid actually running async code
            with patch("kurt.content.fetch.asyncio.run") as mock_run:
                # Properly consume the coroutine to avoid RuntimeWarning
                mock_run.side_effect = lambda coro: (coro.close(), [])[1]

                # Create batch of 15 documents (>10 threshold)
                doc_ids = [f"doc{i}" for i in range(15)]
                fetch_documents_batch(doc_ids)

                # Check that warning was printed
                captured = capsys.readouterr()
                assert "Warning: Fetching large volumes with Trafilatura" in captured.out
                assert "Firecrawl" in captured.out

    def test_batch_fetch_no_warning_for_small_trafilatura_batch(self, capsys):
        """Test that no warning is shown for small batches with Trafilatura."""
        from kurt.content.fetch import fetch_documents_batch

        with patch("kurt.content.fetch._get_fetch_engine") as mock_get_engine:
            mock_get_engine.return_value = "trafilatura"

            # Mock asyncio.run to avoid actually running async code
            with patch("kurt.content.fetch.asyncio.run") as mock_run:
                # Properly consume the coroutine to avoid RuntimeWarning
                mock_run.side_effect = lambda coro: (coro.close(), [])[1]

                # Create batch of 5 documents (<10 threshold)
                doc_ids = [f"doc{i}" for i in range(5)]
                fetch_documents_batch(doc_ids)

                # Check that no warning was printed
                captured = capsys.readouterr()
                assert "Warning" not in captured.out

    def test_batch_fetch_no_warning_for_large_firecrawl_batch(self, capsys):
        """Test that no warning is shown for large batches with Firecrawl."""
        from kurt.content.fetch import fetch_documents_batch

        with patch("kurt.content.fetch._get_fetch_engine") as mock_get_engine:
            mock_get_engine.return_value = "firecrawl"

            # Mock asyncio.run to avoid actually running async code
            with patch("kurt.content.fetch.asyncio.run") as mock_run:
                # Properly consume the coroutine to avoid RuntimeWarning
                mock_run.side_effect = lambda coro: (coro.close(), [])[1]

                # Create batch of 20 documents (>10 threshold)
                doc_ids = [f"doc{i}" for i in range(20)]
                fetch_documents_batch(doc_ids)

                # Check that no warning was printed
                captured = capsys.readouterr()
                assert "Warning" not in captured.out


class TestEngineConfigurationScenarios:
    """Integration tests for realistic configuration scenarios."""

    def test_scenario_no_config_no_env(self, monkeypatch):
        """
        Scenario: Fresh install, no config, no API keys.
        Expected: Use Trafilatura (default fallback).
        """
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        with patch("kurt.content.fetch.load_config", side_effect=FileNotFoundError):
            engine = _get_fetch_engine()
            assert engine == "trafilatura"

    def test_scenario_config_trafilatura_no_api_key(self, monkeypatch):
        """
        Scenario: Config says trafilatura, no API key.
        Expected: Use Trafilatura.
        """
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "trafilatura"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine()
            assert engine == "trafilatura"

    def test_scenario_config_firecrawl_valid_api_key(self, monkeypatch):
        """
        Scenario: Config says firecrawl, valid API key set.
        Expected: Use Firecrawl.
        """
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-123456")

        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "firecrawl"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine()
            assert engine == "firecrawl"

    def test_scenario_config_firecrawl_forgot_api_key(self, monkeypatch):
        """
        Scenario: Config says firecrawl, but user forgot to add API key.
        Expected: Gracefully fallback to Trafilatura.
        """
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "firecrawl"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            engine = _get_fetch_engine()
            assert engine == "trafilatura"

    def test_scenario_override_for_testing(self, monkeypatch):
        """
        Scenario: User wants to test Firecrawl on a single command.
        Expected: Override works with --fetch-engine flag.
        """
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-123456")

        # Config says trafilatura
        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "trafilatura"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            # But override to firecrawl for this command
            engine = _get_fetch_engine(override="firecrawl")
            assert engine == "firecrawl"

    def test_scenario_override_to_trafilatura_saves_costs(self, monkeypatch):
        """
        Scenario: User normally uses Firecrawl but wants to save costs on simple pages.
        Expected: Override to trafilatura works even with Firecrawl configured.
        """
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-123456")

        # Config says firecrawl
        mock_config = MagicMock()
        mock_config.INGESTION_FETCH_ENGINE = "firecrawl"

        with patch("kurt.content.fetch.load_config", return_value=mock_config):
            # But override to trafilatura for simple pages
            engine = _get_fetch_engine(override="trafilatura")
            assert engine == "trafilatura"
