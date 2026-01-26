"""Tests for Git+Dolt branch synchronization."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kurt.db.dolt import BranchInfo, DoltBranchError, DoltDB
from kurt.db.isolation.branch import (
    BranchStatus,
    BranchSyncError,
    BranchSyncErrorCode,
    BranchSyncResult,
    _dolt_branch_exists,
    _git_branch_exists,
    _git_current_branch,
    _git_is_detached_head,
    _is_git_repo,
    create_both,
    delete_both,
    list_branches,
    switch_both,
    sync_to_dolt,
    sync_to_git,
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


# =============================================================================
# Unit Tests - Git Operations
# =============================================================================


class TestGitOperations:
    """Tests for Git helper functions."""

    def test_is_git_repo_true(self, git_repo):
        """Test _is_git_repo returns True for a git repo."""
        assert _is_git_repo(git_repo) is True

    def test_is_git_repo_false(self, tmp_path):
        """Test _is_git_repo returns False for non-repo."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()
        assert _is_git_repo(non_repo) is False

    def test_git_current_branch(self, git_repo):
        """Test _git_current_branch returns current branch."""
        # Default branch should be main or master
        branch = _git_current_branch(git_repo)
        assert branch in ("main", "master")

    def test_git_current_branch_detached(self, git_repo):
        """Test _git_current_branch returns None when detached."""
        # Get the commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        commit = result.stdout.strip()

        # Checkout the commit (detached HEAD)
        subprocess.run(
            ["git", "checkout", commit],
            cwd=git_repo,
            capture_output=True,
        )

        assert _git_current_branch(git_repo) is None

    def test_git_is_detached_head(self, git_repo):
        """Test _git_is_detached_head detection."""
        # Normal state - not detached
        assert _git_is_detached_head(git_repo) is False

        # Detach HEAD
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        commit = result.stdout.strip()
        subprocess.run(
            ["git", "checkout", commit],
            cwd=git_repo,
            capture_output=True,
        )

        assert _git_is_detached_head(git_repo) is True

    def test_git_branch_exists(self, git_repo):
        """Test _git_branch_exists."""
        # Current branch exists
        branch = _git_current_branch(git_repo)
        assert _git_branch_exists(git_repo, branch) is True

        # Non-existent branch
        assert _git_branch_exists(git_repo, "nonexistent-branch-xyz") is False


# =============================================================================
# Unit Tests - Dolt Operations
# =============================================================================


class TestDoltOperations:
    """Tests for Dolt helper functions."""

    def test_dolt_branch_exists_true(self, mock_dolt_db):
        """Test _dolt_branch_exists returns True for existing branch."""
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
            BranchInfo(name="feature", is_current=False),
        ]
        assert _dolt_branch_exists(mock_dolt_db, "main") is True
        assert _dolt_branch_exists(mock_dolt_db, "feature") is True

    def test_dolt_branch_exists_false(self, mock_dolt_db):
        """Test _dolt_branch_exists returns False for non-existing branch."""
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]
        assert _dolt_branch_exists(mock_dolt_db, "nonexistent") is False


# =============================================================================
# Tests - sync_to_git
# =============================================================================


