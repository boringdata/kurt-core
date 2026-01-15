"""Integration tests for RLS (Row Level Security) context propagation.

This tests the full flow:
1. Auth middleware extracts user_id/workspace_id from JWT
2. Sets workspace context via set_workspace_context()
3. managed_session() reads context and sets PostgreSQL session variables
4. RLS policies filter data automatically
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestRLSContextPropagation:
    """Test RLS context flows from middleware to database session."""

    def test_managed_session_applies_rls_variables(self, tmp_project):
        """Test managed_session() sets PostgreSQL session variables when context is set."""
        from kurt.db import managed_session
        from kurt.db.tenant import set_workspace_context

        # Set workspace context (simulating middleware)
        set_workspace_context(workspace_id="ws-456", user_id="user-123")

        # Create a mock session that tracks execute() calls
        with patch("kurt.db.database.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Patch is_cloud_mode and is_postgres to enable RLS
            with patch("kurt.db.tenant.is_cloud_mode") as mock_cloud:
                mock_cloud.return_value = True
                with patch("kurt.db.tenant.is_postgres") as mock_postgres:
                    mock_postgres.return_value = True

                    with managed_session():
                        # managed_session should have called set_rls_context()
                        # which executes SET LOCAL commands
                        pass

                    # Verify SET LOCAL was called with parameterized queries
                    calls = mock_session.execute.call_args_list
                    assert len(calls) >= 2, "Expected at least 2 SET LOCAL calls"

                    # Check user_id was set
                    user_call = calls[0]
                    assert "SET LOCAL app.user_id" in str(user_call[0][0])
                    assert user_call[0][1] == {"user_id": "user-123"}

                    # Check workspace_id was set
                    workspace_call = calls[1]
                    assert "SET LOCAL app.workspace_id" in str(workspace_call[0][0])
                    assert workspace_call[0][1] == {"workspace_id": "ws-456"}

    def test_local_mode_skips_rls(self, tmp_project):
        """Test RLS is skipped in local mode (not cloud, not postgres)."""
        from kurt.db import managed_session
        from kurt.db.tenant import set_workspace_context

        # Set workspace context
        set_workspace_context(workspace_id="ws-456", user_id="user-123")

        # Create a mock session
        with patch("kurt.db.database.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Patch is_cloud_mode to return False (local mode)
            with patch("kurt.db.tenant.is_cloud_mode") as mock_cloud:
                mock_cloud.return_value = False

                with managed_session():
                    pass

                # SET LOCAL should NOT be called in local mode
                # (even if context is set)
                execute_calls = mock_session.execute.call_args_list
                for call in execute_calls:
                    assert "SET LOCAL" not in str(call)

    def test_supabase_session_skips_rls(self, tmp_project):
        """Test SupabaseSession skips SET LOCAL (RLS handled by PostgREST)."""
        from kurt.db import managed_session
        from kurt.db.cloud import SupabaseSession
        from kurt.db.tenant import set_workspace_context

        # Set workspace context
        set_workspace_context(workspace_id="ws-456", user_id="user-123")

        # Create a mock SupabaseSession
        mock_supabase_session = MagicMock(spec=SupabaseSession)

        with patch("kurt.db.database.get_session") as mock_get_session:
            mock_get_session.return_value = mock_supabase_session

            with managed_session():
                pass

            # SET LOCAL should NOT be called for SupabaseSession
            # (RLS is handled by PostgREST via JWT)
            mock_supabase_session.execute.assert_not_called()


class TestSQLInjectionProtection:
    """Test SQL injection protection in RLS context."""

    def test_malicious_user_id_rejected(self, tmp_project):
        """Test malicious user_id doesn't cause SQL injection."""
        from kurt.db import managed_session
        from kurt.db.tenant import set_workspace_context

        # Set malicious context (attempt SQL injection)
        malicious_user_id = "user-123'; DROP TABLE map_documents; --"
        set_workspace_context(workspace_id="ws-456", user_id=malicious_user_id)

        with patch("kurt.db.database.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch("kurt.db.tenant.is_cloud_mode") as mock_cloud:
                mock_cloud.return_value = True
                with patch("kurt.db.tenant.is_postgres") as mock_postgres:
                    mock_postgres.return_value = True

                    with managed_session():
                        pass

                    # Verify parameterized query was used (not string interpolation)
                    calls = mock_session.execute.call_args_list
                    user_call = calls[0]

                    # Should use :user_id parameter, not f-string
                    assert ":user_id" in str(user_call[0][0])
                    # Parameter should be passed separately
                    assert user_call[0][1] == {"user_id": malicious_user_id}
                    # Malicious code should be treated as literal string
                    assert "DROP TABLE" not in str(user_call[0][0])

    def test_malicious_workspace_id_rejected(self, tmp_project):
        """Test malicious workspace_id doesn't cause SQL injection."""
        from kurt.db import managed_session
        from kurt.db.tenant import set_workspace_context

        # Set malicious context
        malicious_workspace_id = "ws'; DELETE FROM fetch_documents WHERE '1'='1"
        set_workspace_context(workspace_id=malicious_workspace_id, user_id="user-123")

        with patch("kurt.db.database.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with patch("kurt.db.tenant.is_cloud_mode") as mock_cloud:
                mock_cloud.return_value = True
                with patch("kurt.db.tenant.is_postgres") as mock_postgres:
                    mock_postgres.return_value = True

                    with managed_session():
                        pass

                    # Verify parameterized query was used
                    calls = mock_session.execute.call_args_list
                    workspace_call = calls[1]

                    assert ":workspace_id" in str(workspace_call[0][0])
                    assert workspace_call[0][1] == {"workspace_id": malicious_workspace_id}
                    assert "DELETE FROM" not in str(workspace_call[0][0])
