"""Tests for authentication middleware."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from kurt.web.api.auth import (
    AuthUser,
    extract_bearer_token,
    get_supabase_config,
    is_cloud_auth_enabled,
)


class TestAuthUser:
    """Tests for AuthUser class."""

    def test_auth_user_creation(self):
        """Test creating AuthUser with all fields."""
        user = AuthUser(
            user_id="user-123",
            email="test@example.com",
            workspace_id="ws-456",
            roles=["admin", "user"],
        )

        assert user.user_id == "user-123"
        assert user.email == "test@example.com"
        assert user.workspace_id == "ws-456"
        assert user.roles == ["admin", "user"]

    def test_auth_user_defaults(self):
        """Test AuthUser with default values."""
        user = AuthUser(user_id="user-123")

        assert user.user_id == "user-123"
        assert user.email is None
        assert user.workspace_id is None
        assert user.roles == []

    def test_auth_user_repr(self):
        """Test AuthUser string representation."""
        user = AuthUser(user_id="user-123", email="test@example.com")
        repr_str = repr(user)

        assert "user_id=user-123" in repr_str
        assert "email=test@example.com" in repr_str


class TestIsCloudAuthEnabled:
    """Tests for is_cloud_auth_enabled function."""

    def test_disabled_by_default(self):
        """Test cloud auth is disabled by default."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("KURT_CLOUD_AUTH", None)
            assert is_cloud_auth_enabled() is False

    def test_enabled_when_true(self):
        """Test cloud auth enabled with KURT_CLOUD_AUTH=true."""
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "true"}, clear=True):
            assert is_cloud_auth_enabled() is True

    def test_case_insensitive(self):
        """Test KURT_CLOUD_AUTH is case insensitive."""
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "TRUE"}, clear=True):
            assert is_cloud_auth_enabled() is True
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "True"}, clear=True):
            assert is_cloud_auth_enabled() is True

    def test_disabled_with_other_values(self):
        """Test cloud auth disabled with non-true values."""
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "false"}, clear=True):
            assert is_cloud_auth_enabled() is False
        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "1"}, clear=True):
            assert is_cloud_auth_enabled() is False


class TestGetSupabaseConfig:
    """Tests for get_supabase_config function."""

    def test_returns_empty_defaults(self):
        """Test returns empty defaults when env vars not set."""
        # Clear cache to ensure fresh config
        get_supabase_config.cache_clear()

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SUPABASE_URL", None)
            os.environ.pop("SUPABASE_ANON_KEY", None)
            os.environ.pop("SUPABASE_JWT_SECRET", None)

            config = get_supabase_config()

            assert "url" in config
            assert "anon_key" in config
            assert "jwt_secret" in config
            assert config["url"] == ""
            assert config["anon_key"] == ""
            assert config["jwt_secret"] == ""

    def test_uses_env_vars_when_set(self):
        """Test uses environment variables when set."""
        get_supabase_config.cache_clear()

        with patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://custom.supabase.co",
                "SUPABASE_ANON_KEY": "custom-anon-key",
                "SUPABASE_JWT_SECRET": "custom-secret",
            },
            clear=True,
        ):
            config = get_supabase_config()

            assert config["url"] == "https://custom.supabase.co"
            assert config["anon_key"] == "custom-anon-key"
            assert config["jwt_secret"] == "custom-secret"

        # Clean up cache
        get_supabase_config.cache_clear()


class TestExtractBearerToken:
    """Tests for extract_bearer_token function."""

    def test_extracts_valid_token(self):
        """Test extracting valid Bearer token."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Bearer abc123token"

        token = extract_bearer_token(mock_request)

        assert token == "abc123token"

    def test_returns_none_when_no_header(self):
        """Test returns None when no Authorization header."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        token = extract_bearer_token(mock_request)

        assert token is None

    def test_returns_none_when_not_bearer(self):
        """Test returns None when not Bearer auth."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Basic abc123"

        token = extract_bearer_token(mock_request)

        assert token is None

    def test_handles_empty_token(self):
        """Test handles Bearer with empty token."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Bearer "

        token = extract_bearer_token(mock_request)

        assert token == ""

    def test_preserves_token_with_special_chars(self):
        """Test preserves token with special characters."""
        mock_request = MagicMock()
        # JWT tokens contain dots and base64 characters
        jwt_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        mock_request.headers.get.return_value = f"Bearer {jwt_token}"

        token = extract_bearer_token(mock_request)

        assert token == jwt_token


class TestApiMe:
    """Tests for /api/me endpoint."""

    def test_local_mode_returns_is_cloud_mode_false(self):
        """Test /api/me returns is_cloud_mode: false in local mode."""
        from fastapi.testclient import TestClient

        from kurt.web.api.server import app

        # Ensure cloud auth is disabled
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("KURT_CLOUD_AUTH", None)

            client = TestClient(app)
            response = client.get("/api/me")

            assert response.status_code == 200
            data = response.json()
            assert data == {"is_cloud_mode": False}

    def test_cloud_mode_no_auth_returns_user_null(self):
        """Test /api/me returns user: null in cloud mode without auth."""
        from fastapi.testclient import TestClient

        from kurt.web.api.server import app

        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "true"}, clear=True):
            with patch("kurt.web.api.server.is_cloud_auth_enabled", return_value=True):
                with patch("kurt.web.api.server.get_authenticated_user", return_value=None):
                    client = TestClient(app)
                    response = client.get("/api/me")

                    assert response.status_code == 200
                    data = response.json()
                    assert data == {"is_cloud_mode": True, "user": None}

    def test_cloud_mode_with_auth_returns_user_info(self):
        """Test /api/me returns user info in cloud mode with auth."""
        from fastapi.testclient import TestClient

        from kurt.web.api.server import app

        mock_user = AuthUser(
            user_id="user-123",
            email="test@example.com",
            workspace_id="ws-456",
        )

        with patch.dict(os.environ, {"KURT_CLOUD_AUTH": "true"}, clear=True):
            with patch("kurt.web.api.server.is_cloud_auth_enabled", return_value=True):
                with patch("kurt.web.api.server.get_authenticated_user", return_value=mock_user):
                    client = TestClient(app)
                    response = client.get("/api/me")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["is_cloud_mode"] is True
                    assert data["user"]["id"] == "user-123"
                    assert data["user"]["email"] == "test@example.com"
                    assert data["workspace"]["id"] == "ws-456"
                    assert data["workspace"]["name"] == "ws-456"
