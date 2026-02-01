"""
Shared workflow error classes.

These errors are used across workflow parsing and validation.
"""


class WorkflowParseError(Exception):
    """Base exception for workflow parsing errors."""

    pass


class CircularDependencyError(WorkflowParseError):
    """Raised when circular dependencies are detected in a workflow graph."""

    def __init__(self, cycle: list[str]):
        """
        Initialize with the cycle path.

        Args:
            cycle: List of step names forming the cycle, including the
                   repeated node at the end (e.g., ["a", "b", "c", "a"]).
        """
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")
