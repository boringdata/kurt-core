"""Tests for workflow CLI utilities."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner
from rich.console import Console

from kurt.workflows.core.cli import (
    OutputFormat,
    StatusColor,
    add_workflow_list_options,
    add_workflow_run_options,
    console,
    create_run_history_table,
    create_status_table,
    create_workflow_table,
    display_empty_result,
    display_not_found,
    display_validation_errors,
    display_validation_success,
    display_workflow_completed,
    display_workflow_started,
    foreground_option,
    format_count,
    format_duration,
    format_status,
    input_option,
    parse_input_value,
    parse_inputs,
    print_error,
    print_info,
    print_json_output,
    print_success,
    print_warning,
    scheduled_option,
    tag_option,
    validate_input_format,
    workflow_format_option,
)


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_output_format_values(self):
        """Test OutputFormat enum values."""
        assert OutputFormat.JSON == "json"
        assert OutputFormat.TEXT == "text"
        assert OutputFormat.TABLE == "table"

    def test_output_format_is_string(self):
        """Test OutputFormat is a string enum."""
        assert isinstance(OutputFormat.JSON, str)


class TestStatusColor:
    """Tests for StatusColor enum."""

    def test_status_color_values(self):
        """Test StatusColor enum values."""
        assert StatusColor.COMPLETED == "green"
        assert StatusColor.SUCCESS == "green"
        assert StatusColor.RUNNING == "yellow"
        assert StatusColor.PENDING == "dim"
        assert StatusColor.FAILED == "red"
        assert StatusColor.ERROR == "red"
        assert StatusColor.CANCELED == "yellow"


class TestParseInputValue:
    """Tests for parse_input_value function."""

    def test_parse_string(self):
        """Test parsing plain strings."""
        assert parse_input_value("hello") == "hello"
        assert parse_input_value("hello world") == "hello world"

    def test_parse_boolean_true(self):
        """Test parsing true boolean strings."""
        assert parse_input_value("true") is True
        assert parse_input_value("True") is True
        assert parse_input_value("TRUE") is True

    def test_parse_boolean_false(self):
        """Test parsing false boolean strings."""
        assert parse_input_value("false") is False
        assert parse_input_value("False") is False
        assert parse_input_value("FALSE") is False

    def test_parse_integer(self):
        """Test parsing integers."""
        assert parse_input_value("42") == 42
        assert parse_input_value("0") == 0
        assert parse_input_value("-10") == -10

    def test_parse_float(self):
        """Test parsing floats."""
        assert parse_input_value("3.14") == 3.14
        assert parse_input_value("-0.5") == -0.5

    def test_parse_json_array(self):
        """Test parsing JSON arrays."""
        assert parse_input_value('["a", "b", "c"]') == ["a", "b", "c"]
        assert parse_input_value("[1, 2, 3]") == [1, 2, 3]

    def test_parse_json_object(self):
        """Test parsing JSON objects."""
        assert parse_input_value('{"key": "value"}') == {"key": "value"}

    def test_parse_json_boolean(self):
        """Test JSON booleans (lowercase only in JSON)."""
        assert parse_input_value("true") is True  # Also matches string parsing


class TestParseInputs:
    """Tests for parse_inputs function."""

    def test_parse_empty(self):
        """Test parsing empty inputs."""
        assert parse_inputs(()) == {}

    def test_parse_single_input(self):
        """Test parsing single input."""
        assert parse_inputs(("key=value",)) == {"key": "value"}

    def test_parse_multiple_inputs(self):
        """Test parsing multiple inputs."""
        result = parse_inputs(("topic=AI", "count=5", "enabled=true"))
        assert result == {"topic": "AI", "count": 5, "enabled": True}

    def test_parse_json_input(self):
        """Test parsing JSON values in inputs."""
        result = parse_inputs(('tags=["a","b"]',))
        assert result == {"tags": ["a", "b"]}

    def test_parse_empty_key_skipped(self):
        """Test that empty keys are skipped."""
        result = parse_inputs(("=value", "key=value"))
        assert result == {"key": "value"}

    def test_parse_value_with_equals(self):
        """Test parsing values containing equals sign."""
        result = parse_inputs(("url=https://example.com?foo=bar",))
        assert result == {"url": "https://example.com?foo=bar"}


class TestValidateInputFormat:
    """Tests for validate_input_format callback."""

    def test_valid_input(self):
        """Test valid key=value input."""
        key, value = validate_input_format(None, None, "topic=AI")
        assert key == "topic"
        assert value == "AI"

    def test_valid_input_with_spaces(self):
        """Test input with spaces around key/value."""
        key, value = validate_input_format(None, None, " topic = AI ")
        assert key == "topic"
        assert value == "AI"

    def test_invalid_input_no_equals(self):
        """Test invalid input without equals sign."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_input_format(None, None, "invalid")
        assert "key=value format" in str(exc_info.value)


