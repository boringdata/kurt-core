"""Tests for Git+Dolt merge operations."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kurt.db.dolt import BranchInfo, DoltDB
from kurt.isolation.merge import (
    DoltConflict,
    MergeConflict,
    MergeError,
    MergeErrorCode,
    MergeExitCode,
    MergeResult,
    _dolt_branch_exists,
    _dolt_get_conflicts,
    _dolt_merge_abort,
    _dolt_merge_commit,
    _dolt_merge_no_commit,
    _dolt_reset_hard,
    _git_branch_exists,
    _git_current_branch,
    _git_merge,
    _git_merge_abort,
    _git_merge_in_progress,
    _is_git_repo,
    abort_merge,
    check_conflicts,
    merge_branch,
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
    db.branch_list.return_value = [
        BranchInfo(name="main", is_current=True),
        BranchInfo(name="feature", is_current=False),
        BranchInfo(name="conflict-feature", is_current=False),
    ]
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
def git_repo_with_feature(git_repo):
    """Git repo with a feature branch containing divergent commits."""
    # Create feature branch
    subprocess.run(
        ["git", "branch", "feature"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Add a commit to main
    (git_repo / "main_file.txt").write_text("Main content\n")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Main commit"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Switch to feature and add a commit
    subprocess.run(
        ["git", "checkout", "feature"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    (git_repo / "feature_file.txt").write_text("Feature content\n")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Feature commit"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Go back to main
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    return git_repo


@pytest.fixture
def git_repo_with_conflict(git_repo):
    """Git repo with a feature branch that will cause merge conflict."""
    # Create feature branch
    subprocess.run(
        ["git", "branch", "conflict-feature"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Add conflicting file on main
    (git_repo / "conflict.txt").write_text("Main version\n")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Main conflict"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Switch to feature and add conflicting content
    subprocess.run(
        ["git", "checkout", "conflict-feature"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    (git_repo / "conflict.txt").write_text("Feature version\n")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Feature conflict"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    # Go back to main
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    return git_repo


# =============================================================================
# Unit Tests - Data Classes
# =============================================================================


class TestDataClasses:
    """Tests for data classes."""

    def test_dolt_conflict_fields(self):
        """Test DoltConflict dataclass fields."""
        conflict = DoltConflict(
            table="documents",
            key="id=123",
            ours={"name": "Alice"},
            theirs={"name": "Bob"},
        )
        assert conflict.table == "documents"
        assert conflict.key == "id=123"
        assert conflict.ours == {"name": "Alice"}
        assert conflict.theirs == {"name": "Bob"}

    def test_merge_conflict_fields(self):
        """Test MergeConflict dataclass fields."""
        conflict = MergeConflict(
            dolt_conflicts=[DoltConflict(table="users", key="id=1")],
            git_conflicts=["file.py"],
            resolution_hint="Fix manually",
        )
        assert len(conflict.dolt_conflicts) == 1
        assert len(conflict.git_conflicts) == 1
        assert conflict.resolution_hint == "Fix manually"

    def test_merge_conflict_defaults(self):
        """Test MergeConflict default values."""
        conflict = MergeConflict()
        assert conflict.dolt_conflicts == []
        assert conflict.git_conflicts == []
        assert conflict.resolution_hint == ""

    def test_merge_result_success(self):
        """Test MergeResult for successful merge."""
        result = MergeResult(
            success=True,
            source_branch="feature",
            target_branch="main",
            dolt_commit_hash="abc123",
            git_commit_hash="def456",
            message="Merged successfully",
        )
        assert result.success is True
        assert result.source_branch == "feature"
        assert result.target_branch == "main"
        assert result.dolt_commit_hash == "abc123"
        assert result.git_commit_hash == "def456"

    def test_merge_error_repr(self):
        """Test MergeError string representation."""
        error = MergeError(
            code=MergeErrorCode.DOLT_CONFLICT,
            message="Conflicts detected",
        )
        repr_str = repr(error)
        assert "dolt_conflict" in repr_str
        assert "Conflicts detected" in repr_str


class TestMergeExitCodes:
    """Tests for exit codes."""

    def test_exit_codes_values(self):
        """Test exit code values match spec."""
        assert MergeExitCode.SUCCESS == 0
        assert MergeExitCode.DOLT_CONFLICTS == 1
        assert MergeExitCode.GIT_CONFLICTS == 2
        assert MergeExitCode.ROLLBACK_FAILED == 3


# =============================================================================
# Unit Tests - Git Operations
# =============================================================================


class TestGitMergeOperations:
    """Tests for Git merge helper functions."""

    def test_is_git_repo_true(self, git_repo):
        """Test _is_git_repo returns True for a git repo."""
        assert _is_git_repo(git_repo) is True

    def test_is_git_repo_false(self, tmp_path):
        """Test _is_git_repo returns False for non-repo."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()
        assert _is_git_repo(non_repo) is False

    def test_git_branch_exists_true(self, git_repo_with_feature):
        """Test _git_branch_exists returns True for existing branch."""
        assert _git_branch_exists(git_repo_with_feature, "feature") is True

    def test_git_branch_exists_false(self, git_repo):
        """Test _git_branch_exists returns False for non-existing branch."""
        assert _git_branch_exists(git_repo, "nonexistent") is False

    def test_git_merge_success(self, git_repo_with_feature):
        """Test successful Git merge."""
        # On main, merge feature
        success, commit_hash, conflicts = _git_merge(git_repo_with_feature, "feature")

        assert success is True
        assert commit_hash != ""  # Got a commit hash
        assert conflicts == []

        # Verify feature_file.txt exists (merged from feature)
        assert (git_repo_with_feature / "feature_file.txt").exists()

    def test_git_merge_conflict(self, git_repo_with_conflict):
        """Test Git merge with conflicts."""
        success, commit_hash, conflicts = _git_merge(
            git_repo_with_conflict, "conflict-feature"
        )

        assert success is False
        assert commit_hash == ""
        assert "conflict.txt" in conflicts

    def test_git_merge_no_commit(self, git_repo_with_feature):
        """Test Git merge with --no-commit flag."""
        success, commit_hash, conflicts = _git_merge(
            git_repo_with_feature, "feature", no_commit=True
        )

        assert success is True
        assert commit_hash == ""  # No commit hash when --no-commit
        assert conflicts == []

    def test_git_merge_abort(self, git_repo_with_conflict):
        """Test aborting a Git merge."""
        # Start merge that will conflict
        _git_merge(git_repo_with_conflict, "conflict-feature")

        # Should have MERGE_HEAD now
        assert _git_merge_in_progress(git_repo_with_conflict) is True

        # Abort
        success = _git_merge_abort(git_repo_with_conflict)
        assert success is True

        # Should no longer have MERGE_HEAD
        assert _git_merge_in_progress(git_repo_with_conflict) is False

    def test_git_merge_in_progress_false(self, git_repo):
        """Test _git_merge_in_progress returns False when no merge."""
        assert _git_merge_in_progress(git_repo) is False


