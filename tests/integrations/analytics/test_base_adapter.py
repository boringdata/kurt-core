"""Unit tests for base analytics adapter interface."""

from datetime import datetime, timedelta

import pytest

from kurt.integrations.analytics.adapters.base import AnalyticsAdapter, AnalyticsMetrics


class TestAnalyticsMetrics:
    """Test AnalyticsMetrics data class."""

    def test_metrics_creation_minimal(self):
        """Test creating metrics with minimal required fields."""
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        assert metrics.pageviews_60d == 1000
        assert metrics.unique_visitors_60d == 500
        assert metrics.pageviews_30d == 600
        assert metrics.unique_visitors_30d == 300
        assert metrics.pageviews_previous_30d == 400
        assert metrics.unique_visitors_previous_30d == 200

    def test_metrics_with_optional_fields(self):
        """Test creating metrics with all optional fields."""
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            avg_session_duration_seconds=120.5,
            bounce_rate=0.35,
            pageviews_trend="increasing",
            trend_percentage=50.0,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        assert metrics.avg_session_duration_seconds == 120.5
        assert metrics.bounce_rate == 0.35
        assert metrics.pageviews_trend == "increasing"
        assert metrics.trend_percentage == 50.0

    def test_metrics_default_values(self):
        """Test that optional fields have proper defaults."""
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        assert metrics.avg_session_duration_seconds is None
        assert metrics.bounce_rate is None
        assert metrics.pageviews_trend == "stable"
        assert metrics.trend_percentage is None


class TestAnalyticsAdapterInterface:
    """Test base AnalyticsAdapter interface."""

    def test_adapter_is_abstract(self):
        """Test that AnalyticsAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            AnalyticsAdapter()  # Should fail - abstract class

    def test_adapter_must_implement_test_connection(self):
        """Test that subclasses must implement test_connection."""

        class IncompleteAdapter(AnalyticsAdapter):
            def get_domain_urls(self, domain, period_days):
                pass

            def sync_metrics(self, urls, period_days):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter()  # Should fail - missing test_connection

    def test_adapter_must_implement_get_domain_urls(self):
        """Test that subclasses must implement get_domain_urls."""

        class IncompleteAdapter(AnalyticsAdapter):
            def test_connection(self):
                pass

            def sync_metrics(self, urls, period_days):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter()  # Should fail - missing get_domain_urls

    def test_adapter_must_implement_sync_metrics(self):
        """Test that subclasses must implement sync_metrics."""

        class IncompleteAdapter(AnalyticsAdapter):
            def test_connection(self):
                pass

            def get_domain_urls(self, domain, period_days):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter()  # Should fail - missing sync_metrics

    def test_adapter_complete_implementation(self):
        """Test that complete implementation can be instantiated."""

        class CompleteAdapter(AnalyticsAdapter):
            def test_connection(self) -> bool:
                return True

            def get_domain_urls(self, domain: str, period_days: int = 60) -> list[str]:
                return []

            def sync_metrics(
                self, urls: list[str], period_days: int = 60
            ) -> dict[str, AnalyticsMetrics]:
                return {}

        adapter = CompleteAdapter()
        assert adapter is not None
        assert adapter.test_connection() is True
        assert adapter.get_domain_urls("example.com") == []
        assert adapter.sync_metrics([]) == {}


class TestAnalyticsTrendCalculation:
    """Test trend calculation logic patterns."""

    def test_increasing_trend_detection(self):
        """Test detecting increasing traffic trend."""
        current = 600
        previous = 400
        change_pct = ((current - previous) / previous) * 100

        assert change_pct == 50.0
        assert change_pct > 10  # Threshold for "increasing"

    def test_decreasing_trend_detection(self):
        """Test detecting decreasing traffic trend."""
        current = 300
        previous = 500
        change_pct = ((current - previous) / previous) * 100

        assert change_pct == -40.0
        assert change_pct < -10  # Threshold for "decreasing"

    def test_stable_trend_detection(self):
        """Test detecting stable traffic trend."""
        current = 420
        previous = 400
        change_pct = ((current - previous) / previous) * 100

        assert change_pct == 5.0
        assert -10 <= change_pct <= 10  # Threshold for "stable"

    def test_zero_baseline_handling(self):
        """Test handling zero baseline for trend calculation."""
        current = 100
        previous = 0

        # Cannot calculate percentage with zero baseline
        if previous == 0:
            change_pct = None
            trend = "increasing" if current > 0 else "stable"
        else:
            change_pct = ((current - previous) / previous) * 100
            trend = "increasing"

        assert change_pct is None
        assert trend == "increasing"

    def test_both_zero_handling(self):
        """Test handling when both periods have zero traffic."""
        current = 0
        previous = 0

        if current == 0 and previous == 0:
            trend = "stable"
            change_pct = None
        else:
            change_pct = ((current - previous) / previous) * 100
            trend = "stable"

        assert trend == "stable"
        assert change_pct is None


class TestAnalyticsMetricsValidation:
    """Test metrics validation and constraints."""

    def test_pageviews_non_negative(self):
        """Test that pageviews should be non-negative."""
        # This is a data contract test - implementations should validate
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        assert metrics.pageviews_60d >= 0
        assert metrics.pageviews_30d >= 0
        assert metrics.pageviews_previous_30d >= 0

    def test_unique_visitors_non_negative(self):
        """Test that unique visitors should be non-negative."""
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        assert metrics.unique_visitors_60d >= 0
        assert metrics.unique_visitors_30d >= 0
        assert metrics.unique_visitors_previous_30d >= 0

    def test_bounce_rate_range(self):
        """Test that bounce rate should be between 0 and 1."""
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            bounce_rate=0.35,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        assert 0.0 <= metrics.bounce_rate <= 1.0

    def test_trend_valid_values(self):
        """Test that trend should be one of the valid values."""
        valid_trends = ["increasing", "decreasing", "stable"]

        for trend in valid_trends:
            metrics = AnalyticsMetrics(
                pageviews_60d=1000,
                unique_visitors_60d=500,
                pageviews_30d=600,
                unique_visitors_30d=300,
                pageviews_previous_30d=400,
                unique_visitors_previous_30d=200,
                pageviews_trend=trend,
                period_start=datetime.utcnow() - timedelta(days=60),
                period_end=datetime.utcnow(),
            )
            assert metrics.pageviews_trend in valid_trends

    def test_period_end_after_start(self):
        """Test that period_end should be after period_start."""
        start = datetime.utcnow() - timedelta(days=60)
        end = datetime.utcnow()

        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=start,
            period_end=end,
        )

        assert metrics.period_end > metrics.period_start

    def test_60d_sum_consistency(self):
        """Test that 60d totals should be >= sum of 30d periods."""
        # This is a logical constraint, not enforced but tested
        metrics = AnalyticsMetrics(
            pageviews_60d=1000,
            unique_visitors_60d=500,
            pageviews_30d=600,
            unique_visitors_30d=300,
            pageviews_previous_30d=400,
            unique_visitors_previous_30d=200,
            period_start=datetime.utcnow() - timedelta(days=60),
            period_end=datetime.utcnow(),
        )

        # 60d should be >= sum of both 30d periods
        assert metrics.pageviews_60d >= metrics.pageviews_30d + metrics.pageviews_previous_30d
        # Note: unique_visitors is NOT additive (same visitor in both periods)