class TestFormatStatus:
    """Tests for format_status function."""

    def test_format_completed(self):
        """Test formatting completed status."""
        result = format_status("completed")
        assert "[green]" in result
        assert "completed" in result

    def test_format_running(self):
        """Test formatting running status."""
        result = format_status("running")
        assert "[yellow]" in result
        assert "running" in result

    def test_format_failed(self):
        """Test formatting failed status."""
        result = format_status("failed")
        assert "[red]" in result
        assert "failed" in result

    def test_format_pending(self):
        """Test formatting pending status."""
        result = format_status("pending")
        assert "[dim]" in result
        assert "pending" in result

    def test_format_unknown_status(self):
        """Test formatting unknown status uses white."""
        result = format_status("unknown")
        assert "[white]" in result

    def test_format_case_insensitive(self):
        """Test status formatting is case insensitive."""
        result = format_status("COMPLETED")
        assert "[green]" in result


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_format_none(self):
        """Test formatting None duration."""
        assert format_duration(None) == "-"

    def test_format_seconds(self):
        """Test formatting seconds."""
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_format_minutes(self):
        """Test formatting minutes."""
        assert format_duration(60) == "1.0m"
        assert format_duration(150) == "2.5m"

    def test_format_hours(self):
        """Test formatting hours."""
        assert format_duration(3600) == "1.0h"
        assert format_duration(5400) == "1.5h"


class TestFormatCount:
    """Tests for format_count function."""

    def test_format_none(self):
        """Test formatting None count."""
        assert format_count(None) == "-"

    def test_format_small_number(self):
        """Test formatting small numbers."""
        assert format_count(42) == "42"

    def test_format_large_number(self):
        """Test formatting large numbers with commas."""
        assert format_count(1000) == "1,000"
        assert format_count(1234567) == "1,234,567"


class TestPrintFunctions:
    """Tests for print helper functions."""

    def test_print_json_output(self, capsys):
        """Test print_json_output produces valid JSON."""
        data = {"key": "value", "count": 42}
        print_json_output(data)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == data

    def test_print_json_output_with_dates(self, capsys):
        """Test print_json_output handles non-serializable types."""
        from datetime import datetime

        data = {"timestamp": datetime(2024, 1, 15, 10, 30)}
        print_json_output(data)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert "2024-01-15" in parsed["timestamp"]


class TestTableCreation:
    """Tests for table creation helpers."""

    def test_create_workflow_table(self):
        """Test creating workflow table."""
        table = create_workflow_table("Test Title")
        assert table.title == "Test Title"
        column_names = [c.header for c in table.columns]
        assert "Name" in column_names
        assert "Title" in column_names
        assert "Schedule" in column_names
        assert "Tags" in column_names

    def test_create_workflow_table_no_title(self):
        """Test creating workflow table without title."""
        table = create_workflow_table()
        assert table.title is None

    def test_create_status_table(self):
        """Test creating status table."""
        table = create_status_table("Status")
        assert table.title == "Status"
        assert table.box is None
        assert table.show_edge is False

    def test_create_run_history_table(self):
        """Test creating run history table."""
        table = create_run_history_table("History")
        assert table.title == "History"
        column_names = [c.header for c in table.columns]
        assert "Run ID" in column_names
        assert "Status" in column_names
        assert "Started" in column_names
        assert "Duration" in column_names
        assert "Trigger" in column_names


