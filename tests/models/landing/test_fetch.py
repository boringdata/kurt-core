"""Tests for landing.fetch model."""


class TestFetchModel:
    """Test suite for fetch model."""

    def test_fetch_model_import(self):
        """Test that fetch model can be imported."""
        from kurt.models.landing import FetchConfig, FetchRow, fetch

        assert fetch is not None
        assert FetchConfig is not None
        assert FetchRow is not None

    def test_fetch_config_defaults(self):
        """Test FetchConfig ConfigParam defaults."""
        from kurt.models.landing import FetchConfig

        config = FetchConfig()

        # ConfigParam fields have default attribute
        assert config.fetch_engine.default == "trafilatura"
        assert config.embedding_max_chars.default == 1000

    def test_fetch_row_schema(self):
        """Test FetchRow schema fields."""
        from kurt.models.landing import FetchRow

        row = FetchRow(
            document_id="test-doc-123",
            status="FETCHED",
            content_length=5000,
            content_hash="abc123",
            embedding_dims=1536,
            links_extracted=10,
            fetch_engine="trafilatura",
        )

        assert row.document_id == "test-doc-123"
        assert row.status == "FETCHED"
        assert row.content_length == 5000
        assert row.content_hash == "abc123"
        assert row.embedding_dims == 1536
        assert row.links_extracted == 10
        assert row.fetch_engine == "trafilatura"

    def test_fetch_row_table_name(self):
        """Test FetchRow table name."""
        from kurt.models.landing import FetchRow

        assert FetchRow.__tablename__ == "landing_fetch"

    def test_fetch_model_registered(self):
        """Test that fetch model is registered in ModelRegistry."""
        # Import to register
        import kurt.models.landing  # noqa: F401
        from kurt.core import ModelRegistry

        model_info = ModelRegistry.get("landing.fetch")
        assert model_info is not None
        assert model_info["name"] == "landing.fetch"

    def test_fetch_row_error_state(self):
        """Test FetchRow error state."""
        from kurt.models.landing import FetchRow

        row = FetchRow(
            document_id="test-doc-456",
            status="ERROR",
            error="Connection timeout",
        )

        assert row.status == "ERROR"
        assert row.error == "Connection timeout"
        assert row.content_length == 0
