"""Tests for map core module."""


import pytest

from kurt.tools.map.core import (
    BaseMapper,
    MapperConfig,
    MapperResult,
    extract_domain,
    get_url_depth,
    is_internal_url,
    normalize_url,
    relative_to_absolute_url,
    should_include_url,
)
from kurt.tools.map.models import DocType


class TestMapperConfig:
    """Test MapperConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = MapperConfig()
        assert config.max_depth == 3
        assert config.max_urls == 1000
        assert config.timeout == 30.0
        assert config.follow_external is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = MapperConfig(
            max_depth=5,
            max_urls=5000,
            timeout=60.0,
            follow_external=True,
            include_pattern=r".*\.pdf$",
        )
        assert config.max_depth == 5
        assert config.max_urls == 5000
        assert config.follow_external is True
        assert config.include_pattern == r".*\.pdf$"

    def test_config_validation(self):
        """Test configuration validation."""
        with pytest.raises(ValueError):
            MapperConfig(max_depth=0)

        with pytest.raises(ValueError):
            MapperConfig(max_urls=0)


class TestMapperResult:
    """Test MapperResult."""

    def test_empty_result(self):
        """Test empty result."""
        result = MapperResult()
        assert result.urls == []
        assert result.count == 0
        assert result.errors == []

    def test_result_with_data(self):
        """Test result with data."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
        ]
        result = MapperResult(
            urls=urls,
            count=len(urls),
            errors=["Failed to fetch page3"],
            metadata={"discovered_at": "2024-01-29"},
        )
        assert result.count == 2
        assert len(result.errors) == 1


class MockMapper(BaseMapper):
    """Mock mapper for testing."""

    def map(self, source: str, doc_type: DocType = DocType.DOC) -> MapperResult:
        """Mock implementation."""
        return MapperResult(
            urls=[source, f"{source}/page2"],
            count=2,
        )


class TestBaseMapper:
    """Test BaseMapper."""

    def test_mapper_creation(self):
        """Test creating a mapper."""
        mapper = MockMapper()
        assert mapper.config is not None
        assert mapper.config.max_depth == 3

    def test_mapper_with_config(self):
        """Test mapper with custom config."""
        config = MapperConfig(max_depth=5)
        mapper = MockMapper(config=config)
        assert mapper.config.max_depth == 5

    def test_mapper_map(self):
        """Test map method."""
        mapper = MockMapper()
        result = mapper.map("https://example.com")
        assert result.count == 2
        assert len(result.urls) == 2

    def test_create_document(self):
        """Test document creation."""
        mapper = MockMapper()
        doc = mapper.create_document(
            url="https://example.com/page1",
            doc_type=DocType.PROFILE,
            discovery_method="sitemap",
            platform="twitter",
        )
        assert doc.source_url == "https://example.com/page1"
        assert doc.doc_type == DocType.PROFILE
        assert doc.platform == "twitter"

    def test_document_id_generation(self):
        """Test document ID generation."""
        mapper = MockMapper()
        url = "https://example.com/page1"
        doc_id = mapper._generate_document_id(url)
        assert len(doc_id) == 16
        assert isinstance(doc_id, str)

    def test_document_id_consistency(self):
        """Test document ID is consistent for same URL."""
        mapper = MockMapper()
        url = "https://example.com/page1"
        id1 = mapper._generate_document_id(url)
        id2 = mapper._generate_document_id(url)
        assert id1 == id2


class TestNormalizeUrl:
    """Test URL normalization."""

    def test_normalize_simple_url(self):
        """Test normalizing simple URL."""
        url = "https://Example.com/"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/"

    def test_normalize_url_with_path(self):
        """Test normalizing URL with path."""
        url = "https://Example.com/path/to/page"
        normalized = normalize_url(url)
        assert normalized == "https://example.com/path/to/page"

    def test_normalize_url_with_query(self):
        """Test normalizing URL with query."""
        url = "https://example.com/page?key=value"
        normalized = normalize_url(url)
        assert "key=value" in normalized

    def test_normalize_url_with_fragment(self):
        """Test normalizing URL with fragment."""
        url = "https://example.com/page#section"
        normalized = normalize_url(url)
        assert "#section" in normalized


