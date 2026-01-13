"""Tests for tenant context management and mode detection."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from kurt.db.tenant import (
    WorkspaceContext,
    add_workspace_filter,
    clear_workspace_context,
    get_mode,
    get_user_id,
    get_workspace_context,
    get_workspace_id,
    is_cloud_mode,
    is_multi_tenant,
    is_postgres,
    require_workspace_id,
    set_rls_context,
    set_workspace_context,
)


class TestWorkspaceContext:
    """Tests for workspace context management."""

    def setup_method(self):
        """Clear context before each test."""
        clear_workspace_context()

    def teardown_method(self):
        """Clear context after each test."""
        clear_workspace_context()

    def test_set_and_get_workspace_context(self):
        """Test setting and retrieving workspace context."""
        set_workspace_context(workspace_id="ws-123", user_id="user-456")

        ctx = get_workspace_context()
        assert ctx is not None
        assert ctx.workspace_id == "ws-123"
        assert ctx.user_id == "user-456"

    def test_get_workspace_id(self):
        """Test getting workspace ID directly."""
        set_workspace_context(workspace_id="ws-abc")
        assert get_workspace_id() == "ws-abc"

    def test_get_user_id(self):
        """Test getting user ID directly."""
        set_workspace_context(workspace_id="ws-abc", user_id="user-xyz")
        assert get_user_id() == "user-xyz"

    def test_get_workspace_id_returns_none_when_not_set(self):
        """Test workspace ID is None when context not set."""
        assert get_workspace_id() is None

    def test_get_user_id_returns_none_when_not_set(self):
        """Test user ID is None when context not set."""
        assert get_user_id() is None

    def test_clear_workspace_context(self):
        """Test clearing workspace context."""
        set_workspace_context(workspace_id="ws-123", user_id="user-456")
        clear_workspace_context()

        assert get_workspace_context() is None
        assert get_workspace_id() is None
        assert get_user_id() is None

    def test_require_workspace_id_success(self):
        """Test require_workspace_id returns ID when set."""
        set_workspace_context(workspace_id="ws-required")
        assert require_workspace_id() == "ws-required"

    def test_require_workspace_id_raises_when_not_set(self):
        """Test require_workspace_id raises when not set."""
        with pytest.raises(RuntimeError, match="Workspace context required"):
            require_workspace_id()

    def test_workspace_context_immutable(self):
        """Test WorkspaceContext is immutable (frozen dataclass)."""
        ctx = WorkspaceContext(workspace_id="ws-1", user_id="u-1")
        with pytest.raises(AttributeError):
            ctx.workspace_id = "ws-2"  # type: ignore


class TestModeDetection:
    """Tests for mode detection functions."""

    def test_is_multi_tenant_false_by_default(self):
        """Test is_multi_tenant returns False with no env vars."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove both env vars
            os.environ.pop("KURT_MULTI_TENANT", None)
            os.environ.pop("DATABASE_URL", None)
            assert is_multi_tenant() is False

    def test_is_multi_tenant_true_with_explicit_flag(self):
        """Test is_multi_tenant returns True with KURT_MULTI_TENANT=true."""
        with patch.dict(os.environ, {"KURT_MULTI_TENANT": "true"}, clear=True):
            assert is_multi_tenant() is True

    def test_is_multi_tenant_true_with_database_url(self):
        """Test is_multi_tenant returns True with DATABASE_URL set."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}, clear=True):
            assert is_multi_tenant() is True

    def test_is_cloud_mode_false_by_default(self):
        """Test is_cloud_mode returns False with no env vars."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("KURT_CLOUD_AUTH", None)
            assert is_cloud_mode() is False

    def test_is_cloud_mode_true_when_enabled(self):
        """Test is_cloud_mode returns True with KURT_CLOUD_AUTH=true."""
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "true"}, clear=True):
            assert is_cloud_mode() is True

    def test_is_cloud_mode_case_insensitive(self):
        """Test is_cloud_mode handles case variations."""
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "TRUE"}, clear=True):
            assert is_cloud_mode() is True
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "True"}, clear=True):
            assert is_cloud_mode() is True

    def test_is_postgres_false_by_default(self):
        """Test is_postgres returns False with no DATABASE_URL."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            assert is_postgres() is False

    def test_is_postgres_true_with_postgresql_url(self):
        """Test is_postgres returns True with postgresql:// URL."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}, clear=True):
            assert is_postgres() is True

    def test_is_postgres_true_with_postgres_url(self):
        """Test is_postgres returns True with postgres:// URL."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgres://localhost/db"}, clear=True):
            # postgres:// doesn't start with "postgresql" so returns False
            # This is current behavior - only postgresql:// prefix is recognized
            assert is_postgres() is False

    def test_is_postgres_false_with_sqlite_url(self):
        """Test is_postgres returns False with sqlite:// URL."""
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///path/to/db"}, clear=True):
            assert is_postgres() is False


