"""File-based registry for workflow definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from kurt.config import get_config_or_default

from .parser import ParsedWorkflow, parse_workflow, validate_workflow

# Supported workflow file extensions (in priority order)
WORKFLOW_EXTENSIONS = [".toml", ".md"]


def get_workflows_dir() -> Path:
    """Get the workflows directory from config (default: workflows/)."""
    config = get_config_or_default()
    return config.get_absolute_workflows_path()


def _find_workflow_files(workflows_dir: Path) -> list[Path]:
    """
    Find all workflow definition files.

    Supports two structures:
    - workflows/simple-workflow.toml or .md (flat file)
    - workflows/complex_workflow/workflow.toml or .md (directory with tools)

    Priority: .toml files take precedence over .md files with the same name.

    Returns:
        List of paths to workflow files
    """
    if not workflows_dir.exists():
        return []

    # Track workflows by name to handle priority
    # Key: workflow identifier (stem for flat, dir name for directory)
    # Value: path to file
    workflows: dict[str, Path] = {}

    # Flat files: workflows/*.toml and workflows/*.md
    for ext in WORKFLOW_EXTENSIONS:
        for path in workflows_dir.glob(f"*{ext}"):
            stem = path.stem
            # Only add if not already found (earlier extensions have priority)
            if stem not in workflows:
                workflows[stem] = path

    # Directory structure: workflows/*/workflow.toml and workflows/*/workflow.md
    for ext in WORKFLOW_EXTENSIONS:
        for path in workflows_dir.glob(f"*/workflow{ext}"):
            dir_name = path.parent.name
            # Only add if not already found (earlier extensions have priority)
            if dir_name not in workflows:
                workflows[dir_name] = path

    return sorted(workflows.values())


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

    if dir_path.is_dir():
        # Check for workflow file in priority order
        for ext in WORKFLOW_EXTENSIONS:
            if (dir_path / f"workflow{ext}").exists():
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

    # Try directory structure first: workflows/{name}/workflow.toml or .md
    dir_name = name.replace("-", "_")
    for ext in WORKFLOW_EXTENSIONS:
        dir_path = workflows_dir / dir_name / f"workflow{ext}"
        if dir_path.exists():
            try:
                parsed = parse_workflow(dir_path)
                return parsed
            except Exception:
                pass

    # Try exact filename match: workflows/{name}.toml or .md
    for ext in WORKFLOW_EXTENSIONS:
        exact_path = workflows_dir / f"{name}{ext}"
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


def find_definition_by_workflow_id(workflow_id: str) -> list[dict]:
    """Find page definitions for a workflow by its workflow ID.

    Looks up the definition_name from workflow events, then reads pages from
    the workflow definition file.

    Returns:
        List of page config dicts, or empty list if none found.
    """
    try:
        from kurt.db.utils import get_dolt_db

        db = get_dolt_db(return_none_if_missing=True)
        if not db:
            return []

        # Look up definition name from workflow metadata
        result = db.query(
            "SELECT metadata_json FROM workflow_runs WHERE workflow_id = ? LIMIT 1",
            [workflow_id],
        )
        if not result.rows:
            return []

        import json

        metadata = result.rows[0].get("metadata_json", "{}")
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        definition_name = metadata.get("definition_name")
        if not definition_name:
            return []

        parsed = get_definition(definition_name)
        if not parsed or not parsed.pages:
            return []

        return [page.model_dump() for page in parsed.pages]
    except Exception:
        return []


def get_page_config(workflow_id: str, page_id: str) -> Optional[dict]:
    """Get a specific page config for a workflow.

    Returns:
        Page config dict or None if not found.
    """
    pages = find_definition_by_workflow_id(workflow_id)
    for page in pages:
        if page.get("id") == page_id:
            return page
    return None


def get_definition_for_workflow(workflow_id: str) -> Optional[dict]:
    """Get the workflow definition associated with a workflow ID.

    Returns:
        Workflow definition as dict, or None if not found.
    """
    try:
        from kurt.db.utils import get_dolt_db

        import json

        db = get_dolt_db(return_none_if_missing=True)
        if not db:
            return None

        result = db.query(
            "SELECT metadata_json FROM workflow_runs WHERE workflow_id = ? LIMIT 1",
            [workflow_id],
        )
        if not result.rows:
            return None

        metadata = result.rows[0].get("metadata_json", "{}")
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else {}
        definition_name = metadata.get("definition_name")
        if not definition_name:
            return None

        parsed = get_definition(definition_name)
        if not parsed:
            return None

        return {"name": parsed.name, "title": parsed.title}
    except Exception:
        return None