# =============================================================================
# Unit Tests - Dolt Operations
# =============================================================================


class TestDoltMergeOperations:
    """Tests for Dolt merge helper functions."""

    def test_dolt_branch_exists_true(self, mock_dolt_db):
        """Test _dolt_branch_exists returns True for existing branch."""
        assert _dolt_branch_exists(mock_dolt_db, "main") is True
        assert _dolt_branch_exists(mock_dolt_db, "feature") is True

    def test_dolt_branch_exists_false(self, mock_dolt_db):
        """Test _dolt_branch_exists returns False for non-existing branch."""
        assert _dolt_branch_exists(mock_dolt_db, "nonexistent") is False

    def test_dolt_merge_no_commit_success(self, mock_dolt_db):
        """Test successful Dolt merge --no-commit."""
        mock_dolt_db._run_cli.return_value = "Fast-forward"

        success, conflicts = _dolt_merge_no_commit(mock_dolt_db, "feature")

        assert success is True
        assert conflicts == []
        mock_dolt_db._run_cli.assert_called_once_with(["merge", "--no-commit", "feature"])

    def test_dolt_merge_no_commit_conflict(self, mock_dolt_db):
        """Test Dolt merge --no-commit with conflicts."""
        mock_dolt_db._run_cli.return_value = "CONFLICT in table users"
        mock_dolt_db.query.return_value = []  # Empty conflicts table

        success, conflicts = _dolt_merge_no_commit(mock_dolt_db, "feature")

        assert success is False
        # conflicts may be empty if query returns nothing

    def test_dolt_merge_commit(self, mock_dolt_db):
        """Test Dolt merge commit."""
        mock_dolt_db._run_cli.side_effect = [
            "",  # add -A
            "commit abc123 Message",  # commit
        ]

        commit_hash = _dolt_merge_commit(mock_dolt_db, "Merge feature")

        assert commit_hash == "abc123"

    def test_dolt_merge_abort(self, mock_dolt_db):
        """Test Dolt merge abort."""
        mock_dolt_db._run_cli.return_value = ""

        success = _dolt_merge_abort(mock_dolt_db)

        assert success is True
        mock_dolt_db._run_cli.assert_called_once_with(["merge", "--abort"])

    def test_dolt_merge_abort_failure(self, mock_dolt_db):
        """Test Dolt merge abort when no merge in progress."""
        mock_dolt_db._run_cli.side_effect = Exception("No merge in progress")

        success = _dolt_merge_abort(mock_dolt_db)

        assert success is False

    def test_dolt_reset_hard(self, mock_dolt_db):
        """Test Dolt reset --hard."""
        mock_dolt_db._run_cli.return_value = ""

        success = _dolt_reset_hard(mock_dolt_db, "HEAD~1")

        assert success is True
        mock_dolt_db._run_cli.assert_called_once_with(["reset", "--hard", "HEAD~1"])

    def test_dolt_reset_hard_failure(self, mock_dolt_db):
        """Test Dolt reset --hard failure."""
        mock_dolt_db._run_cli.side_effect = Exception("Reset failed")

        success = _dolt_reset_hard(mock_dolt_db, "HEAD~1")

        assert success is False


