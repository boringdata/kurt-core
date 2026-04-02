"""Compatibility workflow registry for branches without YAML workflow support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agents import registry as agent_registry
from .agents.parser import ParsedWorkflow


@dataclass
class WorkflowDefinition:
    """Unified workflow definition shape expected by CLI callers."""

    name: str
    title: str
    workflow_type: str
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    inputs: dict[str, Any] = field(default_factory=dict)
    source_path: str | None = None
    schedule_cron: str | None = None
    schedule_enabled: bool = True
    step_count: int | None = None
    agent: Any = None
    guardrails: Any = None


def _adapt_agent_workflow(definition: ParsedWorkflow) -> WorkflowDefinition:
    schedule = definition.schedule
    return WorkflowDefinition(
        name=definition.name,
        title=definition.title,
        workflow_type="agent",
        description=definition.description,
        tags=list(definition.tags),
        inputs=dict(definition.inputs),
        source_path=definition.source_path,
        schedule_cron=schedule.cron if schedule else None,
        schedule_enabled=schedule.enabled if schedule else True,
        step_count=None,
        agent=definition.agent,
        guardrails=definition.guardrails,
    )


def get_workflows_dir():
    """Return the configured workflows directory."""
    return agent_registry.get_workflows_dir()


def ensure_workflows_dir():
    """Ensure the workflows directory exists."""
    return agent_registry.ensure_workflows_dir()


def list_agent_workflows() -> list[WorkflowDefinition]:
    """List agent workflow definitions."""
    return [_adapt_agent_workflow(definition) for definition in agent_registry.list_definitions()]


def get_agent_workflow(name: str) -> WorkflowDefinition | None:
    """Get an agent workflow definition by name."""
    definition = agent_registry.get_definition(name)
    if definition is None:
        return None
    return _adapt_agent_workflow(definition)


def list_yaml_workflows() -> list[WorkflowDefinition]:
    """YAML workflows are not available on this branch."""
    return []


def get_yaml_workflow(name: str) -> WorkflowDefinition | None:
    """YAML workflows are not available on this branch."""
    return None


def list_all_workflows() -> list[WorkflowDefinition]:
    """List all known workflow definitions."""
    return list_agent_workflows()


def get_workflow(name: str) -> WorkflowDefinition | None:
    """Get any workflow definition by name."""
    return get_agent_workflow(name)


def get_workflow_type(name: str) -> str | None:
    """Return the workflow type for a definition."""
    return "agent" if get_agent_workflow(name) else None


def validate_all_workflows() -> dict[str, list[dict[str, Any]]]:
    """Return CLI-friendly validation output."""
    result = agent_registry.validate_all()
    return {
        "valid": [{"name": name, "type": "agent"} for name in result["valid"]],
        "errors": [
            {"file": error["file"], "type": "agent", "errors": error["errors"]}
            for error in result["errors"]
        ],
    }


def discover_yaml_workflows() -> list[Any]:
    """Keep startup hooks working on branches without YAML workflow tables."""
    return []