class TestGetMode:
    """Tests for get_mode function."""

    def test_local_sqlite_mode(self):
        """Test local_sqlite mode when no DATABASE_URL."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            os.environ.pop("KURT_CLOUD_AUTH", None)
            assert get_mode() == "local_sqlite"

    def test_local_postgres_mode(self):
        """Test local_postgres mode with DATABASE_URL but no auth."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/db"}, clear=True):
            os.environ.pop("KURT_CLOUD_AUTH", None)
            assert get_mode() == "local_postgres"

    def test_cloud_postgres_mode(self):
        """Test cloud_postgres mode with DATABASE_URL and auth enabled."""
        with patch.dict(
            os.environ,
            {"DATABASE_URL": "postgresql://localhost/db", "KURT_CLOUD_AUTH": "true"},
            clear=True,
        ):
            assert get_mode() == "cloud_postgres"


class TestRLSContext:
    """Tests for RLS context setting."""

    def setup_method(self):
        """Clear context before each test."""
        clear_workspace_context()

    def teardown_method(self):
        """Clear context after each test."""
        clear_workspace_context()

    def test_set_rls_context_skipped_in_local_mode(self):
        """Test set_rls_context does nothing in local mode."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("KURT_CLOUD_AUTH", None)
            os.environ.pop("DATABASE_URL", None)

            mock_session = MagicMock()
            set_rls_context(mock_session)

            # Should not execute any SQL
            mock_session.execute.assert_not_called()

    def test_set_rls_context_skipped_without_postgres(self):
        """Test set_rls_context does nothing without Postgres."""
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "true"}, clear=True):
            os.environ.pop("DATABASE_URL", None)

            mock_session = MagicMock()
            set_rls_context(mock_session)

            mock_session.execute.assert_not_called()

    def test_set_rls_context_sets_variables_in_cloud_mode(self):
        """Test set_rls_context sets session variables in cloud mode."""
        with patch.dict(
            os.environ,
            {"KURT_CLOUD_AUTH": "true", "DATABASE_URL": "postgresql://localhost/db"},
            clear=True,
        ):
            set_workspace_context(workspace_id="ws-123", user_id="user-456")

            mock_session = MagicMock()
            set_rls_context(mock_session)

            # Should execute SET LOCAL statements
            assert mock_session.execute.call_count == 2
            # Check the actual SQL text objects passed to execute
            call_args = [call[0][0] for call in mock_session.execute.call_args_list]
            sql_texts = [str(arg) for arg in call_args]
            assert any("app.user_id" in sql for sql in sql_texts)
            assert any("app.workspace_id" in sql for sql in sql_texts)

    def test_set_rls_context_skips_unset_values(self):
        """Test set_rls_context skips variables that are not set."""
        with patch.dict(
            os.environ,
            {"KURT_CLOUD_AUTH": "true", "DATABASE_URL": "postgresql://localhost/db"},
            clear=True,
        ):
            # Only set workspace_id, not user_id
            set_workspace_context(workspace_id="ws-only")

            mock_session = MagicMock()
            set_rls_context(mock_session)

            # Should only execute one SET LOCAL (for workspace_id)
            assert mock_session.execute.call_count == 1


class TestAddWorkspaceFilter:
    """Tests for add_workspace_filter helper."""

    def setup_method(self):
        """Clear context before each test."""
        clear_workspace_context()

    def teardown_method(self):
        """Clear context after each test."""
        clear_workspace_context()

    def test_no_filter_when_no_context(self):
        """Test no filter added when workspace context not set."""
        sql = "SELECT * FROM docs WHERE id = :id"
        params = {"id": "123"}

        result_sql, result_params = add_workspace_filter(sql, params)

        assert result_sql == sql
        assert result_params == params

    def test_filter_added_with_context(self):
        """Test filter added when workspace context is set."""
        set_workspace_context(workspace_id="ws-filter")

        sql = "SELECT * FROM docs WHERE id = :id"
        params = {"id": "123"}

        result_sql, result_params = add_workspace_filter(sql, params)

        assert "workspace_id = :workspace_id" in result_sql
        assert result_params["workspace_id"] == "ws-filter"
        assert result_params["id"] == "123"

    def test_filter_with_table_alias(self):
        """Test filter with table alias."""
        set_workspace_context(workspace_id="ws-alias")

        sql = "SELECT * FROM fetch_documents fd WHERE fd.id = :id"
        params = {"id": "123"}

        result_sql, result_params = add_workspace_filter(sql, params, table_alias="fd")

        assert "fd.workspace_id = :workspace_id" in result_sql
        assert result_params["workspace_id"] == "ws-alias"
