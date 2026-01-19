"""Generic routing utility for database mode-aware operations.

Provides helpers to route operations to local (SQLite/PostgreSQL) or cloud (Kurt Cloud API)
implementations based on the current database mode.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

T = TypeVar("T")


def route_by_mode(
    local_fn: Callable[..., T],
    cloud_fn: Callable[..., T],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Route function call to local or cloud implementation based on current mode.

    Args:
        local_fn: Function to call for sqlite/postgres modes
        cloud_fn: Function to call for kurt-cloud mode
        *args: Positional arguments passed to selected function
        **kwargs: Keyword arguments passed to selected function

    Returns:
        Result from the selected function

    Examples:
        # Simple routing
        def get_from_db(filters):
            ...

        def get_from_api(filters):
            ...

        result = route_by_mode(get_from_db, get_from_api, filters)

        # With keyword arguments
        result = route_by_mode(
            local_fn=query_local,
            cloud_fn=query_api,
            filters=filters,
            limit=100
        )
    """
    from kurt.db.tenant import is_cloud_mode

    if is_cloud_mode():
        return cloud_fn(*args, **kwargs)
    else:
        return local_fn(*args, **kwargs)
