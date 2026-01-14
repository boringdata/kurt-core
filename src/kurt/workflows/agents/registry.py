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


def _find_workflow_files(workflows_dir: Path) -> list[Path]:
    """
    Find all workflow definition files.

    Supports two structures:
    - workflows/simple-workflow.md (flat file)
    - workflows/complex_workflow/workflow.md (directory with tools)

    Returns:
        List of paths to workflow.md files
    """
    if not workflows_dir.exists():
        return []

    paths = []

    # Flat files: workflows/*.md
    for path in workflows_dir.glob("*.md"):
        paths.append(path)

    # Directory structure: workflows/*/workflow.md
    for path in workflows_dir.glob("*/workflow.md"):
        paths.append(path)

    return sorted(set(paths))


def get_workflow_dir(name: str) -> Optional[Path]:
    """
    Get the directory for a workflow (if it uses directory structure).

    Args:
        name: Workflow name

    Returns:
        Path to workflow directory or None if flat file
    """
    workflows_dir = get_workflows_dir()

    # Check for directory structure
    # Convert kebab-case to snake_case for directory lookup
    dir_name = name.replace("-", "_")
    dir_path = workflows_dir / dir_name
    if dir_path.is_dir() and (dir_path / "workflow.md").exists():
        return dir_path

    return None


def has_tools(name: str) -> bool:
    """Check if a workflow has a tools.py file."""
    workflow_dir = get_workflow_dir(name)
    if workflow_dir:
        return (workflow_dir / "tools.py").exists()
    return False


def has_schema(name: str) -> bool:
    """Check if a workflow has a schema.yaml file."""
    workflow_dir = get_workflow_dir(name)
    if workflow_dir:
        return (workflow_dir / "schema.yaml").exists()
    return False


def list_definitions() -> list[ParsedWorkflow]:
    """
    List all workflow definitions from workflows/.

    Returns:
        List of parsed workflow definitions
    """
    workflows_dir = get_workflows_dir()
    paths = _find_workflow_files(workflows_dir)

    definitions = []
    for path in paths:
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

    # Try directory structure first: workflows/{name}/workflow.md
    dir_name = name.replace("-", "_")
    dir_path = workflows_dir / dir_name / "workflow.md"
    if dir_path.exists():
        try:
            parsed = parse_workflow(dir_path)
            return parsed
        except Exception:
            pass

    # Try exact filename match: workflows/{name}.md
    exact_path = workflows_dir / f"{name}.md"
    if exact_path.exists():
        try:
            parsed = parse_workflow(exact_path)
            if parsed.name == name:
                return parsed
        except Exception:
            pass

    # Otherwise scan all files for matching name
    for path in _find_workflow_files(workflows_dir):
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

    for path in _find_workflow_files(workflows_dir):
        errors = validate_workflow(path)
        # Show relative path from workflows dir
        rel_path = path.relative_to(workflows_dir)
        if errors:
            result["errors"].append({"file": str(rel_path), "errors": errors})
        else:
            parsed = parse_workflow(path)
            result["valid"].append(parsed.name)

    return result


def ensure_workflows_dir() -> Path:
    """Ensure the workflows directory exists and return its path."""
    workflows_dir = get_workflows_dir()
    workflows_dir.mkdir(parents=True, exist_ok=True)
    return workflows_dir