# =============================================================================
# Tests - merge_branch
# =============================================================================


class TestMergeBranch:
    """Tests for merge_branch function."""

    def test_merge_branch_success(self, git_repo_with_feature, mock_dolt_db):
        """Test successful merge of both Dolt and Git."""
        # Setup Dolt mock
        mock_dolt_db._run_cli.side_effect = [
            "Fast-forward",  # merge --no-commit
            "",  # add -A
            "commit abc123",  # commit
        ]

        result = merge_branch(
            source="feature",
            git_path=git_repo_with_feature,
            dolt_db=mock_dolt_db,
        )

        assert result.success is True
        assert result.source_branch == "feature"
        assert result.target_branch in ("main", "master")
        assert result.dolt_commit_hash == "abc123"
        assert result.git_commit_hash is not None

    def test_merge_branch_dolt_conflict(self, git_repo_with_feature, mock_dolt_db):
        """Test merge fails with Dolt conflicts."""
        # Setup Dolt mock to return conflict
        mock_dolt_db._run_cli.side_effect = [
            "CONFLICT in table users",  # merge --no-commit
            "",  # merge --abort
        ]
        mock_dolt_db.query.return_value = []

        with pytest.raises(MergeError) as exc_info:
            merge_branch(
                source="feature",
                git_path=git_repo_with_feature,
                dolt_db=mock_dolt_db,
            )

        assert exc_info.value.code == MergeErrorCode.DOLT_CONFLICT

    def test_merge_branch_git_conflict_rollback(
        self, git_repo_with_conflict, mock_dolt_db
    ):
        """Test Git conflict triggers Dolt rollback."""
        # Setup Dolt mock - merge succeeds
        mock_dolt_db._run_cli.side_effect = [
            "Fast-forward",  # merge --no-commit
            "",  # add -A
            "commit abc123",  # commit
            "",  # reset --hard (rollback)
        ]

        with pytest.raises(MergeError) as exc_info:
            merge_branch(
                source="conflict-feature",
                git_path=git_repo_with_conflict,
                dolt_db=mock_dolt_db,
            )

        assert exc_info.value.code == MergeErrorCode.GIT_CONFLICT
        assert "conflict.txt" in exc_info.value.conflicts.git_conflicts

    def test_merge_branch_invalid_source(self, git_repo, mock_dolt_db):
        """Test merge fails with invalid source branch."""
        with pytest.raises(MergeError) as exc_info:
            merge_branch(
                source="nonexistent",
                git_path=git_repo,
                dolt_db=mock_dolt_db,
            )

        assert exc_info.value.code == MergeErrorCode.INVALID_BRANCH

    def test_merge_branch_not_git_repo(self, tmp_path, mock_dolt_db):
        """Test merge fails for non-git directory."""
        non_repo = tmp_path / "not_repo"
        non_repo.mkdir()

        with pytest.raises(MergeError) as exc_info:
            merge_branch(
                source="feature",
                git_path=non_repo,
                dolt_db=mock_dolt_db,
            )

        assert exc_info.value.code == MergeErrorCode.GIT_NOT_REPO

    def test_merge_branch_not_dolt_repo(self, git_repo, mock_dolt_db):
        """Test merge fails for non-dolt directory."""
        mock_dolt_db.exists.return_value = False

        with pytest.raises(MergeError) as exc_info:
            merge_branch(
                source="feature",
                git_path=git_repo,
                dolt_db=mock_dolt_db,
            )

        assert exc_info.value.code == MergeErrorCode.DOLT_NOT_REPO

    def test_merge_branch_merge_in_progress(
        self, git_repo_with_conflict, mock_dolt_db
    ):
        """Test merge fails if Git merge already in progress."""
        # Start a conflicting merge
        _git_merge(git_repo_with_conflict, "conflict-feature")

        with pytest.raises(MergeError) as exc_info:
            merge_branch(
                source="conflict-feature",
                git_path=git_repo_with_conflict,
                dolt_db=mock_dolt_db,
            )

        assert exc_info.value.code == MergeErrorCode.MERGE_IN_PROGRESS

        # Cleanup
        _git_merge_abort(git_repo_with_conflict)

    def test_merge_branch_no_commit_flag(self, git_repo_with_feature, mock_dolt_db):
        """Test merge with --no-commit flag."""
        # Setup Dolt mock
        mock_dolt_db._run_cli.side_effect = [
            "Fast-forward",  # merge --no-commit
        ]

        result = merge_branch(
            source="feature",
            git_path=git_repo_with_feature,
            dolt_db=mock_dolt_db,
            no_commit=True,
        )

        assert result.success is True
        assert result.dolt_commit_hash is None
        # In no_commit mode, git_commit_hash is None (no commit made)
        assert result.git_commit_hash is None


