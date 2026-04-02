"""Tests for MapConfig."""

from kurt.tools.map.config import MapConfig


class TestMapConfig:
    """Test suite for MapConfig."""

    def test_config_import(self):
        """Test that MapConfig can be imported."""
        assert MapConfig is not None

    def test_config_defaults(self):
        """Test MapConfig default values."""
        config = MapConfig()

        assert config.source_url is None
        assert config.source_folder is None
        assert config.cms_platform is None
        assert config.cms_instance is None
        assert config.discovery_method == "auto"
        assert config.sitemap_path is None
        assert config.max_depth is None
        assert config.max_pages == 1000
        assert config.include_patterns is None
        assert config.exclude_patterns is None
        assert config.allow_external is False
        assert config.dry_run is False

    def test_config_with_source_url(self):
        """Test MapConfig with source_url."""
        config = MapConfig(source_url="https://example.com")

        assert config.source_url == "https://example.com"
        assert config.source_folder is None

    def test_config_with_sitemap_path(self):
        """Test MapConfig with sitemap_path override."""
        config = MapConfig(
            source_url="https://example.com",
            sitemap_path="/custom-sitemap.xml",
        )

        assert config.source_url == "https://example.com"
        assert config.sitemap_path == "/custom-sitemap.xml"

    def test_config_with_source_folder(self):
        """Test MapConfig with source_folder."""
        config = MapConfig(source_folder="/path/to/docs")

        assert config.source_folder == "/path/to/docs"
        assert config.source_url is None

    def test_config_with_cms(self):
        """Test MapConfig with CMS settings."""
        config = MapConfig(cms_platform="notion", cms_instance="workspace-123")

        assert config.cms_platform == "notion"
        assert config.cms_instance == "workspace-123"

    def test_config_max_depth_valid(self):
        """Test max_depth with valid values."""
        for depth in [1, 2, 3, 4, 5]:
            config = MapConfig(max_depth=depth)
            assert config.max_depth == depth

    def test_config_max_pages_valid(self):
        """Test max_pages with valid values."""
        config = MapConfig(max_pages=500)
        assert config.max_pages == 500

    def test_config_patterns(self):
        """Test include/exclude patterns."""
        config = MapConfig(
            include_patterns="*.md,*.mdx",
            exclude_patterns="**/drafts/*,**/archive/*",
        )

        assert config.include_patterns == "*.md,*.mdx"
        assert config.exclude_patterns == "**/drafts/*,**/archive/*"

    def test_config_model_dump(self):
        """Test config serialization."""
        config = MapConfig(
            source_url="https://example.com",
            max_pages=100,
            dry_run=True,
        )

        data = config.model_dump()

        assert data["source_url"] == "https://example.com"
        assert data["max_pages"] == 100
        assert data["dry_run"] is True

    def test_config_model_validate(self):
        """Test config deserialization."""
        data = {
            "source_folder": "/docs",
            "discovery_method": "folder",
            "max_pages": 50,
        }

        config = MapConfig.model_validate(data)

        assert config.source_folder == "/docs"
        assert config.discovery_method == "folder"
        assert config.max_pages == 50