class TestSyncToGit:
    """Tests for sync_to_git function."""

    def test_sync_to_git_already_in_sync(self, git_repo, mock_dolt_db):
        """Test sync when branches already match."""
        git_branch = _git_current_branch(git_repo)
        mock_dolt_db.branch_current.return_value = git_branch

        result = sync_to_git(git_repo, mock_dolt_db)

        assert result.git_branch == git_branch
        assert result.dolt_branch == git_branch
        assert result.created is False
        mock_dolt_db.branch_switch.assert_not_called()

    def test_sync_to_git_switch_branch(self, git_repo, mock_dolt_db):
        """Test sync switches Dolt to match Git."""
        git_branch = _git_current_branch(git_repo)
        mock_dolt_db.branch_current.return_value = "different-branch"
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=False),
            BranchInfo(name=git_branch, is_current=False),
            BranchInfo(name="different-branch", is_current=True),
        ]

        result = sync_to_git(git_repo, mock_dolt_db)

        assert result.git_branch == git_branch
        assert result.dolt_branch == git_branch
        assert result.created is False
        mock_dolt_db.branch_switch.assert_called_once_with(git_branch, force=False)

    def test_sync_to_git_creates_missing_branch(self, git_repo, mock_dolt_db):
        """Test sync creates branch in Dolt if missing."""
        git_branch = _git_current_branch(git_repo)
        mock_dolt_db.branch_current.return_value = "other-branch"
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="other-branch", is_current=True),
        ]

        result = sync_to_git(git_repo, mock_dolt_db)

        assert result.created is True
        mock_dolt_db.branch_create.assert_called_once_with(git_branch)
        mock_dolt_db.branch_switch.assert_called_once_with(git_branch, force=False)

    def test_sync_to_git_detached_head_error(self, git_repo, mock_dolt_db):
        """Test sync fails with error on detached HEAD."""
        # Detach HEAD
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        commit = result.stdout.strip()
        subprocess.run(
            ["git", "checkout", commit],
            cwd=git_repo,
            capture_output=True,
        )

        with pytest.raises(BranchSyncError) as exc_info:
            sync_to_git(git_repo, mock_dolt_db)

        assert exc_info.value.code == BranchSyncErrorCode.DETACHED_HEAD
        assert "detached HEAD" in exc_info.value.message

    def test_sync_to_git_not_git_repo(self, tmp_path, mock_dolt_db):
        """Test sync fails for non-git directory."""
        non_repo = tmp_path / "not_repo"
        non_repo.mkdir()

        with pytest.raises(BranchSyncError) as exc_info:
            sync_to_git(non_repo, mock_dolt_db)

        assert exc_info.value.code == BranchSyncErrorCode.GIT_NOT_REPO

    def test_sync_to_git_not_dolt_repo(self, git_repo, mock_dolt_db):
        """Test sync fails for non-dolt directory."""
        mock_dolt_db.exists.return_value = False

        with pytest.raises(BranchSyncError) as exc_info:
            sync_to_git(git_repo, mock_dolt_db)

        assert exc_info.value.code == BranchSyncErrorCode.DOLT_NOT_REPO

    def test_sync_to_git_force_checkout(self, git_repo, mock_dolt_db):
        """Test sync with force flag passes to Dolt."""
        git_branch = _git_current_branch(git_repo)
        mock_dolt_db.branch_current.return_value = "other-branch"
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="other-branch", is_current=True),
            BranchInfo(name=git_branch, is_current=False),
        ]

        sync_to_git(git_repo, mock_dolt_db, force=True)

        mock_dolt_db.branch_switch.assert_called_once_with(git_branch, force=True)


# =============================================================================
# Tests - sync_to_dolt
# =============================================================================


class TestSyncToDolt:
    """Tests for sync_to_dolt function."""

    def test_sync_to_dolt_already_in_sync(self, git_repo, mock_dolt_db):
        """Test sync when branches already match."""
        git_branch = _git_current_branch(git_repo)
        mock_dolt_db.branch_current.return_value = git_branch

        result = sync_to_dolt(git_repo, mock_dolt_db)

        assert result.git_branch == git_branch
        assert result.dolt_branch == git_branch
        assert result.created is False

    def test_sync_to_dolt_switch_branch(self, git_repo, mock_dolt_db):
        """Test sync switches Git to match Dolt."""
        dolt_branch = "feature-branch"
        mock_dolt_db.branch_current.return_value = dolt_branch

        # Create the branch in Git first
        subprocess.run(
            ["git", "branch", dolt_branch],
            cwd=git_repo,
            capture_output=True,
        )

        result = sync_to_dolt(git_repo, mock_dolt_db)

        assert result.git_branch == dolt_branch
        assert result.dolt_branch == dolt_branch
        assert result.created is False

        # Verify Git is now on the branch
        assert _git_current_branch(git_repo) == dolt_branch

    def test_sync_to_dolt_creates_missing_branch(self, git_repo, mock_dolt_db):
        """Test sync creates branch in Git if missing."""
        dolt_branch = "new-feature"
        mock_dolt_db.branch_current.return_value = dolt_branch

        result = sync_to_dolt(git_repo, mock_dolt_db)

        assert result.created is True
        assert result.git_branch == dolt_branch
        assert _git_branch_exists(git_repo, dolt_branch) is True
        assert _git_current_branch(git_repo) == dolt_branch

    def test_sync_to_dolt_not_git_repo(self, tmp_path, mock_dolt_db):
        """Test sync fails for non-git directory."""
        non_repo = tmp_path / "not_repo"
        non_repo.mkdir()

        with pytest.raises(BranchSyncError) as exc_info:
            sync_to_dolt(non_repo, mock_dolt_db)

        assert exc_info.value.code == BranchSyncErrorCode.GIT_NOT_REPO

    def test_sync_to_dolt_not_dolt_repo(self, git_repo, mock_dolt_db):
        """Test sync fails for non-dolt directory."""
        mock_dolt_db.exists.return_value = False

        with pytest.raises(BranchSyncError) as exc_info:
            sync_to_dolt(git_repo, mock_dolt_db)

        assert exc_info.value.code == BranchSyncErrorCode.DOLT_NOT_REPO


