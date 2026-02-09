# Testing Strategy: Provider System

**Status:** Draft
**Created:** 2026-02-09

## Overview

This document defines the testing strategy for Kurt's provider system. Testing happens at four levels:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TESTING PYRAMID                                   │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌───────────┐
                              │    E2E    │  ← OpenClaw integration
                              │   Tests   │    Real CLI invocation
                              └─────┬─────┘
                                    │
                         ┌──────────┴──────────┐
                         │    Integration      │  ← Tool + Provider + Registry
                         │       Tests         │    Multiple components together
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │              Component Tests              │  ← Registry, Discovery
              │                                           │    URL matching, validation
              └─────────────────────┬─────────────────────┘
                                    │
   ┌────────────────────────────────┴────────────────────────────────────┐
   │                           Unit Tests                                 │  ← Individual providers
   │                                                                      │    Input/output validation
   └──────────────────────────────────────────────────────────────────────┘
```

---

## Level 1: Unit Tests (Providers)

### What to Test

Each provider should have unit tests covering:
- Input validation
- Output format (FetchResult, MapperResult, etc.)
- Error handling
- Edge cases

### Provider Test Template

```python
# tests/tools/fetch/providers/test_notion.py

import pytest
from unittest.mock import Mock, patch
from kurt.tools.fetch.providers.notion.provider import NotionFetcher
from kurt.tools.fetch.core import FetchResult


class TestNotionFetcher:
    """Unit tests for Notion provider."""

    def test_metadata_attributes(self):
        """Provider has required metadata."""
        assert NotionFetcher.name == "notion"
        assert NotionFetcher.version == "1.0.0"
        assert "notion.so/*" in NotionFetcher.url_patterns
        assert "NOTION_TOKEN" in NotionFetcher.requires_env

    def test_fetch_returns_fetch_result(self):
        """fetch() returns FetchResult type."""
        fetcher = NotionFetcher()
        with patch.dict("os.environ", {"NOTION_TOKEN": "test-token"}):
            with patch("notion_client.Client") as mock_client:
                mock_client.return_value.blocks.children.list.return_value = {
                    "results": [{"type": "paragraph", "paragraph": {"text": []}}]
                }
                result = fetcher.fetch("https://notion.so/page-123")

        assert isinstance(result, FetchResult)
        assert hasattr(result, "content")
        assert hasattr(result, "metadata")
        assert hasattr(result, "success")

    def test_fetch_missing_token(self):
        """Returns error when NOTION_TOKEN not set."""
        fetcher = NotionFetcher()
        with patch.dict("os.environ", {}, clear=True):
            result = fetcher.fetch("https://notion.so/page-123")

        assert result.success is False
        assert "NOTION_TOKEN" in result.error

    def test_fetch_invalid_url(self):
        """Handles non-Notion URLs gracefully."""
        fetcher = NotionFetcher()
        with patch.dict("os.environ", {"NOTION_TOKEN": "test-token"}):
            result = fetcher.fetch("https://example.com/not-notion")

        assert result.success is False
        assert "notion" in result.error.lower()

    def test_fetch_api_error(self):
        """Handles Notion API errors."""
        fetcher = NotionFetcher()
        with patch.dict("os.environ", {"NOTION_TOKEN": "test-token"}):
            with patch("notion_client.Client") as mock_client:
                mock_client.return_value.blocks.children.list.side_effect = Exception(
                    "API rate limit"
                )
                result = fetcher.fetch("https://notion.so/page-123")

        assert result.success is False
        assert "rate limit" in result.error.lower() or "error" in result.error.lower()


class TestNotionFetcherURLParsing:
    """Test URL parsing for different Notion URL formats."""

    @pytest.mark.parametrize("url,expected_page_id", [
        ("https://notion.so/page-abc123", "abc123"),
        ("https://notion.so/My-Page-abc123", "abc123"),
        ("https://www.notion.so/workspace/page-abc123", "abc123"),
        ("https://myteam.notion.site/page-abc123", "abc123"),
    ])
    def test_parse_notion_url(self, url, expected_page_id):
        """Extracts page ID from various Notion URL formats."""
        fetcher = NotionFetcher()
        page_id = fetcher._parse_page_id(url)
        assert page_id == expected_page_id
```

### Fixtures for Provider Testing

```python
# tests/conftest.py

import pytest
from unittest.mock import Mock
from kurt.tools.fetch.core import FetchResult, FetcherConfig


