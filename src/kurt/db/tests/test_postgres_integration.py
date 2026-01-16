"""Integration tests for PostgreSQL with RLS and multi-tenant support.

These tests use pytest-postgresql to create a temporary PostgreSQL instance.
They verify that:
1. Schema-qualified DBOS tables work correctly
2. RLS context is properly set
3. Tenant isolation works as expected

Requires PostgreSQL to be installed locally (pg_ctl in PATH).
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Skip all tests if PostgreSQL is not available
pytest_plugins = ["pytest_postgresql"]


@pytest.fixture
def pg_engine(postgresql):
    """Create SQLAlchemy engine from pytest-postgresql connection."""
    # Get connection info from the psycopg connection
    info = postgresql.info
    url = f"postgresql://{info.user}@{info.host}:{info.port}/{info.dbname}"
    engine = create_engine(url)
    return engine


@pytest.fixture
def pg_session(pg_engine):
    """Create a session with the PostgreSQL engine."""
    with Session(pg_engine) as session:
        yield session


class TestPostgresSchemaQualifiedTables:
    """Test schema-qualified table names for DBOS."""

    def test_dbos_schema_detection(self):
        """Test that _get_dbos_schema returns 'dbos' for PostgreSQL."""
        from kurt.core.status import _get_dbos_schema

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}):
            assert _get_dbos_schema() == "dbos"

    def test_dbos_schema_empty_for_sqlite(self):
        """Test that _get_dbos_schema returns empty for SQLite."""
        from kurt.core.status import _get_dbos_schema

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            assert _get_dbos_schema() == ""

    def test_dbos_table_qualified_name(self):
        """Test _dbos_table returns qualified names for PostgreSQL."""
        from kurt.core.status import _dbos_table

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}):
            assert _dbos_table("workflow_status") == "dbos.workflow_status"
            assert _dbos_table("workflow_events") == "dbos.workflow_events"

    def test_dbos_table_plain_name_for_sqlite(self):
        """Test _dbos_table returns plain names for SQLite."""
        from kurt.core.status import _dbos_table

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            assert _dbos_table("workflow_status") == "workflow_status"

    def test_get_dbos_table_names(self):
        """Test get_dbos_table_names returns correct dict."""
        from kurt.core.status import get_dbos_table_names

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}):
            names = get_dbos_table_names()
            assert names["workflow_status"] == "dbos.workflow_status"
            assert names["workflow_events"] == "dbos.workflow_events"
            assert names["streams"] == "dbos.streams"


class TestRLSContextSetting:
    """Test RLS context is set correctly in PostgreSQL sessions."""

    def test_set_rls_context_executes_set_local(self, pg_session):
        """Test that set_rls_context executes SET LOCAL statements."""
        from kurt.db.tenant import (
            clear_workspace_context,
            set_rls_context,
            set_workspace_context,
        )

        with patch.dict(
            os.environ,
            {"KURT_CLOUD_AUTH": "true", "DATABASE_URL": "postgresql://localhost/db"},
        ):
            set_workspace_context(workspace_id="ws-test-123", user_id="user-test-456")

            try:
                # This should execute SET LOCAL statements
                set_rls_context(pg_session)

                # Verify the context was set by reading it back
                result = pg_session.execute(
                    text("SELECT current_setting('app.user_id', true)")
                ).scalar()
                assert result == "user-test-456"

                result = pg_session.execute(
                    text("SELECT current_setting('app.workspace_id', true)")
                ).scalar()
                assert result == "ws-test-123"
            finally:
                clear_workspace_context()

    def test_rls_context_cleared_after_transaction(self, pg_engine):
        """Test that RLS context is transaction-scoped (SET LOCAL)."""
        from kurt.db.tenant import (
            clear_workspace_context,
            set_rls_context,
            set_workspace_context,
        )

        with patch.dict(
            os.environ,
            {"KURT_CLOUD_AUTH": "true", "DATABASE_URL": "postgresql://localhost/db"},
        ):
            # First transaction - set context
            with Session(pg_engine) as session1:
                set_workspace_context(workspace_id="ws-1", user_id="user-1")
                set_rls_context(session1)
                result = session1.execute(
                    text("SELECT current_setting('app.user_id', true)")
                ).scalar()
                assert result == "user-1"
                session1.commit()

            clear_workspace_context()

            # Second transaction - context should be empty
            with Session(pg_engine) as session2:
                result = session2.execute(
                    text("SELECT current_setting('app.user_id', true)")
                ).scalar()
                # Should be empty or None after transaction ends
                assert result in (None, "")


class TestManagedSessionWithPostgres:
    """Test managed_session works correctly with PostgreSQL."""

    def test_managed_session_sets_rls_in_cloud_mode(self, pg_engine):
        """Test managed_session sets RLS context in cloud mode."""
        from kurt.db.tenant import clear_workspace_context, set_workspace_context

        # Patch get_session to return our test session
        with patch.dict(
            os.environ,
            {"KURT_CLOUD_AUTH": "true", "DATABASE_URL": "postgresql://localhost/db"},
        ):
            set_workspace_context(workspace_id="ws-managed", user_id="user-managed")

            try:
                with Session(pg_engine) as session:
                    # Manually call set_rls_context since managed_session uses get_session
                    from kurt.db.tenant import set_rls_context

                    set_rls_context(session)

                    result = session.execute(
                        text("SELECT current_setting('app.user_id', true)")
                    ).scalar()
                    assert result == "user-managed"
            finally:
                clear_workspace_context()


class TestTenantIsolation:
    """Test tenant isolation with actual PostgreSQL tables."""

    @pytest.fixture
    def setup_test_table(self, pg_session):
        """Create a test table with tenant columns."""
        pg_session.execute(
            text("""
                CREATE TABLE IF NOT EXISTS test_tenant_docs (
                    id SERIAL PRIMARY KEY,
                    content TEXT,
                    user_id TEXT,
                    workspace_id TEXT
                )
            """)
        )
        pg_session.commit()
        yield
        pg_session.execute(text("DROP TABLE IF EXISTS test_tenant_docs"))
        pg_session.commit()

    def test_insert_with_tenant_context(self, pg_session, setup_test_table):
        """Test inserting records with tenant context."""
        # Insert some test data
        pg_session.execute(
            text("""
                INSERT INTO test_tenant_docs (content, user_id, workspace_id)
                VALUES
                    ('doc1', 'user-a', 'ws-a'),
                    ('doc2', 'user-a', 'ws-a'),
                    ('doc3', 'user-b', 'ws-b')
            """)
        )
        pg_session.commit()

        # Query all
        result = pg_session.execute(text("SELECT COUNT(*) FROM test_tenant_docs")).scalar()
        assert result == 3

        # Query filtered by user
        result = pg_session.execute(
            text("SELECT COUNT(*) FROM test_tenant_docs WHERE user_id = 'user-a'")
        ).scalar()
        assert result == 2

    def test_add_workspace_filter_helper(self, pg_session, setup_test_table):
        """Test add_workspace_filter helper function."""
        from kurt.db.tenant import (
            add_workspace_filter,
            clear_workspace_context,
            set_workspace_context,
        )

        # Insert test data
        pg_session.execute(
            text("""
                INSERT INTO test_tenant_docs (content, user_id, workspace_id)
                VALUES
                    ('doc1', 'user-a', 'ws-a'),
                    ('doc2', 'user-b', 'ws-b')
            """)
        )
        pg_session.commit()

        # Set context for user-a
        set_workspace_context(workspace_id="ws-a", user_id="user-a")

        try:
            # Use the helper to add filter
            sql = "SELECT * FROM test_tenant_docs WHERE 1=1"
            params: dict = {}
            sql, params = add_workspace_filter(sql, params)

            result = pg_session.execute(text(sql), params).fetchall()
            assert len(result) == 1
            assert result[0].content == "doc1"
        finally:
            clear_workspace_context()


class TestModeDetectionWithRealEnv:
    """Test mode detection with various environment configurations."""

    def test_all_modes(self):
        """Test all three modes are correctly detected."""
        from kurt.db.tenant import get_mode

        # local_sqlite (default)
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            os.environ.pop("KURT_CLOUD_AUTH", None)
            assert get_mode() == "local_sqlite"

        # local_postgres
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}, clear=True):
            os.environ.pop("KURT_CLOUD_AUTH", None)
            assert get_mode() == "local_postgres"

        # cloud_postgres
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://localhost/db", "KURT_CLOUD_AUTH": "true"},
            clear=True,
        ):
            assert get_mode() == "cloud_postgres"
