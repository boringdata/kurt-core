"""End-to-end tests for domain_analytics workflow."""

import contextlib
import io
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from kurt_new.workflows.domain_analytics import (
    DomainAnalyticsConfig,
    normalize_url_for_analytics,
)
from kurt_new.workflows.domain_analytics.steps import (
    build_analytics_rows,
    deserialize_rows,
    serialize_rows,
)


class TestNormalizeUrl:
    """Test URL normalization utility."""

    def test_removes_protocol(self):
        assert normalize_url_for_analytics("https://example.com/path") == "example.com/path"
        assert normalize_url_for_analytics("http://example.com/path") == "example.com/path"

    def test_removes_www(self):
        assert normalize_url_for_analytics("https://www.example.com/path") == "example.com/path"

    def test_removes_trailing_slash(self):
        assert normalize_url_for_analytics("https://example.com/path/") == "example.com/path"

    def test_removes_query_params(self):
        assert normalize_url_for_analytics("https://example.com/path?utm=123") == "example.com/path"

    def test_removes_fragments(self):
        assert normalize_url_for_analytics("https://example.com/path#section") == "example.com/path"

    def test_handles_root_path(self):
        assert normalize_url_for_analytics("https://example.com") == "example.com"
        assert normalize_url_for_analytics("https://example.com/") == "example.com"

    def test_handles_empty_string(self):
        assert normalize_url_for_analytics("") == ""

    def test_complex_url(self):
        url = "https://www.docs.example.com/guides/quickstart/?utm=123&ref=test#step-1"
        assert normalize_url_for_analytics(url) == "docs.example.com/guides/quickstart"


class TestBuildAnalyticsRows:
    """Test build_analytics_rows function."""

    def test_builds_rows_from_metrics(self, mock_posthog_adapter):
        """Test that rows are built correctly from metrics."""
        metrics_map = mock_posthog_adapter.sync_metrics.return_value

        rows = build_analytics_rows("example.com", metrics_map)

        assert len(rows) == 3

        # Check first row
        row1 = next(r for r in rows if "page1" in r["url"])
        assert row1["domain"] == "example.com"
        assert row1["pageviews_60d"] == 1000
        assert row1["pageviews_trend"] == "increasing"
        assert row1["trend_percentage"] == 50.0

    def test_normalizes_urls(self, mock_posthog_adapter):
        """Test that URLs are normalized in rows."""
        metrics_map = mock_posthog_adapter.sync_metrics.return_value

        rows = build_analytics_rows("example.com", metrics_map)

        # URLs should be normalized (no https://)
        for row in rows:
            assert not row["url"].startswith("https://")
            assert "example.com" in row["url"]


class TestSerializeDeserializeRows:
    """Test row serialization/deserialization for DBOS."""

    def test_serialize_converts_datetimes(self, mock_posthog_adapter):
        """Test that datetimes are converted to ISO strings."""
        metrics_map = mock_posthog_adapter.sync_metrics.return_value
        rows = build_analytics_rows("example.com", metrics_map)

        serialized = serialize_rows(rows)

        for row in serialized:
            assert isinstance(row["period_start"], str)
            assert isinstance(row["period_end"], str)
            assert isinstance(row["synced_at"], str)

    def test_deserialize_converts_strings_back(self, mock_posthog_adapter):
        """Test that ISO strings are converted back to datetimes."""
        from datetime import datetime

        metrics_map = mock_posthog_adapter.sync_metrics.return_value
        rows = build_analytics_rows("example.com", metrics_map)
        serialized = serialize_rows(rows)

        deserialized = deserialize_rows(serialized)

        for row in deserialized:
            assert isinstance(row["period_start"], datetime)
            assert isinstance(row["period_end"], datetime)
            assert isinstance(row["synced_at"], datetime)

    def test_roundtrip_preserves_data(self, mock_posthog_adapter):
        """Test that serialize -> deserialize preserves data."""
        metrics_map = mock_posthog_adapter.sync_metrics.return_value
        rows = build_analytics_rows("example.com", metrics_map)

        serialized = serialize_rows(rows)
        deserialized = deserialize_rows(serialized)

        assert len(deserialized) == len(rows)
        for orig, deser in zip(rows, deserialized):
            assert orig["url"] == deser["url"]
            assert orig["domain"] == deser["domain"]
            assert orig["pageviews_60d"] == deser["pageviews_60d"]