class TestClickOptions:
    """Tests for Click option decorators."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI runner."""
        return CliRunner()

    def test_foreground_option(self, cli_runner):
        """Test foreground option."""

        @click.command()
        @foreground_option
        def cmd(foreground):
            click.echo(f"foreground={foreground}")

        result = cli_runner.invoke(cmd, ["--foreground"])
        assert result.exit_code == 0
        assert "foreground=True" in result.output

        result = cli_runner.invoke(cmd, ["-f"])
        assert result.exit_code == 0
        assert "foreground=True" in result.output

    def test_input_option(self, cli_runner):
        """Test input option (multiple)."""

        @click.command()
        @input_option
        def cmd(inputs):
            click.echo(f"inputs={inputs}")

        result = cli_runner.invoke(cmd, ["-i", "a=1", "-i", "b=2"])
        assert result.exit_code == 0
        assert "('a=1', 'b=2')" in result.output

    def test_tag_option(self, cli_runner):
        """Test tag option."""

        @click.command()
        @tag_option
        def cmd(tag):
            click.echo(f"tag={tag}")

        result = cli_runner.invoke(cmd, ["--tag", "automation"])
        assert result.exit_code == 0
        assert "tag=automation" in result.output

    def test_scheduled_option(self, cli_runner):
        """Test scheduled option."""

        @click.command()
        @scheduled_option
        def cmd(scheduled):
            click.echo(f"scheduled={scheduled}")

        result = cli_runner.invoke(cmd, ["--scheduled"])
        assert result.exit_code == 0
        assert "scheduled=True" in result.output

    def test_workflow_format_option(self, cli_runner):
        """Test workflow format option."""

        @click.command()
        @workflow_format_option
        def cmd(output_format):
            click.echo(f"format={output_format}")

        result = cli_runner.invoke(cmd, ["--format", "json"])
        assert result.exit_code == 0
        assert "format=json" in result.output

    def test_add_workflow_list_options(self, cli_runner):
        """Test composed workflow list options decorator."""

        @click.command()
        @add_workflow_list_options()
        def cmd(tag, scheduled):
            click.echo(f"tag={tag},scheduled={scheduled}")

        result = cli_runner.invoke(cmd, ["--tag", "test", "--scheduled"])
        assert result.exit_code == 0
        assert "tag=test" in result.output
        assert "scheduled=True" in result.output

    def test_add_workflow_run_options(self, cli_runner):
        """Test composed workflow run options decorator."""

        @click.command()
        @add_workflow_run_options()
        def cmd(inputs, foreground):
            click.echo(f"inputs={inputs},foreground={foreground}")

        result = cli_runner.invoke(cmd, ["-i", "key=val", "-f"])
        assert result.exit_code == 0
        assert "inputs=('key=val',)" in result.output
        assert "foreground=True" in result.output


class TestDisplayFunctions:
    """Tests for display helper functions."""

    def test_display_not_found_aborts(self):
        """Test display_not_found raises Abort."""
        with pytest.raises(click.Abort):
            display_not_found("Workflow", "my-workflow")

    def test_display_validation_errors_aborts(self):
        """Test display_validation_errors raises Abort."""
        with pytest.raises(click.Abort):
            display_validation_errors(["Error 1", "Error 2"])


class TestConsoleExport:
    """Test that console is properly exported."""

    def test_console_is_rich_console(self):
        """Test console is a Rich Console instance."""
        assert isinstance(console, Console)
