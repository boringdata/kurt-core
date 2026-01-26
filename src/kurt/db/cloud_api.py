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


