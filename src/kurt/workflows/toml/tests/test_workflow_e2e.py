"""
End-to-end tests for TOML workflow execution.

Tests the complete workflow system with real database operations:
- SQL tool workflows
- Write tool workflows
- Function step workflows
- Mixed workflows combining tools and functions
- CLI integration tests

Uses DoltDB fixtures for realistic integration testing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

# Import tools module to ensure all tools are registered via @register_tool
import kurt.tools  # noqa: F401
from kurt.tools.core import ToolContext
from kurt.workflows.toml.executor import execute_workflow
from kurt.workflows.toml.parser import parse_workflow

# ============================================================================
# DoltDB Fixture
# ============================================================================


@pytest.fixture
def dolt_repo(tmp_path: Path):
    """
    Create a temporary Dolt repository for e2e testing.

    Sets up:
    - Initialized Dolt repo
    - test_data table with sample records
    - results table for write operations
    """
    if not shutil.which("dolt"):
        pytest.skip("Dolt CLI not installed")

    from kurt.db.dolt import DoltDB

    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    # Initialize dolt repo
    subprocess.run(["dolt", "init"], cwd=repo_path, check=True, capture_output=True)

    # Create DoltDB instance
    db = DoltDB(str(repo_path))

    # Create test tables
    db.execute("""
        CREATE TABLE test_data (
            id INT PRIMARY KEY,
            name VARCHAR(255),
            value VARCHAR(255),
            score FLOAT
        )
    """)
    db.execute("""
        CREATE TABLE results (
            id INT PRIMARY KEY AUTO_INCREMENT,
            source VARCHAR(255),
            processed_value VARCHAR(255),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert sample data
    db.execute("INSERT INTO test_data VALUES (1, 'item1', 'value1', 0.5)")
    db.execute("INSERT INTO test_data VALUES (2, 'item2', 'value2', 0.8)")
    db.execute("INSERT INTO test_data VALUES (3, 'item3', 'value3', 0.3)")

    yield repo_path, db


@pytest.fixture
def workflow_dir(dolt_repo, monkeypatch):
    """
    Create a workflow directory with tools.py and change to it.
    """
    repo_path, db = dolt_repo

    # Create workflows subdirectory
    workflows_dir = repo_path / "workflows"
    workflows_dir.mkdir()

    # Create tools.py with custom functions
    tools_py = workflows_dir / "tools.py"
    tools_py.write_text('''"""Custom workflow functions."""

from typing import Any
from datetime import datetime


def transform_records(context: dict[str, Any]) -> dict[str, Any]:
    """Transform records by adding metadata."""
    input_data = context.get("input_data", [])
    config = context.get("config", {})
    prefix = config.get("prefix", "processed")

    results = []
    for record in input_data:
        results.append({
            **record,
            "processed": True,
            "prefix": prefix,
            "processed_at": datetime.utcnow().isoformat(),
        })

    return {
        "records": results,
        "count": len(results),
    }


def aggregate_stats(context: dict[str, Any]) -> dict[str, Any]:
    """Aggregate statistics from input data."""
    input_data = context.get("input_data", [])

    total = len(input_data)
    if not input_data:
        return {"total": 0, "avg_score": 0}

    scores = [r.get("score", 0) for r in input_data if "score" in r]
    avg_score = sum(scores) / len(scores) if scores else 0

    return {
        "total": total,
        "avg_score": round(avg_score, 2),
        "min_score": min(scores) if scores else None,
        "max_score": max(scores) if scores else None,
    }


def filter_records(context: dict[str, Any]) -> dict[str, Any]:
    """Filter records based on config threshold."""
    input_data = context.get("input_data", [])
    config = context.get("config", {})
    threshold = config.get("threshold", 0.5)

    filtered = [r for r in input_data if r.get("score", 0) >= threshold]

    return {
        "filtered": filtered,
        "kept": len(filtered),
        "removed": len(input_data) - len(filtered),
    }


def generate_write_data(context: dict[str, Any]) -> dict[str, Any]:
    """Generate data for write operations."""
    input_data = context.get("input_data", [])
    config = context.get("config", {})

    # Take first input record and transform for writing
    if input_data:
        first = input_data[0]
        return {
            "id": config.get("id", 100),
            "source": first.get("name", "unknown"),
            "processed_value": f"processed_{first.get('value', '')}",
        }

    return {
        "id": config.get("id", 100),
        "source": "generated",
        "processed_value": "no_input",
    }


def echo(context: dict[str, Any]) -> dict[str, Any]:
    """Simple echo function for testing."""
    return {
        "inputs": context.get("inputs", {}),
        "input_data_count": len(context.get("input_data", [])),
        "config": context.get("config", {}),
        "step_id": context.get("step_id"),
    }
''')

    # Change to workflow directory
    original_cwd = os.getcwd()
    os.chdir(workflows_dir)
    monkeypatch.setenv("DOLT_PATH", str(repo_path))

    yield workflows_dir, db

    os.chdir(original_cwd)


# ============================================================================
# SQL Tool E2E Tests
# ============================================================================


class TestSQLToolE2E:
    """E2E tests for SQL tool in workflows."""

    @pytest.mark.asyncio
    async def test_simple_select(self, workflow_dir):
        """Test simple SELECT query workflow."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "sql_select.toml"
        workflow_toml.write_text("""
[workflow]
name = "sql-select-test"

[steps.query]
type = "sql"
[steps.query.config]
query = "SELECT * FROM test_data ORDER BY id"
""")

        workflow = parse_workflow(workflow_toml)
        context = ToolContext(db=db)
        result = await execute_workflow(workflow, inputs={}, context=context)

        assert result.status == "completed"
        assert result.exit_code == 0
        assert len(result.step_results["query"].output_data) == 3

        # Verify data order
        names = [r["name"] for r in result.step_results["query"].output_data]
        assert names == ["item1", "item2", "item3"]

    @pytest.mark.asyncio
    async def test_select_with_where(self, workflow_dir):
        """Test SELECT with WHERE clause."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "sql_where.toml"
        workflow_toml.write_text("""
[workflow]
name = "sql-where-test"

[inputs]
min_score = { type = "float", default = 0.5 }

[steps.query]
type = "sql"
[steps.query.config]
query = "SELECT * FROM test_data WHERE score >= {{min_score}}"
""")

        workflow = parse_workflow(workflow_toml)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={"min_score": 0.5},
            context=context
        )

        assert result.status == "completed"
        # Should return items with score >= 0.5 (item1=0.5, item2=0.8)
        assert len(result.step_results["query"].output_data) == 2

    @pytest.mark.asyncio
    async def test_select_with_limit(self, workflow_dir):
        """Test SELECT with LIMIT."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "sql_limit.toml"
        workflow_toml.write_text("""
