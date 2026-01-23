"""
End-to-end tests for custom function steps in workflows.

Tests the ability to define Python functions in tools.py and
reference them in workflow TOML files using type = "function".
"""

from __future__ import annotations

import os
import pytest
import tempfile
from pathlib import Path

from kurt.engine.parser import (
    parse_workflow,
    WorkflowParseError,
    VALID_STEP_TYPES,
)
from kurt.engine.executor import (
    execute_workflow,
    _load_user_function,
    _execute_user_function,
)
from kurt.tools.base import ToolContext


class TestFunctionStepParsing:
    """Test parsing of function-type steps."""

    def test_function_in_valid_step_types(self):
        """Function should be a valid step type."""
        assert "function" in VALID_STEP_TYPES

    def test_parse_function_step(self, tmp_path: Path):
        """Parse a workflow with a function step."""
        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "test-function"

[steps.process]
type = "function"
function = "my_function"
""")
        workflow = parse_workflow(workflow_toml, validate_tools=False)
        assert workflow.steps["process"].type == "function"
        assert workflow.steps["process"].function == "my_function"

    def test_function_step_with_config(self, tmp_path: Path):
        """Function step can have config."""
        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "test-function-config"

[steps.process]
type = "function"
function = "my_function"
[steps.process.config]
option1 = "value1"
option2 = 42
""")
        workflow = parse_workflow(workflow_toml, validate_tools=False)
        assert workflow.steps["process"].config == {"option1": "value1", "option2": 42}

    def test_function_step_missing_function_key(self, tmp_path: Path):
        """Function step without function key should fail."""
        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "test-missing-function"

[steps.process]
type = "function"
""")
        with pytest.raises(WorkflowParseError, match="missing required 'function' key"):
            parse_workflow(workflow_toml, validate_tools=False)

    def test_function_step_with_depends_on(self, tmp_path: Path):
        """Function step can depend on other steps."""
        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "test-function-deps"

[steps.first]
type = "function"
function = "first_function"

[steps.second]
type = "function"
function = "second_function"
depends_on = ["first"]
""")
        workflow = parse_workflow(workflow_toml, validate_tools=False)
        assert workflow.steps["second"].depends_on == ["first"]


class TestLoadUserFunction:
    """Test loading user functions from tools.py."""

    def test_load_existing_function(self, tmp_path: Path):
        """Load a function that exists in tools.py."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def my_function(context):
    return {"result": "success"}
""")
        func = _load_user_function(tools_py, "my_function")
        assert callable(func)

    def test_load_nonexistent_function(self, tmp_path: Path):
        """Loading nonexistent function raises AttributeError."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def other_function(context):
    return {}
""")
        with pytest.raises(AttributeError, match="not found"):
            _load_user_function(tools_py, "my_function")

    def test_load_from_nonexistent_file(self, tmp_path: Path):
        """Loading from nonexistent file raises FileNotFoundError."""
        tools_py = tmp_path / "nonexistent.py"
        with pytest.raises(FileNotFoundError):
            _load_user_function(tools_py, "my_function")


class TestExecuteUserFunction:
    """Test execution of user functions."""

    @pytest.mark.asyncio
    async def test_execute_sync_function(self, tmp_path: Path):
        """Execute a synchronous function."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def sync_function(context):
    return {"value": context.get("inputs", {}).get("x", 0) * 2}
""")
        func = _load_user_function(tools_py, "sync_function")
        result = await _execute_user_function(func, {"inputs": {"x": 5}})
        assert result == {"value": 10}

    @pytest.mark.asyncio
    async def test_execute_async_function(self, tmp_path: Path):
        """Execute an async function."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
async def async_function(context):
    return {"async": True, "data": context.get("input_data", [])}
""")
        func = _load_user_function(tools_py, "async_function")
        result = await _execute_user_function(func, {"input_data": [{"a": 1}]})
        assert result == {"async": True, "data": [{"a": 1}]}

    @pytest.mark.asyncio
    async def test_function_receives_context(self, tmp_path: Path):
        """Function receives full context dict."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def check_context(context):
    return {
        "has_inputs": "inputs" in context,
        "has_input_data": "input_data" in context,
        "has_config": "config" in context,
        "has_workflow_id": "workflow_id" in context,
        "has_step_id": "step_id" in context,
    }
""")
        func = _load_user_function(tools_py, "check_context")
        result = await _execute_user_function(func, {
            "inputs": {"a": 1},
            "input_data": [],
            "config": {"opt": "val"},
            "workflow_id": "test-123",
            "step_id": "step1",
        })
        assert all(result.values())

    @pytest.mark.asyncio
    async def test_function_none_returns_empty_dict(self, tmp_path: Path):
        """Function returning None is normalized to empty dict."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def returns_none(context):
    pass
""")
        func = _load_user_function(tools_py, "returns_none")
        result = await _execute_user_function(func, {})
        assert result == {}

    @pytest.mark.asyncio
    async def test_function_non_dict_wrapped(self, tmp_path: Path):
        """Non-dict return values are wrapped."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def returns_string(context):
    return "hello"
""")
        func = _load_user_function(tools_py, "returns_string")
        result = await _execute_user_function(func, {})
        assert result == {"result": "hello"}