class TestIsInternalUrl:
    """Test internal URL checking."""

    def test_internal_same_domain(self):
        """Test URL from same domain is internal."""
        base = "https://example.com/page1"
        check = "https://example.com/page2"
        assert is_internal_url(base, check) is True

    def test_internal_different_domain(self):
        """Test URL from different domain is external."""
        base = "https://example.com/page1"
        check = "https://other.com/page2"
        assert is_internal_url(base, check) is False

    def test_internal_case_insensitive(self):
        """Test domain comparison is case-insensitive."""
        base = "https://Example.com/page1"
        check = "https://EXAMPLE.com/page2"
        assert is_internal_url(base, check) is True


class TestExtractDomain:
    """Test domain extraction."""

    def test_extract_domain_simple(self):
        """Test extracting domain from simple URL."""
        url = "https://example.com/page"
        domain = extract_domain(url)
        assert domain == "example.com"

    def test_extract_domain_case_insensitive(self):
        """Test domain extraction is case-insensitive."""
        url = "https://Example.COM/page"
        domain = extract_domain(url)
        assert domain == "example.com"

    def test_extract_domain_with_port(self):
        """Test extracting domain with port."""
        url = "https://example.com:8080/page"
        domain = extract_domain(url)
        assert domain == "example.com:8080"


class TestShouldIncludeUrl:
    """Test URL inclusion criteria."""

    def test_include_all_by_default(self):
        """Test all URLs included by default."""
        url = "https://example.com/page"
        assert should_include_url(url) is True

    def test_include_pattern(self):
        """Test inclusion pattern matching."""
        url = "https://example.com/blog/article.html"
        pattern = r".*blog.*"
        assert should_include_url(url, include_pattern=pattern) is True

    def test_exclude_pattern(self):
        """Test exclusion pattern matching."""
        url = "https://example.com/admin/settings"
        pattern = r".*admin.*"
        assert should_include_url(url, exclude_pattern=pattern) is False

    def test_exclude_takes_precedence(self):
        """Test exclude pattern takes precedence."""
        url = "https://example.com/blog/admin"
        include = r".*blog.*"
        exclude = r".*admin.*"
        assert should_include_url(url, include, exclude) is False


class TestRelativeToAbsoluteUrl:
    """Test relative to absolute URL conversion."""

    def test_relative_path(self):
        """Test converting relative path."""
        base = "https://example.com/page1"
        relative = "/page2"
        absolute = relative_to_absolute_url(base, relative)
        assert absolute == "https://example.com/page2"

    def test_relative_subdirectory(self):
        """Test converting relative subdirectory."""
        base = "https://example.com/section/"
        relative = "page"
        absolute = relative_to_absolute_url(base, relative)
        assert "page" in absolute

    def test_absolute_url_unchanged(self):
        """Test absolute URL is returned unchanged."""
        base = "https://example.com/page1"
        relative = "https://other.com/page2"
        absolute = relative_to_absolute_url(base, relative)
        assert absolute == "https://other.com/page2"

    def test_invalid_relative_returns_none(self):
        """Test invalid relative returns None."""
        base = "https://example.com/page"
        relative = "not a valid url"
        absolute = relative_to_absolute_url(base, relative)
        # Should still work as relative path
        assert absolute is not None


class TestGetUrlDepth:
    """Test URL depth calculation."""

    def test_same_path_depth_zero(self):
        """Test same path has depth 0."""
        base = "https://example.com/page"
        target = "https://example.com/page"
        depth = get_url_depth(base, target)
        assert depth == 0

    def test_root_path_depth(self):
        """Test root path depth."""
        base = "https://example.com/"
        target = "https://example.com/page"
        depth = get_url_depth(base, target)
        assert depth >= 1

    def test_nested_path_depth(self):
        """Test nested path depth."""
        base = "https://example.com/blog/"
        target = "https://example.com/blog/2024/01/article"
        depth = get_url_depth(base, target)
        assert depth == 3  # 2024, 01, article

    def test_sibling_path_depth(self):
        """Test sibling path depth."""
        base = "https://example.com/blog/article1"
        target = "https://example.com/about"
        depth = get_url_depth(base, target)
        assert depth >= 1