# =============================================================================
# Tests - create_both
# =============================================================================


class TestCreateBoth:
    """Tests for create_both function."""

    def test_create_both_new_branch(self, git_repo, mock_dolt_db):
        """Test creating a new branch in both systems."""
        branch_name = "feature/new-feature"
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]

        result = create_both(branch_name, git_repo, mock_dolt_db)

        assert result.git_branch == branch_name
        assert result.dolt_branch == branch_name
        assert result.created is True
        assert _git_branch_exists(git_repo, branch_name) is True
        mock_dolt_db.branch_create.assert_called_once_with(branch_name)
        mock_dolt_db.branch_switch.assert_called_once_with(branch_name, force=False)

    def test_create_both_already_exists(self, git_repo, mock_dolt_db):
        """Test creating a branch that already exists in both."""
        branch_name = "existing-branch"

        # Create in Git
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=git_repo,
            capture_output=True,
        )

        # Mock exists in Dolt
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
            BranchInfo(name=branch_name, is_current=False),
        ]

        result = create_both(branch_name, git_repo, mock_dolt_db)

        assert result.created is False
        mock_dolt_db.branch_create.assert_not_called()

    def test_create_both_no_switch(self, git_repo, mock_dolt_db):
        """Test creating without switching to new branch."""
        branch_name = "feature/no-switch"
        original_branch = _git_current_branch(git_repo)
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]

        result = create_both(branch_name, git_repo, mock_dolt_db, switch=False)

        assert result.created is True
        assert _git_current_branch(git_repo) == original_branch
        mock_dolt_db.branch_switch.assert_not_called()

    def test_create_both_dolt_fails_rollback(self, git_repo, mock_dolt_db):
        """Test Git branch is deleted if Dolt creation fails."""
        branch_name = "feature/will-fail"
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]
        mock_dolt_db.branch_create.side_effect = DoltBranchError("Invalid branch name")

        with pytest.raises(BranchSyncError):
            create_both(branch_name, git_repo, mock_dolt_db)

        # Git branch should have been rolled back
        assert _git_branch_exists(git_repo, branch_name) is False

    def test_create_both_detached_head_error(self, git_repo, mock_dolt_db):
        """Test create_both fails in detached HEAD state."""
        # Detach HEAD
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
        )
        commit = result.stdout.strip()
        subprocess.run(
            ["git", "checkout", commit],
            cwd=git_repo,
            capture_output=True,
        )

        with pytest.raises(BranchSyncError) as exc_info:
            create_both("new-branch", git_repo, mock_dolt_db)

        assert exc_info.value.code == BranchSyncErrorCode.DETACHED_HEAD

    def test_create_both_invalid_dolt_name(self, git_repo, mock_dolt_db):
        """Test error handling for invalid Dolt branch name."""
        branch_name = "feature/test"
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]
        mock_dolt_db.branch_create.side_effect = DoltBranchError(
            "Invalid branch name: illegal characters"
        )

        with pytest.raises(BranchSyncError) as exc_info:
            create_both(branch_name, git_repo, mock_dolt_db)

        assert exc_info.value.code == BranchSyncErrorCode.INVALID_BRANCH_NAME
        # Git branch should have been rolled back
        assert _git_branch_exists(git_repo, branch_name) is False

    def test_create_both_exists_only_in_git(self, git_repo, mock_dolt_db):
        """Test creating when branch exists only in Git."""
        branch_name = "git-only-branch"

        # Create in Git only
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=git_repo,
            capture_output=True,
        )

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]

        result = create_both(branch_name, git_repo, mock_dolt_db)

        assert result.created is True
        mock_dolt_db.branch_create.assert_called_once_with(branch_name)

    def test_create_both_exists_only_in_dolt(self, git_repo, mock_dolt_db):
        """Test creating when branch exists only in Dolt."""
        branch_name = "dolt-only-branch"

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
            BranchInfo(name=branch_name, is_current=False),
        ]

        result = create_both(branch_name, git_repo, mock_dolt_db)

        assert result.created is True
        mock_dolt_db.branch_create.assert_not_called()
        assert _git_branch_exists(git_repo, branch_name) is True


