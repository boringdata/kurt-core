"""Tests for FetchConfig."""

from kurt_new.workflows.fetch import FetchConfig


class TestFetchConfig:
    """Test suite for FetchConfig."""

    def test_config_import(self):
        """Test that FetchConfig can be imported."""
        assert FetchConfig is not None

    def test_config_defaults(self):
        """Test FetchConfig default values."""
        config = FetchConfig()

        assert config.fetch_engine == "trafilatura"
        assert config.embedding_max_chars == 1000
        assert config.embedding_batch_size == 100
        assert config.embedding_concurrency == 3
        assert config.dry_run is False

    def test_config_with_fetch_engine(self):
        """Test FetchConfig with different fetch engines."""
        for engine in ["trafilatura", "httpx", "firecrawl"]:
            config = FetchConfig(fetch_engine=engine)
            assert config.fetch_engine == engine

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

    def test_config_embedding_concurrency(self):
        """Test embedding_concurrency configuration."""
        config = FetchConfig(embedding_concurrency=5)
        assert config.embedding_concurrency == 5

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
