"""Tests for init CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.cli.init import (
    _check_config_exists,
    _check_dolt_repo,
    _check_git_repo,
    _check_hooks_installed,
    _check_workflows_dir,
    _create_config,
    _create_content_dir,
    _create_workflows_dir,
    _detect_partial_init,
    _update_gitignore,
    init,
)
from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


class TestInitCommand:
    """Tests for `kurt init` command help and options."""

    def test_init_help(self, cli_runner: CliRunner):
        """Test init command shows help."""
        result = invoke_cli(cli_runner, init, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Initialize a new Kurt project")

    def test_init_shows_options(self, cli_runner: CliRunner):
        """Test init command lists options in help."""
        result = invoke_cli(cli_runner, init, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--no-dolt")
        assert_output_contains(result, "--no-hooks")
        assert_output_contains(result, "--force")

    def test_init_shows_path_argument(self, cli_runner: CliRunner):
        """Test init command shows path argument in help."""
        result = invoke_cli(cli_runner, init, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "PATH")


@pytest.fixture
def cli_runner_isolated(cli_runner: CliRunner):
    """CLI runner with isolated filesystem."""
    with cli_runner.isolated_filesystem():
        yield cli_runner


class TestCheckFunctions:
    """Tests for detection helper functions."""

    def test_check_git_repo_false(self, cli_runner_isolated):
        """Test _check_git_repo returns False when not a git repo."""
        assert _check_git_repo() is False

    def test_check_git_repo_true(self, cli_runner_isolated):
        """Test _check_git_repo returns True when git repo exists."""
        (Path.cwd() / ".git").mkdir()
        assert _check_git_repo() is True

    def test_check_dolt_repo_false(self, cli_runner_isolated):
        """Test _check_dolt_repo returns False when not a dolt repo."""
        assert _check_dolt_repo() is False

    def test_check_dolt_repo_true(self, cli_runner_isolated):
        """Test _check_dolt_repo returns True when dolt repo exists."""
        (Path.cwd() / ".dolt").mkdir()
        assert _check_dolt_repo() is True

    def test_check_config_exists_false(self, cli_runner_isolated):
        """Test _check_config_exists returns False when no config."""
        assert _check_config_exists() is False

    def test_check_config_exists_toml(self, cli_runner_isolated):
        """Test _check_config_exists returns True with kurt.toml."""
        (Path.cwd() / "kurt.toml").write_text("")
        assert _check_config_exists() is True

    def test_check_config_exists_config(self, cli_runner_isolated):
        """Test _check_config_exists returns True with kurt.config."""
        (Path.cwd() / "kurt.config").write_text("")
        assert _check_config_exists() is True

    def test_check_workflows_dir_false(self, cli_runner_isolated):
        """Test _check_workflows_dir returns False when no directory."""
        assert _check_workflows_dir() is False

    def test_check_workflows_dir_true(self, cli_runner_isolated):
        """Test _check_workflows_dir returns True when directory exists."""
        (Path.cwd() / "workflows").mkdir()
        assert _check_workflows_dir() is True

    def test_check_hooks_installed_no_git(self, cli_runner_isolated):
        """Test _check_hooks_installed returns False without .git."""
        assert _check_hooks_installed() is False

    def test_check_hooks_installed_no_hooks(self, cli_runner_isolated):
        """Test _check_hooks_installed returns False without hooks."""
        (Path.cwd() / ".git" / "hooks").mkdir(parents=True)
        assert _check_hooks_installed() is False

    def test_check_hooks_installed_with_kurt_hook(self, cli_runner_isolated):
        """Test _check_hooks_installed returns True with Kurt hook."""
        hooks_dir = Path.cwd() / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook = hooks_dir / "post-commit"
        hook.write_text("#!/bin/bash\n# Kurt Git Hook\necho 'hello'")
        assert _check_hooks_installed() is True

    def test_check_hooks_installed_with_non_kurt_hook(self, cli_runner_isolated):
        """Test _check_hooks_installed returns False with non-Kurt hook."""
        hooks_dir = Path.cwd() / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook = hooks_dir / "post-commit"
        hook.write_text("#!/bin/bash\necho 'hello'")
        assert _check_hooks_installed() is False


class TestDetectPartialInit:
    """Tests for _detect_partial_init function."""

    def test_detect_empty_directory(self, cli_runner_isolated):
        """Test detection in empty directory."""
        status = _detect_partial_init()
        assert status == {
            "git": False,
            "dolt": False,
            "config": False,
            "workflows": False,
            "hooks": False,
        }

    def test_detect_git_only(self, cli_runner_isolated):
        """Test detection with only Git initialized."""
        (Path.cwd() / ".git").mkdir()
        status = _detect_partial_init()
        assert status["git"] is True
        assert status["dolt"] is False

    def test_detect_full_init(self, cli_runner_isolated):
        """Test detection with all components."""
        (Path.cwd() / ".git" / "hooks").mkdir(parents=True)
        (Path.cwd() / ".dolt").mkdir()
        (Path.cwd() / "kurt.toml").write_text("")
        (Path.cwd() / "workflows").mkdir()

        # Add Kurt hook
        hook = Path.cwd() / ".git" / "hooks" / "post-commit"
        hook.write_text("#!/bin/bash\n# Kurt Git Hook\necho 'hello'")

        status = _detect_partial_init()
        assert all(status.values())


class TestCreateConfig:
    """Tests for _create_config function."""

    def test_creates_kurt_toml(self, cli_runner_isolated):
        """Test config file creation."""
        assert _create_config() is True
        assert (Path.cwd() / "kurt.toml").exists()

    def test_config_has_workspace_id(self, cli_runner_isolated):
        """Test config includes workspace_id."""
        _create_config()
        content = (Path.cwd() / "kurt.toml").read_text()
        assert "workspace_id" in content

    def test_config_has_paths(self, cli_runner_isolated):
        """Test config includes paths section."""
        _create_config()
        content = (Path.cwd() / "kurt.toml").read_text()
        assert "[paths]" in content
        assert 'workflows = "workflows"' in content
        assert 'content = "content"' in content

    def test_config_has_indexing(self, cli_runner_isolated):
        """Test config includes indexing section."""
        _create_config()
        content = (Path.cwd() / "kurt.toml").read_text()
        assert "[indexing]" in content
        assert "llm_model" in content
        assert "embedding_model" in content

    def test_config_skips_if_exists(self, cli_runner_isolated):
        """Test config creation skips if file exists."""
        (Path.cwd() / "kurt.toml").write_text("existing content")
        assert _create_config() is True
        assert (Path.cwd() / "kurt.toml").read_text() == "existing content"


class TestCreateWorkflowsDir:
    """Tests for _create_workflows_dir function."""

    def test_creates_workflows_directory(self, cli_runner_isolated):
        """Test workflows directory creation."""
        assert _create_workflows_dir() is True
        assert (Path.cwd() / "workflows").is_dir()

    def test_creates_example_workflow(self, cli_runner_isolated):
        """Test example workflow file is created."""
        _create_workflows_dir()
        example = Path.cwd() / "workflows" / "example.md"
        assert example.exists()

    def test_example_workflow_content(self, cli_runner_isolated):
        """Test example workflow has valid content."""
        _create_workflows_dir()
        content = (Path.cwd() / "workflows" / "example.md").read_text()
        assert "---" in content  # Has frontmatter
        assert "name: example" in content
        assert "agent:" in content
        assert "guardrails:" in content

    def test_skips_existing_example(self, cli_runner_isolated):
        """Test example workflow not overwritten if exists."""
        (Path.cwd() / "workflows").mkdir()
        example = Path.cwd() / "workflows" / "example.md"
        example.write_text("custom content")

        _create_workflows_dir()
        assert example.read_text() == "custom content"


class TestCreateContentDir:
    """Tests for _create_content_dir function."""

    def test_creates_content_directory(self, cli_runner_isolated):
        """Test content directory creation."""
        assert _create_content_dir() is True
        assert (Path.cwd() / "content").is_dir()

    def test_idempotent(self, cli_runner_isolated):
        """Test content directory creation is idempotent."""
        (Path.cwd() / "content").mkdir()
        (Path.cwd() / "content" / "file.txt").write_text("test")

        assert _create_content_dir() is True
        assert (Path.cwd() / "content" / "file.txt").exists()


class TestUpdateGitignore:
    """Tests for _update_gitignore function."""

    def test_creates_gitignore(self, cli_runner_isolated):
        """Test .gitignore creation."""
        assert _update_gitignore() is True
        assert (Path.cwd() / ".gitignore").exists()

    def test_gitignore_has_kurt_entries(self, cli_runner_isolated):
        """Test .gitignore has Kurt-specific entries."""
        _update_gitignore()
        content = (Path.cwd() / ".gitignore").read_text()
        assert "content/" in content
        assert ".dolt/noms/" in content
        assert ".env" in content

    def test_gitignore_preserves_existing(self, cli_runner_isolated):
        """Test .gitignore preserves existing content."""
        (Path.cwd() / ".gitignore").write_text("*.pyc\n__pycache__/\n")

        _update_gitignore()
        content = (Path.cwd() / ".gitignore").read_text()
        assert "*.pyc" in content
        assert "content/" in content

    def test_gitignore_no_duplicates(self, cli_runner_isolated):
        """Test .gitignore doesn't add duplicates."""
        (Path.cwd() / ".gitignore").write_text("content/\n.env\n")

        _update_gitignore()
        content = (Path.cwd() / ".gitignore").read_text()
        # Count occurrences of content/
        assert content.count("content/") == 1


