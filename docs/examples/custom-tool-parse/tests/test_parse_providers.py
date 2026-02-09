"""Tests for the example parse tool providers.

Demonstrates how to test custom providers both directly and via
the ProviderRegistry discovery mechanism.

Run from the project root:

    .venv/bin/python -m pytest docs/examples/custom-tool-parse/tests/ -v
"""

from pathlib import Path

import pytest

from kurt.tools.core.provider import ProviderRegistry


# ---------------------------------------------------------------------------
# Fixture: load providers via registry (the canonical way)
# ---------------------------------------------------------------------------


@pytest.fixture
def parse_registry():
    """Set up a fresh registry pointing at the example tool directory."""
    registry = ProviderRegistry()
    registry.reset()
    tools_dir = Path(__file__).parent.parent / "kurt" / "tools"
    registry.discover_from([(tools_dir, "project")])
    return registry


@pytest.fixture
def frontmatter_parser(parse_registry):
    """Get an instance of the FrontmatterParser via the registry."""
    return parse_registry.get_provider("parse", "frontmatter")


@pytest.fixture
def markdown_ast_parser(parse_registry):
    """Get an instance of the MarkdownAstParser via the registry."""
    return parse_registry.get_provider("parse", "markdown-ast")


# ---------------------------------------------------------------------------
# FrontmatterParser tests
# ---------------------------------------------------------------------------


class TestFrontmatterParser:
    """Tests for the frontmatter parse provider."""

    def test_metadata(self, frontmatter_parser):
        assert frontmatter_parser.name == "frontmatter"
        assert frontmatter_parser.version == "1.0.0"
        assert "*.md" in frontmatter_parser.url_patterns
        assert frontmatter_parser.requires_env == []

    def test_parse_with_frontmatter(self, frontmatter_parser):
        content = "---\ntitle: Hello\ntags: [a, b]\n---\n\nBody text here."
        result = frontmatter_parser.parse(content)
        assert result.success is True
        assert result.data["title"] == "Hello"
        assert result.data["tags"] == ["a", "b"]
        assert result.metadata["has_frontmatter"] is True
        assert result.metadata["body_length"] > 0

    def test_parse_without_frontmatter(self, frontmatter_parser):
        content = "# Just a heading\n\nNo frontmatter here."
        result = frontmatter_parser.parse(content)
        assert result.success is True
        assert result.data == {}
        assert result.metadata["has_frontmatter"] is False

    def test_parse_unclosed_frontmatter(self, frontmatter_parser):
        content = "---\ntitle: Broken\nNo closing delimiter"
        result = frontmatter_parser.parse(content)
        assert result.success is False
        assert "Unclosed" in result.error

    def test_parse_invalid_yaml(self, frontmatter_parser):
        content = "---\n: invalid: yaml: [broken\n---\nBody"
        result = frontmatter_parser.parse(content)
        assert result.success is False
        assert "YAML" in result.error

    def test_parse_file(self, frontmatter_parser, tmp_path):
        md_file = tmp_path / "test.md"
        md_file.write_text("---\nauthor: Test\n---\n\nContent")
        result = frontmatter_parser.parse(str(md_file))
        assert result.success is True
        assert result.data["author"] == "Test"


# ---------------------------------------------------------------------------
# MarkdownAstParser tests
# ---------------------------------------------------------------------------


class TestMarkdownAstParser:
    """Tests for the markdown-ast parse provider."""

    def test_metadata(self, markdown_ast_parser):
        assert markdown_ast_parser.name == "markdown-ast"
        assert markdown_ast_parser.version == "1.0.0"
        assert "*.md" in markdown_ast_parser.url_patterns

    def test_parse_headings(self, markdown_ast_parser):
        content = "# Title\n\n## Section 1\n\nText\n\n### Subsection\n\n## Section 2\n"
        result = markdown_ast_parser.parse(content)
        assert result.success is True
        assert result.data["heading_count"] == 4
        headings = result.data["headings"]
        assert headings[0] == {"level": 1, "text": "Title"}
        assert headings[1] == {"level": 2, "text": "Section 1"}

    def test_parse_code_blocks(self, markdown_ast_parser):
        content = "# Title\n\n```python\nprint('hello')\n```\n\nText\n\n```\ncode\n```\n"
        result = markdown_ast_parser.parse(content)
        assert result.metadata["code_block_count"] == 2

    def test_parse_links(self, markdown_ast_parser):
        content = "Check [this](https://example.com) and [that](https://other.com)\n"
        result = markdown_ast_parser.parse(content)
        assert result.metadata["link_count"] == 2

    def test_parse_empty_content(self, markdown_ast_parser):
        result = markdown_ast_parser.parse("")
        assert result.success is True
        assert result.data["heading_count"] == 0

    def test_headings_inside_code_blocks_ignored(self, markdown_ast_parser):
        content = "# Real\n\n```\n# Not a heading\n```\n"
        result = markdown_ast_parser.parse(content)
        assert result.data["heading_count"] == 1

    def test_parse_file(self, markdown_ast_parser, tmp_path):
        md_file = tmp_path / "doc.md"
        md_file.write_text("# Hello\n\nWorld\n")
        result = markdown_ast_parser.parse(str(md_file))
        assert result.success is True
        assert result.data["heading_count"] == 1


# ---------------------------------------------------------------------------
# ProviderRegistry integration tests
# ---------------------------------------------------------------------------


class TestParseProviderDiscovery:
    """Test that the parse tool providers are discovered by ProviderRegistry."""

    def test_discover_both_providers(self, parse_registry):
        """Verify the registry finds both parse providers."""
        providers = parse_registry.list_providers("parse")
        names = {p["name"] for p in providers}
        assert "frontmatter" in names
        assert "markdown-ast" in names

    def test_url_pattern_matching(self, parse_registry):
        """Verify URL patterns route to a parse provider."""
        matched = parse_registry.match_provider("parse", "file:///docs/readme.md")
        assert matched in ("frontmatter", "markdown-ast")

    def test_resolve_with_default(self, parse_registry):
        """Verify resolve_provider falls back to default_provider."""
        resolved = parse_registry.resolve_provider(
            "parse",
            provider_name=None,
            url=None,
            default_provider="frontmatter",
        )
        assert resolved == "frontmatter"

    def test_explicit_provider_selection(self, parse_registry):
        """Verify explicit provider name overrides pattern matching."""
        resolved = parse_registry.resolve_provider(
            "parse",
            provider_name="markdown-ast",
            url="file:///docs/readme.md",  # Would match frontmatter too
        )
        assert resolved == "markdown-ast"

    def test_provider_metadata(self, parse_registry):
        """Verify provider metadata is correctly extracted."""
        providers = parse_registry.list_providers("parse")
        fm = next(p for p in providers if p["name"] == "frontmatter")
        assert "*.md" in fm["url_patterns"]
        assert fm["requires_env"] == []
        assert fm["_source"] == "project"
