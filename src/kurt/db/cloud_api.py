"""Cloud mode API client helpers.

Shared utilities for making authenticated requests to kurt-cloud API.
"""

from __future__ import annotations


class KurtCloudAuthError(Exception):
    """Raised when Kurt Cloud authentication fails or is missing."""

    pass


def get_auth_token() -> str:
    """Get Kurt Cloud authentication token.

    Returns:
        str: JWT access token for API requests

    Raises:
        KurtCloudAuthError: If not logged in or token expired
    """
    from kurt.cloud.auth import ensure_fresh_token

    creds = ensure_fresh_token()
    if not creds or not creds.access_token or creds.is_expired():
        raise KurtCloudAuthError("Kurt Cloud session expired. Run 'kurt cloud login' to refresh.")

    return creds.access_token


def api_request(endpoint: str, params: dict | None = None):
    """Make authenticated GET request to kurt-cloud API.

    Args:
        endpoint: API endpoint path (e.g., "/api/status")
        params: Optional query parameters

    Returns:
        Parsed JSON response

    Raises:
        requests.exceptions.HTTPError: On HTTP errors
        KurtCloudAuthError: If credentials are missing/expired
    """
    import requests

    from kurt.cloud.auth import get_cloud_api_url

    api_base = get_cloud_api_url()
    token = get_auth_token()

    response = requests.get(
        f"{api_base}{endpoint}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code == 401:
        raise KurtCloudAuthError("Kurt Cloud session expired. Run 'kurt cloud login' to refresh.")
    response.raise_for_status()
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text
