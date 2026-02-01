"""Tests for Git hooks installation and management."""

from __future__ import annotations

import subprocess

import pytest

from kurt.db.isolation.hooks import (
    HOOK_NAMES,
    HOOK_SCRIPTS,
    HookExitCode,
    HookInstallResult,
    HookUninstallResult,
    _is_bare_repo,
    _is_kurt_hook,
    _is_worktree,
    get_installed_hooks,
    hooks_need_update,
    install_hooks,
    uninstall_hooks,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def git_repo(tmp_path):
    """Create a real Git repository for testing."""
    repo = tmp_path / "git_repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit (needed to have a branch)
    (repo / "README.md").write_text("# Test\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


@pytest.fixture
def bare_repo(tmp_path):
    """Create a bare Git repository."""
    repo = tmp_path / "bare_repo.git"
    subprocess.run(["git", "init", "--bare", str(repo)], check=True, capture_output=True)
    return repo


@pytest.fixture
def git_worktree(git_repo, tmp_path):
    """Create a Git worktree from the main repo."""
    worktree = tmp_path / "worktree"
    subprocess.run(
        ["git", "worktree", "add", str(worktree), "-b", "worktree-branch"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    return worktree


# =============================================================================
# Tests - Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_kurt_hook_true(self, git_repo):
        """Test _is_kurt_hook returns True for Kurt hooks."""
        hook_path = git_repo / ".git" / "hooks" / "test-hook"
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        hook_path.write_text("#!/bin/bash\n# Kurt Git Hook - Auto-generated\necho test")

        assert _is_kurt_hook(hook_path) is True

    def test_is_kurt_hook_false(self, git_repo):
        """Test _is_kurt_hook returns False for non-Kurt hooks."""
        hook_path = git_repo / ".git" / "hooks" / "test-hook"
        hook_path.parent.mkdir(parents=True, exist_ok=True)
        hook_path.write_text("#!/bin/bash\necho 'custom hook'")

        assert _is_kurt_hook(hook_path) is False

    def test_is_kurt_hook_nonexistent(self, git_repo):
        """Test _is_kurt_hook returns False for non-existent files."""
        hook_path = git_repo / ".git" / "hooks" / "nonexistent"
        assert _is_kurt_hook(hook_path) is False

    def test_is_bare_repo_true(self, bare_repo):
        """Test _is_bare_repo returns True for bare repos."""
        assert _is_bare_repo(bare_repo) is True

    def test_is_bare_repo_false(self, git_repo):
        """Test _is_bare_repo returns False for normal repos."""
        assert _is_bare_repo(git_repo) is False

    def test_is_worktree_true(self, git_worktree):
        """Test _is_worktree returns True for worktrees."""
        assert _is_worktree(git_worktree) is True

    def test_is_worktree_false(self, git_repo):
        """Test _is_worktree returns False for main repos."""
        assert _is_worktree(git_repo) is False


# =============================================================================
# Tests - install_hooks
# =============================================================================


class TestInstallHooks:
    """Tests for install_hooks function."""

    def test_install_hooks_success(self, git_repo):
        """Test successful hook installation."""
        result = install_hooks(git_repo)

        assert isinstance(result, HookInstallResult)
        assert set(result.installed) == set(HOOK_NAMES)
        assert result.backed_up == []
        assert result.skipped == []
        assert result.errors == []

        # Verify hooks exist and are executable
        hooks_dir = git_repo / ".git" / "hooks"
        for hook_name in HOOK_NAMES:
            hook_path = hooks_dir / hook_name
            assert hook_path.exists()
            assert hook_path.stat().st_mode & 0o111  # Executable

    def test_install_hooks_content(self, git_repo):
        """Test hook scripts have correct content."""
        install_hooks(git_repo)

        hooks_dir = git_repo / ".git" / "hooks"
        for hook_name in HOOK_NAMES:
            hook_path = hooks_dir / hook_name
            content = hook_path.read_text()
            assert "Kurt Git Hook" in content
            assert "KURT_SKIP_HOOKS" in content
            assert "CI" in content  # CI detection

    def test_install_hooks_not_git_repo(self, tmp_path):
        """Test install fails for non-git directory."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        with pytest.raises(ValueError, match="Not a Git repository"):
            install_hooks(non_repo)

    def test_install_hooks_bare_repo(self, bare_repo):
        """Test install skips bare repositories."""
        result = install_hooks(bare_repo)

        assert result.installed == []
        assert set(result.skipped) == set(HOOK_NAMES)
        assert "bare" in result.errors[0].lower()

    def test_install_hooks_worktree(self, git_worktree):
        """Test install skips worktrees."""
        result = install_hooks(git_worktree)

        assert result.installed == []
        assert set(result.skipped) == set(HOOK_NAMES)
        assert "worktree" in result.errors[0].lower()

    def test_install_hooks_skip_existing(self, git_repo):
        """Test existing non-Kurt hooks are skipped."""
        # Create an existing hook
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        existing_hook = hooks_dir / "post-checkout"
        existing_hook.write_text("#!/bin/bash\necho 'existing hook'")

        result = install_hooks(git_repo)

        assert "post-checkout" in result.skipped
        assert "post-checkout" not in result.installed

        # Original hook content preserved
        assert "existing hook" in existing_hook.read_text()

    def test_install_hooks_force_backup(self, git_repo):
        """Test force flag backs up existing hooks."""
        # Create an existing hook
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        existing_hook = hooks_dir / "post-checkout"
        existing_hook.write_text("#!/bin/bash\necho 'existing hook'")

        result = install_hooks(git_repo, force=True)

        assert "post-checkout" in result.installed
        assert "post-checkout" in result.backed_up

        # Backup exists
        backup = hooks_dir / "post-checkout.pre-kurt"
        assert backup.exists()
        assert "existing hook" in backup.read_text()

        # New hook installed
        assert "Kurt Git Hook" in existing_hook.read_text()

    def test_install_hooks_overwrite_kurt_hook(self, git_repo):
        """Test Kurt hooks are overwritten without backup."""
        # First install
        install_hooks(git_repo)

        # Modify a hook
        hook_path = git_repo / ".git" / "hooks" / "post-checkout"
        hook_path.write_text("#!/bin/bash\n# Kurt Git Hook\necho 'modified'")

        # Second install - should overwrite
        result = install_hooks(git_repo)

        assert "post-checkout" in result.installed
        assert "post-checkout" not in result.backed_up

        # No backup created for Kurt hooks
        backup = git_repo / ".git" / "hooks" / "post-checkout.pre-kurt"
        assert not backup.exists()


# =============================================================================
# Tests - uninstall_hooks
# =============================================================================


class TestUninstallHooks:
    """Tests for uninstall_hooks function."""

    def test_uninstall_hooks_success(self, git_repo):
        """Test successful hook removal."""
        install_hooks(git_repo)
        result = uninstall_hooks(git_repo)

        assert isinstance(result, HookUninstallResult)
        assert set(result.removed) == set(HOOK_NAMES)
        assert result.restored == []
        assert result.errors == []

        # Verify hooks removed
        hooks_dir = git_repo / ".git" / "hooks"
        for hook_name in HOOK_NAMES:
            assert not (hooks_dir / hook_name).exists()

    def test_uninstall_hooks_not_git_repo(self, tmp_path):
        """Test uninstall fails for non-git directory."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        with pytest.raises(ValueError, match="Not a Git repository"):
            uninstall_hooks(non_repo)

    def test_uninstall_hooks_not_installed(self, git_repo):
        """Test uninstall handles missing hooks."""
        result = uninstall_hooks(git_repo)

        assert result.removed == []
        assert set(result.not_found) == set(HOOK_NAMES)

    def test_uninstall_hooks_skip_non_kurt(self, git_repo):
        """Test uninstall skips non-Kurt hooks."""
        # Create a non-Kurt hook
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = hooks_dir / "post-checkout"
        hook_path.write_text("#!/bin/bash\necho 'custom hook'")

        result = uninstall_hooks(git_repo)

        assert "post-checkout" not in result.removed
        assert "post-checkout" in result.not_found
        assert hook_path.exists()

    def test_uninstall_hooks_restore_backup(self, git_repo):
        """Test uninstall restores backed up hooks."""
        # Create an existing hook
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        existing_hook = hooks_dir / "post-checkout"
        existing_hook.write_text("#!/bin/bash\necho 'original hook'")

        # Install with force to backup
        install_hooks(git_repo, force=True)

        # Uninstall
        result = uninstall_hooks(git_repo)

        assert "post-checkout" in result.restored

        # Original hook restored
        assert existing_hook.exists()
        assert "original hook" in existing_hook.read_text()

        # Backup removed
        backup = hooks_dir / "post-checkout.pre-kurt"
        assert not backup.exists()


# =============================================================================
# Tests - get_installed_hooks
# =============================================================================


class TestGetInstalledHooks:
    """Tests for get_installed_hooks function."""

    def test_get_installed_hooks_none(self, git_repo):
        """Test returns empty list when no hooks installed."""
        result = get_installed_hooks(git_repo)
        assert result == []

    def test_get_installed_hooks_all(self, git_repo):
        """Test returns all Kurt hooks."""
        install_hooks(git_repo)
        result = get_installed_hooks(git_repo)
        assert set(result) == set(HOOK_NAMES)

    def test_get_installed_hooks_partial(self, git_repo):
        """Test returns only Kurt hooks."""
        # Install Kurt hooks
        install_hooks(git_repo)

        # Remove one hook
        hook_path = git_repo / ".git" / "hooks" / "post-checkout"
        hook_path.unlink()

        result = get_installed_hooks(git_repo)
        assert "post-checkout" not in result
        assert len(result) == len(HOOK_NAMES) - 1

    def test_get_installed_hooks_ignores_non_kurt(self, git_repo):
        """Test ignores non-Kurt hooks."""
        # Create a non-Kurt hook
        hooks_dir = git_repo / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = hooks_dir / "post-checkout"
        hook_path.write_text("#!/bin/bash\necho 'custom hook'")

        result = get_installed_hooks(git_repo)
        assert "post-checkout" not in result


# =============================================================================
# Tests - hooks_need_update
# =============================================================================


class TestHooksNeedUpdate:
    """Tests for hooks_need_update function."""

    def test_hooks_need_update_none_installed(self, git_repo):
        """Test returns all hooks when none installed."""
        result = hooks_need_update(git_repo)
        assert set(result) == set(HOOK_NAMES)

    def test_hooks_need_update_all_current(self, git_repo):
        """Test returns empty when all hooks are current."""
        install_hooks(git_repo)
        result = hooks_need_update(git_repo)
        assert result == []

    def test_hooks_need_update_outdated(self, git_repo):
        """Test returns hooks with different content."""
        install_hooks(git_repo)

        # Modify a hook
        hook_path = git_repo / ".git" / "hooks" / "post-checkout"
        hook_path.write_text("#!/bin/bash\n# Kurt Git Hook\necho 'outdated version'")

        result = hooks_need_update(git_repo)
        assert "post-checkout" in result

    def test_hooks_need_update_ignores_non_kurt(self, git_repo):
        """Test ignores non-Kurt hooks."""
        # Install Kurt hooks
        install_hooks(git_repo)

        # Replace one with non-Kurt hook
        hook_path = git_repo / ".git" / "hooks" / "post-checkout"
        hook_path.write_text("#!/bin/bash\necho 'custom hook'")

        result = hooks_need_update(git_repo)
        # post-checkout not in result because it's not a Kurt hook
        assert "post-checkout" not in result


# =============================================================================
# Tests - Hook Script Content
# =============================================================================


class TestHookScriptContent:
    """Tests for hook script content and behavior."""

    def test_all_hooks_have_scripts(self):
        """Test all hook names have corresponding scripts."""
        for hook_name in HOOK_NAMES:
            assert hook_name in HOOK_SCRIPTS
            assert len(HOOK_SCRIPTS[hook_name]) > 0

    def test_scripts_have_skip_hooks_check(self):
        """Test all scripts check KURT_SKIP_HOOKS."""
        for hook_name, script in HOOK_SCRIPTS.items():
            assert "KURT_SKIP_HOOKS" in script, f"{hook_name} missing KURT_SKIP_HOOKS"

    def test_scripts_have_ci_detection(self):
        """Test all scripts detect CI environments."""
        for hook_name, script in HOOK_SCRIPTS.items():
            assert 'CI' in script, f"{hook_name} missing CI detection"
            assert 'GITHUB_ACTIONS' in script, f"{hook_name} missing GITHUB_ACTIONS"

    def test_scripts_have_lock_handling(self):
        """Test all scripts have reentrancy lock handling."""
        for hook_name, script in HOOK_SCRIPTS.items():
            assert "kurt-hook.lock" in script, f"{hook_name} missing lock file"
            assert "acquire_lock" in script, f"{hook_name} missing acquire_lock"

    def test_scripts_have_init_check(self):
        """Test all scripts check for Kurt initialization."""
        for hook_name, script in HOOK_SCRIPTS.items():
            assert "kurt.config" in script, f"{hook_name} missing init check"

    def test_post_checkout_branch_only(self):
        """Test post-checkout only runs for branch checkouts."""
        script = HOOK_SCRIPTS["post-checkout"]
        assert '$3' in script  # Branch flag argument
        assert '"$3" != "1"' in script  # Skip non-branch checkouts

    def test_prepare_commit_msg_blocks_merge(self):
        """Test prepare-commit-msg blocks merge commits."""
        script = HOOK_SCRIPTS["prepare-commit-msg"]
        assert 'merge' in script.lower()
        assert 'kurt merge' in script


# =============================================================================
# Tests - HookExitCode
# =============================================================================


class TestHookExitCode:
    """Tests for HookExitCode enum."""

    def test_exit_codes(self):
        """Test exit code values."""
        assert HookExitCode.SUCCESS.value == 0
        assert HookExitCode.SYNC_FAILED.value == 1
        assert HookExitCode.NOT_INITIALIZED.value == 2
