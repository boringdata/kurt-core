"""Parser for workflow definition Markdown files with YAML frontmatter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import frontmatter
from pydantic import BaseModel, Field


class ScheduleConfig(BaseModel):
    """Cron schedule configuration."""

    cron: str
    timezone: str = "UTC"
    enabled: bool = True


class AgentConfig(BaseModel):
    """Claude Code agent configuration."""

    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 50
    allowed_tools: list[str] = Field(
        default_factory=lambda: ["Bash", "Read", "Write", "Edit", "Glob", "Grep"]
    )
    permission_mode: str = "bypassPermissions"  # auto, bypassPermissions


class GuardrailsConfig(BaseModel):
    """Safety guardrails configuration."""

    max_tokens: int = 500000  # Max total tokens (in + out) per run
    max_tool_calls: int = 200  # Max tool invocations per run
    max_time: int = 3600  # Max execution time in seconds


class ParsedWorkflow(BaseModel):
    """Parsed workflow definition from a Markdown file."""

    name: str
    title: str
    description: Optional[str] = None
    schedule: Optional[ScheduleConfig] = None
    agent: AgentConfig = Field(default_factory=AgentConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    inputs: dict[str, Any] = Field(default_factory=dict)  # Simple key/value inputs
    tags: list[str] = Field(default_factory=list)
    body: str  # Markdown instructions (the prompt)

    # Source file path (for reference)
    source_path: Optional[str] = None


def parse_workflow(path: Path) -> ParsedWorkflow:
    """
    Parse a workflow markdown file.

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

    return ParsedWorkflow(
        name=metadata.get("name", path.stem),
        title=metadata.get("title", path.stem),
        description=metadata.get("description"),
        schedule=ScheduleConfig(**schedule_data) if schedule_data else None,
        agent=AgentConfig(**agent_data) if agent_data else AgentConfig(),
        guardrails=GuardrailsConfig(**guardrails_data) if guardrails_data else GuardrailsConfig(),
        inputs=metadata.get("inputs", {}),
        tags=metadata.get("tags", []),
        body=post.content,
        source_path=str(path),
    )


def validate_workflow(path: Path) -> list[str]:
    """
    Validate a workflow file and return any errors.

    Args:
        path: Path to the workflow .md file

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
        if not parsed.body.strip():
            errors.append("Workflow body (prompt) is empty")

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
        if parsed.agent.max_turns < 1:
            errors.append("agent.max_turns must be at least 1")
        if parsed.agent.permission_mode not in ("auto", "bypassPermissions"):
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
