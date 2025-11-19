"""Tests for workflow parser."""

import pytest

from kurt.workflows.parser import (
    VariableSubstitutionError,
    WorkflowParseError,
    load_workflow,
    substitute_variables,
)
from kurt.workflows.schema import StepType, WorkflowDefinition


def test_substitute_variables_simple():
    """Test simple variable substitution."""
    variables = {"name": "John", "age": 30}

    result = substitute_variables("Hello ${name}!", variables)
    assert result == "Hello John!"

    result = substitute_variables("Age: ${age}", variables)
    assert result == "Age: 30"


def test_substitute_variables_full_value():
    """Test substitution that returns the full value (preserves type)."""
    variables = {"count": 42, "items": ["a", "b", "c"]}

    result = substitute_variables("${count}", variables)
    assert result == 42
    assert isinstance(result, int)

    result = substitute_variables("${items}", variables)
    assert result == ["a", "b", "c"]
    assert isinstance(result, list)


def test_substitute_variables_nested():
    """Test nested variable substitution."""
    variables = {
        "user": {"name": "John", "email": "john@example.com"},
        "config": {"host": "localhost", "port": 8080},
    }

    result = substitute_variables("${user.name}", variables)
    assert result == "John"

    result = substitute_variables("${config.host}:${config.port}", variables)
    assert result == "localhost:8080"


def test_substitute_variables_list_access():
    """Test list access in variable substitution."""
    variables = {"items": ["first", "second", "third"]}

    result = substitute_variables("${items[0]}", variables)
    assert result == "first"

    result = substitute_variables("${items[2]}", variables)
    assert result == "third"


def test_substitute_variables_dict():
    """Test substitution in dictionaries."""
    variables = {"host": "localhost", "port": 8080}

    data = {"url": "http://${host}:${port}", "timeout": "${port}"}

    result = substitute_variables(data, variables)
    assert result == {"url": "http://localhost:8080", "timeout": 8080}


def test_substitute_variables_list():
    """Test substitution in lists."""
    variables = {"env": "production"}

    data = ["${env}", "server", "${env}-backup"]

    result = substitute_variables(data, variables)
    assert result == ["production", "server", "production-backup"]


def test_substitute_variables_missing():
    """Test error handling for missing variables."""
    variables = {"name": "John"}

    with pytest.raises(VariableSubstitutionError):
        substitute_variables("${missing}", variables)


def test_substitute_variables_allow_missing():
    """Test allowing missing variables."""
    variables = {"name": "John"}

    result = substitute_variables("Hello ${missing}!", variables, allow_missing=True)
    assert result == "Hello ${missing}!"


def test_load_workflow_simple(tmp_path):
    """Test loading a simple workflow."""
    workflow_file = tmp_path / "test_workflow.yaml"
    workflow_file.write_text("""
name: "Test Workflow"
description: "A test workflow"
version: "1.0"

variables:
  target: "example.com"

steps:
  - name: "step1"
    type: "cli"
    command: "content fetch"
    args:
      url: "${target}"
    output: "result"
""")

    workflow = load_workflow(workflow_file)

    assert workflow.name == "Test Workflow"
    assert workflow.description == "A test workflow"
    assert workflow.version == "1.0"
    assert workflow.variables == {"target": "example.com"}
    assert len(workflow.steps) == 1
    assert workflow.steps[0].name == "step1"
    assert workflow.steps[0].type == StepType.CLI
    assert workflow.steps[0].command == "content fetch"


def test_load_workflow_invalid_yaml(tmp_path):
    """Test error handling for invalid YAML."""
    workflow_file = tmp_path / "invalid.yaml"
    workflow_file.write_text("name: test\n  invalid: [yaml")

    with pytest.raises(WorkflowParseError, match="Invalid YAML"):
        load_workflow(workflow_file)


def test_load_workflow_missing_required_fields(tmp_path):
    """Test error handling for missing required fields."""
    workflow_file = tmp_path / "incomplete.yaml"
    workflow_file.write_text("""
name: "Test"
steps:
  - name: "step1"
    type: "cli"
    # Missing required 'command' field
    output: "result"
""")

    with pytest.raises(WorkflowParseError, match="command is required"):
        load_workflow(workflow_file)


def test_workflow_get_step():
    """Test getting a step by name."""
    workflow = WorkflowDefinition(
        name="Test",
        steps=[
            {"name": "step1", "type": "cli", "command": "test"},
            {"name": "step2", "type": "cli", "command": "test2"},
        ],
    )

    step = workflow.get_step("step1")
    assert step is not None
    assert step.name == "step1"

    step = workflow.get_step("nonexistent")
    assert step is None


def test_workflow_duplicate_step_names():
    """Test that duplicate step names are rejected."""
    with pytest.raises(ValueError, match="Duplicate step names"):
        WorkflowDefinition(
            name="Test",
            steps=[
                {"name": "step1", "type": "cli", "command": "test"},
                {"name": "step1", "type": "cli", "command": "test2"},
            ],
        )


def test_workflow_reserved_variable_names():
    """Test that reserved variable names are rejected."""
    with pytest.raises(ValueError, match="reserved words"):
        WorkflowDefinition(
            name="Test",
            variables={"step": "invalid"},
            steps=[{"name": "step1", "type": "cli", "command": "test"}],
        )
