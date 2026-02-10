"""
Integration tests for workflow executor with provider resolution.

Verifies that the provider system integrates correctly with workflow
execution: explicit provider selection, deprecated engine, URL pattern
matching, default provider fallback, and multi-step workflows.
"""

from __future__ import annotations

import warnings
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kurt.tools.core import ToolResult, ToolResultError
from kurt.workflows.toml.executor import execute_workflow
from kurt.workflows.toml.parser import InputDef, StepDef, WorkflowDefinition, WorkflowMeta

# ============================================================================
# Helpers
# ============================================================================


def make_workflow(
    name: str = "test_workflow",
    inputs: dict[str, InputDef] | None = None,
    steps: dict[str, StepDef] | None = None,
) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow=WorkflowMeta(name=name),
        inputs=inputs or {},
        steps=steps or {},
    )


def make_step(
    step_type: str = "fetch",
    depends_on: list[str] | None = None,
    config: dict[str, Any] | None = None,
) -> StepDef:
    return StepDef(
        type=step_type,
        depends_on=depends_on or [],
        config=config or {},
    )


def make_tool_result(
    success: bool = True,
    data: list[dict[str, Any]] | None = None,
    errors: list[ToolResultError] | None = None,
) -> ToolResult:
    return ToolResult(success=success, data=data or [], errors=errors or [])


# ============================================================================
# Explicit Provider Selection
# ============================================================================


