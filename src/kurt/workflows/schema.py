"""Workflow schema definitions and validation.

Defines the structure of YAML workflow files and provides validation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class StepType(str, Enum):
    """Type of workflow step."""

    CLI = "cli"
    DSPY = "dspy"
    SCRIPT = "script"
    PARALLEL = "parallel"
    FOREACH = "foreach"


class ErrorAction(str, Enum):
    """Action to take on error."""

    RETRY = "retry"
    SKIP = "skip"
    FAIL = "fail"
    FALLBACK = "fallback"


class ErrorHandling(BaseModel):
    """Error handling configuration for a step."""

    action: ErrorAction = ErrorAction.FAIL
    max_retries: int = Field(default=0, ge=0, le=10)
    fallback_step: Optional[str] = None

    @field_validator("fallback_step")
    @classmethod
    def validate_fallback(cls, v, info):
        """Validate fallback_step is provided when action is FALLBACK."""
        if info.data.get("action") == ErrorAction.FALLBACK and not v:
            raise ValueError("fallback_step must be provided when action is 'fallback'")
        return v


class InlineSignatureField(BaseModel):
    """Field definition for inline DSPy signature."""

    name: str = Field(description="Field name")
    type: str = Field(description="Field type (str, int, float, bool, list, dict)")
    description: str = Field(description="Field description for the LLM")


class InlineSignature(BaseModel):
    """Inline DSPy signature definition."""

    inputs: List[InlineSignatureField] = Field(description="Input fields")
    outputs: List[InlineSignatureField] = Field(description="Output fields")
    prompt: str = Field(description="System prompt/instructions for the LLM")


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    name: str = Field(description="Unique name for this step")
    type: StepType = Field(description="Type of step to execute")
    description: Optional[str] = Field(
        default=None, description="Description of what this step does"
    )

    # CLI step fields
    command: Optional[str] = Field(
        default=None, description="CLI command to execute (for cli type)"
    )
    args: Optional[Dict[str, Any]] = Field(default=None, description="Arguments for the command")

    # DSPy step fields
    signature: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None,
        description="DSPy signature: class name (string) or inline definition (dict)",
    )
    inputs: Optional[Dict[str, Any]] = Field(default=None, description="Inputs for DSPy signature")

    # Script step fields
    code: Optional[str] = Field(
        default=None, description="Python code to execute (for script type)"
    )

    # Parallel step fields
    steps: Optional[List["WorkflowStep"]] = Field(
        default=None, description="Sub-steps for parallel execution"
    )

    # Foreach step fields
    items: Optional[str] = Field(
        default=None,
        description="Variable reference to array of items to iterate over (for foreach type)",
    )
    step: Optional["WorkflowStep"] = Field(
        default=None, description="Template step to execute for each item (for foreach type)"
    )
    concurrency: Optional[int] = Field(
        default=10,
        ge=1,
        le=100,
        description="Max concurrent executions (for foreach/parallel types)",
    )

    # Common fields
    output: Optional[str] = Field(default=None, description="Variable name to store step output")
    condition: Optional[str] = Field(
        default=None, description="Python expression to evaluate before running step"
    )
    on_error: Optional[ErrorHandling] = Field(
        default=None, description="Error handling configuration"
    )

    @field_validator("command")
    @classmethod
    def validate_cli_command(cls, v, info):
        """Validate CLI command is provided for cli type."""
        if info.data.get("type") == StepType.CLI and not v:
            raise ValueError("command is required for cli type steps")
        return v

    @field_validator("signature")
    @classmethod
    def validate_dspy_signature(cls, v, info):
        """Validate DSPy signature is provided for dspy type."""
        if info.data.get("type") == StepType.DSPY and not v:
            raise ValueError("signature is required for dspy type steps")
        return v

    @field_validator("code")
    @classmethod
    def validate_script_code(cls, v, info):
        """Validate script code is provided for script type."""
        if info.data.get("type") == StepType.SCRIPT and not v:
            raise ValueError("code is required for script type steps")
        return v

    @field_validator("steps")
    @classmethod
    def validate_parallel_steps(cls, v, info):
        """Validate sub-steps are provided for parallel type."""
        if info.data.get("type") == StepType.PARALLEL and not v:
            raise ValueError("steps is required for parallel type")
        return v

    @field_validator("items")
    @classmethod
    def validate_foreach_items(cls, v, info):
        """Validate items array is provided for foreach type."""
        if info.data.get("type") == StepType.FOREACH and not v:
            raise ValueError("items is required for foreach type steps")
        return v

    @field_validator("step")
    @classmethod
    def validate_foreach_step(cls, v, info):
        """Validate template step is provided for foreach type."""
        if info.data.get("type") == StepType.FOREACH and not v:
            raise ValueError("step is required for foreach type steps")
        return v


class WorkflowDefinition(BaseModel):
    """Complete workflow definition."""

    name: str = Field(description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    version: str = Field(default="1.0", description="Workflow version")

    variables: Optional[Dict[str, Any]] = Field(default=None, description="Default variable values")

    steps: List[WorkflowStep] = Field(description="Workflow steps to execute")

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v):
        """Validate steps list."""
        if not v:
            raise ValueError("At least one step is required")

        # Check for duplicate step names
        step_names = [step.name for step in v]
        if len(step_names) != len(set(step_names)):
            duplicates = [name for name in step_names if step_names.count(name) > 1]
            raise ValueError(f"Duplicate step names found: {duplicates}")

        return v

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, v):
        """Validate variable names."""
        if v is None:
            return v

        reserved_names = {"step", "workflow", "context", "result"}
        invalid_names = set(v.keys()) & reserved_names
        if invalid_names:
            raise ValueError(f"Variable names cannot be reserved words: {invalid_names}")

        return v

    def get_step(self, name: str) -> Optional[WorkflowStep]:
        """Get a step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None

    def validate_step_references(self) -> List[str]:
        """
        Validate that all step references (output variables, fallback steps) are valid.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        step_names = {step.name for step in self.steps}

        for step in self.steps:
            # Check fallback step references
            if step.on_error and step.on_error.fallback_step:
                if step.on_error.fallback_step not in step_names:
                    errors.append(
                        f"Step '{step.name}' references unknown fallback step '{step.on_error.fallback_step}'"
                    )

        return errors


# Update forward references
WorkflowStep.model_rebuild()


__all__ = [
    "StepType",
    "ErrorAction",
    "ErrorHandling",
    "InlineSignatureField",
    "InlineSignature",
    "WorkflowStep",
    "WorkflowDefinition",
]
