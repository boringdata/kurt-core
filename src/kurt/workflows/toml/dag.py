"""
DAG builder for Kurt workflow engine.

Builds an execution plan from step dependencies using topological sort.
Groups steps into execution levels for parallel execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from kurt.workflows.toml.parser import StepDef


class CycleDetectedError(Exception):
    """Raised when a cycle is detected in the dependency graph."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Cycle detected: {cycle_str}")


@dataclass
class ExecutionPlan:
    """
    Execution plan for a workflow.

    Attributes:
        levels: Steps grouped by execution level. Level 0 has no dependencies,
                level N depends only on steps in levels < N. Steps within a
                level can run in parallel.
        total_steps: Total number of steps in the plan.
        parallelizable: True if any level has more than one step.
        critical_path: Longest dependency chain (step names from start to end).
    """

    levels: list[list[str]] = field(default_factory=list)
    total_steps: int = 0
    parallelizable: bool = False
    critical_path: list[str] = field(default_factory=list)


def _detect_cycle(
    steps: dict[str, StepDef],
) -> list[str] | None:
    """
    Detect cycles in the step dependency graph using DFS.

    Uses three-color algorithm:
    - WHITE (0): not visited
    - GRAY (1): in current DFS path
    - BLACK (2): fully processed

    Returns:
        List of step names forming the cycle (including the repeated node),
        or None if no cycle exists.
    """
    WHITE, GRAY, BLACK = 0, 1, 2  # noqa: N806
    color: dict[str, int] = {name: WHITE for name in steps}

    def dfs(node: str, path: list[str]) -> list[str] | None:
        color[node] = GRAY
        path.append(node)

        for dep in steps[node].depends_on:
            if dep not in steps:
                # Missing dependency - handled by parser
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


def _compute_levels(
    steps: dict[str, StepDef],
) -> list[list[str]]:
    """
    Compute execution levels via topological sort.

    Level 0: steps with no dependencies
    Level N: steps whose all dependencies are in levels < N

    Within each level, steps are sorted by:
    1. Priority (from step config, lower = higher priority, default 100)
    2. Alphabetically by step name

    Returns:
        List of levels, each level is a list of step names.
    """
    if not steps:
        return []

    # Track which level each step is assigned to
    step_level: dict[str, int] = {}

    # Compute level for each step (max dependency level + 1)
    def get_level(name: str) -> int:
        if name in step_level:
            return step_level[name]

        step = steps[name]
        # Filter to only valid dependencies (skip missing deps)
        valid_deps = [dep for dep in step.depends_on if dep in steps]
        if not valid_deps:
            step_level[name] = 0
        else:
            # Level is max of dependency levels + 1
            max_dep_level = max(get_level(dep) for dep in valid_deps)
            step_level[name] = max_dep_level + 1

        return step_level[name]

    # Compute levels for all steps
    for name in steps:
        get_level(name)

    # Group steps by level
    max_level = max(step_level.values()) if step_level else 0
    levels: list[list[str]] = [[] for _ in range(max_level + 1)]

    for name, level in step_level.items():
        levels[level].append(name)

    # Sort within each level: by priority (from config), then alphabetically
    def sort_key(name: str) -> tuple[int, str]:
        priority = steps[name].config.get("priority", 100)
        return (priority, name)

    for level in levels:
        level.sort(key=sort_key)

    return levels


