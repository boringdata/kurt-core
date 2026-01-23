"""Tests for Git+Dolt remote operations (pull/push)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kurt.db.dolt import DoltDB
from kurt.isolation.remote import (
    DoltResult,
    GitResult,
    PullResult,
    PushResult,
    RemoteError,
    RemoteErrorCode,
    _dolt_remote_exists,
    _git_current_branch,
    _git_remote_exists,
    _is_auth_error,
    _is_conflict_error,
    _is_git_repo,
    _is_network_error,
    pull,
    push,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_dolt_db():
    """Create a mock DoltDB instance."""
    db = MagicMock(spec=DoltDB)
    db.path = Path("/fake/dolt/repo")
    db.exists.return_value = True
    db.branch_current.return_value = "main"
    return db


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
def git_repo_with_remote(git_repo, tmp_path):
    """Create a Git repo with a local 'remote'."""
    # Create a bare repo as the remote
    remote_path = tmp_path / "remote.git"
    subprocess.run(
        ["git", "clone", "--bare", str(git_repo), str(remote_path)],
        check=True,
        capture_output=True,
    )

    # Add as origin to the git_repo
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_path)],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Set up tracking
    subprocess.run(
        ["git", "fetch", "origin"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "--set-upstream-to=origin/main", "main"],
        cwd=git_repo,
        capture_output=True,
    )

    return git_repo, remote_path


# =============================================================================
# Unit Tests - Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_git_repo_true(self, git_repo):
        """Test _is_git_repo returns True for a git repo."""
        assert _is_git_repo(git_repo) is True

    def test_is_git_repo_false(self, tmp_path):
        """Test _is_git_repo returns False for non-repo."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()
        assert _is_git_repo(non_repo) is False

    def test_git_remote_exists_false(self, git_repo):
        """Test _git_remote_exists returns False when no remotes."""
        assert _git_remote_exists(git_repo, "origin") is False

    def test_git_remote_exists_true(self, git_repo_with_remote):
        """Test _git_remote_exists returns True when remote exists."""
        repo, _ = git_repo_with_remote
        assert _git_remote_exists(repo, "origin") is True

    def test_git_current_branch(self, git_repo):
        """Test _git_current_branch returns current branch."""
        branch = _git_current_branch(git_repo)
        assert branch in ("main", "master")

    def test_is_network_error(self):
        """Test network error detection."""
        assert _is_network_error("Could not resolve host: github.com") is True
        assert _is_network_error("Connection refused") is True
        assert _is_network_error("connection timed out") is True
        assert _is_network_error("Some other error") is False

    def test_is_auth_error(self):
        """Test auth error detection."""
        assert _is_auth_error("Authentication failed") is True
        assert _is_auth_error("Permission denied (publickey)") is True
        assert _is_auth_error("HTTP 401 Unauthorized") is True
        assert _is_auth_error("Some other error") is False

    def test_is_conflict_error(self):
        """Test conflict error detection."""
        assert _is_conflict_error("CONFLICT (content): Merge conflict in file.txt") is True
        assert _is_conflict_error("Automatic merge failed; fix conflicts") is True
        assert _is_conflict_error("Some other error") is False


# =============================================================================
# Unit Tests - Dolt Operations (Mocked)
# =============================================================================


class TestDoltRemoteOperations:
    """Tests for Dolt remote operations with mocks."""

    def test_dolt_remote_exists_true(self, mock_dolt_db):
        """Test _dolt_remote_exists returns True when remote exists."""
        mock_dolt_db._run_cli.return_value = "origin\thttps://dolt.example.com/repo"
        assert _dolt_remote_exists(mock_dolt_db, "origin") is True

    def test_dolt_remote_exists_false(self, mock_dolt_db):
        """Test _dolt_remote_exists returns False when no remotes."""
        mock_dolt_db._run_cli.return_value = ""
        assert _dolt_remote_exists(mock_dolt_db, "origin") is False


# =============================================================================
# Unit Tests - Pull
# =============================================================================