@pytest.fixture
def mock_fetch_result():
    """Factory for creating FetchResult fixtures."""
    def _create(
        content: str = "Test content",
        success: bool = True,
        error: str | None = None,
        **metadata
    ) -> FetchResult:
        return FetchResult(
            content=content,
            success=success,
            error=error,
            metadata={"url": "https://example.com", **metadata},
        )
    return _create


@pytest.fixture
def mock_http_response():
    """Mock HTTP response for testing fetchers."""
    def _create(status_code: int = 200, content: str = "<html>Test</html>"):
        response = Mock()
        response.status_code = status_code
        response.text = content
        response.headers = {"content-type": "text/html"}
        return response
    return _create


@pytest.fixture
def env_with_tokens(monkeypatch):
    """Set common API tokens for testing."""
    monkeypatch.setenv("NOTION_TOKEN", "test-notion-token")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
```

---

## Level 2: Component Tests (Registry & Discovery)

### Registry Tests

```python
# tests/tools/core/test_provider_registry.py

import pytest
from pathlib import Path
from kurt.tools.core.provider import ProviderRegistry, get_provider_registry


class TestProviderRegistry:
    """Tests for ProviderRegistry singleton and discovery."""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """Reset singleton between tests."""
        ProviderRegistry._instance = None
        yield
        ProviderRegistry._instance = None

    def test_singleton_pattern(self):
        """Registry is a singleton."""
        reg1 = get_provider_registry()
        reg2 = get_provider_registry()
        assert reg1 is reg2

    def test_discover_builtin_providers(self):
        """Discovers built-in providers."""
        registry = get_provider_registry()
        registry.discover()

        providers = registry.list_providers("fetch")
        names = [p["name"] for p in providers]

        assert "trafilatura" in names
        assert "httpx" in names

    def test_get_provider_instantiates(self):
        """get_provider() returns instantiated provider."""
        registry = get_provider_registry()
        provider = registry.get_provider("fetch", "trafilatura")

        assert provider is not None
        assert hasattr(provider, "fetch")
        assert callable(provider.fetch)

    def test_get_provider_not_found(self):
        """get_provider() returns None for unknown provider."""
        registry = get_provider_registry()
        provider = registry.get_provider("fetch", "nonexistent")
        assert provider is None


class TestURLPatternMatching:
    """Tests for URL pattern matching."""

    @pytest.fixture
    def registry(self):
        registry = get_provider_registry()
        registry.discover()
        return registry

    @pytest.mark.parametrize("url,expected_provider", [
        ("https://notion.so/my-page", "notion"),
        ("https://myteam.notion.site/page", "notion"),
        ("https://twitter.com/user/status/123", "twitterapi"),
        ("https://x.com/user/status/123", "twitterapi"),
        ("https://example.com/article", "trafilatura"),  # fallback
    ])
    def test_match_provider_by_url(self, registry, url, expected_provider):
        """Matches correct provider based on URL."""
        matched = registry.match_provider("fetch", url)
        assert matched == expected_provider

    def test_match_provider_fallback(self, registry):
        """Falls back to wildcard provider for unknown URLs."""
        matched = registry.match_provider("fetch", "https://random-site.com/page")
        assert matched in ["trafilatura", "httpx"]  # Either fallback is OK

    def test_match_provider_unknown_tool(self, registry):
        """Returns None for unknown tool."""
        matched = registry.match_provider("nonexistent", "https://example.com")
        assert matched is None


class TestProviderValidation:
    """Tests for provider requirement validation."""

    @pytest.fixture
    def registry(self):
        registry = get_provider_registry()
        registry.discover()
        return registry

    def test_validate_provider_no_requirements(self, registry):
        """Providers with no requirements return empty list."""
        missing = registry.validate_provider("fetch", "trafilatura")
        assert missing == []

    def test_validate_provider_missing_env(self, registry, monkeypatch):
        """Returns missing env vars."""
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        missing = registry.validate_provider("fetch", "notion")
        assert "NOTION_TOKEN" in missing

    def test_validate_provider_env_present(self, registry, monkeypatch):
        """Returns empty when env vars present."""
        monkeypatch.setenv("NOTION_TOKEN", "test-token")
        missing = registry.validate_provider("fetch", "notion")
        assert missing == []
```

### Discovery Tests

```python
# tests/tools/core/test_discovery.py

import pytest
from pathlib import Path
import tempfile
import shutil
from kurt.tools.core.provider import ProviderRegistry


