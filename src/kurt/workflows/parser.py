"""YAML workflow parser and loader.

Loads and validates workflow definitions from YAML files.
"""

import re
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import ValidationError

from kurt.workflows.schema import WorkflowDefinition


class WorkflowParseError(Exception):
    """Error parsing workflow YAML."""

    pass


class VariableSubstitutionError(Exception):
    """Error substituting variables in workflow."""

    pass


def load_workflow(file_path: Path | str) -> WorkflowDefinition:
    """
    Load a workflow from a YAML file.

    Args:
        file_path: Path to YAML workflow file

    Returns:
        Parsed and validated WorkflowDefinition

    Raises:
        WorkflowParseError: If file cannot be parsed or validation fails
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise WorkflowParseError(f"Workflow file not found: {file_path}")

    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise WorkflowParseError(f"Invalid YAML syntax: {e}")

    if not isinstance(data, dict):
        raise WorkflowParseError("Workflow file must contain a YAML object")

    try:
        workflow = WorkflowDefinition(**data)
    except ValidationError as e:
        error_msgs = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            error_msgs.append(f"{loc}: {error['msg']}")
        raise WorkflowParseError("Validation errors:\n" + "\n".join(error_msgs))

    # Additional validation
    ref_errors = workflow.validate_step_references()
    if ref_errors:
        raise WorkflowParseError("Reference errors:\n" + "\n".join(ref_errors))

    return workflow


def substitute_variables(value: Any, variables: Dict[str, Any], allow_missing: bool = False) -> Any:
    """
    Substitute variables in a value using ${variable_name} syntax.

    Supports:
    - Simple substitution: ${var_name}
    - Nested access: ${var.field.subfield}
    - List access: ${var[0]}

    Args:
        value: Value to substitute (can be str, dict, list, or primitive)
        variables: Dictionary of available variables
        allow_missing: If True, leave unresolved variables as-is instead of raising error

    Returns:
        Value with variables substituted

    Raises:
        VariableSubstitutionError: If variable not found and allow_missing=False
    """
    if isinstance(value, str):
        # Find all ${...} patterns
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, value)

        if not matches:
            return value

        # If the entire string is a single variable reference, return the actual value
        # (preserves types like int, list, dict)
        if len(matches) == 1 and value == f"${{{matches[0]}}}":
            var_path = matches[0]
            resolved = _resolve_variable_path(var_path, variables, allow_missing)
            if resolved is None and not allow_missing:
                raise VariableSubstitutionError(f"Variable not found: {var_path}")
            return resolved

        # Otherwise, substitute all variables in the string
        result = value
        for var_path in matches:
            resolved = _resolve_variable_path(var_path, variables, allow_missing)
            if resolved is None and not allow_missing:
                raise VariableSubstitutionError(f"Variable not found: {var_path}")
            # Convert to string for substitution
            result = result.replace(
                f"${{{var_path}}}", str(resolved) if resolved is not None else f"${{{var_path}}}"
            )

        return result

    elif isinstance(value, dict):
        return {k: substitute_variables(v, variables, allow_missing) for k, v in value.items()}

    elif isinstance(value, list):
        return [substitute_variables(item, variables, allow_missing) for item in value]

    else:
        # Primitive types (int, float, bool, None) - return as-is
        return value


def _resolve_variable_path(path: str, variables: Dict[str, Any], allow_missing: bool) -> Any:
    """
    Resolve a variable path like 'var.field[0].subfield'.

    Args:
        path: Variable path to resolve
        variables: Available variables
        allow_missing: Whether to return None for missing variables

    Returns:
        Resolved value or None if not found and allow_missing=True
    """
    # Split path by . and [ ] for nested access
    parts = re.split(r"\.|\[|\]", path)
    parts = [p for p in parts if p]  # Remove empty strings

    current = variables
    for part in parts:
        # Check if part is an integer (list index)
        if part.isdigit():
            idx = int(part)
            if isinstance(current, (list, tuple)):
                if idx < len(current):
                    current = current[idx]
                else:
                    if allow_missing:
                        return None
                    raise VariableSubstitutionError(f"Index {idx} out of range in path: {path}")
            else:
                if allow_missing:
                    return None
                raise VariableSubstitutionError(f"Cannot index non-list type in path: {path}")
        else:
            # Dictionary/object attribute access
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                else:
                    if allow_missing:
                        return None
                    raise VariableSubstitutionError(f"Key '{part}' not found in path: {path}")
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                if allow_missing:
                    return None
                raise VariableSubstitutionError(f"Attribute '{part}' not found in path: {path}")

    return current


def validate_workflow_file(file_path: Path | str) -> tuple[bool, str]:
    """
    Validate a workflow file without executing it.

    Args:
        file_path: Path to workflow YAML file

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        workflow = load_workflow(file_path)
        return True, f"Workflow '{workflow.name}' is valid"
    except WorkflowParseError as e:
        return False, f"Validation failed: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"


__all__ = [
    "WorkflowParseError",
    "VariableSubstitutionError",
    "load_workflow",
    "substitute_variables",
    "validate_workflow_file",
]