[workflow]
name = "sql-limit-test"

[inputs]
limit = { type = "int", default = 2 }

[steps.query]
type = "sql"
[steps.query.config]
query = "SELECT * FROM test_data LIMIT {{limit:int}}"
""")

        workflow = parse_workflow(workflow_toml)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={"limit": 2},
            context=context
        )

        assert result.status == "completed"
        assert len(result.step_results["query"].output_data) == 2


# ============================================================================
# Write Tool E2E Tests
# ============================================================================


class TestWriteToolE2E:
    """E2E tests for Write tool in workflows."""

    @pytest.mark.asyncio
    async def test_insert_single_row(self, workflow_dir):
        """Test inserting a single row."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "write_insert.toml"
        workflow_toml.write_text("""
[workflow]
name = "write-insert-test"

[inputs]
name = { type = "string", required = true }
value = { type = "string", required = true }

[steps.write]
type = "write-db"
[steps.write.config]
table = "test_data"
mode = "insert"
""")

        workflow = parse_workflow(workflow_toml)
        context = ToolContext(db=db)

        # Input data is the workflow inputs for first step
        result = await execute_workflow(
            workflow,
            inputs={"id": 10, "name": "new_item", "value": "new_value", "score": 0.9},
            context=context
        )

        assert result.status == "completed"

        # Verify data was inserted
        query_result = db.query("SELECT * FROM test_data WHERE id = 10")
        assert len(query_result.rows) == 1
        assert query_result.rows[0]["name"] == "new_item"

    @pytest.mark.asyncio
    async def test_upsert_existing_row(self, workflow_dir):
        """Test upserting an existing row."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "write_upsert.toml"
        workflow_toml.write_text("""
