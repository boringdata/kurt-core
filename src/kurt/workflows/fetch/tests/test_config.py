"""Tests for FetchConfig."""

from kurt.workflows.fetch import FetchConfig


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

    def test_from_config_fetch_engine(self, tmp_project):
        """Test loading FETCH.FETCH_ENGINE from config file."""
        from kurt.config.base import get_config_file_path

        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write("FETCH.FETCH_ENGINE=tavily\n")

        config = FetchConfig.from_config("fetch")
        assert config.fetch_engine == "tavily"

    def test_from_config_batch_size(self, tmp_project):
        """Test loading FETCH.BATCH_SIZE from config file."""
        from kurt.config.base import get_config_file_path

        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write("FETCH.BATCH_SIZE=15\n")

        config = FetchConfig.from_config("fetch")
        assert config.batch_size == 15

    def test_from_config_multiple_params(self, tmp_project):
        """Test loading multiple FETCH params from config file."""
        from kurt.config.base import get_config_file_path

        config_file = get_config_file_path()
        with open(config_file, "a") as f:
            f.write("FETCH.FETCH_ENGINE=firecrawl\n")
            f.write("FETCH.BATCH_SIZE=50\n")
            f.write("FETCH.EMBEDDING_MAX_CHARS=2000\n")

        config = FetchConfig.from_config("fetch")
        assert config.fetch_engine == "firecrawl"
        assert config.batch_size == 50
        assert config.embedding_max_chars == 2000

    def test_from_config_with_overrides(self, tmp_project):
        """Test from_config with CLI overrides."""
        from kurt.config.base import get_config_file_path

        config_file = get_config_file_path()
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
