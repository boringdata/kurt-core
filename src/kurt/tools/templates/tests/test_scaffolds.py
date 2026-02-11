"""Tests for tool and provider scaffold templates."""

from __future__ import annotations

import ast

from kurt.tools.templates.scaffolds import (
    _capitalize,
    render_base_py,
    render_init_py,
    render_provider_config_py,
    render_provider_py,
    render_tool_py,
)


class TestCapitalize:
    def test_simple(self):
        assert _capitalize("parse") == "Parse"

    def test_snake_case(self):
        assert _capitalize("my_tool") == "MyTool"

    def test_kebab_case(self):
        assert _capitalize("my-tool") == "MyTool"

    def test_mixed(self):
        assert _capitalize("my-fancy_tool") == "MyFancyTool"


class TestRenderToolPy:
    def test_valid_python(self):
        """Generated tool.py should be valid Python."""
        source = render_tool_py("parse")
        ast.parse(source)

    def test_contains_tool_class(self):
        source = render_tool_py("parse")
        assert "class ParseTool" in source
        assert "class ParseInput" in source
        assert "class ParseOutput" in source

    def test_custom_description(self):
        source = render_tool_py("parse", description="Parse files")
        assert "Parse files" in source

    def test_default_description(self):
        source = render_tool_py("parse")
        assert "Parse tool" in source

    def test_snake_case_name(self):
        source = render_tool_py("my_tool")
        assert "class MyToolTool" in source
        assert 'name = "my_tool"' in source


class TestRenderBasePy:
    def test_valid_python(self):
        source = render_base_py("parse")
        ast.parse(source)

    def test_contains_base_class(self):
        source = render_base_py("parse")
        assert "class BaseParse" in source
        assert "class ParseResult" in source

    def test_abstract_method(self):
        source = render_base_py("parse")
        assert "@abstractmethod" in source
        assert "def process" in source


class TestRenderInitPy:
    def test_valid_python(self):
        source = render_init_py("parse")
        ast.parse(source)

    def test_exports(self):
        source = render_init_py("parse")
        assert "ParseTool" in source
        assert "__all__" in source


class TestRenderProviderPy:
    def test_valid_python(self):
        source = render_provider_py("parse", "default")
        ast.parse(source)

    def test_contains_provider_class(self):
        source = render_provider_py("parse", "default")
        assert "class DefaultParse" in source
        assert 'name = "default"' in source

    def test_self_contained(self):
        """Provider should not use relative imports."""
        source = render_provider_py("parse", "default")
        assert "from ." not in source
        assert "from .." not in source

    def test_has_result_model(self):
        """Provider defines its own Result model."""
        source = render_provider_py("parse", "default")
        assert "class ParseResult" in source

    def test_custom_provider_name(self):
        source = render_provider_py("fetch", "my_api")
        assert "class MyApiFetch" in source
        assert 'name = "my_api"' in source


class TestRenderProviderConfigPy:
    def test_valid_python(self):
        source = render_provider_config_py("parse", "default")
        ast.parse(source)

    def test_contains_config_class(self):
        source = render_provider_config_py("parse", "default")
        assert "class DefaultParseProviderConfig" in source

    def test_has_timeout_field(self):
        source = render_provider_config_py("parse", "default")
        assert "timeout" in source