[workflow]
name = "write-upsert-test"

[steps.write]
type = "write-db"
[steps.write.config]
table = "test_data"
mode = "upsert"
key = ["id"]
""")

        workflow = parse_workflow(workflow_toml)
        context = ToolContext(db=db)

        # Upsert existing id=1 with new value
        result = await execute_workflow(
            workflow,
            inputs={"id": 1, "name": "updated_item1", "value": "updated_value1", "score": 0.99},
            context=context
        )

        assert result.status == "completed"

        # Verify data was updated
        query_result = db.query("SELECT * FROM test_data WHERE id = 1")
        assert len(query_result.rows) == 1
        assert query_result.rows[0]["name"] == "updated_item1"
        assert query_result.rows[0]["score"] == 0.99


# ============================================================================
# Function Step E2E Tests
# ============================================================================


class TestFunctionStepE2E:
    """E2E tests for function steps in workflows."""

    @pytest.mark.asyncio
    async def test_simple_function(self, workflow_dir):
        """Test simple function execution."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "func_simple.toml"
        workflow_toml.write_text("""
[workflow]
name = "func-simple-test"

[inputs]
message = { type = "string", default = "hello" }

[steps.echo]
type = "function"
function = "echo"
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={"message": "test"},
            context=context,
            tools_path=workflows_dir / "tools.py",
        )

        assert result.status == "completed"
        output = result.step_results["echo"].output_data[0]
        assert output["inputs"]["message"] == "test"

    @pytest.mark.asyncio
    async def test_function_with_config(self, workflow_dir):
        """Test function with config parameters."""
        workflows_dir, db = workflow_dir

        # First read some data
        workflow_toml = workflows_dir / "func_config.toml"
        workflow_toml.write_text("""
[workflow]
name = "func-config-test"

[steps.read]
type = "sql"
[steps.read.config]
query = "SELECT * FROM test_data"

[steps.filter]
type = "function"
function = "filter_records"
depends_on = ["read"]
[steps.filter.config]
threshold = 0.6
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            tools_path=workflows_dir / "tools.py",
        )

        assert result.status == "completed"
        output = result.step_results["filter"].output_data[0]
        # Only item2 (score=0.8) should pass threshold 0.6
        assert output["kept"] == 1
        assert output["removed"] == 2

    @pytest.mark.asyncio
    async def test_chained_functions(self, workflow_dir):
        """Test chained function execution."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "func_chain.toml"
        workflow_toml.write_text("""
[workflow]
name = "func-chain-test"

[steps.read]
type = "sql"
[steps.read.config]
query = "SELECT * FROM test_data"

[steps.transform]
type = "function"
function = "transform_records"
depends_on = ["read"]
[steps.transform.config]
prefix = "chain_test"

[steps.stats]
type = "function"
function = "aggregate_stats"
depends_on = ["read"]
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            tools_path=workflows_dir / "tools.py",
        )

        assert result.status == "completed"

        # Check transform output
        transform_out = result.step_results["transform"].output_data[0]
        assert transform_out["count"] == 3

        # Check stats output
        stats_out = result.step_results["stats"].output_data[0]
        assert stats_out["total"] == 3
        # avg of 0.5, 0.8, 0.3 = 0.53
        assert 0.5 <= stats_out["avg_score"] <= 0.55


# ============================================================================
# Mixed Workflow E2E Tests
# ============================================================================


class TestMixedWorkflowE2E:
    """E2E tests for workflows mixing SQL, Write, and Function steps."""

    @pytest.mark.asyncio
    async def test_read_transform_write(self, workflow_dir):
        """Test complete ETL: read -> transform -> write."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "etl_full.toml"
        workflow_toml.write_text("""
