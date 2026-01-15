"""
Tests for DocumentRegistry across all database modes.

This test suite verifies that document queries work correctly in:
1. SQLite mode (local development)
2. PostgreSQL mode (direct connection)
3. Kurt Cloud mode (PostgREST/Supabase)

Each mode uses different JOIN strategies:
- SQLite/PostgreSQL: SQLAlchemy outerjoin()
- Kurt Cloud: document_lifecycle VIEW

Usage:
    # Default: Only SQLite
    pytest src/kurt/documents/tests/test_multi_mode.py

    # With PostgreSQL (requires DATABASE_URL=postgresql://...)
    pytest src/kurt/documents/tests/test_multi_mode.py --run-postgres

    # With Kurt Cloud (requires kurt cloud login)
    pytest src/kurt/documents/tests/test_multi_mode.py --run-cloud

    # All modes
    pytest src/kurt/documents/tests/test_multi_mode.py --run-postgres --run-cloud
"""

from __future__ import annotations

import pytest

from kurt.db import managed_session
from kurt.documents import DocumentFilters, DocumentRegistry
from kurt.workflows.fetch.models import FetchStatus


class TestDocumentRegistryAllModes:
    """Test DocumentRegistry in all database modes.

    By default, only SQLite tests run. Use --run-postgres and --run-cloud
    to enable additional modes.
    """

    def test_list_all_documents(self, db_mode_project_with_docs):
        """Test listing all documents works in all modes."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session)

        # All 7 test documents should be returned
        assert len(docs) == 7

    def test_list_with_join(self, db_mode_project_with_docs):
        """Test JOIN queries work in all modes."""
        registry = DocumentRegistry()

        with managed_session() as session:
            # Query documents with fetch data
            docs = registry.list(session, DocumentFilters(fetch_status=FetchStatus.SUCCESS))

        # Should return 2 successfully fetched documents
        assert len(docs) == 2
        for doc in docs:
            assert doc.fetch_status == FetchStatus.SUCCESS
            assert doc.content_length is not None

    def test_list_not_fetched(self, db_mode_project_with_docs):
        """Test filtering for not-yet-fetched documents."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(not_fetched=True))

        # Should return 3 documents (doc-1, doc-2, doc-3)
        assert len(docs) == 3
        for doc in docs:
            assert doc.fetch_status is None

    def test_get_by_id(self, db_mode_project_with_docs):
        """Test getting single document by ID."""
        registry = DocumentRegistry()

        with managed_session() as session:
            doc = registry.get(session, "doc-4")

        assert doc is not None
        assert doc.document_id == "doc-4"
        assert doc.fetch_status == FetchStatus.SUCCESS
        assert doc.content_length == 5000

    def test_filter_by_url(self, db_mode_project_with_docs):
        """Test filtering by URL substring."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(url_contains="docs"))

        # Should find docs with "/docs/" in URL
        assert len(docs) >= 4  # doc-1, doc-2, doc-4, doc-5

    def test_filter_with_errors(self, db_mode_project_with_docs):
        """Test filtering for documents with errors."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(has_error=True))

        # Should return doc-6 (fetch error) and doc-7 (map error)
        assert len(docs) == 2


# =============================================================================
# Extended Tests with Parametrization
# =============================================================================


@pytest.mark.parametrize(
    "db_mode_project_with_docs",
    [
        pytest.param("sqlite", id="sqlite"),
        pytest.param("postgres", id="postgres", marks=pytest.mark.postgres),
        pytest.param("cloud", id="cloud", marks=pytest.mark.cloud),
    ],
    indirect=True,
)
class TestAllModesParametrized:
    """Extended tests that explicitly test all modes.

    These only run with appropriate flags (--run-postgres, --run-cloud).
    """

    def test_join_returns_tuples(self, db_mode_project_with_docs):
        """Verify that JOINs return proper MapDocument + FetchDocument tuples."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(ids=["doc-4"]))

        assert len(docs) == 1
        doc = docs[0]

        # Verify both map and fetch data are present
        assert doc.document_id == "doc-4"
        assert doc.source_url == "https://example.com/docs/api"
        assert doc.fetch_status == FetchStatus.SUCCESS
        assert doc.content_length == 5000

    def test_join_with_nulls(self, db_mode_project_with_docs):
        """Verify JOIN handles NULL fetch records (LEFT OUTER JOIN)."""
        registry = DocumentRegistry()

        with managed_session() as session:
            docs = registry.list(session, DocumentFilters(ids=["doc-1"]))

        assert len(docs) == 1
        doc = docs[0]

        # Has map data but no fetch data
        assert doc.document_id == "doc-1"
        assert doc.source_url == "https://example.com/docs/intro"
        assert doc.fetch_status is None
        assert doc.content_length is None


class TestCloudModeSpecifics:
    """Tests specific to Kurt Cloud mode (PostgREST)."""

    @pytest.mark.skip(reason="Requires Kurt Cloud authentication and setup")
    def test_uses_document_lifecycle_view(self):
        """Verify that cloud mode uses document_lifecycle VIEW for JOINs."""
        # This would require:
        # 1. Mock or real Kurt Cloud connection
        # 2. Verify _exec_join_query uses the VIEW
        # 3. Check that PostgREST query is correct
        pass

    @pytest.mark.skip(reason="Requires Kurt Cloud authentication and setup")
    def test_handles_postgrest_null_strings(self):
        """Verify that PostgREST 'null' strings are parsed correctly."""
        # This would test that string 'null' → None conversion works
        pass

    @pytest.mark.skip(reason="Requires Kurt Cloud authentication and setup")
    def test_parses_json_fields(self):
        """Verify that JSON fields are parsed from strings."""
        # metadata_json comes back as string from PostgREST, should be parsed
        pass


class TestPostgreSQLModeSpecifics:
    """Tests specific to PostgreSQL mode."""

    @pytest.mark.skip(reason="Requires PostgreSQL server")
    def test_uses_native_join(self):
        """Verify that PostgreSQL uses native SQL JOIN."""
        # This would verify SQLAlchemy generates proper JOIN SQL
        pass

    @pytest.mark.skip(reason="Requires PostgreSQL server and migration")
    def test_document_lifecycle_view_exists(self):
        """Verify that document_lifecycle VIEW exists in PostgreSQL."""
        from sqlalchemy import text

        from kurt.db import managed_session

        with managed_session() as session:
            result = session.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'document_lifecycle'
            """
                )
            )
            assert result.scalar() == "document_lifecycle"


# ============================================================================
# Integration Test Markers
# ============================================================================
#
# To run tests with real databases:
#
# SQLite (default):
#   pytest src/kurt/documents/tests/test_multi_mode.py -k sqlite
#
# PostgreSQL (requires server):
#   export DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"
#   pytest src/kurt/documents/tests/test_multi_mode.py -k postgresql --run-postgres
#
# Kurt Cloud (requires auth):
#   export DATABASE_URL="kurt"
#   kurt cloud login
#   pytest src/kurt/documents/tests/test_multi_mode.py -k cloud --run-cloud
#