class TestAdapterFactory:
    """Test get_adapter factory function."""

    def test_get_posthog_adapter(self, tmp_project_with_analytics_config):
        """Test creating PostHog adapter."""
        from kurt_new.workflows.domain_analytics import get_adapter

        adapter = get_adapter(
            "posthog",
            {"project_id": "123", "api_key": "test_key"},
        )

        from kurt_new.integrations.domains_analytics.posthog import PostHogAdapter

        assert isinstance(adapter, PostHogAdapter)

    def test_get_unsupported_adapter_raises(self):
        """Test that unsupported platform raises ValueError."""
        from kurt_new.workflows.domain_analytics import get_adapter

        with pytest.raises(ValueError, match="Unsupported"):
            get_adapter("unknown_platform", {})

    def test_get_ga4_adapter_not_implemented(self):
        """Test that GA4 adapter raises NotImplementedError."""
        from kurt_new.workflows.domain_analytics import get_adapter

        with pytest.raises(NotImplementedError):
            get_adapter("ga4", {})

    def test_get_plausible_adapter_not_implemented(self):
        """Test that Plausible adapter raises NotImplementedError."""
        from kurt_new.workflows.domain_analytics import get_adapter

        with pytest.raises(NotImplementedError):
            get_adapter("plausible", {})


# ============================================================================
# DBOS E2E Tests (require full kurt project setup)
# ============================================================================


@pytest.fixture
def reset_dbos_state():
    """Reset DBOS state between tests."""
    try:
        import dbos._dbos as dbos_module

        if (
            hasattr(dbos_module, "_dbos_global_instance")
            and dbos_module._dbos_global_instance is not None
        ):
            instance = dbos_module._dbos_global_instance
            if (
                hasattr(instance, "_destroy")
                and hasattr(instance, "_initialized")
                and instance._initialized
            ):
                instance._destroy(workflow_completion_timeout_sec=0)
            dbos_module._dbos_global_instance = None
    except (ImportError, AttributeError, Exception):
        pass

    yield

    try:
        import dbos._dbos as dbos_module

        if (
            hasattr(dbos_module, "_dbos_global_instance")
            and dbos_module._dbos_global_instance is not None
        ):
            instance = dbos_module._dbos_global_instance
            if (
                hasattr(instance, "_destroy")
                and hasattr(instance, "_initialized")
                and instance._initialized
            ):
                instance._destroy(workflow_completion_timeout_sec=0)
            dbos_module._dbos_global_instance = None
    except (ImportError, AttributeError, Exception):
        pass


@pytest.fixture
def tmp_kurt_project(tmp_path: Path, monkeypatch, reset_dbos_state):
    """
    Create a full temporary kurt project with config, database, and DBOS.
    """
    from dbos import DBOS, DBOSConfig

    from kurt_new.db import init_database

    # Create required directories
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir(parents=True, exist_ok=True)

    # Create config file with analytics config
    config_file = tmp_path / "kurt.config"
    config_file.write_text(
        """# Kurt Project Configuration
PATH_DB=".kurt/kurt.sqlite"

# Analytics Configuration
ANALYTICS_POSTHOG_PROJECT_ID="12345"
ANALYTICS_POSTHOG_API_KEY="phx_test_key"
ANALYTICS_POSTHOG_HOST="https://app.posthog.com"
"""
    )

    # Ensure no DATABASE_URL env var interferes
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Initialize database
    init_database()

    # Get database URL for DBOS config
    db_path = tmp_path / ".kurt" / "kurt.sqlite"
    db_url = f"sqlite:///{db_path}"

    # Initialize DBOS with config
    config = DBOSConfig(
        name="kurt_test",
        database_url=db_url,
    )

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        DBOS(config=config)
        DBOS.launch()

    yield tmp_path

    # Cleanup
    try:
        DBOS.destroy(workflow_completion_timeout_sec=0)
    except Exception:
        pass

    os.chdir(original_cwd)