[workflow]
name = "etl-full-test"
description = "Read, transform, and write data"

[steps.read]
type = "sql"
[steps.read.config]
query = "SELECT * FROM test_data WHERE score > 0.4 LIMIT 1"

[steps.transform]
type = "function"
function = "generate_write_data"
depends_on = ["read"]
[steps.transform.config]
id = 200

[steps.write]
type = "write-db"
depends_on = ["transform"]
[steps.write.config]
table = "results"
mode = "insert"
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            tools_path=workflows_dir / "tools.py",
        )

        assert result.status == "completed"
        assert result.step_results["read"].status == "completed"
        assert result.step_results["transform"].status == "completed"
        assert result.step_results["write"].status == "completed"

        # Verify data was written to results table
        query_result = db.query("SELECT * FROM results WHERE id = 200")
        assert len(query_result.rows) == 1
        assert "processed_" in query_result.rows[0]["processed_value"]

    @pytest.mark.asyncio
    async def test_parallel_functions(self, workflow_dir):
        """Test parallel function execution from same source."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "parallel_funcs.toml"
        workflow_toml.write_text("""
[workflow]
name = "parallel-funcs-test"

[steps.read]
type = "sql"
[steps.read.config]
query = "SELECT * FROM test_data"

[steps.transform]
type = "function"
function = "transform_records"
depends_on = ["read"]

[steps.stats]
type = "function"
function = "aggregate_stats"
depends_on = ["read"]

[steps.filter]
type = "function"
function = "filter_records"
depends_on = ["read"]
[steps.filter.config]
threshold = 0.5
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            tools_path=workflows_dir / "tools.py",
        )

        assert result.status == "completed"

        # All parallel steps should complete
        assert result.step_results["transform"].status == "completed"
        assert result.step_results["stats"].status == "completed"
        assert result.step_results["filter"].status == "completed"

    @pytest.mark.asyncio
    async def test_diamond_workflow(self, workflow_dir):
        """Test diamond pattern: read -> (A, B) -> merge."""
        workflows_dir, db = workflow_dir

        # Add a merge function to tools.py
        tools_py = workflows_dir / "tools.py"
        current_content = tools_py.read_text()
        tools_py.write_text(current_content + '''

def merge_results(context: dict[str, Any]) -> dict[str, Any]:
    """Merge results from multiple upstream steps."""
    input_data = context.get("input_data", [])

    # Collect all records from upstream
    all_records = []
    for item in input_data:
        if isinstance(item, dict):
            if "records" in item:
                all_records.extend(item["records"])
            elif "filtered" in item:
                all_records.extend(item["filtered"])
            else:
                all_records.append(item)

    return {
        "merged_count": len(all_records),
        "sources": len(input_data),
    }
''')

        workflow_toml = workflows_dir / "diamond.toml"
        workflow_toml.write_text("""
[workflow]
name = "diamond-test"

[steps.read]
type = "sql"
[steps.read.config]
query = "SELECT * FROM test_data"

[steps.transform]
type = "function"
function = "transform_records"
depends_on = ["read"]

[steps.filter]
type = "function"
function = "filter_records"
depends_on = ["read"]
[steps.filter.config]
threshold = 0.4

[steps.merge]
type = "function"
function = "merge_results"
depends_on = ["transform", "filter"]
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            tools_path=workflows_dir / "tools.py",
        )

        assert result.status == "completed"
        merge_out = result.step_results["merge"].output_data[0]
        assert merge_out["sources"] == 2  # transform + filter outputs


# ============================================================================
# Error Handling E2E Tests
# ============================================================================


class TestErrorHandlingE2E:
    """E2E tests for error handling in workflows."""

    @pytest.mark.asyncio
    async def test_sql_error_fails_workflow(self, workflow_dir):
        """Test that SQL errors fail the workflow."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "sql_error.toml"
        workflow_toml.write_text("""
[workflow]
name = "sql-error-test"

[steps.bad_query]
type = "sql"
[steps.bad_query.config]
query = "SELECT * FROM nonexistent_table"
""")

        workflow = parse_workflow(workflow_toml)
        context = ToolContext(db=db)
        result = await execute_workflow(workflow, inputs={}, context=context)

        assert result.status == "failed"
        assert result.step_results["bad_query"].status == "failed"

    @pytest.mark.asyncio
    async def test_function_error_fails_step(self, workflow_dir):
        """Test that function errors fail the step."""
        workflows_dir, db = workflow_dir

        # Add a failing function
        tools_py = workflows_dir / "tools.py"
        current_content = tools_py.read_text()
        tools_py.write_text(current_content + '''

def failing_function(context: dict[str, Any]) -> dict[str, Any]:
    """Function that always fails."""
    raise ValueError("Intentional failure for testing")
''')

        workflow_toml = workflows_dir / "func_error.toml"
        workflow_toml.write_text("""
[workflow]
name = "func-error-test"

[steps.fail]
type = "function"
function = "failing_function"
""")

        workflow = parse_workflow(workflow_toml, validate_tools=False)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            tools_path=workflows_dir / "tools.py",
        )

        assert result.status == "failed"
        assert result.step_results["fail"].status == "failed"
        assert "Intentional failure" in result.step_results["fail"].error

    @pytest.mark.asyncio
    async def test_continue_on_error(self, workflow_dir):
        """Test continue_on_error allows workflow to proceed."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "continue_error.toml"
        workflow_toml.write_text("""
