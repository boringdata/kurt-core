"""Tests for 'kurt tool new' and 'kurt tool new-provider' CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from kurt.tools.provider_cli import new_provider_cmd, new_tool_cmd


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_root(tmp_path):
    """Create a fake project root with kurt.toml."""
    (tmp_path / "kurt.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "kurt" / "tools").mkdir(parents=True)
    return tmp_path


class TestNewToolCmd:
    def test_creates_tool_structure(self, runner, project_root):
        """Creates full tool directory structure."""
        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            result = runner.invoke(new_tool_cmd, ["parse"])

        assert result.exit_code == 0
        tool_dir = project_root / "kurt" / "tools" / "parse"
        assert (tool_dir / "tool.py").exists()
        assert (tool_dir / "base.py").exists()
        assert (tool_dir / "__init__.py").exists()
        assert (tool_dir / "providers" / "__init__.py").exists()
        assert (tool_dir / "providers" / "default" / "__init__.py").exists()
        assert (tool_dir / "providers" / "default" / "provider.py").exists()
        assert (tool_dir / "providers" / "default" / "config.py").exists()

    def test_tool_py_has_class(self, runner, project_root):
        """Generated tool.py contains the tool class."""
        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            runner.invoke(new_tool_cmd, ["parse"])

        content = (project_root / "kurt" / "tools" / "parse" / "tool.py").read_text()
        assert "class ParseTool" in content

    def test_shows_next_steps(self, runner, project_root):
        """Output includes next steps guidance."""
        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            result = runner.invoke(new_tool_cmd, ["parse"])

        assert "Next steps" in result.output
        assert "kurt tool check parse" in result.output

    def test_fails_if_exists(self, runner, project_root):
        """Fails if tool directory already exists."""
        (project_root / "kurt" / "tools" / "parse").mkdir(parents=True)

        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            result = runner.invoke(new_tool_cmd, ["parse"])

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_fails_without_project(self, runner):
        """Fails if not in a project."""
        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=None,
        ):
            result = runner.invoke(new_tool_cmd, ["parse"])

        assert result.exit_code != 0
        assert "kurt.toml" in result.output

    def test_user_location(self, runner, tmp_path):
        """--location user creates in ~/.kurt/tools/."""
        with patch("kurt.tools.provider_cli.Path") as mock_path:
            mock_path.home.return_value = tmp_path
            mock_path.cwd = Path.cwd
            # Ensure Path() constructor works normally for non-home calls
            mock_path.side_effect = lambda *a, **kw: Path(*a, **kw)
            mock_path.home.return_value = tmp_path

            result = runner.invoke(new_tool_cmd, ["parse", "--location", "user"])

        assert result.exit_code == 0
        tool_dir = tmp_path / ".kurt" / "tools" / "parse"
        assert (tool_dir / "tool.py").exists()

    def test_custom_description(self, runner, project_root):
        """--description adds custom description."""
        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            result = runner.invoke(
                new_tool_cmd, ["parse", "-d", "Parse files into structured data"]
            )

        assert result.exit_code == 0
        content = (project_root / "kurt" / "tools" / "parse" / "tool.py").read_text()
        assert "Parse files into structured data" in content


class TestNewProviderCmd:
    def test_creates_provider_structure(self, runner, project_root):
        """Creates provider directory with files."""
        # Create tool first
        tool_dir = project_root / "kurt" / "tools" / "fetch" / "providers"
        tool_dir.mkdir(parents=True)

        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            result = runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        assert result.exit_code == 0
        provider_dir = tool_dir / "my-api"
        assert (provider_dir / "__init__.py").exists()
        assert (provider_dir / "provider.py").exists()
        assert (provider_dir / "config.py").exists()

    def test_provider_py_has_class(self, runner, project_root):
        """Generated provider.py contains the provider class."""
        (project_root / "kurt" / "tools" / "fetch" / "providers").mkdir(parents=True)

        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        content = (
            project_root
            / "kurt"
            / "tools"
            / "fetch"
            / "providers"
            / "my-api"
            / "provider.py"
        ).read_text()
        assert "class MyApiFetch" in content
        assert 'name = "my-api"' in content

    def test_shows_next_steps(self, runner, project_root):
        """Output includes next steps guidance."""
        (project_root / "kurt" / "tools" / "fetch" / "providers").mkdir(parents=True)

        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            result = runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        assert "Next steps" in result.output
        assert "kurt tool check fetch" in result.output

    def test_fails_if_exists(self, runner, project_root):
        """Fails if provider already exists."""
        provider_dir = (
            project_root / "kurt" / "tools" / "fetch" / "providers" / "my-api"
        )
        provider_dir.mkdir(parents=True)

        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=project_root,
        ):
            result = runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_fails_without_project(self, runner):
        """Fails if not in a project."""
        with patch(
            "kurt.tools.provider_cli._find_project_root",
            return_value=None,
        ):
            result = runner.invoke(new_provider_cmd, ["fetch", "my-api"])

        assert result.exit_code != 0
        assert "kurt.toml" in result.output