# =============================================================================
# Tests - abort_merge
# =============================================================================


class TestAbortMerge:
    """Tests for abort_merge function."""

    def test_abort_merge_both(self, git_repo_with_conflict, mock_dolt_db):
        """Test aborting merge in both systems."""
        # Start a Git merge that conflicts
        _git_merge(git_repo_with_conflict, "conflict-feature")

        # Setup Dolt mock
        mock_dolt_db._run_cli.return_value = ""

        success = abort_merge(git_repo_with_conflict, mock_dolt_db)

        assert success is True
        assert not _git_merge_in_progress(git_repo_with_conflict)

    def test_abort_merge_no_merge_in_progress(self, git_repo, mock_dolt_db):
        """Test abort when no merge in progress."""
        mock_dolt_db._run_cli.side_effect = Exception("No merge in progress")

        # Should still succeed (no merge to abort)
        success = abort_merge(git_repo, mock_dolt_db)

        assert success is True


# =============================================================================
# Tests - check_conflicts
# =============================================================================


class TestCheckConflicts:
    """Tests for check_conflicts function."""

    def test_check_conflicts_no_conflicts(self, git_repo_with_feature, mock_dolt_db):
        """Test check_conflicts when no conflicts exist."""
        conflicts = check_conflicts(
            source="feature",
            target="main",
            git_path=git_repo_with_feature,
            dolt_db=mock_dolt_db,
        )

        # May find no conflicts (depends on git merge-tree availability)
        assert isinstance(conflicts, MergeConflict)

    def test_check_conflicts_invalid_branch(self, git_repo, mock_dolt_db):
        """Test check_conflicts with invalid branch."""
        with pytest.raises(MergeError) as exc_info:
            check_conflicts(
                source="nonexistent",
                target="main",
                git_path=git_repo,
                dolt_db=mock_dolt_db,
            )

        assert exc_info.value.code == MergeErrorCode.INVALID_BRANCH


# =============================================================================
# Tests - MergeError
# =============================================================================


class TestMergeError:
    """Tests for MergeError class."""

    def test_error_with_conflicts(self):
        """Test MergeError with conflict details."""
        conflicts = MergeConflict(
            git_conflicts=["file1.py", "file2.py"],
            resolution_hint="Edit files manually",
        )
        error = MergeError(
            code=MergeErrorCode.GIT_CONFLICT,
            message="Git merge failed",
            conflicts=conflicts,
        )

        assert error.code == MergeErrorCode.GIT_CONFLICT
        assert error.conflicts is not None
        assert len(error.conflicts.git_conflicts) == 2

    def test_error_codes_all_defined(self):
        """Test all error codes are defined."""
        codes = list(MergeErrorCode)
        expected = [
            "DOLT_CONFLICT",
            "GIT_CONFLICT",
            "ROLLBACK_FAILED",
            "GIT_NOT_AVAILABLE",
            "GIT_NOT_REPO",
            "DOLT_NOT_AVAILABLE",
            "DOLT_NOT_REPO",
            "MERGE_IN_PROGRESS",
            "INVALID_BRANCH",
            "NOTHING_TO_MERGE",
        ]
        for code_name in expected:
            assert hasattr(MergeErrorCode, code_name)
