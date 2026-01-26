"""
TOML workflow parser for Kurt engine.

Parses workflow definition files into Pydantic models with strict validation:
- Step types must match registered tool names
- Dependencies must reference existing steps
- No circular dependencies
- No unknown keys (strict mode)
"""

from __future__ import annotations

import sys
from pathlib import Path

# tomllib is Python 3.11+, use tomli backport for 3.10
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from kurt.tools.registry import TOOLS

# Valid input types for workflow inputs
InputType = Literal["string", "int", "float", "bool"]

# Step type aliases: user-friendly names -> actual tool registry names
# This allows TOML files to use short names like "llm" instead of "batch-llm"
STEP_TYPE_ALIASES: dict[str, str] = {
    "llm": "batch-llm",
    "embed": "batch-embedding",
}

# Valid step types - must match tool registry keys (after alias resolution)
# "function" is special: executes user-defined Python function from tools.py
VALID_STEP_TYPES = frozenset(["map", "fetch", "llm", "embed", "write", "sql", "agent", "function"])


def resolve_step_type(step_type: str) -> str:
    """Resolve step type alias to actual tool name."""
    return STEP_TYPE_ALIASES.get(step_type, step_type)


class WorkflowParseError(Exception):
    """Base exception for workflow parsing errors."""

    pass


class UnknownStepTypeError(WorkflowParseError):
    """Raised when a step has an unknown type."""

    def __init__(self, step_name: str, step_type: str):
        self.step_name = step_name
        self.step_type = step_type
        super().__init__(f"Step {step_name} has unknown type: {step_type}")


class UnknownDependsOnError(WorkflowParseError):
    """Raised when a step depends on an unknown step."""

    def __init__(self, step_name: str, dep: str):
        self.step_name = step_name
        self.dep = dep
        super().__init__(f"Step {step_name} depends on unknown step: {dep}")


