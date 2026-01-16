"""Tests for GitHub App client."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Check dependencies available
try:
    import httpx  # noqa: F401
    import jwt  # noqa: F401

    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    pytest.skip("httpx and PyJWT required for GitHub App tests", allow_module_level=True)


@pytest.fixture
def mock_env_credentials(monkeypatch):
    """Set up mock GitHub App credentials in environment."""
    monkeypatch.setenv("GITHUB_APP_ID", "123456")
    # Don't need real RSA key - we'll mock jwt.encode()
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "fake-private-key")


@pytest.fixture
def github_client(mock_env_credentials):
    """Create GitHub App client with mock credentials."""
    from kurt.github.app_client import GitHubAppClient

    return GitHubAppClient()


def test_client_initialization_from_env(mock_env_credentials):
    """Test client can be initialized from environment variables."""
    from kurt.github.app_client import GitHubAppClient

    client = GitHubAppClient()
    assert client.app_id == "123456"
    assert client.private_key == "fake-private-key"


def test_client_initialization_fails_without_credentials():
    """Test client raises error if credentials are missing."""
    from kurt.github.app_client import GitHubAppClient

    with pytest.raises(ValueError, match="GITHUB_APP_ID"):
        GitHubAppClient()


def test_generate_jwt(github_client):
    """Test JWT generation."""
    with patch("jwt.encode") as mock_encode:
        mock_encode.return_value = "mocked_jwt_token"

        jwt_token = github_client.generate_jwt()

        assert jwt_token == "mocked_jwt_token"

        # Verify jwt.encode was called with correct parameters
        mock_encode.assert_called_once()
        call_args = mock_encode.call_args
        payload = call_args[0][0]

        assert payload["iss"] == "123456"
        assert "iat" in payload
        assert "exp" in payload
        assert call_args[1]["algorithm"] == "RS256"


@pytest.mark.asyncio
async def test_get_installation_token(github_client):
    """Test fetching installation access token."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "token": "ghs_installation_token_123",
        "expires_at": "2026-01-16T11:00:00Z",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("jwt.encode", return_value="mocked_jwt"):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await github_client.get_installation_token(12345)

            assert result["token"] == "ghs_installation_token_123"
            assert isinstance(result["expires_at"], datetime)
            assert result["expires_at"].tzinfo is not None

            # Verify API call
            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            assert "installations/12345/access_tokens" in call_args[0][0]


@pytest.mark.asyncio
async def test_get_workspace_token_fresh(github_client):
    """Test getting workspace token fetches new token if none exists."""
    from kurt.db.workspace_models import Workspace

    # Mock workspace with no token
    workspace = Workspace(
        id="ws-123",
        name="Test Workspace",
        slug="test",
        github_owner="acme",
        github_repo="docs",
        github_installation_id=12345,
        owner_user_id="user-1",
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "token": "ghs_new_token",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    mock_response.raise_for_status = MagicMock()

    with patch("jwt.encode", return_value="mocked_jwt"):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            with patch("kurt.db.managed_session") as mock_session:
                mock_session_instance = MagicMock()
                mock_session_instance.get.return_value = workspace
                mock_session_instance.__enter__.return_value = mock_session_instance
                mock_session.return_value = mock_session_instance

                token = await github_client.get_workspace_token("ws-123")

                assert token == "ghs_new_token"
                # Verify workspace was updated
                assert workspace.github_installation_token == "ghs_new_token"
                assert workspace.github_installation_token_expires_at is not None


@pytest.mark.asyncio
async def test_get_workspace_token_cached(github_client):
    """Test getting workspace token uses cached token if valid."""
    from kurt.db.workspace_models import Workspace

    # Mock workspace with valid token (expires in 1 hour)
    workspace = Workspace(
        id="ws-123",
        name="Test Workspace",
        slug="test",
        github_owner="acme",
        github_repo="docs",
        github_installation_id=12345,
        owner_user_id="user-1",
        github_installation_token="ghs_cached_token",
        github_installation_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    with patch("kurt.db.managed_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = workspace
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session.return_value = mock_session_instance

        with patch("httpx.AsyncClient") as mock_client:
            # Should NOT make HTTP request
            token = await github_client.get_workspace_token("ws-123")

            assert token == "ghs_cached_token"
            mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_get_workspace_token_expired(github_client):
    """Test getting workspace token refreshes if expired."""
    from kurt.db.workspace_models import Workspace

    # Mock workspace with expired token
    workspace = Workspace(
        id="ws-123",
        name="Test Workspace",
        slug="test",
        github_owner="acme",
        github_repo="docs",
        github_installation_id=12345,
        owner_user_id="user-1",
        github_installation_token="ghs_old_token",
        github_installation_token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "token": "ghs_refreshed_token",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    mock_response.raise_for_status = MagicMock()

    with patch("jwt.encode", return_value="mocked_jwt"):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            with patch("kurt.db.managed_session") as mock_session:
                mock_session_instance = MagicMock()
                mock_session_instance.get.return_value = workspace
                mock_session_instance.__enter__.return_value = mock_session_instance
                mock_session.return_value = mock_session_instance

                token = await github_client.get_workspace_token("ws-123")

                assert token == "ghs_refreshed_token"
                # Verify token was refreshed
                assert workspace.github_installation_token == "ghs_refreshed_token"


@pytest.mark.asyncio
async def test_get_workspace_token_no_installation(github_client):
    """Test error if workspace doesn't have GitHub App installed."""
    from kurt.db.workspace_models import Workspace

    workspace = Workspace(
        id="ws-123",
        name="Test Workspace",
        slug="test",
        github_owner="acme",
        github_repo="docs",
        github_installation_id=None,  # Not installed
        owner_user_id="user-1",
    )

    with patch("kurt.db.managed_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = workspace
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session.return_value = mock_session_instance

        with pytest.raises(ValueError, match="GitHub App not installed"):
            await github_client.get_workspace_token("ws-123")


@pytest.mark.asyncio
async def test_list_installation_repositories(github_client):
    """Test listing repositories for an installation."""
    mock_token_response = MagicMock()
    mock_token_response.json.return_value = {
        "token": "ghs_token",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    mock_token_response.raise_for_status = MagicMock()

    mock_repos_response = MagicMock()
    mock_repos_response.json.return_value = {
        "repositories": [
            {"id": 1, "name": "repo1", "full_name": "acme/repo1"},
            {"id": 2, "name": "repo2", "full_name": "acme/repo2"},
        ]
    }
    mock_repos_response.raise_for_status = MagicMock()

    with patch("jwt.encode", return_value="mocked_jwt"):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_token_response
            mock_client_instance.get.return_value = mock_repos_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            repos = await github_client.list_installation_repositories(12345)

            assert len(repos) == 2
            assert repos[0]["name"] == "repo1"
            assert repos[1]["full_name"] == "acme/repo2"
