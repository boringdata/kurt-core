"""Tests for analytics models and database interactions.

Tests the UUID primary key change in AnalyticsDomain to ensure:
1. Domain can be queried by domain field (not primary key)
2. UUID primary key is correctly set
3. No regressions from changing PK from domain to id
"""

from uuid import UUID

import pytest

from kurt.db.database import get_session
from kurt.db.models import AnalyticsDomain


@pytest.fixture
def analytics_session(tmp_path, monkeypatch):
    """Create a test database session with analytics tables."""

    from click.testing import CliRunner

    from kurt.cli import main

    # Create test project directory
    project_dir = tmp_path / "test-analytics"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)

    # Initialize Kurt project (creates DB)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0

    session = get_session()
    yield session
    session.close()


class TestAnalyticsDomainUUIDPrimaryKey:
    """Test AnalyticsDomain UUID primary key functionality."""

    def test_domain_has_uuid_primary_key(self, analytics_session):
        """Test that AnalyticsDomain uses UUID as primary key."""
        # Create a domain
        domain = AnalyticsDomain(
            domain="docs.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain)
        analytics_session.commit()

        # Verify ID is UUID
        assert domain.id is not None
        assert isinstance(domain.id, UUID)

    def test_domain_field_is_unique_not_primary(self, analytics_session):
        """Test that domain field is unique but not the primary key."""
        # Create first domain
        domain1 = AnalyticsDomain(
            domain="test.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain1)
        analytics_session.commit()

        # Try to create duplicate domain (should fail due to unique constraint)
        domain2 = AnalyticsDomain(
            domain="test.example.com",  # Same domain
            platform="ga4",
            has_data=False,
        )
        analytics_session.add(domain2)

        with pytest.raises(Exception):  # IntegrityError or similar
            analytics_session.commit()

    def test_query_by_domain_field_not_primary_key(self, analytics_session):
        """Test querying by domain field (regression test for session.get() bug)."""
        # Create a domain
        domain = AnalyticsDomain(
            domain="test.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain)
        analytics_session.commit()

        domain_id = domain.id
        domain_name = domain.domain

        # THIS WOULD FAIL with old code: session.get(AnalyticsDomain, domain_name)
        # because session.get() uses primary key (id=UUID), not domain field

        # CORRECT: Query by domain field using filter
        found = (
            analytics_session.query(AnalyticsDomain)
            .filter(AnalyticsDomain.domain == domain_name)
            .first()
        )

        assert found is not None
        assert found.id == domain_id
        assert found.domain == domain_name

    def test_session_get_requires_uuid_not_string(self, analytics_session):
        """Test that session.get() requires UUID, not domain string."""
        # Create a domain
        domain = AnalyticsDomain(
            domain="test.example.com",
            platform="posthog",
            has_data=False,
        )
        analytics_session.add(domain)
        analytics_session.commit()

        domain_id = domain.id
        domain_name = domain.domain

        # session.get() by UUID (primary key) - WORKS
        found_by_id = analytics_session.get(AnalyticsDomain, domain_id)
        assert found_by_id is not None
        assert found_by_id.domain == domain_name

        # session.get() by domain string - FAILS (raises error)
        # This is the regression we fixed in commands/analytics.py
        with pytest.raises(Exception):  # StatementError from SQLAlchemy
            analytics_session.get(AnalyticsDomain, domain_name)

    def test_multiple_domains_different_uuids(self, analytics_session):
        """Test that multiple domains get different UUID primary keys."""
        domain1 = AnalyticsDomain(domain="docs.example.com", platform="posthog", has_data=False)
        domain2 = AnalyticsDomain(domain="blog.example.com", platform="ga4", has_data=False)

        analytics_session.add_all([domain1, domain2])
        analytics_session.commit()

        # Each should have unique UUID
        assert domain1.id != domain2.id
        assert isinstance(domain1.id, UUID)
        assert isinstance(domain2.id, UUID)

        # But we can query each by domain field
        found1 = (
            analytics_session.query(AnalyticsDomain)
            .filter(AnalyticsDomain.domain == "docs.example.com")
            .first()
        )
        found2 = (
            analytics_session.query(AnalyticsDomain)
            .filter(AnalyticsDomain.domain == "blog.example.com")
            .first()
        )

        assert found1.id == domain1.id
        assert found2.id == domain2.id
