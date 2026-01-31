"""
Kurt Workflow Engine.

This module provides TOML-based workflow parsing and execution:
- parse_workflow(): Parse TOML files into WorkflowDefinition
- execute_workflow(): Execute a workflow asynchronously with parallel steps
- interpolate_config(): Replace {{var}} placeholders with input values
- build_dag(): Build execution plan from step dependencies
- WorkflowDefinition, InputDef, StepDef: Pydantic models for workflow schema
- ExecutionPlan: Execution plan with levels, critical path, parallelism info
- WorkflowResult, StepResult: Execution result types

Example:
    from kurt.workflows.toml import parse_workflow, build_dag, execute_workflow

    # Parse a workflow file
    workflow = parse_workflow("workflows/my_pipeline.toml")

    # Build execution plan (topological sort into levels)
    plan = build_dag(workflow.steps)
    print(f"Levels: {plan.levels}")
    print(f"Critical path: {plan.critical_path}")
    print(f"Parallelizable: {plan.parallelizable}")

    # Execute the workflow
    result = await execute_workflow(workflow, {"url": "https://example.com"})
    print(f"Status: {result.status}")
    print(f"Exit code: {result.exit_code}")

    # Access workflow metadata
    print(workflow.workflow.name)
    print(workflow.workflow.description)

    # Access inputs
    for name, input_def in workflow.inputs.items():
        print(f"{name}: {input_def.type}, required={input_def.required}")

    # Access steps
    for name, step_def in workflow.steps.items():
        print(f"{name}: type={step_def.type}, depends_on={step_def.depends_on}")

    # Interpolate step config with input values
    from kurt.workflows.toml import interpolate_config
    config = {"model": "{{model_name}}", "temperature": "{{temp}}"}
    inputs = {"model_name": "gpt-4", "temp": 0.7}
    result = interpolate_config(config, inputs)
"""

from .dag import (
    CycleDetectedError,
    ExecutionPlan,
    build_dag,
)
from .executor import (
    ExitCode,
    StepResult,
    WorkflowExecutor,
    WorkflowResult,
    execute_workflow,
)
from .fixtures import (
    FixtureLoadError,
    FixtureNotFoundError,
    FixtureReport,
    FixtureSet,
    StepFixture,
    analyze_fixture_coverage,
    discover_fixture_steps,
    load_fixture,
    load_fixtures,
    load_jsonl,
)
from .interpolation import (
    InterpolationError,
    extract_variables,
    interpolate_config,
    interpolate_step_config,
    validate_config_variables,
)
from .parser import (
    STEP_TYPE_ALIASES,
    CircularDependencyError,
    InputDef,
    StepDef,
    UnknownDependsOnError,
    UnknownKeyError,
    UnknownStepTypeError,
    WorkflowDefinition,
    WorkflowMeta,
    WorkflowParseError,
    parse_workflow,
    resolve_step_type,
)

__all__ = [
    # Main functions
    "parse_workflow",
    "execute_workflow",
    "interpolate_config",
    "interpolate_step_config",
    "build_dag",
    # Executor
    "WorkflowExecutor",
    "WorkflowResult",
    "StepResult",
    "ExitCode",
    # Utilities
    "extract_variables",
    "validate_config_variables",
    # Fixtures
    "load_fixtures",
    "load_fixture",
    "load_jsonl",
    "discover_fixture_steps",
    "analyze_fixture_coverage",
    "FixtureSet",
    "StepFixture",
    "FixtureReport",
    "FixtureLoadError",
    "FixtureNotFoundError",
    # Models
    "WorkflowDefinition",
    "WorkflowMeta",
    "InputDef",
    "StepDef",
    "ExecutionPlan",
    # Errors
    "WorkflowParseError",
    "UnknownStepTypeError",
    "UnknownDependsOnError",
    "CircularDependencyError",
    "CycleDetectedError",
    "UnknownKeyError",
    "InterpolationError",
    # Step type utilities
    "STEP_TYPE_ALIASES",
    "resolve_step_type",
]
