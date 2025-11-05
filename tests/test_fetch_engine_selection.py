"""Unit tests for fetch engine selection logic."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from kurt.content.fetch import _get_fetch_engine


def test_engine_override_httpx():
    """Test that override parameter works for httpx."""
    engine = _get_fetch_engine(override="httpx")
    assert engine == "httpx"


def test_engine_override_trafilatura():
    """Test that override parameter works for trafilatura."""
    engine = _get_fetch_engine(override="trafilatura")
    assert engine == "trafilatura"


def test_engine_override_firecrawl_with_api_key():
    """Test that override parameter works for firecrawl when API key exists."""
    with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"}):
        engine = _get_fetch_engine(override="firecrawl")
        assert engine == "firecrawl"


def test_engine_override_firecrawl_without_api_key():
    """Test that override for firecrawl fails without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Cannot use Firecrawl"):
            _get_fetch_engine(override="firecrawl")


def test_engine_override_invalid():
    """Test that invalid override raises error."""
    with pytest.raises(ValueError, match="Invalid fetch engine"):
        _get_fetch_engine(override="invalid_engine")


def test_engine_from_config_httpx():
    """Test that httpx engine is selected from config."""
    # Create temporary config file
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "kurt.config"
        config_path.write_text('INGESTION_FETCH_ENGINE = "httpx"\n')

        # Change to temp directory so load_config finds kurt.config
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            engine = _get_fetch_engine()
            assert engine == "httpx"
        finally:
            os.chdir(original_cwd)


def test_engine_from_config_trafilatura():
    """Test that trafilatura engine is selected from config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "kurt.config"
        config_path.write_text('INGESTION_FETCH_ENGINE = "trafilatura"\n')

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            engine = _get_fetch_engine()
            assert engine == "trafilatura"
        finally:
            os.chdir(original_cwd)


def test_engine_from_config_firecrawl_with_api_key():
    """Test that firecrawl engine is selected from config when API key exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "kurt.config"
        config_path.write_text('INGESTION_FETCH_ENGINE = "firecrawl"\n')

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"}):
                engine = _get_fetch_engine()
                assert engine == "firecrawl"
        finally:
            os.chdir(original_cwd)


def test_engine_from_config_firecrawl_without_api_key():
    """Test that trafilatura fallback is used when firecrawl config but no API key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "kurt.config"
        config_path.write_text('INGESTION_FETCH_ENGINE = "firecrawl"\n')

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            with patch.dict(os.environ, {}, clear=True):
                engine = _get_fetch_engine()
                assert engine == "trafilatura"  # Falls back to default
        finally:
            os.chdir(original_cwd)


def test_engine_default_when_no_config():
    """Test that trafilatura is used when no config file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # No kurt.config file created
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            engine = _get_fetch_engine()
            assert engine == "trafilatura"
        finally:
            os.chdir(original_cwd)


def test_override_takes_precedence_over_config():
    """Test that override parameter takes precedence over config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "kurt.config"
        config_path.write_text('INGESTION_FETCH_ENGINE = "trafilatura"\n')

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # Override should win over config
            engine = _get_fetch_engine(override="httpx")
            assert engine == "httpx"
        finally:
            os.chdir(original_cwd)
