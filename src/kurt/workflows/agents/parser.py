"""Parser for workflow definition files (TOML and Markdown with YAML frontmatter)."""

from __future__ import annotations

import sys
from pathlib import Path

# tomllib is Python 3.11+, use tomli backport for earlier versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from typing import Any, Literal, Optional

import frontmatter
from pydantic import BaseModel, Field

from kurt.workflows.core import GuardrailsConfig, ScheduleConfig


class WorkflowConfig(BaseModel):
    """Top-level workflow configuration."""

    name: str  # Unique identifier (kebab-case)
    title: str  # Display name
    description: Optional[str] = None


class AgentConfig(BaseModel):
    """Claude Code agent configuration."""

    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 50
    prompt: Optional[str] = None  # Agent instructions (for TOML format)
    allowed_tools: Optional[list[str]] = Field(
        default_factory=lambda: ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
    )
    permission_mode: Optional[str] = "bypassPermissions"  # auto, bypassPermissions


class StepConfig(BaseModel):
    """DAG step configuration for step-driven workflows."""

    type: Literal["function", "agent", "llm"]
    depends_on: list[str] = Field(default_factory=list)

    # type=function
    function: Optional[str] = None  # Function name in tools.py

    # type=agent
    model: Optional[str] = None
    max_turns: Optional[int] = None
    prompt: Optional[str] = None

    # type=llm
    prompt_template: Optional[str] = None
    output_schema: Optional[str] = None  # Pydantic model name


class ParsedWorkflow(BaseModel):
    """Parsed workflow definition from a TOML or Markdown file."""

    # Core workflow config (flat for backwards compat, structured for TOML)
    name: str
    title: str
    description: Optional[str] = None

    # Workflow config object (for TOML format)
    workflow: Optional[WorkflowConfig] = None

    # Orchestration modes (mutually exclusive in practice)
    schedule: Optional[ScheduleConfig] = None
    agent: Optional[AgentConfig] = None
    steps: dict[str, StepConfig] = Field(default_factory=dict)

    # Common config
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    inputs: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    # Body/prompt content
    body: str = ""  # Markdown instructions (for MD format) or empty for TOML

    # Source file path (for reference)
    source_path: Optional[str] = None

    @property
    def is_agent_driven(self) -> bool:
        """Check if this is an agent-driven workflow."""
        return self.agent is not None and not self.steps

    @property
    def is_steps_driven(self) -> bool:
        """Check if this is a step-driven workflow with DAG steps."""
        return bool(self.steps)

    @property
    def effective_prompt(self) -> str:
        """Get the effective prompt (from agent.prompt for TOML, body for MD)."""
        if self.agent and self.agent.prompt:
            return self.agent.prompt
        return self.body


def detect_file_format(path: Path) -> Literal["toml", "markdown"]:
    """Detect file format based on extension."""
    suffix = path.suffix.lower()
    if suffix == ".toml":
        return "toml"
    elif suffix in (".md", ".markdown"):
        return "markdown"
    else:
        # Try to detect by content
        try:
            content = path.read_text()
            if content.strip().startswith("["):
                return "toml"
            elif content.strip().startswith("---"):
                return "markdown"
        except Exception:
            pass
        # Default to markdown for backwards compatibility
        return "markdown"


def parse_toml_workflow(path: Path) -> ParsedWorkflow:
    """
    Parse a TOML workflow file.

    Args:
        path: Path to the workflow .toml file

    Returns:
        ParsedWorkflow instance

    Raises:
        ValueError: If the file cannot be parsed
    """
    content = path.read_text()
    data = tomllib.loads(content)

    # Extract workflow section (required)
    workflow_data = data.get("workflow", {})
    if not workflow_data:
        raise ValueError("Missing required [workflow] section in TOML file")

    workflow_config = WorkflowConfig(
        name=workflow_data.get("name", path.stem),
        title=workflow_data.get("title", path.stem),
        description=workflow_data.get("description"),
    )

    # Extract agent section (optional)
    agent_data = data.get("agent")
    agent_config = None
    if agent_data:
        agent_config = AgentConfig(**agent_data)

    # Extract steps sections (optional)
    steps: dict[str, StepConfig] = {}
    steps_data = data.get("steps", {})
    for step_name, step_data in steps_data.items():
        steps[step_name] = StepConfig(**step_data)

    # Extract schedule section (optional)
    schedule_data = data.get("schedule")
    schedule_config = None
    if schedule_data:
        schedule_config = ScheduleConfig(**schedule_data)

    # Extract guardrails section (optional)
    guardrails_data = data.get("guardrails", {})
    guardrails_config = GuardrailsConfig(**guardrails_data)

    # Extract inputs and tags
    inputs = data.get("inputs", {})
    tags = data.get("tags", [])

    return ParsedWorkflow(
        name=workflow_config.name,
        title=workflow_config.title,
        description=workflow_config.description,
        workflow=workflow_config,
        agent=agent_config,
        steps=steps,
        schedule=schedule_config,
        guardrails=guardrails_config,
        inputs=inputs,
        tags=tags,
        body="",  # TOML uses agent.prompt instead
        source_path=str(path),
    )