class TestFunctionStepExecution:
    """End-to-end tests for function step execution."""

    @pytest.mark.asyncio
    async def test_execute_simple_function_workflow(self, tmp_path: Path):
        """Execute a workflow with a single function step."""
        # Create tools.py
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def process(context):
    inputs = context.get("inputs", {})
    return {"doubled": inputs.get("value", 0) * 2}
""")

        # Create workflow
        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "simple-function"

[inputs]
value = { type = "int", required = true }

[steps.process]
type = "function"
function = "process"
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        result = await execute_workflow(
            workflow,
            inputs={"value": 5},
            tools_path=tools_py,
        )

        assert result.status == "completed"
        assert result.exit_code == 0
        assert "process" in result.step_results
        assert result.step_results["process"].status == "completed"
        assert result.step_results["process"].output_data == [{"doubled": 10}]

    @pytest.mark.asyncio
    async def test_execute_chained_function_workflow(self, tmp_path: Path):
        """Execute a workflow with chained function steps."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def step_one(context):
    return {"value": 10}

def step_two(context):
    input_data = context.get("input_data", [])
    prev_value = input_data[0].get("value", 0) if input_data else 0
    return {"value": prev_value + 5}
""")

        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "chained-functions"

[steps.one]
type = "function"
function = "step_one"

[steps.two]
type = "function"
function = "step_two"
depends_on = ["one"]
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        result = await execute_workflow(
            workflow,
            inputs={},
            tools_path=tools_py,
        )

        assert result.status == "completed"
        assert result.step_results["two"].output_data == [{"value": 15}]

    @pytest.mark.asyncio
    async def test_function_step_uses_config(self, tmp_path: Path):
        """Function step receives config from TOML."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def configurable(context):
    config = context.get("config", {})
    multiplier = config.get("multiplier", 1)
    return {"result": 10 * multiplier}
""")

        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "with-config"

[steps.calc]
type = "function"
function = "configurable"
[steps.calc.config]
multiplier = 3
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        result = await execute_workflow(
            workflow,
            inputs={},
            tools_path=tools_py,
        )

        assert result.status == "completed"
        assert result.step_results["calc"].output_data == [{"result": 30}]

    @pytest.mark.asyncio
    async def test_function_not_found_fails_gracefully(self, tmp_path: Path):
        """Workflow fails gracefully when function doesn't exist."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def other_function(context):
    return {}
""")

        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "missing-function"

[steps.process]
type = "function"
function = "nonexistent"
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        result = await execute_workflow(
            workflow,
            inputs={},
            tools_path=tools_py,
        )

        assert result.status == "failed"
        assert result.exit_code == 1
        assert result.step_results["process"].status == "failed"
        assert "not found" in result.step_results["process"].error.lower()

    @pytest.mark.asyncio
    async def test_tools_file_not_found_fails_gracefully(self, tmp_path: Path):
        """Workflow fails gracefully when tools.py doesn't exist."""
        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "no-tools-file"

