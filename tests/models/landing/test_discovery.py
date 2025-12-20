"""Tests for landing.discovery model."""


class TestDiscoveryModel:
    """Test suite for discovery model."""

    def test_discovery_model_import(self):
        """Test that discovery model can be imported."""
        from kurt.models.landing import DiscoveryConfig, DiscoveryRow, discovery

        assert discovery is not None
        assert DiscoveryConfig is not None
        assert DiscoveryRow is not None

    def test_discovery_config_defaults(self):
        """Test DiscoveryConfig ConfigParam defaults."""
        from kurt.models.landing import DiscoveryConfig

        config = DiscoveryConfig()

        # ConfigParam fields have default attribute
        assert config.source_url.default is None
        assert config.source_folder.default is None
        assert config.discovery_method.default == "auto"
        assert config.max_pages.default == 1000
        assert config.allow_external.default is False

    def test_discovery_row_schema(self):
        """Test DiscoveryRow schema fields."""
        from kurt.models.landing import DiscoveryRow

        row = DiscoveryRow(
            document_id="test-doc-123",
            source_url="https://example.com/page",
            source_type="url",
            discovery_method="sitemap",
            status="DISCOVERED",
            is_new=True,
        )

        assert row.document_id == "test-doc-123"
        assert row.source_url == "https://example.com/page"
        assert row.source_type == "url"
        assert row.discovery_method == "sitemap"
        assert row.status == "DISCOVERED"
        assert row.is_new is True

    def test_discovery_row_table_name(self):
        """Test DiscoveryRow table name."""
        from kurt.models.landing import DiscoveryRow

        assert DiscoveryRow.__tablename__ == "landing_discovery"

    def test_discovery_model_registered(self):
        """Test that discovery model is registered in ModelRegistry."""
        # Import to register
        import kurt.models.landing  # noqa: F401
        from kurt.core import ModelRegistry

        model_info = ModelRegistry.get("landing.discovery")
        assert model_info is not None
        assert model_info["name"] == "landing.discovery"
