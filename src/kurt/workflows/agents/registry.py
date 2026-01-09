"""File-based registry for workflow definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from kurt.config import get_config_or_default

from .parser import ParsedWorkflow, parse_workflow, validate_workflow


def get_workflows_dir() -> Path:
    """Get the workflows directory from config (default: workflows/)."""
    config = get_config_or_default()
    return config.get_absolute_workflows_path()


def list_definitions() -> list[ParsedWorkflow]:
    """
    List all workflow definitions from .kurt/workflows/.

    Returns:
        List of parsed workflow definitions
    """
    workflows_dir = get_workflows_dir()
    if not workflows_dir.exists():
        return []

    definitions = []
    for path in sorted(workflows_dir.glob("*.md")):
        try:
            parsed = parse_workflow(path)
            definitions.append(parsed)
        except Exception:
            continue  # Skip invalid files in listing

    return definitions


def get_definition(name: str) -> Optional[ParsedWorkflow]:
    """
    Get a workflow definition by name.

    Args:
        name: Workflow name (from frontmatter) or filename without extension

    Returns:
        ParsedWorkflow or None if not found
    """
    workflows_dir = get_workflows_dir()
    if not workflows_dir.exists():
        return None

    # Try exact filename match first
    exact_path = workflows_dir / f"{name}.md"
    if exact_path.exists():
        try:
            parsed = parse_workflow(exact_path)
            if parsed.name == name:
                return parsed
        except Exception:
            pass

    # Otherwise scan all files for matching name
    for path in workflows_dir.glob("*.md"):
        try:
            parsed = parse_workflow(path)
            if parsed.name == name:
                return parsed
        except Exception:
            continue

    return None


def validate_all() -> dict:
    """
    Validate all workflow definitions.

    Returns:
        dict with {"valid": [...], "errors": [...]}
    """
    workflows_dir = get_workflows_dir()
    if not workflows_dir.exists():
        return {"valid": [], "errors": []}

    result = {"valid": [], "errors": []}

    for path in workflows_dir.glob("*.md"):
        errors = validate_workflow(path)
        if errors:
            result["errors"].append({"file": str(path.name), "errors": errors})
        else:
            parsed = parse_workflow(path)
            result["valid"].append(parsed.name)

    return result


def ensure_workflows_dir() -> Path:
    """Ensure the workflows directory exists and return its path."""
    workflows_dir = get_workflows_dir()
    workflows_dir.mkdir(parents=True, exist_ok=True)
    return workflows_dir