class CircularDependencyError(WorkflowParseError):
    """Raised when circular dependencies are detected."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class UnknownKeyError(WorkflowParseError):
    """Raised when an unknown key is found in strict mode."""

    def __init__(self, location: str, key: str):
        self.location = location
        self.key = key
        super().__init__(f"{location} has unknown key: {key}")


class InputDef(BaseModel):
    """
    Definition of a workflow input parameter.

    Attributes:
        type: Input data type ('string', 'int', 'float', 'bool')
        required: Whether the input is required (default: False)
        default: Default value if not provided (None if required)
    """

    type: InputType
    required: bool = False
    default: Any | None = None

    @model_validator(mode="after")
    def validate_default_type(self) -> "InputDef":
        """Validate that default value matches declared type."""
        if self.default is None:
            return self

        expected_types = {
            "string": str,
            "int": int,
            "float": (int, float),  # Allow int for float
            "bool": bool,
        }

        expected = expected_types[self.type]
        if not isinstance(self.default, expected):
            raise ValueError(
                f"Default value {self.default!r} does not match type {self.type}"
            )

        return self


class StepDef(BaseModel):
    """
    Definition of a workflow step.

    Attributes:
        type: Tool name to execute (must be in VALID_STEP_TYPES).
              Special type "function" executes user-defined Python function.
        depends_on: List of step names this step depends on
        config: Tool-specific configuration (validated at execution time)
        function: For type="function", the name of the function to call from tools.py
        continue_on_error: Whether to continue workflow on step failure
    """

    type: str
    depends_on: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    function: str | None = Field(default=None)
    continue_on_error: bool = False


class WorkflowMeta(BaseModel):
    """
    Workflow metadata from [workflow] section.

    Attributes:
        name: Workflow identifier
        description: Human-readable description (optional)
    """

    name: str
    description: str | None = None


class WorkflowDefinition(BaseModel):
    """
    Complete workflow definition parsed from TOML.

    Attributes:
        workflow: Workflow metadata (name, description)
        inputs: Input parameter definitions
        steps: Step definitions keyed by step name
    """

    workflow: WorkflowMeta
    inputs: dict[str, InputDef] = Field(default_factory=dict)
    steps: dict[str, StepDef] = Field(default_factory=dict)


# Valid keys for each section (strict validation)
_WORKFLOW_KEYS = frozenset(["name", "description"])
_INPUT_KEYS = frozenset(["type", "required", "default"])
# function step uses "function" key instead of "config" to specify the function name
_STEP_KEYS = frozenset(["type", "depends_on", "config", "continue_on_error", "function"])
_TOP_LEVEL_KEYS = frozenset(["workflow", "inputs", "steps"])


def _check_unknown_keys(
    data: dict[str, Any],
    valid_keys: frozenset[str],
    location: str,
) -> None:
    """Check for unknown keys and raise UnknownKeyError if found."""
    for key in data:
        if key not in valid_keys:
            raise UnknownKeyError(location, key)


def _detect_circular_dependencies(steps: dict[str, StepDef]) -> list[str] | None:
    """
    Detect circular dependencies in step graph.

    Uses DFS with coloring:
    - WHITE (0): unvisited
    - GRAY (1): in current path
    - BLACK (2): fully processed

    Returns:
        List of step names forming a cycle, or None if no cycle.
    """
    WHITE, GRAY, BLACK = 0, 1, 2  # noqa: N806
    color: dict[str, int] = {name: WHITE for name in steps}
    {name: None for name in steps}

    def visit(node: str, path: list[str]) -> list[str] | None:
        color[node] = GRAY
        path.append(node)

        for dep in steps[node].depends_on:
            if dep not in color:
                # Dependency doesn't exist - handled elsewhere
                continue
            if color[dep] == GRAY:
                # Found cycle - build cycle path
                cycle_start = path.index(dep)
                return path[cycle_start:] + [dep]
            if color[dep] == WHITE:
                result = visit(dep, path)
                if result:
                    return result

        path.pop()
        color[node] = BLACK
        return None

    for node in steps:
        if color[node] == WHITE:
            result = visit(node, [])
            if result:
                return result

    return None


def _resolve_output_schema(config: dict[str, Any], models_path: Path | None) -> None:
    """
    Resolve output_schema reference if present (in-place).

    For llm steps, output_schema can be a string reference to a class
    in models.py (e.g., "ExtractedEntity"). This function resolves
    the reference to the actual class.

    Args:
        config: Step config dict (modified in place)
        models_path: Path to models.py file (or None to skip resolution)
    """
    if "output_schema" not in config:
        return

    schema_ref = config["output_schema"]
    if not isinstance(schema_ref, str):
        # Already resolved or not a reference
        return

    if models_path is None or not models_path.exists():
        # No models file, keep as string (will fail at execution)
        return

    # Import the models module dynamically
    import importlib.util

    spec = importlib.util.spec_from_file_location("models", models_path)
    if spec is None or spec.loader is None:
        return

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        # If models.py has errors, keep as string reference
        return

    # Look up the class by name
    if hasattr(module, schema_ref):
        config["output_schema"] = getattr(module, schema_ref)


def parse_workflow(
    toml_path: str | Path,
    *,
    models_path: str | Path | None = None,
    validate_tools: bool = True,
) -> WorkflowDefinition:
    """
    Parse a TOML workflow file into a WorkflowDefinition.

    Args:
        toml_path: Path to the TOML workflow file
        models_path: Optional path to models.py for output_schema resolution.
                    If None, looks for models.py in same directory as TOML.
        validate_tools: If True, validate step types against tool registry.
                       Set to False for testing without registered tools.

    Returns:
        WorkflowDefinition with validated workflow, inputs, and steps.

    Raises:
        FileNotFoundError: If TOML file doesn't exist
        tomllib.TOMLDecodeError: If TOML is malformed
        UnknownKeyError: If unknown keys found (strict validation)
        UnknownStepTypeError: If step type not in VALID_STEP_TYPES
        UnknownDependsOnError: If step depends on non-existent step
        CircularDependencyError: If circular dependencies detected
    """
    toml_path = Path(toml_path)

    # Read and parse TOML
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    # Determine models path
    if models_path is not None:
        models_path = Path(models_path)
    else:
        models_path = toml_path.parent / "models.py"

    # Strict validation: check top-level keys
    _check_unknown_keys(data, _TOP_LEVEL_KEYS, "Workflow file")

    # Parse [workflow] section (required)
    if "workflow" not in data:
        raise WorkflowParseError("Missing required [workflow] section")

    workflow_data = data["workflow"]
    _check_unknown_keys(workflow_data, _WORKFLOW_KEYS, "[workflow]")
    workflow = WorkflowMeta.model_validate(workflow_data)

    # Parse [inputs] section (optional)
    inputs: dict[str, InputDef] = {}
    if "inputs" in data:
        for input_name, input_data in data["inputs"].items():
            if not isinstance(input_data, dict):
                raise WorkflowParseError(
                    f"Input {input_name} must be a table, got {type(input_data).__name__}"
                )
            _check_unknown_keys(input_data, _INPUT_KEYS, f"[inputs.{input_name}]")
            inputs[input_name] = InputDef.model_validate(input_data)

    # Parse [steps.*] sections (optional but usually present)
    steps: dict[str, StepDef] = {}
    if "steps" in data:
        for step_name, step_data in data["steps"].items():
            if not isinstance(step_data, dict):
                raise WorkflowParseError(
                    f"Step {step_name} must be a table, got {type(step_data).__name__}"
                )
            _check_unknown_keys(step_data, _STEP_KEYS, f"[steps.{step_name}]")

            # Validate step type against valid types
            step_type = step_data.get("type")
            if step_type is None:
                raise WorkflowParseError(f"Step {step_name} missing required 'type' key")

            if step_type not in VALID_STEP_TYPES:
                raise UnknownStepTypeError(step_name, step_type)

            # Validate function-type steps
            if step_type == "function":
                if "function" not in step_data:
                    raise WorkflowParseError(
                        f"Step {step_name} has type 'function' but missing required 'function' key"
                    )
            else:
                # Additional validation: if validate_tools is True, check tool registry
                # Use resolved step type (after alias expansion) for registry lookup
                resolved_type = resolve_step_type(step_type)
                if validate_tools and resolved_type not in TOOLS:
                    # Only warn if TOOLS is non-empty (tools have been registered)
                    # Otherwise allow for testing without full tool setup
                    if TOOLS:
                        raise UnknownStepTypeError(step_name, step_type)

            # Resolve output_schema for llm steps
            config = step_data.get("config", {}).copy()
            if step_type == "llm" and "output_schema" in config:
                _resolve_output_schema(config, models_path)
                step_data = {**step_data, "config": config}

            steps[step_name] = StepDef.model_validate(step_data)

    # Validate dependencies: all depends_on must reference existing steps
    step_names = set(steps.keys())
    for step_name, step_def in steps.items():
        for dep in step_def.depends_on:
            if dep not in step_names:
                raise UnknownDependsOnError(step_name, dep)

    # Detect circular dependencies
    if steps:
        cycle = _detect_circular_dependencies(steps)
        if cycle:
            raise CircularDependencyError(cycle)

    return WorkflowDefinition(
        workflow=workflow,
        inputs=inputs,
        steps=steps,
    )