class TestInitFunctionalNoDolt:
    """Functional tests for `kurt init --no-dolt` (no external dependencies)."""

    def test_init_no_dolt_creates_git(self, cli_runner_isolated):
        """Test init --no-dolt creates git repository."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            cli_runner_isolated.invoke(init, ["--no-dolt"])

            # Git init should be called
            calls = [str(c) for c in mock_run.call_args_list]
            assert any("git" in str(c) and "init" in str(c) for c in calls)

    def test_init_no_dolt_skips_dolt(self, cli_runner_isolated):
        """Test init --no-dolt skips Dolt initialization."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            cli_runner_isolated.invoke(init, ["--no-dolt"])

            # Dolt init should NOT be called
            calls = [str(c) for c in mock_run.call_args_list]
            assert not any("dolt" in str(c) for c in calls)

    def test_init_no_dolt_creates_config(self, cli_runner_isolated):
        """Test init --no-dolt creates config file."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert (Path.cwd() / "kurt.toml").exists()

    def test_init_no_dolt_creates_workflows(self, cli_runner_isolated):
        """Test init --no-dolt creates workflows directory."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert (Path.cwd() / "workflows").is_dir()

    def test_init_no_dolt_creates_content(self, cli_runner_isolated):
        """Test init --no-dolt creates content directory."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert (Path.cwd() / "content").is_dir()

    def test_init_no_dolt_creates_gitignore(self, cli_runner_isolated):
        """Test init --no-dolt creates .gitignore."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert (Path.cwd() / ".gitignore").exists()


