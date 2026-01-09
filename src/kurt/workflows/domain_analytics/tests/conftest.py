"""Test fixtures for domain_analytics workflow tests."""

import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path, monkeypatch):
    """
    Create a temporary project directory with kurt.config file.
    """
    (tmp_path / ".kurt").mkdir(parents=True, exist_ok=True)

    config_file = tmp_path / "kurt.config"
    config_file.write_text(
        """# Kurt Project Configuration
PATH_DB=".kurt/kurt.sqlite"
"""
    )

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    yield tmp_path

    os.chdir(original_cwd)


@pytest.fixture
def tmp_project_with_analytics_config(tmp_project: Path):
    """
    Create a temporary project with analytics configuration.
    """
    config_file = tmp_project / "kurt.config"

    with open(config_file, "a") as f:
        f.write("\n# Analytics Configuration\n")
        f.write('ANALYTICS_POSTHOG_PROJECT_ID="12345"\n')
        f.write('ANALYTICS_POSTHOG_API_KEY="phx_test_key"\n')
        f.write('ANALYTICS_POSTHOG_HOST="https://app.posthog.com"\n')

    return tmp_project


@pytest.fixture
def tmp_project_with_placeholder_config(tmp_project: Path):
    """
    Create a temporary project with placeholder analytics configuration.
    """
    config_file = tmp_project / "kurt.config"

    with open(config_file, "a") as f:
        f.write("\n# Analytics Configuration (placeholders)\n")
        f.write('ANALYTICS_POSTHOG_PROJECT_ID="YOUR_PROJECT_ID"\n')
        f.write('ANALYTICS_POSTHOG_API_KEY="YOUR_PERSONAL_API_KEY"\n')

    return tmp_project


@pytest.fixture
def mock_posthog_adapter():
    """
    Create a mock PostHog adapter for testing.
    """
    from datetime import datetime, timedelta
    from unittest.mock import MagicMock

    from kurt.integrations.domains_analytics import AnalyticsMetrics

    now = datetime.utcnow()

    adapter = MagicMock()
    adapter.test_connection.return_value = True
    adapter.get_domain_urls.return_value = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/docs/guide",
    ]
    adapter.sync_metrics.return_value = {
        "https://example.com/page1": AnalyticsMetrics(
            pageviews_60d=1000,
            pageviews_30d=600,
            pageviews_previous_30d=400,
            pageviews_trend="increasing",
            trend_percentage=50.0,
            period_start=now - timedelta(days=60),
            period_end=now,
        ),
        "https://example.com/page2": AnalyticsMetrics(
            pageviews_60d=500,
            pageviews_30d=200,
            pageviews_previous_30d=300,
            pageviews_trend="decreasing",
            trend_percentage=-33.3,
            period_start=now - timedelta(days=60),
            period_end=now,
        ),
        "https://example.com/docs/guide": AnalyticsMetrics(
            pageviews_60d=100,
            pageviews_30d=50,
            pageviews_previous_30d=50,
            pageviews_trend="stable",
            trend_percentage=0.0,
            period_start=now - timedelta(days=60),
            period_end=now,
        ),
    }

    return adapter


@pytest.fixture
def mock_metrics_map():
    """
    Create a mock metrics map for testing sync_domain_metrics.
    """
    from datetime import datetime, timedelta

    from kurt.integrations.domains_analytics import AnalyticsMetrics

    now = datetime.utcnow()

    return {
        "https://example.com/page1": AnalyticsMetrics(
            pageviews_60d=1000,
            pageviews_30d=600,
            pageviews_previous_30d=400,
            pageviews_trend="increasing",
            trend_percentage=50.0,
            period_start=now - timedelta(days=60),
            period_end=now,
        ),
        "https://example.com/page2": AnalyticsMetrics(
            pageviews_60d=500,
            pageviews_30d=200,
            pageviews_previous_30d=300,
            pageviews_trend="decreasing",
            trend_percentage=-33.3,
            period_start=now - timedelta(days=60),
            period_end=now,
        ),
        "https://example.com/docs/guide": AnalyticsMetrics(
            pageviews_60d=100,
            pageviews_30d=50,
            pageviews_previous_30d=50,
            pageviews_trend="stable",
            trend_percentage=0.0,
            period_start=now - timedelta(days=60),
            period_end=now,
        ),
    }
