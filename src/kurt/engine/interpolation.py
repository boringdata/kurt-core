"""
Input interpolation engine for Kurt workflows.

Replaces {{var}} placeholders in step config values with workflow inputs.
Supports type coercion from string inputs to target types (int, float, bool).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

# Pattern to match {{var}} and {{var:type}} placeholders
# Matches: {{name}}, {{ name }}, {{name:int}}, {{name:float}}, {{name:bool}}, {{name:str}}
# Does NOT match: \{{escaped}}
_VAR_PATTERN = re.compile(r"(?<!\\)\{\{\s*(\w+)(?::(\w+))?\s*\}\}")

# Type coercion map
_TYPE_MAP = {
    "int": int,
    "float": float,
    "bool": bool,
    "str": str,
}

# Pattern to match escaped braces \{{ or \}}
_ESCAPE_PATTERN = re.compile(r"\\(\{\{|\}\})")


@dataclass
class InterpolationError(Exception):
    """
    Error during config interpolation.

    Attributes:
        type: Error category (missing_input, unknown_var, type_coercion, escape_error)
        var: Variable name that caused the error
        step: Step name where error occurred
        field: Config field path (e.g., "config.model" or "config.options.temperature")
        message: Human-readable error message
        expected_type: Expected type for type_coercion errors
    """

    type: Literal["missing_input", "unknown_var", "type_coercion", "escape_error"]
    var: str
    step: str
    field: str
    message: str
    expected_type: str | None = None

    def __str__(self) -> str:
        return self.message


def _coerce_value(
    value: Any,
    target_type: type | None,
    var_name: str,
    step_name: str,
    field_path: str,
) -> Any:
    """
    Coerce a value to the target type.

    Args:
        value: Input value to coerce
        target_type: Target Python type (int, float, bool, str, or None)
        var_name: Variable name (for error messages)
        step_name: Step name (for error messages)
        field_path: Config field path (for error messages)

    Returns:
        Coerced value

    Raises:
        InterpolationError: If coercion fails
    """
    if target_type is None:
        return value

    # Already correct type
    if isinstance(value, target_type):
        return value

    # If target is str, always convert
    if target_type is str:
        return str(value)

    # If value is not a string, we can't coerce
    if not isinstance(value, str):
        # For int/float, try numeric conversion
        if target_type is int and isinstance(value, float):
            if value == int(value):
                return int(value)
            raise InterpolationError(
                type="type_coercion",
                var=var_name,
                step=step_name,
                field=field_path,
                message=f"Cannot convert {value!r} to int for {var_name}",
                expected_type="int",
            )
        if target_type is float and isinstance(value, (int, float)):
            return float(value)
        # Already correct type after basic checks
        return value

    # String to target type coercion
    try:
        if target_type is int:
            return int(value)
        elif target_type is float:
            return float(value)
        elif target_type is bool:
            lower = value.lower().strip()
            if lower in ("true", "1", "yes"):
                return True
            elif lower in ("false", "0", "no"):
                return False
            else:
                raise ValueError(f"Invalid boolean value: {value}")
    except (ValueError, AttributeError) as e:
        raise InterpolationError(
            type="type_coercion",
            var=var_name,
            step=step_name,
            field=field_path,
            message=f"Cannot convert {value!r} to {target_type.__name__} for {var_name}",
            expected_type=target_type.__name__,
        ) from e

    return value


def _unescape_braces(text: str) -> str:
    """
    Replace escaped braces with literal braces.

    \{{ -> {{
    \}} -> }}
    """
    return _ESCAPE_PATTERN.sub(r"\1", text)


def _interpolate_string(
    text: str,
    inputs: dict[str, Any],
    valid_vars: set[str],
    step_name: str,
    field_path: str,
    target_type: type | None = None,
) -> Any:
    """
    Interpolate a single string value.

    If the entire string is a single {{var}} placeholder, return the
    typed input value. Otherwise, return a string with substitutions.

    Args:
        text: String to interpolate
        inputs: Input values
        valid_vars: Set of valid variable names (from workflow inputs)
        step_name: Step name (for error messages)
        field_path: Config field path (for error messages)
        target_type: Target type for the field (for type coercion)

    Returns:
        Interpolated value (may be any type if whole string is a placeholder)

    Raises:
        InterpolationError: On missing or unknown variables
    """
    # Find all variable references
    matches = list(_VAR_PATTERN.finditer(text))

    if not matches:
        # No variables, just unescape
        return _unescape_braces(text)

    # Check if entire string is a single variable reference
    if len(matches) == 1:
        match = matches[0]
        var_name = match.group(1)
        type_hint = match.group(2)  # Optional type hint (e.g., "int")

        # Check for unknown variable
        if var_name not in valid_vars:
            raise InterpolationError(
                type="unknown_var",
                var=var_name,
                step=step_name,
                field=field_path,
                message=f"Unknown variable {{{{{var_name}}}}} in step {step_name}",
            )

        # Check for missing input
        if var_name not in inputs:
            raise InterpolationError(
                type="missing_input",
                var=var_name,
                step=step_name,
                field=field_path,
                message=f"Required input {var_name} not provided",
            )

        # Check if the placeholder spans the entire string (after stripping)
        prefix = text[: match.start()]
        suffix = text[match.end() :]

        # If entire string is just the placeholder (ignoring whitespace)
        if not prefix.strip() and not suffix.strip():
            value = inputs[var_name]
            # Determine target type: explicit hint takes precedence over field type
            coerce_type = target_type
            if type_hint and type_hint in _TYPE_MAP:
                coerce_type = _TYPE_MAP[type_hint]
            # Coerce to target type if specified
            return _coerce_value(value, coerce_type, var_name, step_name, field_path)

    # Multiple variables or partial string - always return string
    result = text
    for match in reversed(matches):  # Reverse to preserve indices
        var_name = match.group(1)

        # Check for unknown variable
        if var_name not in valid_vars:
            raise InterpolationError(
                type="unknown_var",
                var=var_name,
                step=step_name,
                field=field_path,
                message=f"Unknown variable {{{{{var_name}}}}} in step {step_name}",
            )

        # Check for missing input
        if var_name not in inputs:
            raise InterpolationError(
                type="missing_input",
                var=var_name,
                step=step_name,
                field=field_path,
                message=f"Required input {var_name} not provided",
            )

        value = str(inputs[var_name])
        result = result[: match.start()] + value + result[match.end() :]

    # Unescape remaining escaped braces
    result = _unescape_braces(result)

    # Try to coerce the final string to target type
    if target_type is not None and target_type is not str:
        return _coerce_value(result, target_type, "interpolated", step_name, field_path)

    return result


def _interpolate_value(
    value: Any,
    inputs: dict[str, Any],
    valid_vars: set[str],
    step_name: str,
    field_path: str,
    target_type: type | None = None,
) -> Any:
    """
    Recursively interpolate a value.

    Handles strings, dicts, lists, and passes through other types.
    """
    if isinstance(value, str):
        return _interpolate_string(
            value, inputs, valid_vars, step_name, field_path, target_type
        )
    elif isinstance(value, dict):
        return {
            k: _interpolate_value(
                v, inputs, valid_vars, step_name, f"{field_path}.{k}"
            )
            for k, v in value.items()
        }
    elif isinstance(value, list):
        return [
            _interpolate_value(
                item, inputs, valid_vars, step_name, f"{field_path}[{i}]"
            )
            for i, item in enumerate(value)
        ]
    else:
        # Pass through unchanged (int, float, bool, None, etc.)
        return value


def interpolate_config(
    config: dict[str, Any],
    inputs: dict[str, Any],
    *,
    valid_vars: set[str] | None = None,
    step_name: str = "unknown",
    type_hints: dict[str, type] | None = None,
) -> dict[str, Any]:
    """
    Interpolate a step config dict with input values.

    Replaces {{var}} placeholders in config values with corresponding
    input values. Supports:
    - String substitution: "Hello {{name}}" -> "Hello World"
    - Full value replacement: "{{count}}" -> 42 (preserves type)
    - Nested dicts/lists: Recursively interpolates
    - Type coercion: String "42" -> int 42 (with type_hints)
    - Escape syntax: "\\{{literal}}" -> "{{literal}}"

    Args:
        config: Step config dictionary to interpolate
        inputs: Input values to substitute
        valid_vars: Set of valid variable names. If None, uses keys from inputs.
                   Used for typo detection - errors on unknown {{var}}.
        step_name: Step name for error messages
        type_hints: Optional dict mapping field names to target types
                   for type coercion (e.g., {"batch_size": int})

    Returns:
        New dict with interpolated values

    Raises:
        InterpolationError: On missing required inputs, unknown variables,
                           or type coercion failures

    Example:
        >>> config = {"model": "{{model_name}}", "temperature": "{{temp}}"}
        >>> inputs = {"model_name": "gpt-4", "temp": "0.7"}
        >>> type_hints = {"temperature": float}
        >>> interpolate_config(config, inputs, type_hints=type_hints)
        {"model": "gpt-4", "temperature": 0.7}
    """
    if valid_vars is None:
        valid_vars = set(inputs.keys())

    type_hints = type_hints or {}

    result = {}
    for key, value in config.items():
        target_type = type_hints.get(key)
        result[key] = _interpolate_value(
            value, inputs, valid_vars, step_name, key, target_type
        )

    return result


def interpolate_step_config(
    step_config: dict[str, Any],
    inputs: dict[str, Any],
    *,
    workflow_input_names: set[str],
    step_name: str,
    type_hints: dict[str, type] | None = None,
) -> dict[str, Any]:
    """
    Interpolate a step's config field.

    Convenience wrapper around interpolate_config that uses workflow
    input names for validation.

    Args:
        step_config: The step's config dict
        inputs: Resolved input values (with defaults applied)
        workflow_input_names: Set of input names defined in [inputs] section
        step_name: Step name for error messages
        type_hints: Optional type hints for coercion

    Returns:
        Interpolated config dict

    Raises:
        InterpolationError: On interpolation errors
    """
    return interpolate_config(
        step_config,
        inputs,
        valid_vars=workflow_input_names,
        step_name=step_name,
        type_hints=type_hints,
    )


def extract_variables(text: str) -> set[str]:
    """
    Extract all variable names from a string.

    Useful for validation or dependency analysis.

    Args:
        text: String potentially containing {{var}} placeholders

    Returns:
        Set of variable names found

    Example:
        >>> extract_variables("Hello {{name}}, your score is {{score}}")
        {"name", "score"}
    """
    return {match.group(1) for match in _VAR_PATTERN.finditer(text)}


def validate_config_variables(
    config: dict[str, Any],
    valid_vars: set[str],
    step_name: str,
) -> list[InterpolationError]:
    """
    Validate that all variables in a config are valid.

    Returns a list of errors rather than raising, useful for
    linting/validation tools.

    Args:
        config: Config dict to validate
        valid_vars: Set of valid variable names
        step_name: Step name for error messages

    Returns:
        List of InterpolationError for any unknown variables
    """
    errors: list[InterpolationError] = []

    def check_value(value: Any, field_path: str) -> None:
        if isinstance(value, str):
            for match in _VAR_PATTERN.finditer(value):
                var_name = match.group(1)
                if var_name not in valid_vars:
                    errors.append(
                        InterpolationError(
                            type="unknown_var",
                            var=var_name,
                            step=step_name,
                            field=field_path,
                            message=f"Unknown variable {{{{{var_name}}}}} in step {step_name}",
                        )
                    )
        elif isinstance(value, dict):
            for k, v in value.items():
                check_value(v, f"{field_path}.{k}")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                check_value(item, f"{field_path}[{i}]")

    for key, value in config.items():
        check_value(value, key)

    return errors
