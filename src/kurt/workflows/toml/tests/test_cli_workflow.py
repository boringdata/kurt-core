"""
Tests for the workflow CLI commands (dry-run and test).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kurt.cli.workflow import run_cmd, test_cmd


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def sample_workflow(tmp_path: Path) -> Path:
    """Create a sample workflow TOML file."""
    workflow_content = """
[workflow]
name = "sample_pipeline"
description = "A sample test workflow"

[inputs.url]
type = "string"
required = true

[inputs.max_pages]
type = "int"
default = 100

[steps.discover]
type = "map"
config.source = "url"
config.url = "{{url}}"
config.max_pages = "{{max_pages}}"

[steps.fetch]
type = "fetch"
depends_on = ["discover"]
config.concurrency = 5

[steps.process]
type = "llm"
depends_on = ["fetch"]
config.model = "gpt-4"
config.prompt_template = "Process: {{content}}"
"""
    workflow_path = tmp_path / "sample.toml"
    workflow_path.write_text(workflow_content)
    return workflow_path


@pytest.fixture
def sample_fixtures(tmp_path: Path) -> Path:
    """Create sample fixture files."""
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()

    # discover.output.jsonl
    (fixtures_dir / "discover.output.jsonl").write_text(
        '{"url": "https://example.com/page1", "source_type": "page"}\n'
        '{"url": "https://example.com/page2", "source_type": "page"}\n'
    )

    # fetch.output.jsonl
    (fixtures_dir / "fetch.output.jsonl").write_text(
        '{"url": "https://example.com/page1", "content": "Content 1"}\n'
        '{"url": "https://example.com/page2", "content": "Content 2"}\n'
    )

    return fixtures_dir


# ============================================================================
# Dry-Run Tests
# ============================================================================


class TestRunDryRun:
    """Tests for kurt run --dry-run."""

    def test_dry_run_basic(self, cli_runner: CliRunner, sample_workflow: Path):
        """Basic dry-run outputs workflow info."""
        result = cli_runner.invoke(
            run_cmd,
            [str(sample_workflow), "--dry-run", "-i", "url=https://example.com"],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["workflow"] == "sample_pipeline"
        assert output["dry_run"] is True
        assert output["description"] == "A sample test workflow"

    def test_dry_run_shows_inputs(self, cli_runner: CliRunner, sample_workflow: Path):
        """Dry-run shows input validation."""
        result = cli_runner.invoke(
            run_cmd,
            [str(sample_workflow), "--dry-run", "-i", "url=https://example.com"],
        )

        output = json.loads(result.output)

        assert "inputs" in output
        assert "url" in output["inputs"]
        assert output["inputs"]["url"]["required"] is True
        assert output["inputs"]["url"]["provided"] is True
        assert output["inputs"]["url"]["value"] == "https://example.com"

        assert "max_pages" in output["inputs"]
        assert output["inputs"]["max_pages"]["default"] == 100
        assert output["inputs"]["max_pages"]["provided"] is False

    def test_dry_run_shows_execution_plan(self, cli_runner: CliRunner, sample_workflow: Path):
        """Dry-run shows execution plan from DAG builder."""
        result = cli_runner.invoke(
            run_cmd,
            [str(sample_workflow), "--dry-run", "-i", "url=https://example.com"],
        )

        output = json.loads(result.output)

        assert "execution_plan" in output
        plan = output["execution_plan"]

        assert "levels" in plan
        assert "total_steps" in plan
        assert plan["total_steps"] == 3
        assert "critical_path" in plan

    def test_dry_run_shows_step_validation(self, cli_runner: CliRunner, sample_workflow: Path):
        """Dry-run shows step config validation."""
        result = cli_runner.invoke(
            run_cmd,
            [str(sample_workflow), "--dry-run", "-i", "url=https://example.com"],
        )

        output = json.loads(result.output)

        assert "steps" in output
        assert "discover" in output["steps"]
        assert "fetch" in output["steps"]
        assert "process" in output["steps"]

        # Each step should have validation info
        discover = output["steps"]["discover"]
        assert "validation" in discover
        assert "valid" in discover["validation"]

    def test_dry_run_missing_input(self, cli_runner: CliRunner, sample_workflow: Path):
        """Dry-run detects missing required inputs."""
        result = cli_runner.invoke(
            run_cmd,
            [str(sample_workflow), "--dry-run"],  # Missing required 'url' input
        )

        output = json.loads(result.output)

        assert "missing_inputs" in output
        assert "url" in output["missing_inputs"]
        assert output["valid"] is False

    def test_dry_run_reports_overall_validity(self, cli_runner: CliRunner, sample_workflow: Path):
        """Dry-run reports overall workflow validity."""
        result = cli_runner.invoke(
            run_cmd,
            [str(sample_workflow), "--dry-run", "-i", "url=https://example.com"],
        )

        output = json.loads(result.output)

        assert "valid" in output
        # With URL provided and no cycle, should be valid
        # (tool validation may vary based on registered tools)


# ============================================================================
# Test Command Tests
# ============================================================================


class TestTestCommand:
    """Tests for kurt test command."""

    def test_test_basic(self, cli_runner: CliRunner, sample_workflow: Path, sample_fixtures: Path):
        """Basic test command runs successfully."""
        result = cli_runner.invoke(
            test_cmd,
            [
                str(sample_workflow),
                "--fixtures", str(sample_fixtures),
                "-i", "url=https://example.com",
                "--json",
            ],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["success"] is True
        assert output["workflow"] == "sample_pipeline"

    def test_test_shows_coverage(self, cli_runner: CliRunner, sample_workflow: Path, sample_fixtures: Path):
        """Test command shows fixture coverage."""
        result = cli_runner.invoke(
            test_cmd,
            [
                str(sample_workflow),
                "--fixtures", str(sample_fixtures),
                "-i", "url=https://example.com",
                "--json",
            ],
        )

        output = json.loads(result.output)

        assert "fixture_coverage" in output
        coverage = output["fixture_coverage"]

        # discover and fetch have fixtures
        assert "discover" in coverage["steps_with_fixtures"]
        assert "fetch" in coverage["steps_with_fixtures"]

        # process does not have fixture
        assert "process" in coverage["steps_without_fixtures"]

    def test_test_shows_step_details(self, cli_runner: CliRunner, sample_workflow: Path, sample_fixtures: Path):
        """Test command shows per-step details."""
        result = cli_runner.invoke(
            test_cmd,
            [
                str(sample_workflow),
                "--fixtures", str(sample_fixtures),
                "-i", "url=https://example.com",
                "--json",
            ],
        )

        output = json.loads(result.output)

        assert "steps" in output

        # discover has fixture
        discover = output["steps"]["discover"]
        assert discover["has_fixture"] is True
        assert discover["fixture_records"] == 2
        assert discover["would_execute"] is False

        # process does not have fixture
        process = output["steps"]["process"]
        assert process["has_fixture"] is False
        assert process["would_execute"] is True

    def test_test_missing_fixtures_dir(self, cli_runner: CliRunner, sample_workflow: Path, tmp_path: Path):
        """Test command fails for missing fixtures directory."""
        result = cli_runner.invoke(
            test_cmd,
            [
                str(sample_workflow),
                "--fixtures", str(tmp_path / "nonexistent"),
                "-i", "url=https://example.com",
            ],
        )

        # Should fail because fixtures dir doesn't exist
        assert result.exit_code != 0

    def test_test_strict_mode(self, cli_runner: CliRunner, sample_workflow: Path, sample_fixtures: Path):
        """Strict mode fails when fixtures are missing."""
        result = cli_runner.invoke(
            test_cmd,
            [
                str(sample_workflow),
                "--fixtures", str(sample_fixtures),
                "-i", "url=https://example.com",
                "--strict",
                "--json",
            ],
        )

        # Should fail because 'process' step has no fixture
        assert result.exit_code != 0

    def test_test_text_output(self, cli_runner: CliRunner, sample_workflow: Path, sample_fixtures: Path):
        """Test command produces readable text output."""
        result = cli_runner.invoke(
            test_cmd,
            [
                str(sample_workflow),
                "--fixtures", str(sample_fixtures),
                "-i", "url=https://example.com",
            ],
        )

        assert result.exit_code == 0
        assert "Workflow:" in result.output
        assert "Coverage:" in result.output
        assert "discover" in result.output
        assert "fetch" in result.output


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_workflow_with_cycle(self, cli_runner: CliRunner, tmp_path: Path):
        """Dry-run detects circular dependencies (caught at parse time)."""
        workflow_content = """