def parse_markdown_workflow(path: Path) -> ParsedWorkflow:
    """
    Parse a Markdown workflow file with YAML frontmatter.

    Args:
        path: Path to the workflow .md file

    Returns:
        ParsedWorkflow instance

    Raises:
        ValueError: If the file cannot be parsed
    """
    post = frontmatter.load(path)
    metadata = dict(post.metadata)

    # Extract and build nested configs
    schedule_data = metadata.pop("schedule", None)
    agent_data = metadata.pop("agent", None)
    guardrails_data = metadata.pop("guardrails", None)

    # Build agent config with body as implicit prompt
    agent_config = None
    if agent_data:
        agent_config = AgentConfig(**agent_data)
    else:
        # For backwards compat, create default agent config
        agent_config = AgentConfig()

    return ParsedWorkflow(
        name=metadata.get("name", path.stem),
        title=metadata.get("title", path.stem),
        description=metadata.get("description"),
        workflow=None,  # Markdown format doesn't use workflow section
        schedule=ScheduleConfig(**schedule_data) if schedule_data else None,
        agent=agent_config,
        steps={},  # Markdown format doesn't support steps
        guardrails=GuardrailsConfig(**guardrails_data) if guardrails_data else GuardrailsConfig(),
        inputs=metadata.get("inputs", {}),
        tags=metadata.get("tags", []),
        body=post.content,
        source_path=str(path),
    )


def parse_workflow(path: Path) -> ParsedWorkflow:
    """
    Parse a workflow file (TOML or Markdown).

    Auto-detects file format based on extension.

    Args:
        path: Path to the workflow file (.toml or .md)

    Returns:
        ParsedWorkflow instance

    Raises:
        ValueError: If the file cannot be parsed
    """
    file_format = detect_file_format(path)

    if file_format == "toml":
        return parse_toml_workflow(path)
    else:
        return parse_markdown_workflow(path)


def validate_workflow(path: Path) -> list[str]:
    """
    Validate a workflow file and return any errors.

    Args:
        path: Path to the workflow file (.toml or .md)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    try:
        parsed = parse_workflow(path)

        if not parsed.name:
            errors.append("Missing required field: name")
        if not parsed.title:
            errors.append("Missing required field: title")

        # For agent-driven workflows, check prompt
        if parsed.is_agent_driven:
            if not parsed.effective_prompt.strip():
                errors.append("Workflow body (prompt) is empty")

        # For step-driven workflows, check steps
        if parsed.is_steps_driven:
            for step_name, step in parsed.steps.items():
                if step.type == "function" and not step.function:
                    errors.append(f"Step '{step_name}': type=function requires 'function' field")
                if step.type == "agent" and not step.prompt:
                    errors.append(f"Step '{step_name}': type=agent requires 'prompt' field")
                if step.type == "llm" and not step.prompt_template:
                    errors.append(f"Step '{step_name}': type=llm requires 'prompt_template' field")

            # Validate DAG (no circular dependencies)
            _validate_dag(parsed.steps, errors)

        # Validate cron expression if schedule is present
        if parsed.schedule and parsed.schedule.cron:
            try:
                from croniter import croniter

                croniter(parsed.schedule.cron)
            except ImportError:
                pass  # croniter not installed, skip validation
            except Exception as e:
                errors.append(f"Invalid cron expression: {e}")

        # Validate agent config
        if parsed.agent:
            if parsed.agent.max_turns < 1:
                errors.append("agent.max_turns must be at least 1")
            if parsed.agent.permission_mode and parsed.agent.permission_mode not in (
                "auto",
                "bypassPermissions",
            ):
                errors.append(f"Invalid permission_mode: {parsed.agent.permission_mode}")

        # Validate guardrails
        if parsed.guardrails.max_tokens < 1000:
            errors.append("guardrails.max_tokens must be at least 1000")
        if parsed.guardrails.max_tool_calls < 1:
            errors.append("guardrails.max_tool_calls must be at least 1")
        if parsed.guardrails.max_time < 60:
            errors.append("guardrails.max_time must be at least 60 seconds")

    except Exception as e:
        errors.append(f"Parse error: {e}")

    return errors


def _validate_dag(steps: dict[str, StepConfig], errors: list[str]) -> None:
    """Validate DAG structure (no cycles, valid dependencies)."""
    # Check all dependencies exist
    step_names = set(steps.keys())
    for step_name, step in steps.items():
        for dep in step.depends_on:
            if dep not in step_names:
                errors.append(f"Step '{step_name}': depends_on '{dep}' does not exist")

    # Check for cycles using topological sort
    try:
        from graphlib import CycleError, TopologicalSorter

        graph = {name: set(step.depends_on) for name, step in steps.items()}
        sorter = TopologicalSorter(graph)
        # This will raise CycleError if there's a cycle
        list(sorter.static_order())
    except CycleError as e:
        errors.append(f"Circular dependency detected: {e}")
    except ImportError:
        pass  # graphlib not available (Python < 3.9), skip cycle detection