# =============================================================================
# Tests - BranchSyncError
# =============================================================================


class TestBranchSyncError:
    """Tests for BranchSyncError class."""

    def test_error_repr(self):
        """Test error string representation."""
        error = BranchSyncError(
            code=BranchSyncErrorCode.DETACHED_HEAD,
            message="Cannot sync in detached HEAD state",
        )
        repr_str = repr(error)
        assert "detached_head" in repr_str
        assert "Cannot sync" in repr_str

    def test_error_with_details(self):
        """Test error with additional details."""
        error = BranchSyncError(
            code=BranchSyncErrorCode.BRANCH_CREATE_FAILED,
            message="Failed to create branch",
            details="Branch name contains invalid characters",
        )
        assert error.code == BranchSyncErrorCode.BRANCH_CREATE_FAILED
        assert error.details == "Branch name contains invalid characters"


# =============================================================================
# Tests - BranchSyncResult
# =============================================================================


class TestBranchSyncResult:
    """Tests for BranchSyncResult class."""

    def test_result_fields(self):
        """Test result dataclass fields."""
        result = BranchSyncResult(
            git_branch="main",
            dolt_branch="main",
            created=True,
        )
        assert result.git_branch == "main"
        assert result.dolt_branch == "main"
        assert result.created is True

    def test_result_default_created(self):
        """Test created defaults to False."""
        result = BranchSyncResult(
            git_branch="main",
            dolt_branch="main",
        )
        assert result.created is False


# =============================================================================
# Tests - switch_both
# =============================================================================


