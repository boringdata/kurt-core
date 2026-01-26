"""Tests for cloud API helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kurt.db.cloud_api import KurtCloudAuthError, api_request, get_auth_token


class _DummyCreds:
    def __init__(self, access_token: str | None, expired: bool) -> None:
        self.access_token = access_token
        self._expired = expired

    def is_expired(self) -> bool:
        return self._expired


def test_get_auth_token_uses_refresh(monkeypatch):
    monkeypatch.setattr(
        "kurt.auth.ensure_fresh_token",
        lambda: _DummyCreds("fresh-token", False),
    )

    assert get_auth_token() == "fresh-token"


def test_get_auth_token_raises_when_expired(monkeypatch):
    monkeypatch.setattr(
        "kurt.auth.ensure_fresh_token",
        lambda: _DummyCreds("expired-token", True),
    )

    with pytest.raises(KurtCloudAuthError):
        get_auth_token()


def test_api_request_handles_empty_body(monkeypatch):
    monkeypatch.setattr("kurt.db.cloud_api.get_auth_token", lambda: "token")
    monkeypatch.setattr("kurt.auth.credentials.get_cloud_api_url", lambda: "http://test")

    response = MagicMock()
    response.status_code = 204
    response.content = b""
    response.raise_for_status = MagicMock()

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: response)

    assert api_request("/core/api/status") is None


def test_api_request_handles_non_json(monkeypatch):
    monkeypatch.setattr("kurt.db.cloud_api.get_auth_token", lambda: "token")
    monkeypatch.setattr("kurt.auth.credentials.get_cloud_api_url", lambda: "http://test")

    response = MagicMock()
    response.status_code = 200
    response.content = b"ok"
    response.text = "ok"
    response.raise_for_status = MagicMock()
    response.json.side_effect = ValueError("not json")

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: response)

    assert api_request("/core/api/status") == "ok"


def test_api_request_raises_on_401(monkeypatch):
    monkeypatch.setattr("kurt.db.cloud_api.get_auth_token", lambda: "token")
    monkeypatch.setattr("kurt.auth.credentials.get_cloud_api_url", lambda: "http://test")

    response = MagicMock()
    response.status_code = 401
    response.content = b""
    response.raise_for_status = MagicMock()

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: response)

    with pytest.raises(KurtCloudAuthError):
        api_request("/core/api/status")
