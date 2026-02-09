"""Tests for tool/provider scaffolding commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.tools.provider_cli import new_provider_cmd, new_tool_cmd
from kurt.tools.templates.scaffolds import (
    _capitalize,
    render_base_py,
    render_init_py,
    render_provider_config_py,
    render_provider_py,
    render_tool_py,
)


# ---------------------------------------------------------------------------
# Template rendering tests
# ---------------------------------------------------------------------------


class TestCapitalize:
    def test_simple(self):
        assert _capitalize("fetch") == "Fetch"

    def test_snake_case(self):
        assert _capitalize("my_tool") == "MyTool"

    def test_kebab_case(self):
        assert _capitalize("my-tool") == "MyTool"


class TestRenderToolPy:
    def test_contains_class(self):
        result = render_tool_py("parse")
        assert "class ParseTool(" in result
        assert "class ParseInput(" in result
        assert "class ParseOutput(" in result

    def test_contains_name(self):
        result = render_tool_py("parse")
        assert 'name = "parse"' in result

    def test_uses_description(self):
        result = render_tool_py("parse", "Parse documents")
        assert "Parse documents" in result

    def test_snake_case_name(self):
        result = render_tool_py("my_tool")
        assert "class MyToolTool(" in result


class TestRenderBasePy:
    def test_contains_base_class(self):
        result = render_base_py("parse")
        assert "class BaseParse(ABC):" in result
        assert "class ParseResult(" in result

    def test_contains_abstract_method(self):
        result = render_base_py("parse")
        assert "@abstractmethod" in result
        assert "def process(" in result


class TestRenderProviderPy:
    def test_contains_provider_class(self):
        result = render_provider_py("parse", "frontmatter")
        assert "class FrontmatterParse(" in result
        assert 'name = "frontmatter"' in result

    def test_self_contained(self):
        """Provider should define its own Result model (no relative imports)."""
        result = render_provider_py("parse", "my-api")
        assert "class ParseResult(" in result
        assert "from ..." not in result


class TestRenderProviderConfigPy:
    def test_contains_config_class(self):
        result = render_provider_config_py("parse", "frontmatter")
        assert "class FrontmatterParseProviderConfig(" in result

    def test_has_timeout(self):
        result = render_provider_config_py("parse", "default")
        assert "timeout" in result


class TestRenderInitPy:
    def test_contains_imports(self):
        result = render_init_py("parse")
        assert "from kurt.tools.parse.tool import" in result
        assert "ParseTool" in result


# ---------------------------------------------------------------------------
# CLI command tests
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """Create a temporary project with kurt.toml."""
    (tmp_path / "kurt.toml").write_text("")
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestNewToolCmd:
    def test_creates_tool_files(self, runner, project_dir):
        """Creates all expected tool files."""
        result = runner.invoke(new_tool_cmd, ["my-parser"])

        assert result.exit_code == 0
        tool_dir = project_dir / "kurt" / "tools" / "my-parser"
        assert (tool_dir / "tool.py").exists()
        assert (tool_dir / "base.py").exists()
        assert (tool_dir / "__init__.py").exists()
        assert (tool_dir / "providers" / "__init__.py").exists()
        assert (tool_dir / "providers" / "default" / "__init__.py").exists()
        assert (tool_dir / "providers" / "default" / "provider.py").exists()
        assert (tool_dir / "providers" / "default" / "config.py").exists()

    def test_tool_py_content(self, runner, project_dir):
        """Generated tool.py has correct class name."""
        runner.invoke(new_tool_cmd, ["my-parser"])

        content = (project_dir / "kurt" / "tools" / "my-parser" / "tool.py").read_text()
        assert "class MyParserTool(" in content
        assert 'name = "my-parser"' in content

    def test_provider_py_is_self_contained(self, runner, project_dir):
        """Generated provider.py has no relative imports."""
        runner.invoke(new_tool_cmd, ["my-parser"])

        content = (
            project_dir
            / "kurt"
            / "tools"
            / "my-parser"
            / "providers"
            / "default"
            / "provider.py"
        ).read_text()
        assert "from ..." not in content
        assert "class MyParserResult(" in content

    def test_shows_next_steps(self, runner, project_dir):
        """Shows helpful next steps after creation."""
        result = runner.invoke(new_tool_cmd, ["my-parser"])

        assert "Next steps" in result.output
        assert "tool.py" in result.output
        assert "kurt tool check" in result.output

    def test_errors_if_exists(self, runner, project_dir):
        """Errors if tool directory already exists."""
        runner.invoke(new_tool_cmd, ["my-parser"])
        result = runner.invoke(new_tool_cmd, ["my-parser"])

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_errors_without_project(self, runner, tmp_path, monkeypatch):
        """Errors if not in a Kurt project."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(new_tool_cmd, ["my-parser"])

        assert result.exit_code != 0
        assert "kurt.toml" in result.output

    def test_user_location(self, runner, tmp_path, monkeypatch):
        """--location user creates in ~/.kurt/tools/."""
        monkeypatch.chdir(tmp_path)
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)

        result = runner.invoke(new_tool_cmd, ["my-parser", "--location", "user"])

        assert result.exit_code == 0
        assert (home / ".kurt" / "tools" / "my-parser" / "tool.py").exists()

    def test_with_description(self, runner, project_dir):
        """--description flag sets tool description."""
        runner.invoke(new_tool_cmd, ["my-parser", "-d", "Parse structured data"])

        content = (project_dir / "kurt" / "tools" / "my-parser" / "tool.py").read_text()
        assert "Parse structured data" in content


class TestNewProviderCmd:
    def test_creates_provider_files(self, runner, project_dir):
        """Creates provider directory with files."""
        result = runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        assert result.exit_code == 0
        provider_dir = project_dir / "kurt" / "tools" / "fetch" / "providers" / "my-api"
        assert (provider_dir / "__init__.py").exists()
        assert (provider_dir / "provider.py").exists()
        assert (provider_dir / "config.py").exists()

    def test_provider_content(self, runner, project_dir):
        """Generated provider.py has correct class name."""
        runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        content = (
            project_dir
            / "kurt"
            / "tools"
            / "fetch"
            / "providers"
            / "my-api"
            / "provider.py"
        ).read_text()
        assert "class MyApiFetch(" in content
        assert 'name = "my-api"' in content

    def test_shows_next_steps(self, runner, project_dir):
        """Shows helpful next steps after creation."""
        result = runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        assert "Next steps" in result.output
        assert "provider.py" in result.output

    def test_errors_if_exists(self, runner, project_dir):
        """Errors if provider directory already exists."""
        runner.invoke(new_provider_cmd, ["fetch", "my-api"])
        result = runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_errors_without_project(self, runner, tmp_path, monkeypatch):
        """Errors if not in a Kurt project."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        assert result.exit_code != 0
        assert "kurt.toml" in result.output

    def test_user_location(self, runner, tmp_path, monkeypatch):
        """--location user creates in ~/.kurt/tools/."""
        monkeypatch.chdir(tmp_path)
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: home)

        result = runner.invoke(
            new_provider_cmd, ["fetch", "my-api", "--location", "user"]
        )

        assert result.exit_code == 0
        assert (
            home / ".kurt" / "tools" / "fetch" / "providers" / "my-api" / "provider.py"
        ).exists()