class TestExplicitProviderSelection:
    """Verify config.provider is consumed and injected as engine."""

    @pytest.mark.asyncio
    async def test_provider_passed_as_engine_to_tool(self):
        """config.provider is removed and injected as engine in params."""
        workflow = make_workflow(
            steps={
                "fetch_step": make_step(
                    "fetch",
                    config={"provider": "tavily", "url": "https://example.com"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True, data=[{"content": "ok"}])

        with patch(
            "kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert captured["fetch"]["engine"] == "tavily"
        assert "provider" not in captured["fetch"]

    @pytest.mark.asyncio
    async def test_provider_for_map_tool(self):
        """config.provider works for map tool."""
        workflow = make_workflow(
            steps={
                "map_step": make_step(
                    "map",
                    config={"provider": "sitemap", "source": "https://example.com/sitemap.xml"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True, data=[{"url": "https://example.com/page"}])

        with patch(
            "kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert captured["map"]["engine"] == "sitemap"


# ============================================================================
# Deprecated Engine Config
# ============================================================================


class TestDeprecatedEngineConfig:
    """Verify config.engine works with deprecation warning."""

    @pytest.mark.asyncio
    async def test_engine_emits_deprecation_warning(self):
        """config.engine triggers DeprecationWarning."""
        workflow = make_workflow(
            steps={
                "fetch_step": make_step(
                    "fetch",
                    config={"engine": "firecrawl", "url": "https://example.com"},
                )
            }
        )

        async def mock_execute(name, params, ctx=None, on_progress=None):
            return make_tool_result(success=True)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with patch(
                "kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute
            ):
                result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        deprecation_msgs = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert len(deprecation_msgs) >= 1
        assert "deprecated" in str(deprecation_msgs[0].message).lower()

    @pytest.mark.asyncio
    async def test_engine_still_passed_to_tool(self):
        """config.engine value reaches the tool as engine param."""
        workflow = make_workflow(
            steps={
                "fetch_step": make_step(
                    "fetch",
                    config={"engine": "httpx", "url": "https://example.com"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True)

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            with patch(
                "kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute
            ):
                await execute_workflow(workflow, {})

        assert captured["fetch"]["engine"] == "httpx"


# ============================================================================
# URL Auto-Matching
# ============================================================================


class TestURLAutoMatching:
    """Verify URL pattern matching selects provider automatically."""

    @pytest.mark.asyncio
    async def test_twitter_url_resolves_provider(self):
        """Twitter URL auto-selects twitterapi provider."""
        workflow = make_workflow(
            steps={
                "fetch_step": make_step(
                    "fetch",
                    config={"url": "https://x.com/user/status/123456"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True, data=[{"content": "tweet"}])

        mock_registry = MagicMock()
        mock_registry.resolve_provider.return_value = "twitterapi"

        with (
            patch("kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute),
            patch("kurt.workflows.toml.executor.get_provider_registry", return_value=mock_registry),
            patch("kurt.tools.core.registry.get_tool", side_effect=Exception("no tool")),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert captured["fetch"]["engine"] == "twitterapi"

    @pytest.mark.asyncio
    async def test_source_field_used_for_matching(self):
        """config.source is used for URL pattern matching (map tool)."""
        workflow = make_workflow(
            steps={
                "map_step": make_step(
                    "map",
                    config={"source": "https://example.com/feed.xml"},
                )
            }
        )

        captured_url = {}

        class FakeRegistry:
            def resolve_provider(self, tool, url=None, default_provider=None):
                captured_url["url"] = url
                return "rss"

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True)

        with (
            patch("kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute),
            patch("kurt.workflows.toml.executor.get_provider_registry", return_value=FakeRegistry()),
            patch("kurt.tools.core.registry.get_tool", side_effect=Exception("no tool")),
        ):
            await execute_workflow(workflow, {})

        assert captured_url["url"] == "https://example.com/feed.xml"
        assert captured["map"]["engine"] == "rss"


# ============================================================================
# Default Provider Fallback
# ============================================================================


class TestDefaultProviderFallback:
    """Verify tool's default_provider is used as fallback."""

    @pytest.mark.asyncio
    async def test_default_provider_used_when_no_match(self):
        """Tool's default_provider is used when no URL pattern matches."""
        workflow = make_workflow(
            steps={
                "fetch_step": make_step(
                    "fetch",
                    config={"url": "https://example.com/page"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True)

        class FakeRegistry:
            def resolve_provider(self, tool, url=None, default_provider=None):
                return default_provider

        mock_tool = type("MockTool", (), {"default_provider": "trafilatura"})

        with (
            patch("kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute),
            patch("kurt.workflows.toml.executor.get_provider_registry", return_value=FakeRegistry()),
            patch("kurt.tools.core.registry.get_tool", return_value=mock_tool),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert captured["fetch"]["engine"] == "trafilatura"


# ============================================================================
# Multi-Step Workflow
# ============================================================================


class TestMultiStepWorkflow:
    """Verify provider resolution works across multi-step workflows."""

    @pytest.mark.asyncio
    async def test_different_providers_per_step(self):
        """Each step can use a different provider."""
        workflow = make_workflow(
            steps={
                "discover": make_step(
                    "map",
                    config={"provider": "sitemap", "source": "https://example.com/sitemap.xml"},
                ),
                "fetch_content": make_step(
                    "fetch",
                    depends_on=["discover"],
                    config={"provider": "trafilatura"},
                ),
            }
        )

        captured = {}
        call_order = []

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            call_order.append(name)
            if name == "map":
                return make_tool_result(
                    success=True, data=[{"url": "https://example.com/page1"}]
                )
            return make_tool_result(success=True, data=[{"content": "text"}])

        with patch(
            "kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert call_order == ["map", "fetch"]
        assert captured["map"]["engine"] == "sitemap"
        assert captured["fetch"]["engine"] == "trafilatura"

    @pytest.mark.asyncio
    async def test_mixed_explicit_and_auto_resolved(self):
        """Workflow with both explicit and auto-resolved providers."""
        workflow = make_workflow(
            steps={
                "discover": make_step(
                    "map",
                    config={"provider": "crawl"},
                ),
                "fetch_tweet": make_step(
                    "fetch",
                    depends_on=["discover"],
                    config={"url": "https://x.com/user/status/789"},
                ),
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            if name == "map":
                return make_tool_result(
                    success=True, data=[{"url": "https://x.com/user/status/789"}]
                )
            return make_tool_result(success=True, data=[{"content": "tweet"}])

        mock_registry = MagicMock()
        mock_registry.resolve_provider.return_value = "twitterapi"

        with (
            patch("kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute),
            patch("kurt.workflows.toml.executor.get_provider_registry", return_value=mock_registry),
            patch("kurt.tools.core.registry.get_tool", side_effect=Exception("no tool")),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert captured["map"]["engine"] == "crawl"
        assert captured["fetch"]["engine"] == "twitterapi"

    @pytest.mark.asyncio
    async def test_provider_with_interpolated_config(self):
        """Provider works with config interpolation from workflow inputs."""
        workflow = make_workflow(
            inputs={"target_url": InputDef(type="string", required=True)},
            steps={
                "fetch_step": make_step(
                    "fetch",
                    config={
                        "provider": "tavily",
                        "url": "{{target_url}}",
                    },
                )
            },
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True)

        with patch(
            "kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(
                workflow, {"target_url": "https://example.com/article"}
            )

        assert result.status == "completed"
        assert captured["fetch"]["engine"] == "tavily"
        assert captured["fetch"]["url"] == "https://example.com/article"


# ============================================================================
# Edge Cases
# ============================================================================


class TestProviderEdgeCases:
    """Edge cases for provider resolution in workflows."""

    @pytest.mark.asyncio
    async def test_function_steps_skip_provider_resolution(self):
        """Function-type steps bypass provider resolution entirely."""
        workflow = make_workflow(
            steps={
                "func_step": StepDef(
                    type="function",
                    depends_on=[],
                    config={"function": "my_func", "provider": "should_be_ignored"},
                )
            }
        )

        # Function steps don't go through provider resolution
        # They call _execute_function_step instead
        # Just verify it doesn't crash trying to resolve
        with patch(
            "kurt.workflows.toml.executor.execute_tool", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = make_tool_result(success=True)
            # Function steps will try to load a function, which will fail
            # but that's expected - we're testing that provider resolution is skipped
            result = await execute_workflow(workflow, {})

        # Function step will fail because my_func doesn't exist
        # but it should NOT fail in provider resolution
        assert "func_step" in result.step_results

    @pytest.mark.asyncio
    async def test_no_provider_no_engine_passes_through(self):
        """Steps without provider or engine pass config through cleanly."""
        workflow = make_workflow(
            steps={
                "fetch_step": make_step(
                    "fetch",
                    config={"url": "https://example.com", "max_pages": 5},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True)

        mock_registry = MagicMock()
        mock_registry.resolve_provider.return_value = None

        with (
            patch("kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute),
            patch("kurt.workflows.toml.executor.get_provider_registry", return_value=mock_registry),
            patch("kurt.tools.core.registry.get_tool", side_effect=Exception("no tool")),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert "engine" not in captured["fetch"]
        assert captured["fetch"]["url"] == "https://example.com"
        assert captured["fetch"]["max_pages"] == 5


# ============================================================================
# Map Engine Override Tests (bd-285.7.5)
# ============================================================================


class TestMapEngineOverride:
    """Verify engine field on MapInput overrides discovery_method."""

    def test_map_input_accepts_engine_field(self):
        """MapInput accepts engine field without validation error."""
        from kurt.tools.map.tool import MapInput

        params = MapInput(source="url", url="https://example.com", engine="sitemap")
        assert params.engine == "sitemap"

    def test_map_input_engine_defaults_to_none(self):
        """MapInput engine defaults to None when not set."""
        from kurt.tools.map.tool import MapInput

        params = MapInput(source="url", url="https://example.com")
        assert params.engine is None

    @pytest.mark.asyncio
    async def test_engine_overrides_discovery_method_in_map_tool(self):
        """Engine field overrides discovery_method in MapTool.run()."""
        from kurt.tools.map.tool import MapInput, MapTool

        tool = MapTool()
        params = MapInput(
            source="url",
            url="https://example.com/data",
            discovery_method="auto",
            engine="rss",  # Force RSS even though URL isn't RSS-like
        )
        context = MagicMock()
        context.http = None

        # Mock the _map_url method to capture what params it receives
        captured_params = {}

        async def mock_map_url(p, ctx, on_progress):
            captured_params["discovery_method"] = p.discovery_method
            captured_params["engine"] = p.engine
            return [], None

        tool._map_url = mock_map_url
        await tool.run(params, context)

        # Engine should have overridden discovery_method to "rss"
        assert captured_params["discovery_method"] == "rss"

    @pytest.mark.asyncio
    async def test_engine_does_not_override_with_unknown_value(self):
        """Unknown engine value does not override discovery_method."""
        from kurt.tools.map.tool import MapInput, MapTool

        tool = MapTool()
        params = MapInput(
            source="url",
            url="https://example.com",
            discovery_method="auto",
            engine="custom_provider",  # Not a valid discovery method
        )
        context = MagicMock()
        context.http = None

        captured_params = {}

        async def mock_map_url(p, ctx, on_progress):
            captured_params["discovery_method"] = p.discovery_method
            return [], None

        tool._map_url = mock_map_url
        await tool.run(params, context)

        # discovery_method should remain "auto" (unknown engine ignored)
        assert captured_params["discovery_method"] == "auto"

    @pytest.mark.asyncio
    async def test_executor_resolved_provider_reaches_map_as_engine(self):
        """Provider resolved by executor reaches map tool as engine param."""
        workflow = make_workflow(
            steps={
                "map_step": make_step(
                    "map",
                    config={"provider": "rss", "source": "url", "url": "https://example.com"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True, data=[{"url": "https://example.com/feed"}])

        with patch(
            "kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        # The engine should be "rss" (from provider resolution)
        assert captured["map"]["engine"] == "rss"

    @pytest.mark.asyncio
    async def test_auto_resolved_provider_reaches_map(self):
        """URL-based auto-resolved provider reaches map tool as engine."""
        workflow = make_workflow(
            steps={
                "map_step": make_step(
                    "map",
                    config={"source": "url", "url": "https://example.com/feed.xml"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True)

        mock_registry = MagicMock()
        mock_registry.resolve_provider.return_value = "rss"

        with (
            patch("kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute),
            patch("kurt.workflows.toml.executor.get_provider_registry", return_value=mock_registry),
            patch("kurt.tools.core.registry.get_tool", side_effect=Exception("no tool")),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert captured["map"]["engine"] == "rss"


# ============================================================================
# Upstream Input Data Provider Selection (bd-285.7.4)
# ============================================================================


class TestUpstreamInputDataProviderSelection:
    """Integration tests for provider auto-selection from upstream URLs."""

    @pytest.mark.asyncio
    async def test_map_to_fetch_pipeline_uses_upstream_urls(self):
        """In map → fetch pipeline, fetch resolves provider from upstream URLs."""
        workflow = make_workflow(
            steps={
                "discover": make_step(
                    "map",
                    config={"provider": "sitemap", "source": "url", "url": "https://x.com/sitemap.xml"},
                ),
                "fetch_content": make_step(
                    "fetch",
                    depends_on=["discover"],
                    config={},  # No URL in config - comes from upstream
                ),
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            if name == "map":
                return make_tool_result(
                    success=True,
                    data=[
                        {"url": "https://x.com/user/status/123"},
                        {"url": "https://x.com/user/status/456"},
                    ],
                )
            return make_tool_result(success=True, data=[{"content": "tweet"}])

        mock_registry = MagicMock()
        mock_registry.resolve_provider.return_value = "twitterapi"

        with (
            patch("kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute),
            patch("kurt.workflows.toml.executor.get_provider_registry", return_value=mock_registry),
            patch("kurt.tools.core.registry.get_tool", side_effect=Exception("no tool")),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        # Fetch step should get engine from upstream URL matching
        assert captured["fetch"]["engine"] == "twitterapi"

    @pytest.mark.asyncio
    async def test_config_url_overrides_upstream_in_pipeline(self):
        """Fetch step's config.url takes priority over upstream URLs for matching."""
        workflow = make_workflow(
            steps={
                "discover": make_step(
                    "map",
                    config={"provider": "sitemap", "source": "url", "url": "https://x.com/sitemap.xml"},
                ),
                "fetch_content": make_step(
                    "fetch",
                    depends_on=["discover"],
                    config={"url": "https://docs.example.com/page"},
                ),
            }
        )

        captured = {}
        captured_urls = []

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            if name == "map":
                return make_tool_result(
                    success=True,
                    data=[{"url": "https://x.com/user/status/123"}],
                )
            return make_tool_result(success=True)

        class TrackingRegistry:
            def resolve_provider(self, tool, url=None, default_provider=None):
                captured_urls.append(url)
                return "trafilatura"

        with (
            patch("kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute),
            patch(
                "kurt.workflows.toml.executor.get_provider_registry",
                return_value=TrackingRegistry(),
            ),
            patch("kurt.tools.core.registry.get_tool", side_effect=Exception("no tool")),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        # For the fetch step, config URL (docs.example.com) should be used for matching
        # not the upstream twitter URL
        fetch_resolve_url = captured_urls[-1]  # Last resolve call is for fetch step
        assert "docs.example.com" in fetch_resolve_url


# ============================================================================
# Upstream Input Data URL Matching (bd-285.5.3)
# ============================================================================


class TestUpstreamInputDataURLMatching:
    """Verify provider auto-selection from upstream input_data URLs."""

    @pytest.mark.asyncio
    async def test_fetch_resolves_provider_from_upstream_urls(self):
        """Fetch step auto-selects provider based on URLs from map step output."""
        workflow = make_workflow(
            steps={
                "discover": make_step(
                    "map",
                    config={
                        "provider": "sitemap",
                        "source": "https://x.com/sitemap.xml",
                    },
                ),
                "fetch_content": make_step(
                    "fetch",
                    depends_on=["discover"],
                    # No URL in config - URLs come from upstream
                ),
            }
        )

        captured = {}
        call_order = []

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            call_order.append(name)
            if name == "map":
                return make_tool_result(
                    success=True,
                    data=[
                        {"url": "https://x.com/user/status/123"},
                        {"url": "https://x.com/user/status/456"},
                    ],
                )
            return make_tool_result(success=True, data=[{"content": "tweet"}])

        mock_registry = MagicMock()
        mock_registry.resolve_provider.return_value = "twitterapi"

        with (
            patch(
                "kurt.workflows.toml.executor.execute_tool",
                side_effect=mock_execute,
            ),
            patch(
                "kurt.workflows.toml.executor.get_provider_registry",
                return_value=mock_registry,
            ),
            patch(
                "kurt.tools.core.registry.get_tool",
                side_effect=Exception("no tool"),
            ),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert call_order == ["map", "fetch"]
        # Fetch should have resolved provider from upstream URLs
        assert captured["fetch"]["engine"] == "twitterapi"

    @pytest.mark.asyncio
    async def test_config_url_overrides_upstream_urls(self):
        """Config URL takes priority over upstream input_data URLs."""
        workflow = make_workflow(
            steps={
                "discover": make_step(
                    "map",
                    config={"provider": "sitemap", "source": "https://x.com/sitemap.xml"},
                ),
                "fetch_content": make_step(
                    "fetch",
                    depends_on=["discover"],
                    config={"url": "https://example.com/override"},
                ),
            }
        )

        captured = {}
        captured_registry_calls: list[dict[str, Any]] = []

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            if name == "map":
                return make_tool_result(
                    success=True,
                    data=[{"url": "https://x.com/user/status/123"}],
                )
            return make_tool_result(success=True)

        class TrackingRegistry:
            def resolve_provider(self, tool, url=None, default_provider=None):
                captured_registry_calls.append({"tool": tool, "url": url})
                return "trafilatura" if url and "example.com" in url else "twitterapi"

        with (
            patch(
                "kurt.workflows.toml.executor.execute_tool",
                side_effect=mock_execute,
            ),
            patch(
                "kurt.workflows.toml.executor.get_provider_registry",
                return_value=TrackingRegistry(),
            ),
            patch(
                "kurt.tools.core.registry.get_tool",
                side_effect=Exception("no tool"),
            ),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        # For the fetch step, config URL should be used for matching
        fetch_calls = [c for c in captured_registry_calls if c["tool"] == "fetch"]
        assert any(c["url"] == "https://example.com/override" for c in fetch_calls)


# ============================================================================
# Map Tool Engine Override (bd-285.5.4)
# ============================================================================


class TestMapToolEngineOverride:
    """Verify engine from provider resolution reaches MapTool."""

    @pytest.mark.asyncio
    async def test_map_engine_passed_in_params(self):
        """Resolved engine is included in map tool params."""
        workflow = make_workflow(
            steps={
                "map_step": make_step(
                    "map",
                    config={"provider": "rss", "source": "url", "url": "https://example.com/feed"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True)

        with patch(
            "kurt.workflows.toml.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert captured["map"]["engine"] == "rss"

    @pytest.mark.asyncio
    async def test_map_engine_from_auto_resolved_provider(self):
        """Auto-resolved provider reaches map tool as engine."""
        workflow = make_workflow(
            steps={
                "map_step": make_step(
                    "map",
                    config={"source": "url", "url": "https://example.com/feed.rss"},
                )
            }
        )

        captured = {}

        async def mock_execute(name, params, ctx=None, on_progress=None):
            captured[name] = params.copy()
            return make_tool_result(success=True)

        mock_registry = MagicMock()
        mock_registry.resolve_provider.return_value = "rss"

        with (
            patch(
                "kurt.workflows.toml.executor.execute_tool",
                side_effect=mock_execute,
            ),
            patch(
                "kurt.workflows.toml.executor.get_provider_registry",
                return_value=mock_registry,
            ),
            patch(
                "kurt.tools.core.registry.get_tool",
                side_effect=Exception("no tool"),
            ),
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert captured["map"]["engine"] == "rss"
