"""
E2E tests for `kurt admin` commands.

These tests verify admin commands work correctly including
telemetry management and feedback logging.
"""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestAdminHelp:
    """Tests for admin command help."""

    def test_admin_help(self, cli_runner: CliRunner):
        """Verify admin group shows help."""
        from kurt.admin.cli import admin

        result = invoke_cli(cli_runner, admin, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Administrative commands")

    def test_telemetry_help(self, cli_runner: CliRunner):
        """Verify telemetry group shows help."""
        from kurt.admin.cli import admin

        result = invoke_cli(cli_runner, admin, ["telemetry", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "telemetry")

    def test_feedback_help(self, cli_runner: CliRunner):
        """Verify feedback group shows help."""
        from kurt.admin.cli import admin

        result = invoke_cli(cli_runner, admin, ["feedback", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "feedback")


class TestTelemetryStatus:
    """E2E tests for telemetry status command."""

    @patch("kurt.admin.telemetry.config.get_telemetry_status")
    def test_telemetry_status_enabled(self, mock_status, cli_runner: CliRunner):
        """Verify telemetry status shows enabled state."""
        from kurt.admin.cli import admin

        mock_status.return_value = {
            "enabled": True,
            "disabled_reason": None,
            "config_path": "~/.config/kurt/telemetry.json",
            "machine_id": "test-machine-id-123",
            "is_ci": False,
        }

        result = invoke_cli(cli_runner, admin, ["telemetry", "status"])
        assert_cli_success(result)
        assert_output_contains(result, "Enabled")

    @patch("kurt.admin.telemetry.config.get_telemetry_status")
    def test_telemetry_status_disabled(self, mock_status, cli_runner: CliRunner):
        """Verify telemetry status shows disabled state."""
        from kurt.admin.cli import admin

        mock_status.return_value = {
            "enabled": False,
            "disabled_reason": "user",
            "config_path": "~/.config/kurt/telemetry.json",
            "machine_id": None,
            "is_ci": False,
        }

        result = invoke_cli(cli_runner, admin, ["telemetry", "status"])
        assert_cli_success(result)
        assert_output_contains(result, "Disabled")


class TestTelemetryEnable:
    """E2E tests for telemetry enable command."""

    @patch("kurt.admin.telemetry.config.set_telemetry_enabled")
    @patch("kurt.admin.telemetry.config.is_telemetry_enabled")
    def test_telemetry_enable(self, mock_is_enabled, mock_set, cli_runner: CliRunner):
        """Verify telemetry enable command works."""
        from kurt.admin.cli import admin

        mock_is_enabled.return_value = False

        result = invoke_cli(cli_runner, admin, ["telemetry", "enable"])
        assert_cli_success(result)
        assert_output_contains(result, "enabled")
        mock_set.assert_called_once_with(True)

    @patch("kurt.admin.telemetry.config.is_telemetry_enabled")
    def test_telemetry_enable_already_enabled(self, mock_is_enabled, cli_runner: CliRunner):
        """Verify telemetry enable shows message when already enabled."""
        from kurt.admin.cli import admin

        mock_is_enabled.return_value = True

        result = invoke_cli(cli_runner, admin, ["telemetry", "enable"])
        assert_cli_success(result)
        assert_output_contains(result, "already enabled")


class TestTelemetryDisable:
    """E2E tests for telemetry disable command."""

    @patch("kurt.admin.telemetry.config.set_telemetry_enabled")
    @patch("kurt.admin.telemetry.config.is_telemetry_enabled")
    def test_telemetry_disable(self, mock_is_enabled, mock_set, cli_runner: CliRunner):
        """Verify telemetry disable command works."""
        from kurt.admin.cli import admin

        mock_is_enabled.return_value = True

        result = invoke_cli(cli_runner, admin, ["telemetry", "disable"])
        assert_cli_success(result)
        assert_output_contains(result, "disabled")
        mock_set.assert_called_once_with(False)

    @patch("kurt.admin.telemetry.config.is_telemetry_enabled")
    def test_telemetry_disable_already_disabled(self, mock_is_enabled, cli_runner: CliRunner):
        """Verify telemetry disable shows message when already disabled."""
        from kurt.admin.cli import admin

        mock_is_enabled.return_value = False

        result = invoke_cli(cli_runner, admin, ["telemetry", "disable"])
        assert_cli_success(result)
        assert_output_contains(result, "already disabled")


class TestFeedbackLogSubmission:
    """E2E tests for feedback log-submission command."""

    @patch("kurt.admin.telemetry.feedback_tracker.track_feedback_submitted")
    def test_feedback_log_submission(self, mock_track, cli_runner: CliRunner):
        """Verify feedback log-submission command works."""
        from kurt.admin.cli import admin

        result = invoke_cli(
            cli_runner,
            admin,
            [
                "feedback",
                "log-submission",
                "--rating",
                "4",
                "--event-id",
                "test-123",
            ],
        )
        assert_cli_success(result)
        assert_output_contains(result, "Logged feedback")
        mock_track.assert_called_once()

    @patch("kurt.admin.telemetry.feedback_tracker.track_feedback_submitted")
    def test_feedback_log_submission_with_category(self, mock_track, cli_runner: CliRunner):
        """Verify feedback log-submission with issue category."""
        from kurt.admin.cli import admin

        result = invoke_cli(
            cli_runner,
            admin,
            [
                "feedback",
                "log-submission",
                "--rating",
                "2",
                "--issue-category",
                "tone",
                "--event-id",
                "test-456",
            ],
        )
        assert_cli_success(result)
        mock_track.assert_called_once_with(
            rating=2,
            has_comment=False,
            issue_category="tone",
        )

    @patch("kurt.admin.telemetry.feedback_tracker.track_feedback_submitted")
    def test_feedback_log_submission_with_comment(self, mock_track, cli_runner: CliRunner):
        """Verify feedback log-submission with has-comment flag."""
        from kurt.admin.cli import admin

        result = invoke_cli(
            cli_runner,
            admin,
            [
                "feedback",
                "log-submission",
                "--rating",
                "5",
                "--has-comment",
                "--event-id",
                "test-789",
            ],
        )
        assert_cli_success(result)
        mock_track.assert_called_once_with(
            rating=5,
            has_comment=True,
            issue_category=None,
        )

    def test_feedback_log_submission_missing_required(self, cli_runner: CliRunner):
        """Verify feedback log-submission fails without required args."""
        from kurt.admin.cli import admin

        # Missing --rating
        result = invoke_cli(
            cli_runner,
            admin,
            ["feedback", "log-submission", "--event-id", "test"],
        )
        assert result.exit_code != 0

        # Missing --event-id
        result = invoke_cli(
            cli_runner,
            admin,
            ["feedback", "log-submission", "--rating", "3"],
        )
        assert result.exit_code != 0

    def test_feedback_log_submission_invalid_rating(self, cli_runner: CliRunner):
        """Verify feedback log-submission rejects invalid rating."""
        from kurt.admin.cli import admin

        result = invoke_cli(
            cli_runner,
            admin,
            [
                "feedback",
                "log-submission",
                "--rating",
                "not-a-number",
                "--event-id",
                "test",
            ],
        )
        assert result.exit_code != 0

    def test_feedback_log_submission_invalid_category(self, cli_runner: CliRunner):
        """Verify feedback log-submission rejects invalid category."""
        from kurt.admin.cli import admin

        result = invoke_cli(
            cli_runner,
            admin,
            [
                "feedback",
                "log-submission",
                "--rating",
                "3",
                "--issue-category",
                "invalid-category",
                "--event-id",
                "test",
            ],
        )
        assert result.exit_code != 0


class TestAdminFromMainCLI:
    """E2E tests for accessing admin through main CLI."""

    def test_admin_accessible_from_main(self, cli_runner: CliRunner):
        """Verify admin command is accessible from main CLI."""
        from kurt.cli.main import main

        result = cli_runner.invoke(main, ["admin", "--help"], catch_exceptions=False)
        assert_cli_success(result)
        assert_output_contains(result, "Administrative")

    def test_telemetry_accessible_from_main(self, cli_runner: CliRunner):
        """Verify telemetry subcommand is accessible from main CLI."""
        from kurt.cli.main import main

        result = cli_runner.invoke(
            main, ["admin", "telemetry", "--help"], catch_exceptions=False
        )
        assert_cli_success(result)
        assert_output_contains(result, "telemetry")
