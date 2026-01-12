"""Tests for feedback CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from kurt.cli.admin import admin
from kurt.core.tests.conftest import (
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

    def test_log_submission_with_required_args(self, cli_runner: CliRunner, tmp_project):
        """Test log-submission command with required arguments.

        This test catches bugs where arguments are passed incorrectly to
        track_feedback_submitted().
        """
        result = invoke_cli(
            cli_runner,
            admin,
            ["feedback", "log-submission", "--rating", "4", "--event-id", "test-event-123"],
        )
        assert_cli_success(result)
        assert_output_contains(result, "test-event-123")

    def test_log_submission_with_all_args(self, cli_runner: CliRunner, tmp_project):
        """Test log-submission command with all arguments."""
        result = invoke_cli(
            cli_runner,
            admin,
            [
                "feedback",
                "log-submission",
                "--rating",
                "2",
                "--has-comment",
                "--issue-category",
                "tone",
                "--event-id",
                "test-event-456",
            ],
        )
        assert_cli_success(result)
        assert_output_contains(result, "test-event-456")

    def test_log_submission_requires_rating(self, cli_runner: CliRunner):
        """Test log-submission command requires --rating option."""
        result = cli_runner.invoke(admin, ["feedback", "log-submission", "--event-id", "test-123"])
        assert result.exit_code != 0
        assert "rating" in result.output.lower()

    def test_log_submission_requires_event_id(self, cli_runner: CliRunner):
        """Test log-submission command requires --event-id option."""
        result = cli_runner.invoke(admin, ["feedback", "log-submission", "--rating", "3"])
        assert result.exit_code != 0
        assert "event-id" in result.output.lower()

    def test_log_submission_validates_issue_category(self, cli_runner: CliRunner):
        """Test log-submission rejects invalid issue categories."""
        result = cli_runner.invoke(
            admin,
            [
                "feedback",
                "log-submission",
                "--rating",
                "3",
                "--event-id",
                "test-123",
                "--issue-category",
                "invalid_category",
            ],
        )
        assert result.exit_code != 0
