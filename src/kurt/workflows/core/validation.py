"""
Shared workflow validation utilities.

Contains:
- Cycle detection for dependency graphs (DFS 3-color algorithm)
- Cron expression validation
"""

from __future__ import annotations

from typing import Any, Protocol


class HasDependsOn(Protocol):
    """Protocol for objects that have a depends_on attribute."""

    depends_on: list[str]


def detect_cycle(
    steps: dict[str, HasDependsOn | dict[str, Any]],
) -> list[str] | None:
    """
    Detect cycles in a step dependency graph using DFS 3-color algorithm.

    The algorithm uses three colors:
    - WHITE (0): unvisited node
    - GRAY (1): node in current DFS path (potential back edge target)
    - BLACK (2): fully processed node

    When we encounter a GRAY node while traversing, we've found a back edge
    indicating a cycle.

    Args:
        steps: Dictionary mapping step names to step definitions.
               Each step must have a `depends_on` attribute or key
               containing a list of dependency step names.

    Returns:
        List of step names forming the cycle (including the repeated node),
        or None if no cycle exists.

    Example:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Step:
        ...     depends_on: list[str]
        >>> steps = {
        ...     "a": Step(depends_on=["b"]),
        ...     "b": Step(depends_on=["c"]),
        ...     "c": Step(depends_on=["a"]),  # Creates cycle: a -> b -> c -> a
        ... }
        >>> detect_cycle(steps)
        ['a', 'b', 'c', 'a']
    """
    WHITE, GRAY, BLACK = 0, 1, 2  # noqa: N806 - algorithm state constants
    color: dict[str, int] = {name: WHITE for name in steps}

    def get_depends_on(step: HasDependsOn | dict[str, Any]) -> list[str]:
        """Extract depends_on from step (handles both objects and dicts)."""
        if isinstance(step, dict):
            return step.get("depends_on", [])
        return step.depends_on

    def dfs(node: str, path: list[str]) -> list[str] | None:
        """DFS traversal with cycle detection."""
        color[node] = GRAY
        path.append(node)

        for dep in get_depends_on(steps[node]):
            if dep not in steps:
                # Dependency doesn't exist - handled by parser
                continue

            if color[dep] == GRAY:
                # Found cycle: path from dep to current node + dep
                cycle_start_idx = path.index(dep)
                return path[cycle_start_idx:] + [dep]

            if color[dep] == WHITE:
                result = dfs(dep, path)
                if result is not None:
                    return result

        path.pop()
        color[node] = BLACK
        return None

    # Sort step names for deterministic cycle detection
    for node in sorted(steps.keys()):
        if color[node] == WHITE:
            result = dfs(node, [])
            if result is not None:
                return result

    return None


def validate_cron(cron_expression: str) -> list[str]:
    """
    Validate a cron expression.

    Args:
        cron_expression: The cron expression to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    try:
        from croniter import croniter

        croniter(cron_expression)
    except ImportError:
        # croniter not installed, skip validation
        pass
    except Exception as e:
        errors.append(f"Invalid cron expression: {e}")

    return errors