[workflow]
name = "cyclic"

[steps.a]
type = "map"
depends_on = ["c"]

[steps.b]
type = "fetch"
depends_on = ["a"]

[steps.c]
type = "llm"
depends_on = ["b"]
"""
        workflow_path = tmp_path / "cyclic.toml"
        workflow_path.write_text(workflow_content)

        result = cli_runner.invoke(
            run_cmd,
            [str(workflow_path), "--dry-run"],
        )

        # Circular dependency is caught at parse time, not dry-run
        assert result.exit_code != 0
        assert "Circular dependency" in result.output

    def test_empty_workflow(self, cli_runner: CliRunner, tmp_path: Path):
        """Dry-run handles empty workflow."""
        workflow_content = """
[workflow]
name = "empty"
description = "Empty workflow"
"""
        workflow_path = tmp_path / "empty.toml"
        workflow_path.write_text(workflow_content)

        result = cli_runner.invoke(
            run_cmd,
            [str(workflow_path), "--dry-run"],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)

        assert output["workflow"] == "empty"
        assert output["execution_plan"]["total_steps"] == 0

    def test_invalid_fixture_file(self, cli_runner: CliRunner, sample_workflow: Path, tmp_path: Path):
        """Test command handles invalid fixture files."""
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()

        # Create invalid JSONL
        (fixtures_dir / "discover.output.jsonl").write_text("not valid json\n")

        result = cli_runner.invoke(
            test_cmd,
            [
                str(sample_workflow),
                "--fixtures", str(fixtures_dir),
                "-i", "url=https://example.com",
                "--json",
            ],
        )

        # Invalid fixture file should cause an error
        assert result.exit_code != 0
        # Error message in output (may be JSON or text depending on where error occurs)
        assert "Invalid JSON" in result.output or "error" in result.output.lower()