class TestDomainAnalyticsE2E:
    """End-to-end tests for domain analytics workflow with real DBOS."""

    def test_sync_workflow_with_mock_adapter(self, tmp_kurt_project: Path, mock_metrics_map):
        """Test full workflow execution with mocked adapter."""
        from kurt_new.db import managed_session
        from kurt_new.workflows.domain_analytics import run_domain_analytics
        from kurt_new.workflows.domain_analytics.models import AnalyticsDomain, PageAnalytics

        with patch(
            "kurt_new.workflows.domain_analytics.steps.sync_domain_metrics",
            return_value=mock_metrics_map,
        ):
            config = DomainAnalyticsConfig(domain="example.com", platform="posthog")
            result = run_domain_analytics(config)

        assert result["domain"] == "example.com"
        assert result["platform"] == "posthog"
        assert result["total_urls"] == 3
        assert result["total_pageviews"] == 1600  # 1000 + 500 + 100
        assert result["rows_written"] == 3
        assert result["rows_updated"] == 0
        assert "workflow_id" in result

        # Verify data in database
        with managed_session() as session:
            # Check AnalyticsDomain
            domain_record = session.get(AnalyticsDomain, "example.com")
            assert domain_record is not None
            assert domain_record.platform == "posthog"
            assert domain_record.has_data is True

            # Check PageAnalytics
            pages = session.query(PageAnalytics).filter(PageAnalytics.domain == "example.com").all()
            assert len(pages) == 3

            # Check specific page metrics
            page1 = next((p for p in pages if "page1" in p.url), None)
            assert page1 is not None
            assert page1.pageviews_60d == 1000
            assert page1.pageviews_trend == "increasing"

    def test_sync_workflow_dry_run(self, tmp_kurt_project: Path, mock_metrics_map):
        """Test workflow in dry run mode doesn't persist."""
        from kurt_new.db import managed_session
        from kurt_new.workflows.domain_analytics import run_domain_analytics
        from kurt_new.workflows.domain_analytics.models import AnalyticsDomain, PageAnalytics

        with patch(
            "kurt_new.workflows.domain_analytics.steps.sync_domain_metrics",
            return_value=mock_metrics_map,
        ):
            config = DomainAnalyticsConfig(domain="example.com", platform="posthog", dry_run=True)
            result = run_domain_analytics(config)

        assert result["dry_run"] is True
        assert result["total_urls"] == 3
        assert result["rows_written"] == 0
        assert result["rows_updated"] == 0

        # Verify nothing in database
        with managed_session() as session:
            domain_record = session.get(AnalyticsDomain, "example.com")
            assert domain_record is None

            pages = session.query(PageAnalytics).all()
            assert len(pages) == 0

    def test_sync_workflow_updates_existing(self, tmp_kurt_project: Path, mock_metrics_map):
        """Test re-running workflow updates existing records."""
        from kurt_new.db import managed_session
        from kurt_new.workflows.domain_analytics import run_domain_analytics
        from kurt_new.workflows.domain_analytics.models import PageAnalytics

        with patch(
            "kurt_new.workflows.domain_analytics.steps.sync_domain_metrics",
            return_value=mock_metrics_map,
        ):
            # First run - inserts
            config = DomainAnalyticsConfig(domain="example.com", platform="posthog")
            result1 = run_domain_analytics(config)

        assert result1["rows_written"] == 3
        assert result1["rows_updated"] == 0

        with patch(
            "kurt_new.workflows.domain_analytics.steps.sync_domain_metrics",
            return_value=mock_metrics_map,
        ):
            # Second run - updates
            result2 = run_domain_analytics(config)

        assert result2["rows_written"] == 0
        assert result2["rows_updated"] == 3

        # Still only 3 records in database
        with managed_session() as session:
            pages = session.query(PageAnalytics).all()
            assert len(pages) == 3

    def test_sync_workflow_empty_domain(self, tmp_kurt_project: Path):
        """Test workflow with domain that has no analytics data."""
        from kurt_new.db import managed_session
        from kurt_new.workflows.domain_analytics import run_domain_analytics
        from kurt_new.workflows.domain_analytics.models import PageAnalytics

        # Return empty metrics map
        with patch(
            "kurt_new.workflows.domain_analytics.steps.sync_domain_metrics",
            return_value={},
        ):
            config = DomainAnalyticsConfig(domain="empty.com", platform="posthog")
            result = run_domain_analytics(config)

        assert result["total_urls"] == 0
        assert result["total_pageviews"] == 0
        assert result["rows_written"] == 0

        # Verify nothing persisted (no rows = nothing to persist)
        with managed_session() as session:
            pages = session.query(PageAnalytics).filter(PageAnalytics.domain == "empty.com").all()
            assert len(pages) == 0
