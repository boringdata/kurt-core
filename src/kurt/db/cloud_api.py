"""Cloud mode API client helpers.

Shared utilities for making authenticated requests to kurt-cloud API.
"""

from __future__ import annotations


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

    from kurt.db.cloud import get_api_base_url, get_auth_token

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
