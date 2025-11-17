"""Tests for analytics service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kurt.db.models import AnalyticsDomain
from kurt.integrations.analytics.service import AnalyticsService


class TestGetAdapterForPlatform:
    """Test adapter factory method."""

    def test_get_posthog_adapter(self):
        """Test creating PostHog adapter."""
        platform_config = {
            "project_id": "phc_test123",
            "api_key": "phx_test456",
        }

        with patch(
            "kurt.integrations.analytics.adapters.posthog.PostHogAdapter"
        ) as mock_adapter_class:
            AnalyticsService.get_adapter_for_platform("posthog", platform_config)

            # Verify adapter was created with correct credentials
            mock_adapter_class.assert_called_once_with(
                project_id="phc_test123",
                api_key="phx_test456",
            )

    def test_unsupported_platform(self):
        """Test error for unsupported platform."""
        with pytest.raises(ValueError) as exc_info:
            AnalyticsService.get_adapter_for_platform("unknown", {})

        assert "Unsupported analytics platform: unknown" in str(exc_info.value)

    def test_ga4_not_implemented(self):
        """Test GA4 adapter raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc_info:
            AnalyticsService.get_adapter_for_platform("ga4", {"property_id": "123"})

        assert "GA4 adapter not yet implemented" in str(exc_info.value)


class TestTestPlatformConnection:
    """Test platform connection testing."""

    def test_connection_successful(self):
        """Test successful connection."""
        platform_config = {"project_id": "phc_test", "api_key": "phx_test"}

        mock_adapter = MagicMock()
        mock_adapter.test_connection.return_value = True

        with patch.object(AnalyticsService, "get_adapter_for_platform", return_value=mock_adapter):
            result = AnalyticsService.test_platform_connection("posthog", platform_config)

            assert result is True
            mock_adapter.test_connection.assert_called_once()

    def test_connection_failed(self):
        """Test failed connection."""
        platform_config = {"project_id": "phc_test", "api_key": "phx_test"}

        mock_adapter = MagicMock()
        mock_adapter.test_connection.return_value = False

        with patch.object(AnalyticsService, "get_adapter_for_platform", return_value=mock_adapter):
            result = AnalyticsService.test_platform_connection("posthog", platform_config)

            assert result is False


class TestRegisterDomain:
    """Test domain registration."""

    def test_register_new_domain(self, analytics_session):
        """Test registering a new domain."""
        domain_obj = AnalyticsService.register_domain(
            analytics_session, "docs.example.com", "posthog"
        )

        assert domain_obj.domain == "docs.example.com"
        assert domain_obj.platform == "posthog"
        assert domain_obj.has_data is False
        assert domain_obj.created_at is not None
        assert domain_obj.updated_at is not None

        # Verify saved to database
        analytics_session.commit()
        saved = (
            analytics_session.query(AnalyticsDomain)
            .filter(AnalyticsDomain.domain == "docs.example.com")
            .first()
        )
        assert saved is not None
        assert saved.id == domain_obj.id

    def test_update_existing_domain(self, analytics_session):
        """Test updating an existing domain registration."""
        # Create initial domain
        initial = AnalyticsDomain(
            domain="docs.example.com",
            platform="ga4",
            has_data=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        analytics_session.add(initial)
        analytics_session.commit()

        initial_id = initial.id
        initial_created_at = initial.created_at

        # Update to different platform
        updated = AnalyticsService.register_domain(analytics_session, "docs.example.com", "posthog")

        assert updated.id == initial_id  # Same record
        assert updated.platform == "posthog"  # Updated platform
        assert updated.created_at == initial_created_at  # Created date unchanged
        assert updated.updated_at > initial_created_at  # Updated date changed


# These test classes have been removed as they test old DocumentAnalytics functionality
# that was replaced with PageAnalytics in PR #19.
# The new PageAnalytics tests are in test_page_analytics_service.py


# Fixtures
@pytest.fixture
def analytics_session(tmp_path, monkeypatch):
    """Create a test database session with analytics tables."""
    from click.testing import CliRunner

    from kurt.cli import main
    from kurt.db.database import get_session

    # Create test project directory
    project_dir = tmp_path / "test-analytics-service"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Initialize Kurt project (creates DB)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0

    session = get_session()
    yield session
    session.close()