class TestDiscoveryPrecedence:
    """Tests for provider discovery precedence."""

    @pytest.fixture
    def temp_dirs(self, tmp_path, monkeypatch):
        """Create temp directories for user and project tools."""
        user_tools = tmp_path / "user" / ".kurt" / "tools"
        project_tools = tmp_path / "project" / "kurt" / "tools"

        user_tools.mkdir(parents=True)
        project_tools.mkdir(parents=True)

        monkeypatch.setenv("HOME", str(tmp_path / "user"))
        monkeypatch.setenv("KURT_PROJECT_ROOT", str(tmp_path / "project"))

        return {"user": user_tools, "project": project_tools}

    def test_project_overrides_user(self, temp_dirs):
        """Project providers override user providers."""
        # Create user provider
        user_provider = temp_dirs["user"] / "fetch" / "providers" / "custom"
        user_provider.mkdir(parents=True)
        (user_provider / "provider.py").write_text('''
class CustomFetcher:
    name = "custom"
    version = "1.0.0"
    url_patterns = []
    requires_env = []
    _source = "user"
''')

        # Create project provider with same name
        project_provider = temp_dirs["project"] / "fetch" / "providers" / "custom"
        project_provider.mkdir(parents=True)
        (project_provider / "provider.py").write_text('''
class CustomFetcher:
    name = "custom"
    version = "2.0.0"
    url_patterns = []
    requires_env = []
    _source = "project"
''')

        # Reset and discover
        ProviderRegistry._instance = None
        registry = ProviderRegistry()
        registry.discover()

        providers = registry.list_providers("fetch")
        custom = next(p for p in providers if p["name"] == "custom")

        # Project version wins
        assert custom["version"] == "2.0.0"
        assert custom["_source"] == "project"

    def test_user_overrides_builtin(self, temp_dirs):
        """User providers override builtin providers."""
        # Create user provider that shadows trafilatura
        user_provider = temp_dirs["user"] / "fetch" / "providers" / "trafilatura"
        user_provider.mkdir(parents=True)
        (user_provider / "provider.py").write_text('''
class TrafilaturaFetcher:
    name = "trafilatura"
    version = "99.0.0"  # Override version
    url_patterns = ["*"]
    requires_env = []
''')

        ProviderRegistry._instance = None
        registry = ProviderRegistry()
        registry.discover()

        providers = registry.list_providers("fetch")
        traf = next(p for p in providers if p["name"] == "trafilatura")

        # User version wins
        assert traf["version"] == "99.0.0"
```

---

## Level 3: Integration Tests (Tool + Provider)

### Tool Integration Tests

```python
# tests/tools/fetch/test_fetch_tool_integration.py

import pytest
from kurt.tools.fetch.tool import FetchTool
from kurt.tools.core import ToolContext, ToolResult


class TestFetchToolIntegration:
    """Integration tests for FetchTool with providers."""

    @pytest.fixture
    def tool(self):
        return FetchTool()

    @pytest.fixture
    def context(self):
        return ToolContext()

    @pytest.mark.integration
    async def test_fetch_with_auto_provider(self, tool, context):
        """Auto-selects provider based on URL."""
        params = tool.InputModel(url="https://example.com")
        result = await tool.run(params, context)

        assert isinstance(result, ToolResult)
        assert result.success
        assert len(result.data) > 0
        assert "content" in result.data[0]

    @pytest.mark.integration
    async def test_fetch_with_explicit_provider(self, tool, context):
        """Uses explicitly specified provider."""
        context.settings["_provider_name"] = "httpx"
        params = tool.InputModel(url="https://example.com")
        result = await tool.run(params, context)

        assert result.success
        assert result.data[0]["metadata"]["provider"] == "httpx"

    @pytest.mark.integration
    async def test_fetch_provider_validation_fails(self, tool, context, monkeypatch):
        """Fails when provider requirements not met."""
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        context.settings["_provider_name"] = "notion"
        params = tool.InputModel(url="https://notion.so/page")

        result = await tool.run(params, context)

        assert result.success is False
        assert "NOTION_TOKEN" in str(result.errors)

    @pytest.mark.integration
    async def test_fetch_progress_callback(self, tool, context):
        """Progress callback is invoked."""
        events = []

        def on_progress(event):
            events.append(event)

        params = tool.InputModel(url="https://example.com")
        await tool.run(params, context, on_progress=on_progress)

        assert len(events) > 0
        assert any(e.status == "completed" for e in events)


