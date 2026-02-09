"""Tests for Kurt skill CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from kurt.cli.skill import install_openclaw, skill, skill_status, uninstall_openclaw


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def skill_dir(tmp_path):
    return tmp_path / ".claude" / "skills" / "kurt"


class TestInstallOpenclaw:
    def test_installs_skill(self, runner, skill_dir):
        """Install creates skill files."""
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            result = runner.invoke(install_openclaw)

        assert result.exit_code == 0
        assert "installed successfully" in result.output
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "skill.py").exists()
        assert (skill_dir / "README.md").exists()

    def test_shows_next_steps(self, runner, skill_dir):
        """Install shows helpful next steps."""
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            result = runner.invoke(install_openclaw)

        assert "/kurt fetch" in result.output
        assert "/kurt map" in result.output
        assert "/kurt tool list" in result.output

    def test_dry_run(self, runner, skill_dir):
        """--dry-run shows what would happen without creating files."""
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            result = runner.invoke(install_openclaw, ["--dry-run"])

        assert result.exit_code == 0
        assert "Would create" in result.output
        assert not skill_dir.exists()

    def test_force_overwrites(self, runner, skill_dir):
        """--force overwrites existing installation."""
        # First install
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            runner.invoke(install_openclaw)

            # Modify a file
            (skill_dir / "SKILL.md").write_text("modified")

            # Force reinstall
            result = runner.invoke(install_openclaw, ["--force"])

        assert result.exit_code == 0
        content = (skill_dir / "SKILL.md").read_text()
        assert "modified" not in content

    def test_prompts_if_exists(self, runner, skill_dir):
        """Prompts for confirmation if already installed."""
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            runner.invoke(install_openclaw)

            # Decline overwrite
            result = runner.invoke(install_openclaw, input="n\n")

        assert result.exit_code != 0  # Aborted


class TestUninstallOpenclaw:
    def test_removes_skill(self, runner, skill_dir):
        """Uninstall removes skill directory."""
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            runner.invoke(install_openclaw)
            assert skill_dir.exists()

            result = runner.invoke(uninstall_openclaw, input="y\n")

        assert result.exit_code == 0
        assert "removed" in result.output
        assert not skill_dir.exists()

    def test_not_installed(self, runner, skill_dir):
        """Shows message if not installed."""
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            result = runner.invoke(uninstall_openclaw)

        assert result.exit_code == 0
        assert "not installed" in result.output


class TestSkillStatus:
    def test_installed(self, runner, skill_dir):
        """Shows installed status."""
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            runner.invoke(install_openclaw)
            result = runner.invoke(skill_status)

        assert result.exit_code == 0
        assert "installed" in result.output
        assert "SKILL.md" in result.output

    def test_not_installed(self, runner, skill_dir):
        """Shows not installed status."""
        with patch(
            "kurt.cli.skill.Path.home", return_value=skill_dir.parent.parent.parent
        ):
            result = runner.invoke(skill_status)

        assert result.exit_code == 0
        assert "not installed" in result.output
        assert "install-openclaw" in result.output


class TestSkillGroup:
    def test_skill_group_help(self, runner):
        """Skill group shows help."""
        result = runner.invoke(skill, ["--help"])
        assert result.exit_code == 0
        assert "install-openclaw" in result.output
        assert "uninstall-openclaw" in result.output
        assert "status" in result.output
