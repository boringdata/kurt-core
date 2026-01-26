"""
Unit tests for AnalyticsTool.

Tests tool registration, input/output validation, and basic functionality
with mocked PostHog integration.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from kurt.tools.core import (
    TOOLS,
    SubstepEvent,
    ToolContext,
    ToolInputError,
    execute_tool,
    get_tool,
    get_tool_info,
)


@pytest.fixture(autouse=True)
def ensure_analytics_registered():
    """Ensure AnalyticsTool is registered before each test."""
    # Import to trigger registration if not already done
    from kurt.tools.analytics import AnalyticsTool

    # Add to registry if not present (clear_registry may have removed it)
    if "analytics" not in TOOLS:
        TOOLS["analytics"] = AnalyticsTool

    yield


# ============================================================================
# Registration Tests
# ============================================================================


class TestAnalyticsToolRegistration:
    """Test AnalyticsTool registration in the registry."""

    def test_tool_is_registered(self):
        """AnalyticsTool should be registered under 'analytics' name."""
        assert "analytics" in TOOLS

    def test_get_tool_returns_analytics_tool(self):
        """get_tool('analytics') returns AnalyticsTool class."""
        from kurt.tools.analytics import AnalyticsTool

        tool_class = get_tool("analytics")
        assert tool_class is AnalyticsTool

    def test_tool_has_required_attributes(self):
        """AnalyticsTool has all required Tool attributes."""
        from kurt.tools.analytics import AnalyticsTool

        assert AnalyticsTool.name == "analytics"
        assert AnalyticsTool.description is not None
        assert AnalyticsTool.InputModel is not None
        assert AnalyticsTool.OutputModel is not None

    def test_get_tool_info(self):
        """get_tool_info returns correct metadata for analytics tool."""
        info = get_tool_info("analytics")

        assert info["name"] == "analytics"
        assert "analytics" in info["description"].lower()
        assert info["input_schema"] is not None
        assert info["output_schema"] is not None

    def test_input_schema_has_expected_properties(self):
        """Input schema should have domain, platform, period_days, dry_run."""
        info = get_tool_info("analytics")
        input_props = info["input_schema"]["properties"]

        assert "domain" in input_props
        assert "platform" in input_props
        assert "period_days" in input_props
        assert "dry_run" in input_props

    def test_output_schema_has_expected_properties(self):
        """Output schema should have domain, total_urls, total_pageviews, pages."""
        info = get_tool_info("analytics")
        output_props = info["output_schema"]["properties"]

        assert "domain" in output_props
        assert "total_urls" in output_props
        assert "total_pageviews" in output_props
        assert "pages" in output_props


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestAnalyticsInputValidation:
    """Test AnalyticsInput validation."""

    def test_valid_input_minimal(self):
        """Minimal valid input with just domain."""
        from kurt.tools.analytics import AnalyticsInput

        input_model = AnalyticsInput(domain="example.com")
        assert input_model.domain == "example.com"
        assert input_model.platform == "posthog"
        assert input_model.period_days == 60
        assert input_model.dry_run is False

    def test_valid_input_all_fields(self):
        """Valid input with all fields specified."""
        from kurt.tools.analytics import AnalyticsInput

        input_model = AnalyticsInput(
            domain="example.com",
            platform="posthog",
            period_days=30,
            dry_run=True,
        )
        assert input_model.domain == "example.com"
        assert input_model.platform == "posthog"
        assert input_model.period_days == 30
        assert input_model.dry_run is True

    def test_invalid_platform(self):
        """Invalid platform should raise validation error."""
        from pydantic import ValidationError

        from kurt.tools.analytics import AnalyticsInput

        with pytest.raises(ValidationError):
            AnalyticsInput(domain="example.com", platform="invalid_platform")

    def test_valid_platforms(self):
        """All supported platforms should validate."""
        from kurt.tools.analytics import AnalyticsInput

        for platform in ["posthog", "ga4", "plausible"]:
            input_model = AnalyticsInput(domain="example.com", platform=platform)
            assert input_model.platform == platform

    def test_period_days_min_value(self):
        """period_days must be at least 1."""
        from pydantic import ValidationError

        from kurt.tools.analytics import AnalyticsInput

        with pytest.raises(ValidationError):
            AnalyticsInput(domain="example.com", period_days=0)

    def test_period_days_max_value(self):
        """period_days must be at most 365."""
        from pydantic import ValidationError

        from kurt.tools.analytics import AnalyticsInput

        with pytest.raises(ValidationError):
            AnalyticsInput(domain="example.com", period_days=400)

    def test_missing_domain_raises(self):
        """Missing domain should raise validation error."""
        from pydantic import ValidationError

        from kurt.tools.analytics import AnalyticsInput

        with pytest.raises(ValidationError):
            AnalyticsInput()

    @pytest.mark.asyncio
    async def test_execute_with_invalid_params(self):
        """execute_tool raises ToolInputError for invalid params."""
        with pytest.raises(ToolInputError) as exc_info:
            await execute_tool("analytics", {"wrong_field": "value"})
        assert exc_info.value.tool_name == "analytics"


# ============================================================================
# Output Model Tests
# ============================================================================


class TestAnalyticsOutputModels:
    """Test AnalyticsOutput and PageMetricsOutput models."""

    def test_analytics_output_minimal(self):
        """AnalyticsOutput with minimal fields."""
        from kurt.tools.analytics import AnalyticsOutput

        output = AnalyticsOutput(
            domain="example.com",
            platform="posthog",
            period_days=60,
        )
        assert output.domain == "example.com"
        assert output.total_urls == 0
        assert output.total_pageviews == 0
        assert output.pages == []

    def test_page_metrics_output(self):
        """PageMetricsOutput with all fields."""
        from kurt.tools.analytics import PageMetricsOutput

        page = PageMetricsOutput(
            id="test-123",
            url="https://example.com/page",
            domain="example.com",
            pageviews_60d=1000,
            pageviews_30d=600,
            pageviews_previous_30d=400,
            unique_visitors_60d=500,
            unique_visitors_30d=300,
            unique_visitors_previous_30d=200,
            avg_session_duration_seconds=45.5,
            bounce_rate=0.35,
            pageviews_trend="up",
            trend_percentage=50.0,
        )
        assert page.pageviews_60d == 1000
        assert page.pageviews_trend == "up"
        assert page.trend_percentage == 50.0


# ============================================================================
# Tool Execution Tests (with mocked integration)
# ============================================================================


class TestAnalyticsToolExecution:
    """Test AnalyticsTool.run() with mocked PostHog integration."""

    @pytest.mark.asyncio
    async def test_sync_with_no_data(self):
        """Tool returns empty result when no analytics data found."""
        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.return_value = {}

            result = await execute_tool(
                "analytics",
                {"domain": "empty.com", "platform": "posthog"},
            )

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["total_urls"] == 0
        assert result.data[0]["total_pageviews"] == 0
        assert result.data[0]["pages"] == []

    @pytest.mark.asyncio
    async def test_sync_with_data(self):
        """Tool returns metrics when data is found."""
        from kurt.integrations.domains_analytics.base import AnalyticsMetrics

        mock_metrics = {
            "https://example.com/page1": AnalyticsMetrics(
                pageviews_60d=100,
                pageviews_30d=60,
                pageviews_previous_30d=40,
                unique_visitors_60d=50,
                unique_visitors_30d=30,
                unique_visitors_previous_30d=20,
                pageviews_trend="up",
                trend_percentage=50.0,
                period_start=datetime(2024, 1, 1),
                period_end=datetime(2024, 3, 1),
            ),
            "https://example.com/page2": AnalyticsMetrics(
                pageviews_60d=200,
                pageviews_30d=120,
                pageviews_previous_30d=80,
                unique_visitors_60d=100,
                unique_visitors_30d=60,
                unique_visitors_previous_30d=40,
                pageviews_trend="up",
                trend_percentage=50.0,
                period_start=datetime(2024, 1, 1),
                period_end=datetime(2024, 3, 1),
            ),
        }

        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.return_value = mock_metrics

            with patch(
                "kurt.integrations.domains_analytics.utils.normalize_url_for_analytics",
                side_effect=lambda url: url,
            ):
                result = await execute_tool(
                    "analytics",
                    {"domain": "example.com", "platform": "posthog", "period_days": 60},
                )

        assert result.success is True
        assert len(result.data) == 1
        output = result.data[0]

        assert output["domain"] == "example.com"
        assert output["platform"] == "posthog"
        assert output["period_days"] == 60
        assert output["total_urls"] == 2
        assert output["total_pageviews"] == 300  # 100 + 200

        # Check pages
        assert len(output["pages"]) == 2
        page_urls = {p["url"] for p in output["pages"]}
        assert "https://example.com/page1" in page_urls
        assert "https://example.com/page2" in page_urls

    @pytest.mark.asyncio
    async def test_platform_not_implemented_error(self):
        """Tool handles NotImplementedError gracefully."""
        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.side_effect = NotImplementedError("GA4 adapter coming soon")

            result = await execute_tool(
                "analytics",
                {"domain": "example.com", "platform": "ga4"},
            )

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "platform_not_implemented"
        assert "GA4" in result.errors[0].message

    @pytest.mark.asyncio
    async def test_sync_failure_error(self):
        """Tool handles sync failures gracefully."""
        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.side_effect = Exception("API connection failed")

            result = await execute_tool(
                "analytics",
                {"domain": "example.com", "platform": "posthog"},
            )

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "sync_failed"
        assert "API connection failed" in result.errors[0].message

    @pytest.mark.asyncio
    async def test_progress_callback_called(self):
        """Tool emits progress events during execution."""
        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.return_value = {}

            await execute_tool(
                "analytics",
                {"domain": "example.com"},
                on_progress=on_progress,
            )

        # Should have at least running and completed events
        assert len(events) >= 2
        assert any(e.status == "running" for e in events)
        assert any(e.status == "completed" for e in events)

    @pytest.mark.asyncio
    async def test_substeps_in_result(self):
        """Tool includes substeps in result."""
        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.return_value = {}

            result = await execute_tool(
                "analytics",
                {"domain": "example.com"},
            )

        assert len(result.substeps) >= 1
        assert any(s.name == "sync_analytics" for s in result.substeps)

    @pytest.mark.asyncio
    async def test_metadata_added(self):
        """Tool result includes timing metadata."""
        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.return_value = {}

            result = await execute_tool(
                "analytics",
                {"domain": "example.com"},
            )

        assert result.metadata is not None
        assert result.metadata.started_at is not None
        assert result.metadata.completed_at is not None
        assert result.metadata.duration_ms >= 0


# ============================================================================
# Context Tests
# ============================================================================


class TestAnalyticsToolContext:
    """Test AnalyticsTool with different contexts."""

    @pytest.mark.asyncio
    async def test_uses_provided_context(self):
        """Tool uses the provided context."""
        context = ToolContext(settings={"project_root": "/test/path"})

        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.return_value = {}

            result = await execute_tool(
                "analytics",
                {"domain": "example.com"},
                context=context,
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_creates_default_context(self):
        """Tool creates default context when none provided."""
        with patch(
            "kurt.integrations.domains_analytics.sync_domain_metrics"
        ) as mock_sync:
            mock_sync.return_value = {}

            result = await execute_tool(
                "analytics",
                {"domain": "example.com"},
            )

        assert result.success is True