[workflow]
name = "continue-error-test"

[steps.bad]
type = "sql"
continue_on_error = true
[steps.bad.config]
query = "SELECT * FROM nonexistent_table"

[steps.good]
type = "sql"
[steps.good.config]
query = "SELECT * FROM test_data LIMIT 1"
""")

        workflow = parse_workflow(workflow_toml)
        context = ToolContext(db=db)
        result = await execute_workflow(
            workflow,
            inputs={},
            context=context,
            continue_on_error=True,
        )

        # Workflow completes despite error in first step
        assert result.step_results["bad"].status == "failed"
        assert result.step_results["good"].status == "completed"


# ============================================================================
# CLI E2E Tests
# ============================================================================


class TestCLIE2E:
    """E2E tests for workflow CLI commands."""

    def test_cli_run_dry_run(self, workflow_dir):
        """Test CLI dry-run mode."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "cli_test.toml"
        workflow_toml.write_text("""
[workflow]
name = "cli-dry-run-test"

[inputs]
query = { type = "string", required = true }

[steps.read]
type = "sql"
[steps.read.config]
query = "{{query}}"
""")

        runner = CliRunner()
        from kurt.workflows.toml.cli import run_cmd

        result = runner.invoke(
            run_cmd,
            [str(workflow_toml), "--dry-run", "--input", "query=SELECT 1"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["dry_run"] is True
        assert output["valid"] is True

    def test_cli_run_validates_function_steps(self, workflow_dir):
        """Test CLI validates function steps exist."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "cli_func_test.toml"
        workflow_toml.write_text("""
[workflow]
name = "cli-func-validation-test"

[steps.process]
type = "function"
function = "echo"
""")

        runner = CliRunner()
        from kurt.workflows.toml.cli import run_cmd

        result = runner.invoke(
            run_cmd,
            [str(workflow_toml), "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["steps"]["process"]["validation"]["valid"] is True
        assert output["steps"]["process"]["validation"]["function"] == "echo"

    def test_cli_run_detects_missing_function(self, workflow_dir):
        """Test CLI detects missing function."""
        workflows_dir, db = workflow_dir

        workflow_toml = workflows_dir / "cli_missing_func.toml"
        workflow_toml.write_text("""
[workflow]
name = "cli-missing-func-test"

[steps.process]
type = "function"
function = "nonexistent_function"
""")

        runner = CliRunner()
        from kurt.workflows.toml.cli import run_cmd

        result = runner.invoke(
            run_cmd,
            [str(workflow_toml), "--dry-run"],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["steps"]["process"]["validation"]["valid"] is False
        assert "not found" in output["steps"]["process"]["validation"]["errors"][0]