class TestPull:
    """Tests for pull function."""

    def test_pull_git_only_no_remote(self, git_repo, mock_dolt_db):
        """Test pull fails when Git remote doesn't exist."""
        with pytest.raises(RemoteError) as exc_info:
            pull(git_repo, mock_dolt_db, remote="origin", git_only=True)

        assert exc_info.value.code == RemoteErrorCode.GIT_REMOTE_NOT_FOUND

    def test_pull_dolt_only_no_remote(self, git_repo, mock_dolt_db):
        """Test pull fails when Dolt remote doesn't exist."""
        mock_dolt_db._run_cli.return_value = ""  # No remotes

        with pytest.raises(RemoteError) as exc_info:
            pull(git_repo, mock_dolt_db, remote="origin", dolt_only=True)

        assert exc_info.value.code == RemoteErrorCode.DOLT_REMOTE_NOT_FOUND

    def test_pull_not_git_repo(self, tmp_path, mock_dolt_db):
        """Test pull fails for non-git directory."""
        non_repo = tmp_path / "not_repo"
        non_repo.mkdir()

        with pytest.raises(RemoteError) as exc_info:
            pull(non_repo, mock_dolt_db, remote="origin")

        assert exc_info.value.code == RemoteErrorCode.GIT_NOT_REPO

    def test_pull_not_dolt_repo(self, git_repo, mock_dolt_db):
        """Test pull fails for non-dolt directory."""
        mock_dolt_db.exists.return_value = False

        # Add a git remote first
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test/repo"],
            cwd=git_repo,
            capture_output=True,
        )

        with pytest.raises(RemoteError) as exc_info:
            pull(git_repo, mock_dolt_db, remote="origin")

        assert exc_info.value.code == RemoteErrorCode.DOLT_NOT_REPO


# =============================================================================
# Unit Tests - Push
# =============================================================================


class TestPush:
    """Tests for push function."""

    def test_push_git_only_no_remote(self, git_repo, mock_dolt_db):
        """Test push fails when Git remote doesn't exist."""
        with pytest.raises(RemoteError) as exc_info:
            push(git_repo, mock_dolt_db, remote="origin", git_only=True)

        assert exc_info.value.code == RemoteErrorCode.GIT_REMOTE_NOT_FOUND

    def test_push_dolt_only_no_remote(self, git_repo, mock_dolt_db):
        """Test push fails when Dolt remote doesn't exist."""
        mock_dolt_db._run_cli.return_value = ""  # No remotes

        with pytest.raises(RemoteError) as exc_info:
            push(git_repo, mock_dolt_db, remote="origin", dolt_only=True)

        assert exc_info.value.code == RemoteErrorCode.DOLT_REMOTE_NOT_FOUND

    def test_push_not_git_repo(self, tmp_path, mock_dolt_db):
        """Test push fails for non-git directory."""
        non_repo = tmp_path / "not_repo"
        non_repo.mkdir()

        with pytest.raises(RemoteError) as exc_info:
            push(non_repo, mock_dolt_db, remote="origin")

        assert exc_info.value.code == RemoteErrorCode.GIT_NOT_REPO

    def test_push_not_dolt_repo(self, git_repo, mock_dolt_db):
        """Test push fails for non-dolt directory."""
        mock_dolt_db.exists.return_value = False

        # Add a git remote first
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test/repo"],
            cwd=git_repo,
            capture_output=True,
        )

        with pytest.raises(RemoteError) as exc_info:
            push(git_repo, mock_dolt_db, remote="origin")

        assert exc_info.value.code == RemoteErrorCode.DOLT_NOT_REPO


# =============================================================================
# Unit Tests - Result Classes
# =============================================================================


