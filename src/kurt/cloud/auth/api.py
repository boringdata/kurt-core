"""API helpers for Kurt Cloud authentication."""

from __future__ import annotations

import json
import urllib.request
from typing import Optional

import click

from kurt.cloud.auth.credentials import get_cloud_api_url


def get_user_info(access_token: str) -> dict:
    """Get user info from Kurt Cloud using the access token."""
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/auth/verify"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        raise click.ClickException(f"Failed to get user info: {e}")


def refresh_access_token(refresh_token: str) -> Optional[dict]:
    """Refresh the access token via Kurt Cloud API."""
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/auth/refresh"
    data = json.dumps({"refresh_token": refresh_token}).encode()

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None
