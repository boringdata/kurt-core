"""Workflow registry exports for branches without YAML workflow modules."""

from .registry import (
    discover_yaml_workflows,
    ensure_workflows_dir,
    get_agent_workflow,
    get_workflow,
    get_workflow_type,
    get_workflows_dir,
    get_yaml_workflow,
    list_agent_workflows,
    list_all_workflows,
    list_yaml_workflows,
    validate_all_workflows,
)

DBOS_AVAILABLE = False


def get_dbos():
    """Return the DBOS handle when available."""
    raise RuntimeError("DBOS is not available on this branch")

__all__ = [
    "DBOS_AVAILABLE",
    "get_dbos",
    "get_workflows_dir",
    "list_agent_workflows",
    "get_agent_workflow",
    "list_yaml_workflows",
    "get_yaml_workflow",
    "list_all_workflows",
    "get_workflow",
    "get_workflow_type",
    "validate_all_workflows",
    "ensure_workflows_dir",
    "discover_yaml_workflows",
]