def _compute_critical_path(
    steps: dict[str, StepDef],
    levels: list[list[str]],
) -> list[str]:
    """
    Compute the critical path (longest dependency chain).

    Uses dynamic programming: for each step, the path length is
    max(path lengths of dependencies) + 1.

    When multiple paths have the same length, ties are broken by:
    1. Priority (lower = higher priority)
    2. Alphabetically by step name

    Returns:
        List of step names from start to end of the longest path.
    """
    if not steps or not levels:
        return []

    # path_length[name] = length of longest path ending at this step
    # predecessor[name] = previous step in the longest path
    path_length: dict[str, int] = {}
    predecessor: dict[str, str | None] = {}

    def sort_key(name: str) -> tuple[int, str]:
        priority = steps[name].config.get("priority", 100)
        return (priority, name)

    # Process levels in order (topological order)
    for level in levels:
        for name in level:
            step = steps[name]
            # Filter to only valid dependencies (skip missing deps)
            valid_deps = [dep for dep in step.depends_on if dep in steps]
            if not valid_deps:
                path_length[name] = 1
                predecessor[name] = None
            else:
                # Find the dependency with the longest path
                # Tie-break: prefer lower priority (higher precedence), then alphabetically earlier
                def dep_key(d: str) -> tuple[int, int, str]:
                    return (path_length[d], -sort_key(d)[0], sort_key(d)[1])

                # Use min on inverted sort key for alphabetical tie-break
                # Actually: max on path_length, min on (priority, name) for tie-break
                best_dep = None
                best_score = (-1, float("inf"), "")  # (length, priority, name)
                for dep in valid_deps:
                    prio, nm = sort_key(dep)
                    score = (path_length[dep], -prio, nm)
                    # Prefer: longer path, lower priority, alphabetically earlier
                    if (score[0] > best_score[0] or  # longer path
                        (score[0] == best_score[0] and score[1] > best_score[1]) or  # lower priority (higher -prio)
                        (score[0] == best_score[0] and score[1] == best_score[1] and score[2] < best_score[2])):  # alpha
                        best_score = score
                        best_dep = dep

                path_length[name] = path_length[best_dep] + 1
                predecessor[name] = best_dep

    # Find the step with the longest path
    # Tie-break: prefer lower priority, then alphabetically earlier
    end_step = None
    best_score = (-1, float("inf"), "")
    for name in steps:
        prio, nm = sort_key(name)
        score = (path_length[name], -prio, nm)
        if (score[0] > best_score[0] or
            (score[0] == best_score[0] and score[1] > best_score[1]) or
            (score[0] == best_score[0] and score[1] == best_score[1] and score[2] < best_score[2])):
            best_score = score
            end_step = name

    # Reconstruct path from end to start
    path: list[str] = []
    current: str | None = end_step
    while current is not None:
        path.append(current)
        current = predecessor[current]

    path.reverse()
    return path


def build_dag(steps: dict[str, StepDef]) -> ExecutionPlan:
    """
    Build an execution plan from step definitions.

    Performs topological sort to group steps into execution levels.
    Steps within a level can run in parallel.

    Args:
        steps: Dictionary mapping step names to StepDef objects.

    Returns:
        ExecutionPlan with levels, total_steps, parallelizable, and critical_path.

    Raises:
        CycleDetectedError: If circular dependencies are detected.
            The error message includes the cycle path.

    Example:
        >>> steps = {
        ...     "a": StepDef(type="map"),
        ...     "b": StepDef(type="fetch", depends_on=["a"]),
        ...     "c": StepDef(type="llm", depends_on=["a"]),
        ...     "d": StepDef(type="write", depends_on=["b", "c"]),
        ... }
        >>> plan = build_dag(steps)
        >>> plan.levels
        [['a'], ['b', 'c'], ['d']]
        >>> plan.parallelizable
        True
        >>> plan.critical_path
        ['a', 'b', 'd']  # or ['a', 'c', 'd'] depending on tie-break
    """
    if not steps:
        return ExecutionPlan(
            levels=[],
            total_steps=0,
            parallelizable=False,
            critical_path=[],
        )

    # Detect cycles first
    cycle = _detect_cycle(steps)
    if cycle is not None:
        raise CycleDetectedError(cycle)

    # Compute execution levels
    levels = _compute_levels(steps)

    # Compute critical path
    critical_path = _compute_critical_path(steps, levels)

    # Check if parallelizable
    parallelizable = any(len(level) > 1 for level in levels)

    return ExecutionPlan(
        levels=levels,
        total_steps=len(steps),
        parallelizable=parallelizable,
        critical_path=critical_path,
    )
