"""Cloud mode API client helpers.

Shared utilities for making authenticated requests to kurt-cloud API.
"""

from __future__ import annotations


class KurtCloudAuthError(Exception):
    """Raised when Kurt Cloud authentication fails or is missing."""

    pass


def get_api_base_url() -> str:
    """Get Kurt Cloud API base URL.

    Returns:
        str: API base URL (e.g., "https://kurt-cloud.vercel.app")

    Raises:
        KurtCloudAuthError: If not logged in or invalid configuration
    """
    from kurt.cli.auth.credentials import get_cloud_api_url

    return get_cloud_api_url()


def get_auth_token() -> str:
    """Get Kurt Cloud authentication token.

    Returns:
        str: JWT access token for API requests

    Raises:
        KurtCloudAuthError: If not logged in or token expired
    """
    from kurt.cli.auth.credentials import load_credentials

    creds = load_credentials()
    if not creds or not creds.access_token:
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

    api_base = get_api_base_url()
    token = get_auth_token()

    response = requests.get(
        f"{api_base}{endpoint}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