class TestSwitchBoth:
    """Tests for switch_both function."""

    def test_switch_both_existing_branches(self, git_repo, mock_dolt_db):
        """Test switching to a branch that exists in both systems."""
        branch_name = "feature-branch"

        # Create branch in Git
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=git_repo,
            capture_output=True,
        )

        # Mock exists in Dolt
        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
            BranchInfo(name=branch_name, is_current=False),
        ]

        result = switch_both(branch_name, git_repo, mock_dolt_db)

        assert result.git_branch == branch_name
        assert result.dolt_branch == branch_name
        assert result.created is False
        assert _git_current_branch(git_repo) == branch_name
        mock_dolt_db.branch_switch.assert_called_once_with(branch_name, force=False)

    def test_switch_both_creates_missing_in_dolt(self, git_repo, mock_dolt_db):
        """Test switch creates branch in Dolt if missing."""
        branch_name = "git-only"

        # Create branch in Git only
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=git_repo,
            capture_output=True,
        )

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]

        result = switch_both(branch_name, git_repo, mock_dolt_db)

        assert result.created is True
        mock_dolt_db.branch_create.assert_called_once_with(branch_name)
        mock_dolt_db.branch_switch.assert_called_once()

    def test_switch_both_creates_missing_in_git(self, git_repo, mock_dolt_db):
        """Test switch creates branch in Git if missing."""
        branch_name = "dolt-only"

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
            BranchInfo(name=branch_name, is_current=False),
        ]

        result = switch_both(branch_name, git_repo, mock_dolt_db)

        assert result.created is True
        assert _git_branch_exists(git_repo, branch_name) is True
        assert _git_current_branch(git_repo) == branch_name

    def test_switch_both_nonexistent_branch(self, git_repo, mock_dolt_db):
        """Test switch fails for branch that doesn't exist anywhere."""
        branch_name = "nonexistent-branch"

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]

        with pytest.raises(BranchSyncError) as exc_info:
            switch_both(branch_name, git_repo, mock_dolt_db)

        assert exc_info.value.code == BranchSyncErrorCode.BRANCH_CHECKOUT_FAILED

    def test_switch_both_force(self, git_repo, mock_dolt_db):
        """Test switch with force flag."""
        branch_name = "feature-branch"

        # Create branch in Git
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=git_repo,
            capture_output=True,
        )

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
            BranchInfo(name=branch_name, is_current=False),
        ]

        switch_both(branch_name, git_repo, mock_dolt_db, force=True)

        mock_dolt_db.branch_switch.assert_called_once_with(branch_name, force=True)


# =============================================================================
# Tests - delete_both
# =============================================================================


class TestDeleteBoth:
    """Tests for delete_both function."""

    def test_delete_both_existing_branches(self, git_repo, mock_dolt_db):
        """Test deleting a branch from both systems."""
        branch_name = "feature-to-delete"

        # Create branch in Git
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=git_repo,
            capture_output=True,
        )

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
            BranchInfo(name=branch_name, is_current=False),
        ]
        mock_dolt_db.branch_current.return_value = "main"

        result = delete_both(branch_name, git_repo, mock_dolt_db)

        assert result.git_branch == branch_name
        assert _git_branch_exists(git_repo, branch_name) is False
        mock_dolt_db.branch_delete.assert_called_once_with(branch_name, force=False)

    def test_delete_both_cannot_delete_current_git(self, git_repo, mock_dolt_db):
        """Test cannot delete current Git branch."""
        current_branch = _git_current_branch(git_repo)

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name=current_branch, is_current=False),
        ]
        mock_dolt_db.branch_current.return_value = "other-branch"

        with pytest.raises(BranchSyncError) as exc_info:
            delete_both(current_branch, git_repo, mock_dolt_db)

        assert "current Git branch" in exc_info.value.message

    def test_delete_both_cannot_delete_current_dolt(self, git_repo, mock_dolt_db):
        """Test cannot delete current Dolt branch."""
        branch_name = "feature-branch"

        # Create branch in Git
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=git_repo,
            capture_output=True,
        )

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name=branch_name, is_current=True),
        ]
        mock_dolt_db.branch_current.return_value = branch_name

        with pytest.raises(BranchSyncError) as exc_info:
            delete_both(branch_name, git_repo, mock_dolt_db)

        assert "current Dolt branch" in exc_info.value.message

    def test_delete_both_nonexistent_branch(self, git_repo, mock_dolt_db):
        """Test delete fails for branch that doesn't exist."""
        branch_name = "nonexistent-branch"

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
        ]
        mock_dolt_db.branch_current.return_value = "main"

        with pytest.raises(BranchSyncError) as exc_info:
            delete_both(branch_name, git_repo, mock_dolt_db)

        assert "does not exist" in exc_info.value.message

    def test_delete_both_force(self, git_repo, mock_dolt_db):
        """Test delete with force flag."""
        branch_name = "feature-to-delete"

        # Create branch in Git
        subprocess.run(
            ["git", "branch", branch_name],
            cwd=git_repo,
            capture_output=True,
        )

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name="main", is_current=True),
            BranchInfo(name=branch_name, is_current=False),
        ]
        mock_dolt_db.branch_current.return_value = "main"

        delete_both(branch_name, git_repo, mock_dolt_db, force=True)

        mock_dolt_db.branch_delete.assert_called_once_with(branch_name, force=True)