[steps.process]
type = "function"
function = "anything"
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        result = await execute_workflow(
            workflow,
            inputs={},
            tools_path=tmp_path / "nonexistent_tools.py",
        )

        assert result.status == "failed"
        assert result.step_results["process"].status == "failed"

    @pytest.mark.asyncio
    async def test_function_exception_fails_step(self, tmp_path: Path):
        """Function raising exception fails the step."""
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def failing_function(context):
    raise ValueError("Something went wrong")
""")

        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "failing-function"

[steps.process]
type = "function"
function = "failing_function"
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        result = await execute_workflow(
            workflow,
            inputs={},
            tools_path=tools_py,
        )

        assert result.status == "failed"
        assert result.step_results["process"].status == "failed"
        assert "Something went wrong" in result.step_results["process"].error


class TestMixedWorkflowsWithDolt:
    """E2E tests for workflows mixing SQL tools with custom functions."""

    @pytest.fixture
    def dolt_project(self, tmp_path: Path, monkeypatch):
        """Create a temp project with DoltDB initialized."""
        import shutil
        import subprocess

        # Skip if dolt not installed
        if not shutil.which("dolt"):
            pytest.skip("Dolt CLI not installed")

        from kurt.db.dolt import DoltDB

        # Create project structure
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        # Initialize dolt repo using CLI directly
        subprocess.run(
            ["dolt", "init"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Set up environment
        monkeypatch.setenv("DOLT_PATH", str(repo_path))
        original_cwd = os.getcwd()
        os.chdir(repo_path)

        # Create DoltDB instance and set up tables
        db = DoltDB(str(repo_path))
        db.execute("CREATE TABLE test_data (id INT PRIMARY KEY, name VARCHAR(255), value VARCHAR(255))")
        db.execute("INSERT INTO test_data VALUES (1, 'item1', 'value1')")
        db.execute("INSERT INTO test_data VALUES (2, 'item2', 'value2')")

        yield repo_path, db

        os.chdir(original_cwd)

    @pytest.mark.asyncio
    async def test_sql_then_function_workflow(self, dolt_project):
        """Test workflow that reads SQL then processes with function."""
        tmp_path, db = dolt_project

        # Create tools.py
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def process_rows(context):
    input_data = context.get("input_data", [])
    return {
        "count": len(input_data),
        "processed": True,
        "names": [row.get("name") for row in input_data],
    }
""")

        # Create workflow
        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "sql-then-function"

[steps.read]
type = "sql"
[steps.read.config]
query = "SELECT * FROM test_data"

[steps.process]
type = "function"
function = "process_rows"
depends_on = ["read"]
""")

        workflow = parse_workflow(workflow_toml, validate_tools=True)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            tools_path=tools_py,
        )

        assert result.status == "completed"
        assert result.step_results["read"].status == "completed"
        assert len(result.step_results["read"].output_data) == 2

        assert result.step_results["process"].status == "completed"
        process_output = result.step_results["process"].output_data[0]
        assert process_output["count"] == 2
        assert process_output["processed"] is True
        assert "item1" in process_output["names"]

    @pytest.mark.asyncio
    async def test_function_then_write_workflow(self, dolt_project):
        """Test workflow that generates data with function then writes with SQL tool."""
        tmp_path, db = dolt_project

        # Create tools.py - must include id for primary key
        tools_py = tmp_path / "tools.py"
        tools_py.write_text("""
def generate_data(context):
    return {
        "id": 100,
        "name": "generated_item",
        "value": "generated_value",
    }
""")

        # Create workflow
        workflow_toml = tmp_path / "workflow.toml"
        workflow_toml.write_text("""
[workflow]
name = "function-then-write"

[steps.generate]
type = "function"
function = "generate_data"

[steps.write]
type = "write"
depends_on = ["generate"]
[steps.write.config]
table = "test_data"
mode = "insert"
""")

        workflow = parse_workflow(workflow_toml, validate_tools=True)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            tools_path=tools_py,
        )

        assert result.status == "completed"
        assert result.step_results["generate"].status == "completed"
        assert result.step_results["write"].status == "completed"

        # Verify data was written
        query_result = db.query("SELECT * FROM test_data WHERE name = 'generated_item'")
        assert len(query_result.rows) == 1
        assert query_result.rows[0]["value"] == "generated_value"
