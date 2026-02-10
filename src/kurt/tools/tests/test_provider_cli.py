"""Tests for the provider CLI commands (kurt tool list/info/check/providers)."""

import json

import pytest
from click.testing import CliRunner

from kurt.tools.cli import tools_group
from kurt.tools.core.provider import ProviderRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the singleton registry before each test."""
    registry = ProviderRegistry()
    registry.reset()
    yield
    registry.reset()


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_providers(tmp_path):
    """Create mock provider files for testing."""
    # Create a mock fetch tool with two providers
    fetch_dir = tmp_path / "fetch" / "providers"

    alpha_dir = fetch_dir / "alpha"
    alpha_dir.mkdir(parents=True)
    (alpha_dir / "provider.py").write_text(
        """
from pydantic import BaseModel

class AlphaFetcher:
    name = "alpha"
    version = "2.0.0"
    url_patterns = ["*.example.com/*"]
    requires_env = ["ALPHA_KEY"]

    def fetch(self, url):
        return {"content": url}
"""
    )

    beta_dir = fetch_dir / "beta"
    beta_dir.mkdir(parents=True)
    (beta_dir / "provider.py").write_text(
        """
class BetaFetcher:
    name = "beta"
    version = "1.0.0"
    url_patterns = ["*"]
    requires_env = []

    def fetch(self, url):
        return {"content": url}
"""
    )

    # Create a mock parse tool with one provider
    parse_dir = tmp_path / "parse" / "providers" / "json-parser"
    parse_dir.mkdir(parents=True)
    (parse_dir / "provider.py").write_text(
        """
class JsonParser:
    name = "json-parser"
    version = "1.0.0"
    url_patterns = ["*.json"]
    requires_env = []

    def parse(self, source):
        return {}
"""
    )

    # Register with registry
    registry = ProviderRegistry()
    registry.discover_from([(tmp_path, "project")])

    return tmp_path


# ---------------------------------------------------------------------------
# kurt tool list
# ---------------------------------------------------------------------------


class TestListCommand:
    def test_list_table_output(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["list"])
        assert result.exit_code == 0
        assert "fetch" in result.output
        assert "parse" in result.output

    def test_list_json_output(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        names = {t["name"] for t in data}
        assert "fetch" in names
        assert "parse" in names
        # Check structure
        fetch = next(t for t in data if t["name"] == "fetch")
        assert fetch["provider_count"] == 2
        assert len(fetch["providers"]) == 2

    def test_list_filter_source(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["list", "--json", "--source", "project"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        for tool in data:
            assert tool["source"] == "project"

    def test_list_no_tools(self, runner):
        # Mark registry as already discovered (empty) to prevent
        # it from scanning the real filesystem during the command
        registry = ProviderRegistry()
        registry._discovered = True
        result = runner.invoke(tools_group, ["list"])
        assert result.exit_code == 0
        assert "No tools found" in result.output


# ---------------------------------------------------------------------------
# kurt tool info
# ---------------------------------------------------------------------------


class TestInfoCommand:
    def test_info_table_output(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["info", "fetch"])
        assert result.exit_code == 0
        assert "fetch" in result.output
        assert "alpha" in result.output
        assert "beta" in result.output

    def test_info_json_output(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["info", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["name"] == "fetch"
        assert len(data["providers"]) == 2
        alpha = next(p for p in data["providers"] if p["name"] == "alpha")
        assert alpha["version"] == "2.0.0"
        assert "ALPHA_KEY" in alpha["requires_env"]

    def test_info_not_found(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["info", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# kurt tool providers
# ---------------------------------------------------------------------------


class TestProvidersCommand:
    def test_providers_output(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["providers", "fetch"])
        assert result.exit_code == 0
        assert "alpha" in result.output
        assert "beta" in result.output
        assert "ALPHA_KEY" in result.output

    def test_providers_json(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["providers", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2
        names = {p["name"] for p in data}
        assert names == {"alpha", "beta"}

    def test_providers_not_found(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["providers", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# kurt tool check
# ---------------------------------------------------------------------------


class TestCheckCommand:
    def test_check_all(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["check"])
        assert result.exit_code == 0
        assert "fetch" in result.output
        assert "parse" in result.output

    def test_check_specific_tool(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["check", "fetch"])
        assert result.exit_code == 0
        assert "fetch" in result.output
        # alpha requires ALPHA_KEY which is not set
        assert "ALPHA_KEY" in result.output

    def test_check_json(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["tool"] == "fetch"
        alpha = next(p for p in data["providers"] if p["name"] == "alpha")
        assert alpha["valid"] is False
        assert "ALPHA_KEY" in alpha["missing_env"]
        beta = next(p for p in data["providers"] if p["name"] == "beta")
        assert beta["valid"] is True

    def test_check_not_found(self, runner, mock_providers):
        result = runner.invoke(tools_group, ["check", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_check_all_valid(self, runner, mock_providers, monkeypatch):
        monkeypatch.setenv("ALPHA_KEY", "test_value")
        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["all_valid"] is True
