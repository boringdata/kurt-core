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


# ---------------------------------------------------------------------------
# kurt tool check: ConfigModel validation (bd-26w.5.2)
# ---------------------------------------------------------------------------


@pytest.fixture
def config_providers(tmp_path):
    """Create mock providers with ConfigModel for config validation tests."""
    fetch_dir = tmp_path / "fetch" / "providers"

    # Provider with a ConfigModel that has typed fields
    typed_dir = fetch_dir / "typed"
    typed_dir.mkdir(parents=True)
    (typed_dir / "provider.py").write_text(
        """
from pydantic import BaseModel, Field

class TypedConfig(BaseModel):
    timeout: int = 30
    retries: int = Field(default=3, ge=0, le=10)
    format: str = "markdown"

class TypedFetcher:
    name = "typed"
    version = "1.0.0"
    url_patterns = []
    requires_env = []
    ConfigModel = TypedConfig

    def fetch(self, url):
        return {"content": url}
"""
    )

    # Provider WITHOUT a ConfigModel (should be gracefully skipped)
    plain_dir = fetch_dir / "plain"
    plain_dir.mkdir(parents=True)
    (plain_dir / "provider.py").write_text(
        """
class PlainFetcher:
    name = "plain"
    version = "1.0.0"
    url_patterns = ["*"]
    requires_env = []

    def fetch(self, url):
        return {"content": url}
"""
    )

    # Register with registry
    registry = ProviderRegistry()
    registry.discover_from([(tmp_path, "project")])

    return tmp_path


class TestCheckConfigValidation:
    """Tests for provider ConfigModel validation in 'kurt tool check' (bd-26w.5.2).

    These tests verify that ``check_cmd`` validates provider configuration
    from TOML files using ProviderConfigResolver + provider ConfigModel.
    """

    def test_check_config_valid_defaults(self, runner, config_providers):
        """Provider with ConfigModel and no TOML config uses defaults successfully."""
        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        typed = next(p for p in data["providers"] if p["name"] == "typed")
        # Config should validate with defaults (no TOML file)
        assert typed["config_valid"] is True
        assert typed["config_errors"] == []

    def test_check_config_invalid_type_in_toml(self, runner, config_providers, monkeypatch):
        """Invalid TOML value type surfaces as config error."""
        # Create a project kurt.toml with an invalid timeout (string instead of int)
        toml_path = config_providers / "kurt.toml"
        toml_path.write_text(
            """
[tool.fetch.providers.typed]
timeout = "not-an-integer"
"""
        )
        # Point resolver to this project root
        monkeypatch.chdir(config_providers)
        from kurt.config.provider_config import ProviderConfigResolver

        ProviderConfigResolver().reset()

        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        typed = next(p for p in data["providers"] if p["name"] == "typed")
        assert typed["config_valid"] is False
        assert len(typed["config_errors"]) > 0
        # Error should mention the field name
        error_text = " ".join(typed["config_errors"]).lower()
        assert "timeout" in error_text

    def test_check_config_invalid_range_in_toml(self, runner, config_providers, monkeypatch):
        """Out-of-range value (retries > 10) surfaces as config error."""
        toml_path = config_providers / "kurt.toml"
        toml_path.write_text(
            """
[tool.fetch.providers.typed]
retries = 99
"""
        )
        monkeypatch.chdir(config_providers)
        from kurt.config.provider_config import ProviderConfigResolver

        ProviderConfigResolver().reset()

        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        typed = next(p for p in data["providers"] if p["name"] == "typed")
        assert typed["config_valid"] is False
        error_text = " ".join(typed["config_errors"]).lower()
        assert "retries" in error_text

    def test_check_config_valid_toml_overrides(self, runner, config_providers, monkeypatch):
        """Valid TOML config values pass validation."""
        toml_path = config_providers / "kurt.toml"
        toml_path.write_text(
            """
[tool.fetch.providers.typed]
timeout = 60
retries = 5
format = "html"
"""
        )
        monkeypatch.chdir(config_providers)
        from kurt.config.provider_config import ProviderConfigResolver

        ProviderConfigResolver().reset()

        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        typed = next(p for p in data["providers"] if p["name"] == "typed")
        assert typed["config_valid"] is True
        assert typed["config_errors"] == []

    def test_check_config_skipped_without_config_model(self, runner, config_providers):
        """Provider without ConfigModel skips config validation gracefully."""
        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        plain = next(p for p in data["providers"] if p["name"] == "plain")
        # No ConfigModel -> config_valid should be None (not checked)
        assert plain["config_valid"] is None
        assert plain["config_errors"] == []

    def test_check_config_shown_in_text_output(self, runner, config_providers, monkeypatch):
        """Config errors appear in human-readable text output."""
        toml_path = config_providers / "kurt.toml"
        toml_path.write_text(
            """
[tool.fetch.providers.typed]
timeout = "bad"
"""
        )
        monkeypatch.chdir(config_providers)
        from kurt.config.provider_config import ProviderConfigResolver

        ProviderConfigResolver().reset()

        result = runner.invoke(tools_group, ["check", "fetch"])
        assert result.exit_code == 0
        # Should show config error in output
        assert "config" in result.output.lower()

    def test_check_all_valid_includes_config(self, runner, config_providers):
        """all_valid is True only when both env AND config are valid."""
        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["all_valid"] is True

    def test_check_all_valid_false_on_config_error(self, runner, config_providers, monkeypatch):
        """all_valid is False when config validation fails."""
        toml_path = config_providers / "kurt.toml"
        toml_path.write_text(
            """
[tool.fetch.providers.typed]
timeout = "invalid"
"""
        )
        monkeypatch.chdir(config_providers)
        from kurt.config.provider_config import ProviderConfigResolver

        ProviderConfigResolver().reset()

        result = runner.invoke(tools_group, ["check", "fetch", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["all_valid"] is False