class TestResultClasses:
    """Tests for result dataclasses."""

    def test_git_result_defaults(self):
        """Test GitResult default values."""
        result = GitResult(status="success")
        assert result.status == "success"
        assert result.commits_pulled == 0
        assert result.commits_pushed == 0
        assert result.error is None

    def test_dolt_result_defaults(self):
        """Test DoltResult default values."""
        result = DoltResult(status="success")
        assert result.status == "success"
        assert result.commits_pulled == 0
        assert result.commits_pushed == 0
        assert result.error is None

    def test_pull_result_to_dict(self):
        """Test PullResult.to_dict()."""
        result = PullResult(
            git=GitResult(status="success", commits_pulled=3),
            dolt=DoltResult(status="success", commits_pulled=1),
        )
        d = result.to_dict()
        assert d["git"]["status"] == "success"
        assert d["git"]["commits_pulled"] == 3
        assert d["dolt"]["status"] == "success"
        assert d["dolt"]["commits_pulled"] == 1

    def test_push_result_to_dict(self):
        """Test PushResult.to_dict()."""
        result = PushResult(
            git=GitResult(status="success", commits_pushed=2),
            dolt=DoltResult(status="error", error="Network error"),
        )
        d = result.to_dict()
        assert d["git"]["status"] == "success"
        assert d["git"]["commits_pushed"] == 2
        assert d["dolt"]["status"] == "error"
        assert d["dolt"]["error"] == "Network error"


# =============================================================================
# Unit Tests - RemoteError
# =============================================================================


class TestRemoteError:
    """Tests for RemoteError class."""

    def test_error_repr(self):
        """Test error string representation."""
        error = RemoteError(
            code=RemoteErrorCode.GIT_NETWORK_ERROR,
            message="Network error",
        )
        repr_str = repr(error)
        assert "git_network_error" in repr_str
        assert "Network error" in repr_str

    def test_error_with_details_and_suggestion(self):
        """Test error with details and suggestion."""
        error = RemoteError(
            code=RemoteErrorCode.DOLT_REMOTE_NOT_FOUND,
            message="Dolt remote 'origin' not found",
            details="No remotes configured",
            suggestion="Run: dolt remote add origin <url>",
        )
        assert error.code == RemoteErrorCode.DOLT_REMOTE_NOT_FOUND
        assert error.details == "No remotes configured"
        assert error.suggestion == "Run: dolt remote add origin <url>"


# =============================================================================
# Integration Tests - Git Only (real Git, mocked Dolt)
# =============================================================================


class TestGitOnlyIntegration:
    """Integration tests for Git-only operations."""

    def test_pull_git_only_success(self, git_repo_with_remote, mock_dolt_db):
        """Test pull with --git-only succeeds."""
        repo, remote = git_repo_with_remote

        # Pull should succeed (already up to date)
        result = pull(repo, mock_dolt_db, remote="origin", git_only=True)

        assert result.git.status == "success"
        assert result.dolt.status == "skipped"

    def test_push_git_only_success(self, git_repo_with_remote, mock_dolt_db):
        """Test push with --git-only succeeds."""
        repo, remote = git_repo_with_remote

        # Make a new commit
        (repo / "newfile.txt").write_text("New content\n")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "New commit"],
            cwd=repo,
            capture_output=True,
        )

        # Push should succeed
        result = push(repo, mock_dolt_db, remote="origin", git_only=True)

        assert result.git.status == "success"
        assert result.git.commits_pushed >= 1
        assert result.dolt.status == "skipped"

    def test_pull_git_only_with_new_commits(self, git_repo_with_remote, mock_dolt_db):
        """Test pull with --git-only when there are new commits."""
        repo, remote = git_repo_with_remote

        # Push a commit to the remote from another clone
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            clone_path = Path(tmpdir) / "clone"
            subprocess.run(
                ["git", "clone", str(remote), str(clone_path)],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "other@test.com"],
                cwd=clone_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Other User"],
                cwd=clone_path,
                check=True,
                capture_output=True,
            )
            (clone_path / "remote_file.txt").write_text("From remote\n")
            subprocess.run(["git", "add", "."], cwd=clone_path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Remote commit"],
                cwd=clone_path,
                capture_output=True,
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=clone_path,
                check=True,
                capture_output=True,
            )

        # Pull should get the new commit
        result = pull(repo, mock_dolt_db, remote="origin", git_only=True)

        assert result.git.status == "success"
        assert result.git.commits_pulled >= 1
        assert (repo / "remote_file.txt").exists()
