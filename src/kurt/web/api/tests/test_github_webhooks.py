"""Tests for GitHub webhook handlers."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from kurt.web.api.server import app

    return TestClient(app)


@pytest.fixture
def installation_created_payload():
    """Sample GitHub installation.created webhook payload."""
    return {
        "action": "created",
        "installation": {
            "id": 12345,
            "account": {"login": "acme-corp"},
        },
        "repositories": [
            {"name": "documentation"},
            {"name": "website"},
        ],
    }


@pytest.fixture
def installation_deleted_payload():
    """Sample GitHub installation.deleted webhook payload."""
    return {
        "action": "deleted",
        "installation": {
            "id": 12345,
            "account": {"login": "acme-corp"},
        },
    }


def test_ping_webhook(client):
    """Test ping webhook returns pong."""
    response = client.post(
        "/api/webhooks/github",
        json={},
        headers={"X-GitHub-Event": "ping"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pong"


def test_installation_created(client, installation_created_payload):
    """Test installation.created webhook links installation to workspace."""
    from kurt.db.workspace_models import Workspace

    # Mock existing workspace matching the repo
    workspace = Workspace(
        id="ws-123",
        name="Acme Docs",
        slug="acme-docs",
        github_owner="acme-corp",
        github_repo="documentation",
        github_installation_id=None,  # Not yet installed
        owner_user_id="user-1",
    )

    with patch("kurt.web.api.github_webhooks.managed_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.first.return_value = workspace
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session.return_value = mock_session_instance

        response = client.post(
            "/api/webhooks/github",
            json=installation_created_payload,
            headers={"X-GitHub-Event": "installation"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "installation_linked"
        assert data["installation_id"] == 12345

        # Verify workspace was updated
        assert workspace.github_installation_id == 12345


def test_installation_created_no_matching_workspace(client, installation_created_payload):
    """Test installation.created with no matching workspace."""
    with patch("kurt.web.api.github_webhooks.managed_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.first.return_value = None  # No match
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session.return_value = mock_session_instance

        response = client.post(
            "/api/webhooks/github",
            json=installation_created_payload,
            headers={"X-GitHub-Event": "installation"},
        )

        assert response.status_code == 200
        # Installation tracked but not linked to any workspace


def test_installation_deleted(client, installation_deleted_payload):
    """Test installation.deleted webhook unlinks installation."""
    from kurt.db.workspace_models import Workspace

    # Mock workspace with installation
    workspace = Workspace(
        id="ws-123",
        name="Acme Docs",
        slug="acme-docs",
        github_owner="acme-corp",
        github_repo="documentation",
        github_installation_id=12345,
        github_installation_token="old_token",
        owner_user_id="user-1",
    )

    with patch("kurt.web.api.github_webhooks.managed_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.all.return_value = [workspace]
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session.return_value = mock_session_instance

        response = client.post(
            "/api/webhooks/github",
            json=installation_deleted_payload,
            headers={"X-GitHub-Event": "installation"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "installation_unlinked"

        # Verify workspace was cleared
        assert workspace.github_installation_id is None
        assert workspace.github_installation_token is None


def test_installation_repositories_added(client):
    """Test installation_repositories.added event."""
    from kurt.db.workspace_models import Workspace

    payload = {
        "action": "added",
        "installation": {
            "id": 12345,
            "account": {"login": "acme-corp"},
        },
        "repositories_added": [
            {"name": "new-repo"},
        ],
        "repositories_removed": [],
    }

    workspace = Workspace(
        id="ws-new",
        name="New Repo Workspace",
        slug="new-repo",
        github_owner="acme-corp",
        github_repo="new-repo",
        github_installation_id=None,
        owner_user_id="user-1",
    )

    with patch("kurt.web.api.github_webhooks.managed_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.first.return_value = workspace
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session.return_value = mock_session_instance

        response = client.post(
            "/api/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "installation_repositories"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "repositories_added"
        assert data["count"] == 1

        # Verify installation was linked
        assert workspace.github_installation_id == 12345


def test_installation_repositories_removed(client):
    """Test installation_repositories.removed event."""
    from kurt.db.workspace_models import Workspace

    payload = {
        "action": "removed",
        "installation": {
            "id": 12345,
            "account": {"login": "acme-corp"},
        },
        "repositories_added": [],
        "repositories_removed": [
            {"name": "old-repo"},
        ],
    }

    workspace = Workspace(
        id="ws-old",
        name="Old Repo",
        slug="old-repo",
        github_owner="acme-corp",
        github_repo="old-repo",
        github_installation_id=12345,
        owner_user_id="user-1",
    )

    with patch("kurt.web.api.github_webhooks.managed_session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.exec.return_value.first.return_value = workspace
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session.return_value = mock_session_instance

        response = client.post(
            "/api/webhooks/github",
            json=payload,
            headers={"X-GitHub-Event": "installation_repositories"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "repositories_removed"
        assert data["count"] == 1

        # Verify installation was unlinked
        assert workspace.github_installation_id is None


def test_unknown_event_ignored(client):
    """Test unknown webhook events are ignored."""
    response = client.post(
        "/api/webhooks/github",
        json={"action": "something"},
        headers={"X-GitHub-Event": "unknown_event"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"
    assert data["event"] == "unknown_event"


def test_webhook_signature_verification():
    """Test webhook signature verification logic."""
    from kurt.web.api.github_webhooks import verify_webhook_signature

    payload = b'{"test": "data"}'
    secret = "my_webhook_secret"

    import hashlib
    import hmac

    # Generate valid signature
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    # Test valid signature
    assert verify_webhook_signature(payload, expected, secret) is True

    # Test invalid signature
    assert verify_webhook_signature(payload, "sha256=wrong", secret) is False

    # Test missing signature
    assert verify_webhook_signature(payload, "", secret) is False
    assert verify_webhook_signature(payload, None, secret) is False