class TestInitPartialDetection:
    """Tests for partial initialization detection."""

    def test_detects_existing_dolt(self, cli_runner_isolated):
        """Test init detects existing Dolt repository."""
        (Path.cwd() / ".dolt").mkdir()

        result = cli_runner_isolated.invoke(init, [])

        assert result.exit_code == 1
        assert "already initialized" in result.output.lower() or "existing project" in result.output.lower()

    def test_detects_missing_components(self, cli_runner_isolated):
        """Test init reports missing components."""
        (Path.cwd() / ".git").mkdir()  # Only Git

        result = cli_runner_isolated.invoke(init, [])

        assert result.exit_code == 1
        assert "missing" in result.output.lower()

    def test_force_completes_partial(self, cli_runner_isolated):
        """Test init --force completes partial setup."""
        (Path.cwd() / ".git").mkdir()

        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("kurt.cli.init._install_hooks") as mock_hooks:
                mock_hooks.return_value = True

                cli_runner_isolated.invoke(init, ["--force", "--no-dolt"])

                # Should create missing components
                assert (Path.cwd() / "kurt.toml").exists()
                assert (Path.cwd() / "workflows").is_dir()


class TestInitExitCodes:
    """Tests for exit codes."""

    def test_exit_code_0_on_success(self, cli_runner_isolated):
        """Test exit code 0 on successful init."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert result.exit_code == 0

    def test_exit_code_1_already_initialized(self, cli_runner_isolated):
        """Test exit code 1 when already initialized."""
        (Path.cwd() / ".dolt").mkdir()

        result = cli_runner_isolated.invoke(init, [])

        assert result.exit_code == 1

    def test_exit_code_2_on_git_failure(self, cli_runner_isolated):
        """Test exit code 2 when Git init fails."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert result.exit_code == 2


class TestInitWithPath:
    """Tests for init with path argument."""

    def test_init_with_path_creates_directory(self, cli_runner_isolated):
        """Test init creates target directory if needed."""
        original_cwd = Path.cwd()
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            cli_runner_isolated.invoke(init, ["new_project", "--no-dolt"])

            # The directory should exist (cwd changes during init)
            assert (original_cwd / "new_project").is_dir()

    def test_init_with_existing_path(self, cli_runner_isolated):
        """Test init works with existing directory."""
        (Path.cwd() / "existing").mkdir()

        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = cli_runner_isolated.invoke(init, ["existing", "--no-dolt"])

            assert result.exit_code == 0


class TestInitNoHooks:
    """Tests for --no-hooks option."""

    def test_no_hooks_skips_hook_install(self, cli_runner_isolated):
        """Test --no-hooks skips hook installation."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("kurt.cli.init._install_hooks") as mock_hooks:
                cli_runner_isolated.invoke(init, ["--no-dolt", "--no-hooks"])

                mock_hooks.assert_not_called()

    def test_no_dolt_implies_no_hooks(self, cli_runner_isolated):
        """Test --no-dolt implies hooks are skipped (hooks need dolt)."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("kurt.cli.init._install_hooks") as mock_hooks:
                result = cli_runner_isolated.invoke(init, ["--no-dolt"])

                # Hooks should not be installed with --no-dolt
                mock_hooks.assert_not_called()
                assert "skipped" in result.output.lower()


class TestInitOutput:
    """Tests for init command output format."""

    def test_shows_initialized_message(self, cli_runner_isolated):
        """Test init shows initialized message."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert "initialized" in result.output.lower()

    def test_shows_component_status(self, cli_runner_isolated):
        """Test init shows status of each component."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert "Git" in result.output or "git" in result.output.lower()
            assert "config" in result.output.lower()
            assert "workflows" in result.output.lower()

    def test_shows_doctor_hint(self, cli_runner_isolated):
        """Test init shows 'kurt doctor' hint."""
        with patch("kurt.cli.init.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = cli_runner_isolated.invoke(init, ["--no-dolt"])

            assert "kurt doctor" in result.output
