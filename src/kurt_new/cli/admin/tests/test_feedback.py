"""Tests for feedback CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from kurt_new.cli.admin import admin
from kurt_new.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestFeedbackGroup:
    """Tests for `admin feedback` command group."""

    def test_feedback_help(self, cli_runner: CliRunner):
        """Test feedback group shows help."""
        result = invoke_cli(cli_runner, admin, ["feedback", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Log feedback telemetry events")

    def test_feedback_list_commands(self, cli_runner: CliRunner):
        """Test feedback group lists all commands."""
        result = invoke_cli(cli_runner, admin, ["feedback", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "log-submission")


class TestLogSubmissionCommand:
    """Tests for `admin feedback log-submission` command."""

    def test_log_submission_help(self, cli_runner: CliRunner):
        """Test log-submission command shows help."""
        result = invoke_cli(cli_runner, admin, ["feedback", "log-submission", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Log a feedback submission event")

    def test_log_submission_shows_options(self, cli_runner: CliRunner):
        """Test log-submission command lists options in help."""
        result = invoke_cli(cli_runner, admin, ["feedback", "log-submission", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--rating")
        assert_output_contains(result, "--has-comment")
        assert_output_contains(result, "--issue-category")
        assert_output_contains(result, "--event-id")

    def test_log_submission_issue_categories(self, cli_runner: CliRunner):
        """Test log-submission lists valid issue categories."""
        result = invoke_cli(cli_runner, admin, ["feedback", "log-submission", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "tone")
        assert_output_contains(result, "structure")
        assert_output_contains(result, "info")
