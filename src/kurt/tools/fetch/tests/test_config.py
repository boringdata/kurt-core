"""Tests for FetchConfig."""

import os
from unittest.mock import patch

from kurt.tools.fetch.config import FetchConfig, has_embedding_api_keys


class TestFetchConfig:
    """Test suite for FetchConfig."""

    def test_config_import(self):
        """Test that FetchConfig can be imported."""
        assert FetchConfig is not None

    def test_config_defaults(self):
        """Test FetchConfig default values."""
        config = FetchConfig()

        assert config.fetch_engine == "trafilatura"
        assert config.batch_size is None
        assert config.embed is None  # None = auto-detect from API keys
        assert config.embedding_max_chars == 1000
        assert config.embedding_batch_size == 100
        assert config.dry_run is False

    def test_config_with_fetch_engine(self):
        """Test FetchConfig with different fetch engines."""
        for engine in ["trafilatura", "httpx", "firecrawl", "tavily"]:
            config = FetchConfig(fetch_engine=engine)
            assert config.fetch_engine == engine

    def test_config_batch_size_default(self):
        """Test batch_size default is None."""
        config = FetchConfig()
        assert config.batch_size is None

    def test_config_batch_size_valid(self):
        """Test batch_size with valid values."""
        for size in [1, 10, 20, 50, 100]:
            config = FetchConfig(batch_size=size)
            assert config.batch_size == size

    def test_config_embedding_max_chars_valid(self):
        """Test embedding_max_chars with valid values."""
        for chars in [100, 500, 1000, 2000, 5000]:
            config = FetchConfig(embedding_max_chars=chars)
            assert config.embedding_max_chars == chars

    def test_config_embedding_max_chars_bounds(self):
        """Test embedding_max_chars validation bounds."""
        # Min bound (100)
        config_min = FetchConfig(embedding_max_chars=100)
        assert config_min.embedding_max_chars == 100

        # Max bound (5000)
        config_max = FetchConfig(embedding_max_chars=5000)
        assert config_max.embedding_max_chars == 5000

    def test_config_embedding_batch_size(self):
        """Test embedding_batch_size configuration."""
        config = FetchConfig(embedding_batch_size=50)
        assert config.embedding_batch_size == 50

    def test_config_dry_run(self):
        """Test dry_run flag."""
        config = FetchConfig(dry_run=True)
        assert config.dry_run is True

        config = FetchConfig(dry_run=False)
        assert config.dry_run is False

    def test_config_embed_default_is_none(self):
        """Test embed default is None for auto-detection."""
        config = FetchConfig()
        assert config.embed is None

    def test_config_embed_explicit_true(self):
        """Test embed can be explicitly enabled."""
        config = FetchConfig(embed=True)
        assert config.embed is True

    def test_config_embed_explicit_false(self):
        """Test embed can be explicitly disabled."""
        config = FetchConfig(embed=False)
        assert config.embed is False


class TestHasEmbeddingApiKeys:
    """Test suite for has_embedding_api_keys function."""

    def test_no_api_keys(self):
        """Test returns False when no API keys are set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing keys
            for key in ["OPENAI_API_KEY", "VOYAGE_API_KEY", "COHERE_API_KEY"]:
                os.environ.pop(key, None)
            assert has_embedding_api_keys() is False

    def test_with_openai_key(self):
        """Test returns True when OPENAI_API_KEY is set."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=False):
            assert has_embedding_api_keys() is True

    def test_with_voyage_key(self):
        """Test returns True when VOYAGE_API_KEY is set."""
        with patch.dict(os.environ, {"VOYAGE_API_KEY": "voyage-test"}, clear=False):
            assert has_embedding_api_keys() is True

    def test_with_cohere_key(self):
        """Test returns True when COHERE_API_KEY is set."""
        with patch.dict(os.environ, {"COHERE_API_KEY": "cohere-test"}, clear=False):
            assert has_embedding_api_keys() is True

    def test_config_model_dump(self):
        """Test config serialization."""
        config = FetchConfig(
            fetch_engine="firecrawl",
            embedding_max_chars=2000,
            dry_run=True,
        )

        data = config.model_dump()

        assert data["fetch_engine"] == "firecrawl"
        assert data["embedding_max_chars"] == 2000
        assert data["dry_run"] is True

    def test_config_model_validate(self):
        """Test config deserialization."""
        data = {
            "fetch_engine": "httpx",
            "embedding_max_chars": 500,
        }

        config = FetchConfig.model_validate(data)

        assert config.fetch_engine == "httpx"
        assert config.embedding_max_chars == 500


class TestFetchConfigFromFile:
    """Test FetchConfig loading from kurt.config file."""

    def test_from_config_fetch_engine(self, tmp_project_with_legacy_config):
        """Test loading FETCH.FETCH_ENGINE from config file."""
        from pathlib import Path

        # Use legacy config file for dot-notation support
        config_file = Path.cwd() / "kurt.config"
        with open(config_file, "a") as f:
            f.write("FETCH.FETCH_ENGINE=tavily\n")

        config = FetchConfig.from_config("fetch")
        assert config.fetch_engine == "tavily"

    def test_from_config_batch_size(self, tmp_project_with_legacy_config):
        """Test loading FETCH.BATCH_SIZE from config file."""
        from pathlib import Path

        config_file = Path.cwd() / "kurt.config"
        with open(config_file, "a") as f:
            f.write("FETCH.BATCH_SIZE=15\n")

        config = FetchConfig.from_config("fetch")
        assert config.batch_size == 15

    def test_from_config_multiple_params(self, tmp_project_with_legacy_config):
        """Test loading multiple FETCH params from config file."""
        from pathlib import Path

        config_file = Path.cwd() / "kurt.config"
        with open(config_file, "a") as f:
            f.write("FETCH.FETCH_ENGINE=firecrawl\n")
            f.write("FETCH.BATCH_SIZE=50\n")
            f.write("FETCH.EMBEDDING_MAX_CHARS=2000\n")

        config = FetchConfig.from_config("fetch")
        assert config.fetch_engine == "firecrawl"
        assert config.batch_size == 50
        assert config.embedding_max_chars == 2000

    def test_from_config_with_overrides(self, tmp_project_with_legacy_config):
        """Test from_config with CLI overrides."""
        from pathlib import Path

        config_file = Path.cwd() / "kurt.config"
        with open(config_file, "a") as f:
            f.write("FETCH.FETCH_ENGINE=trafilatura\n")
            f.write("FETCH.BATCH_SIZE=10\n")

        # CLI override takes precedence
        config = FetchConfig.from_config("fetch", fetch_engine="tavily", batch_size=20)
        assert config.fetch_engine == "tavily"
        assert config.batch_size == 20

    def test_from_config_fallback_to_global(self, tmp_project):
        """Test FETCH.FETCH_ENGINE falls back to INGESTION_FETCH_ENGINE."""
        # No FETCH.FETCH_ENGINE set, should fall back to global
        config = FetchConfig.from_config("fetch")
        assert config.fetch_engine == "trafilatura"  # Default from INGESTION_FETCH_ENGINE