class TestMapToolIntegration:
    """Integration tests for MapTool with providers."""

    @pytest.fixture
    def tool(self):
        from kurt.tools.map.tool import MapTool
        return MapTool()

    @pytest.mark.integration
    async def test_map_sitemap(self, tool):
        """Maps URLs from sitemap."""
        context = ToolContext()
        params = tool.InputModel(source="https://example.com/sitemap.xml")
        result = await tool.run(params, context)

        assert isinstance(result, ToolResult)
        # May fail if sitemap doesn't exist, but should not crash
        assert isinstance(result.success, bool)

    @pytest.mark.integration
    async def test_map_folder(self, tool, tmp_path):
        """Maps files from folder."""
        # Create test files
        (tmp_path / "doc1.md").write_text("# Doc 1")
        (tmp_path / "doc2.md").write_text("# Doc 2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "doc3.md").write_text("# Doc 3")

        context = ToolContext()
        params = tool.InputModel(
            source=str(tmp_path),
            engine="folder",
            pattern="**/*.md",
        )
        result = await tool.run(params, context)

        assert result.success
        assert len(result.data) == 3
```

### Workflow Integration Tests

```python
# tests/workflows/test_workflow_with_providers.py

import pytest
from pathlib import Path


class TestWorkflowWithProviders:
    """Integration tests for workflows using the provider system."""

    @pytest.fixture
    def workflow_toml(self, tmp_path):
        """Create a test workflow."""
        workflow = tmp_path / "test-workflow.toml"
        workflow.write_text('''
[workflow]
name = "test-pipeline"

[steps.discover]
type = "map"
config.source = "./docs"
config.engine = "folder"
config.pattern = "*.md"

[steps.fetch]
type = "fetch"
config.provider = "httpx"
depends_on = ["discover"]
''')
        return workflow

    @pytest.mark.integration
    async def test_workflow_executes_with_providers(self, workflow_toml, tmp_path):
        """Workflow executes using provider system."""
        from kurt.workflows.toml import execute_workflow

        # Create test docs
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.md").write_text("# Test\nhttps://example.com")

        result = await execute_workflow(workflow_toml)

        assert result["status"] == "completed"
        assert "discover" in result["steps"]
        assert "fetch" in result["steps"]
```

---

## Level 4: E2E Tests (OpenClaw Integration)

### CLI E2E Tests

```python
# tests/e2e/test_cli_e2e.py

import pytest
import subprocess
import json


class TestCLIE2E:
    """End-to-end tests via CLI."""

    @pytest.mark.e2e
    def test_kurt_fetch_json_output(self):
        """kurt fetch returns valid JSON."""
        result = subprocess.run(
            ["kurt", "fetch", "https://example.com", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "success" in data
        assert "data" in data

    @pytest.mark.e2e
    def test_kurt_tool_list(self):
        """kurt tool list shows available tools."""
        result = subprocess.run(
            ["kurt", "tool", "list", "--output", "json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        tools = [t["name"] for t in data]
        assert "fetch" in tools
        assert "map" in tools

    @pytest.mark.e2e
    def test_kurt_tool_providers(self):
        """kurt tool providers shows available providers."""
        result = subprocess.run(
            ["kurt", "tool", "providers", "fetch", "--output", "json"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        names = [p["name"] for p in data]
        assert "trafilatura" in names

    @pytest.mark.e2e
    def test_kurt_tool_check(self):
        """kurt tool check validates requirements."""
        result = subprocess.run(
            ["kurt", "tool", "check", "fetch"],
            capture_output=True,
            text=True,
        )

        # Should succeed (trafilatura has no requirements)
        assert result.returncode == 0
        assert "valid" in result.stdout.lower() or "✓" in result.stdout


class TestOpenClawE2E:
    """End-to-end tests for OpenClaw skill integration."""

    @pytest.fixture
    def skill_path(self, tmp_path):
        """Install skill to temp location."""
        skill_dir = tmp_path / ".claude" / "skills" / "kurt"
        skill_dir.mkdir(parents=True)

        # Copy skill files
        import shutil
        from kurt import __path__ as kurt_path
        src = Path(kurt_path[0]) / "integrations" / "openclaw"
        if src.exists():
            shutil.copytree(src, skill_dir, dirs_exist_ok=True)
        else:
            # Create minimal skill for testing
            (skill_dir / "skill.py").write_text('''
import subprocess, sys, json
result = subprocess.run(["kurt"] + sys.argv[1:] + ["--output", "json"],
                       capture_output=True, text=True)
print(result.stdout or result.stderr)
''')

        return skill_dir

    @pytest.mark.e2e
    def test_skill_invocation(self, skill_path):
        """Skill can be invoked directly."""
        result = subprocess.run(
            ["python", str(skill_path / "skill.py"), "fetch", "https://example.com"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should produce JSON output
        try:
            data = json.loads(result.stdout)
            assert "success" in data or "error" in data
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output: {result.stdout}")

    @pytest.mark.e2e
    def test_skill_md_exists(self, skill_path):
        """SKILL.md manifest exists."""
        skill_md = skill_path / "SKILL.md"
        # May not exist if not yet implemented
        if skill_md.exists():
            content = skill_md.read_text()
            assert "name: kurt" in content
            assert "actions:" in content
```

---

## Test Configuration

### pytest.ini

```ini
[pytest]
markers =
    integration: Integration tests (require network/filesystem)
    e2e: End-to-end tests (require full installation)
    slow: Slow tests (external API calls)

testpaths = tests
asyncio_mode = auto

# Default: skip slow tests
addopts = -m "not e2e and not slow"
```

### Running Tests

```bash
# Unit tests only (fast)
pytest tests/tools/fetch/providers/

# Component tests
pytest tests/tools/core/

# Integration tests
pytest -m integration

# E2E tests (requires installation)
pytest -m e2e

# All tests
pytest -m ""

# With coverage
pytest --cov=kurt.tools --cov-report=html
```

### CI Pipeline

```yaml
# .github/workflows/test.yml

name: Test Provider System

on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/tools/ -m "not integration and not e2e"

  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e ".[dev]"
      - run: pytest -m integration

  e2e:
    runs-on: ubuntu-latest
    needs: [unit, integration]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -e ".[dev]"
      - run: pytest -m e2e
```

---

## Test Utilities

### Mock Providers

```python
# tests/mocks/providers.py

from kurt.tools.fetch.core import BaseFetcher, FetchResult


class MockFetcher(BaseFetcher):
    """Mock fetcher for testing."""

    name = "mock"
    version = "1.0.0"
    url_patterns = ["mock://*"]
    requires_env = []

    def __init__(self, response: FetchResult | None = None):
        self._response = response or FetchResult(
            content="Mock content",
            success=True,
            metadata={"source": "mock"},
        )

    def fetch(self, url: str) -> FetchResult:
        return self._response


class FailingFetcher(BaseFetcher):
    """Fetcher that always fails."""

    name = "failing"
    version = "1.0.0"
    url_patterns = []
    requires_env = []

    def fetch(self, url: str) -> FetchResult:
        return FetchResult(
            content="",
            success=False,
            error="Intentional failure for testing",
        )
```

### Registry Test Helpers

```python
# tests/helpers/registry.py

from contextlib import contextmanager
from kurt.tools.core.provider import ProviderRegistry


@contextmanager
def isolated_registry():
    """Context manager for isolated registry testing."""
    # Save original
    original = ProviderRegistry._instance

    # Reset
    ProviderRegistry._instance = None

    try:
        yield ProviderRegistry()
    finally:
        # Restore
        ProviderRegistry._instance = original


@contextmanager
def mock_provider(tool_name: str, provider_class):
    """Temporarily register a mock provider."""
    registry = ProviderRegistry()
    original = registry._providers.get(tool_name, {}).copy()

    try:
        if tool_name not in registry._providers:
            registry._providers[tool_name] = {}
        registry._providers[tool_name][provider_class.name] = provider_class
        yield
    finally:
        registry._providers[tool_name] = original
```

---

## Coverage Requirements

| Component | Min Coverage | Notes |
|-----------|--------------|-------|
| Provider classes | 80% | Core fetch/map logic |
| ProviderRegistry | 90% | Critical discovery logic |
| URL matching | 95% | Must be reliable |
| Tool integration | 70% | Complex async code |
| CLI commands | 60% | E2E covers more |

---

## Summary

| Level | What | How | When |
|-------|------|-----|------|
| **Unit** | Individual providers | pytest, mocks | Every commit |
| **Component** | Registry, discovery | pytest, temp dirs | Every commit |
| **Integration** | Tool + providers | pytest -m integration | PR merge |
| **E2E** | CLI, OpenClaw | subprocess, real install | Release |

**Key Testing Principles:**

1. **Providers are pure** — Easy to unit test with mocks
2. **Registry is singleton** — Reset between tests
3. **Discovery is filesystem** — Use temp directories
4. **E2E validates integration** — Real CLI invocation

---

*Testing strategy created: 2026-02-09*
