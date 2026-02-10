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