# =============================================================================
# Tests - list_branches
# =============================================================================


class TestListBranches:
    """Tests for list_branches function."""

    def test_list_branches_in_sync(self, git_repo, mock_dolt_db):
        """Test listing branches when they're in sync."""
        current_branch = _git_current_branch(git_repo)

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name=current_branch, hash="abc1234", is_current=True),
        ]
        mock_dolt_db.branch_current.return_value = current_branch

        statuses = list_branches(git_repo, mock_dolt_db)

        assert len(statuses) == 1
        assert statuses[0].branch == current_branch
        assert statuses[0].in_sync is True
        assert statuses[0].is_current is True
        assert statuses[0].status == "clean"

    def test_list_branches_dolt_missing(self, git_repo, mock_dolt_db):
        """Test listing shows 'dolt missing' for Git-only branches."""
        current_branch = _git_current_branch(git_repo)

        # Create extra Git branch
        subprocess.run(
            ["git", "branch", "git-only"],
            cwd=git_repo,
            capture_output=True,
        )

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name=current_branch, hash="abc1234", is_current=True),
        ]
        mock_dolt_db.branch_current.return_value = current_branch

        statuses = list_branches(git_repo, mock_dolt_db)

        # Find the git-only branch
        git_only = next(s for s in statuses if s.branch == "git-only")
        assert git_only.in_sync is False
        assert git_only.status == "dolt missing"
        assert git_only.git_commit is not None
        assert git_only.dolt_commit is None

    def test_list_branches_git_missing(self, git_repo, mock_dolt_db):
        """Test listing shows 'git missing' for Dolt-only branches."""
        current_branch = _git_current_branch(git_repo)

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name=current_branch, hash="abc1234", is_current=True),
            BranchInfo(name="dolt-only", hash="def5678", is_current=False),
        ]
        mock_dolt_db.branch_current.return_value = current_branch

        statuses = list_branches(git_repo, mock_dolt_db)

        # Find the dolt-only branch
        dolt_only = next(s for s in statuses if s.branch == "dolt-only")
        assert dolt_only.in_sync is False
        assert dolt_only.status == "git missing"
        assert dolt_only.git_commit is None
        assert dolt_only.dolt_commit == "def5678"

    def test_list_branches_sorted(self, git_repo, mock_dolt_db):
        """Test branches are sorted alphabetically."""
        current_branch = _git_current_branch(git_repo)

        # Create branches
        subprocess.run(["git", "branch", "zebra"], cwd=git_repo, capture_output=True)
        subprocess.run(["git", "branch", "alpha"], cwd=git_repo, capture_output=True)

        mock_dolt_db.branch_list.return_value = [
            BranchInfo(name=current_branch, hash="abc", is_current=True),
            BranchInfo(name="zebra", hash="xyz", is_current=False),
            BranchInfo(name="alpha", hash="abc", is_current=False),
        ]
        mock_dolt_db.branch_current.return_value = current_branch

        statuses = list_branches(git_repo, mock_dolt_db)

        branch_names = [s.branch for s in statuses]
        assert branch_names == sorted(branch_names)


# =============================================================================
# Tests - BranchStatus
# =============================================================================


class TestBranchStatus:
    """Tests for BranchStatus dataclass."""

    def test_branch_status_defaults(self):
        """Test BranchStatus default values."""
        status = BranchStatus(branch="test")

        assert status.branch == "test"
        assert status.git_commit is None
        assert status.dolt_commit is None
        assert status.in_sync is False
        assert status.is_current is False
        assert status.status == "unknown"

    def test_branch_status_all_fields(self):
        """Test BranchStatus with all fields."""
        status = BranchStatus(
            branch="main",
            git_commit="abc1234",
            dolt_commit="def5678",
            in_sync=True,
            is_current=True,
            status="clean",
        )

        assert status.branch == "main"
        assert status.git_commit == "abc1234"
        assert status.dolt_commit == "def5678"
        assert status.in_sync is True
        assert status.is_current is True
        assert status.status == "clean"
