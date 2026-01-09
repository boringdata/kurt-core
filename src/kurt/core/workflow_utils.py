"""Workflow utilities and decorators."""

from __future__ import annotations

import functools
import os
from typing import Any, Callable, TypeVar

from dbos import DBOS

F = TypeVar("F", bound=Callable[..., Any])


def store_parent_workflow_id() -> None:
    """
    Store parent workflow ID from environment if available.

    Must be called from INSIDE a @DBOS.workflow() decorated function.
    """
    parent_id = os.environ.get("KURT_PARENT_WORKFLOW_ID")
    if parent_id:
        try:
            DBOS.set_event("parent_workflow_id", parent_id)
        except Exception:
            pass


def with_parent_workflow_id(func: F) -> F:
    """
    Decorator that stores parent_workflow_id at workflow start.

    Use this decorator AFTER @DBOS.workflow() to automatically
    link child workflows to their parent:

        @DBOS.workflow()
        @with_parent_workflow_id
        def my_workflow(config_dict: dict) -> dict:
            ...

    When an agent runs `kurt` commands, the parent workflow ID is
    passed via KURT_PARENT_WORKFLOW_ID environment variable. This
    decorator reads that variable and stores it as a DBOS event,
    enabling nested workflow display in the UI.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        store_parent_workflow_id()
        return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
