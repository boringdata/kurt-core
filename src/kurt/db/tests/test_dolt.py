"""Tests for DoltDB client."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kurt.db.dolt import (
    BranchInfo,
    ConnectionPool,
    DoltBranchError,
    DoltConnectionError,
    DoltDB,
    DoltQueryError,
    DoltTransaction,
    DoltTransactionError,
    QueryResult,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def dolt_available() -> bool:
    """Check if dolt CLI is available."""
    return shutil.which("dolt") is not None


@pytest.fixture
def tmp_dolt_repo(tmp_path: Path, dolt_available: bool) -> Path | None:
    """Create a temporary Dolt repository for testing.

    Returns None if dolt is not installed.
    """
    if not dolt_available:
        pytest.skip("Dolt CLI not installed")

    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize dolt repo
    subprocess.run(
        ["dolt", "init"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Configure git user for commits (--set required in newer Dolt versions)
    subprocess.run(
        ["dolt", "config", "--local", "--set", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["dolt", "config", "--local", "--set", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


# =============================================================================
# QueryResult Tests
# =============================================================================


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_empty_result(self):
        """Test empty QueryResult."""
        result = QueryResult(rows=[])
        assert len(result) == 0
        assert list(result) == []

    def test_result_with_rows(self):
        """Test QueryResult with rows."""
        rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        result = QueryResult(rows=rows)

        assert len(result) == 2
        assert list(result) == rows

    def test_result_iteration(self):
        """Test iterating over QueryResult."""
        rows = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = QueryResult(rows=rows)

        ids = [row["id"] for row in result]
        assert ids == [1, 2, 3]

    def test_affected_rows(self):
        """Test affected_rows field."""
        result = QueryResult(rows=[], affected_rows=5)
        assert result.affected_rows == 5

    def test_last_insert_id(self):
        """Test last_insert_id field."""
        result = QueryResult(rows=[], last_insert_id=42)
        assert result.last_insert_id == 42


# =============================================================================
# BranchInfo Tests
# =============================================================================


class TestBranchInfo:
    """Tests for BranchInfo dataclass."""

    def test_basic_branch(self):
        """Test basic BranchInfo."""
        branch = BranchInfo(name="main", hash="abc123", is_current=True)
        assert branch.name == "main"
        assert branch.hash == "abc123"
        assert branch.is_current is True
        assert branch.remote is None

    def test_remote_branch(self):
        """Test remote BranchInfo."""
        branch = BranchInfo(name="feature", hash="def456", remote="origin")
        assert branch.name == "feature"
        assert branch.remote == "origin"


# =============================================================================
# DoltTransaction Tests
# =============================================================================


class TestDoltTransaction:
    """Tests for DoltTransaction."""

    def test_execute_queues_statements(self):
        """Test that execute queues statements."""
        mock_db = MagicMock()
        tx = DoltTransaction(_db=mock_db)

        tx.execute("INSERT INTO users VALUES (?)", [1])
        tx.execute("INSERT INTO users VALUES (?)", [2])

        assert len(tx._statements) == 2
        assert tx._statements[0] == ("INSERT INTO users VALUES (?)", [1])
        assert tx._statements[1] == ("INSERT INTO users VALUES (?)", [2])

    def test_execute_after_commit_raises(self):
        """Test that execute after commit raises error."""
        mock_db = MagicMock()
        tx = DoltTransaction(_db=mock_db)
        tx._committed = True

        with pytest.raises(DoltTransactionError, match="already finished"):
            tx.execute("SELECT 1", [])

    def test_execute_after_rollback_raises(self):
        """Test that execute after rollback raises error."""
        mock_db = MagicMock()
        tx = DoltTransaction(_db=mock_db)
        tx._rolled_back = True

        with pytest.raises(DoltTransactionError, match="already finished"):
            tx.execute("SELECT 1", [])

    def test_query_calls_db(self):
        """Test that query calls db.query directly."""
        mock_db = MagicMock()
        mock_db.query.return_value = QueryResult(rows=[{"id": 1}])
        tx = DoltTransaction(_db=mock_db)

        result = tx.query("SELECT * FROM users", [])

        mock_db.query.assert_called_once_with("SELECT * FROM users", [])
        assert result.rows == [{"id": 1}]

    def test_commit_executes_all_statements(self):
        """Test that commit executes all queued statements."""
        mock_db = MagicMock()
        mock_db.execute.return_value = QueryResult(rows=[], affected_rows=1)
        tx = DoltTransaction(_db=mock_db)

        tx.execute("INSERT INTO users VALUES (?)", [1])
        tx.execute("INSERT INTO users VALUES (?)", [2])
        tx._commit()

        assert mock_db.execute.call_count == 2
        assert tx._committed is True

    def test_commit_rolls_back_on_error(self):
        """Test that commit marks rollback on error."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("DB error")
        tx = DoltTransaction(_db=mock_db)

        tx.execute("INSERT INTO users VALUES (?)", [1])

        with pytest.raises(DoltTransactionError, match="Transaction failed"):
            tx._commit()

        assert tx._rolled_back is True

    def test_rollback_clears_statements(self):
        """Test that rollback clears statements."""
        mock_db = MagicMock()
        tx = DoltTransaction(_db=mock_db)

        tx.execute("INSERT INTO users VALUES (?)", [1])
        tx._rollback()

        assert len(tx._statements) == 0
        assert tx._rolled_back is True


# =============================================================================
# DoltDB Initialization Tests
# =============================================================================


class TestDoltDBInit:
    """Tests for DoltDB initialization (server-only mode)."""

    def test_init_server_mode_no_dolt_check(self):
        """Test server mode doesn't check for dolt CLI."""
        with patch("shutil.which", return_value=None):
            # Should not raise - server mode doesn't need CLI
            db = DoltDB("/tmp/test", mode="server")
            assert db.mode == "server"

    def test_init_default_settings(self):
        """Test default initialization settings (server mode)."""
        with patch("shutil.which", return_value=None):
            # Server mode is default and doesn't require dolt CLI
            db = DoltDB("/tmp/test_repo")

            assert db.path == Path("/tmp/test_repo").resolve()
            assert db.mode == "server"
            assert db._host == "localhost"
            assert db._port == 3306
            assert db._user == "root"
            assert db._password == ""
            assert db._database == "test_repo"
            assert db._pool_size == 5

    def test_init_custom_server_settings(self):
        """Test custom server mode settings."""
        with patch("shutil.which", return_value=None):
            db = DoltDB(
                "/tmp/test",
                mode="server",
                host="db.example.com",
                port=3307,
                user="admin",
                password="secret",
                database="mydb",
                pool_size=10,
            )

            assert db._host == "db.example.com"
            assert db._port == 3307
            assert db._user == "admin"
            assert db._password == "secret"
            assert db._database == "mydb"
            assert db._pool_size == 10


# =============================================================================
# DoltDB Repository Management Tests
# =============================================================================


class TestDoltDBRepository:
    """Tests for DoltDB repository management."""

    def test_exists_returns_true_when_repo_exists(self, tmp_dolt_repo: Path):
        """Test exists returns True for existing repo."""
        db = DoltDB(tmp_dolt_repo)
        assert db.exists() is True

    def test_exists_returns_false_when_no_repo(self, tmp_path: Path, dolt_available: bool):
        """Test exists returns False when no repo."""
        if not dolt_available:
            pytest.skip("Dolt CLI not installed")

        db = DoltDB(tmp_path / "no_repo")
        assert db.exists() is False

    def test_init_creates_repo(self, tmp_path: Path, dolt_available: bool):
        """Test init creates a new repository."""
        if not dolt_available:
            pytest.skip("Dolt CLI not installed")

        repo_path = tmp_path / "new_repo"
        db = DoltDB(repo_path)

        assert db.exists() is False
        db.init()
        assert db.exists() is True

    def test_init_skips_existing_repo(self, tmp_dolt_repo: Path):
        """Test init doesn't fail on existing repo."""
        db = DoltDB(tmp_dolt_repo)
        # Should not raise
        db.init()
        assert db.exists() is True


# =============================================================================
# DoltDB Query Tests (Embedded Mode)
# =============================================================================


class TestDoltDBQueryEmbedded:
    """Tests for DoltDB query operations in embedded mode."""

    def test_query_select(self, tmp_dolt_repo: Path):
        """Test SELECT query returns results."""
        db = DoltDB(tmp_dolt_repo)

        # Create a table and insert data
        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")
        db.execute("INSERT INTO users VALUES (1, 'Alice')")
        db.execute("INSERT INTO users VALUES (2, 'Bob')")

        result = db.query("SELECT * FROM users ORDER BY id")

        assert len(result) == 2
        assert result.rows[0]["id"] == 1
        assert result.rows[0]["name"] == "Alice"
        assert result.rows[1]["id"] == 2
        assert result.rows[1]["name"] == "Bob"

    def test_query_with_parameters(self, tmp_dolt_repo: Path):
        """Test query with parameter interpolation."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")
        db.execute("INSERT INTO users VALUES (1, 'Alice')")
        db.execute("INSERT INTO users VALUES (2, 'Bob')")

        result = db.query("SELECT * FROM users WHERE id = ?", [1])

        assert len(result) == 1
        assert result.rows[0]["name"] == "Alice"

    def test_query_one_returns_first_row(self, tmp_dolt_repo: Path):
        """Test query_one returns first row."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")
        db.execute("INSERT INTO users VALUES (1, 'Alice')")
        db.execute("INSERT INTO users VALUES (2, 'Bob')")

        row = db.query_one("SELECT * FROM users ORDER BY id")

        assert row is not None
        assert row["id"] == 1
        assert row["name"] == "Alice"

    def test_query_one_returns_none_when_empty(self, tmp_dolt_repo: Path):
        """Test query_one returns None for empty result."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")

        row = db.query_one("SELECT * FROM users")

        assert row is None

    def test_execute_create_table(self, tmp_dolt_repo: Path):
        """Test execute for CREATE TABLE."""
        db = DoltDB(tmp_dolt_repo)

        result = db.execute("CREATE TABLE test (id INT PRIMARY KEY)")

        # Should not raise
        assert result.rows == []

    def test_execute_insert(self, tmp_dolt_repo: Path):
        """Test execute for INSERT."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")
        db.execute("INSERT INTO users VALUES (1, 'Alice')")

        # Verify data was inserted
        query_result = db.query("SELECT * FROM users")
        assert len(query_result) == 1


# =============================================================================
# DoltDB Parameter Interpolation Tests
# =============================================================================


class TestDoltDBParameterInterpolation:
    """Tests for parameter interpolation in embedded mode."""

    def test_interpolate_string(self, tmp_dolt_repo: Path):
        """Test string parameter interpolation."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")
        db.execute("INSERT INTO users VALUES (?, ?)", [1, "Alice"])

        result = db.query("SELECT * FROM users")
        assert result.rows[0]["name"] == "Alice"

    def test_interpolate_string_with_quotes(self, tmp_dolt_repo: Path):
        """Test string with single quotes is properly escaped."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")
        db.execute("INSERT INTO users VALUES (?, ?)", [1, "O'Brien"])

        result = db.query("SELECT * FROM users")
        assert result.rows[0]["name"] == "O'Brien"

    def test_interpolate_integer(self, tmp_dolt_repo: Path):
        """Test integer parameter interpolation."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE numbers (id INT PRIMARY KEY, value INT)")
        db.execute("INSERT INTO numbers VALUES (1, ?)", [42])

        result = db.query("SELECT * FROM numbers")
        assert result.rows[0]["value"] == 42

    def test_interpolate_float(self, tmp_dolt_repo: Path):
        """Test float parameter interpolation."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE numbers (id INT PRIMARY KEY, value DOUBLE)")
        db.execute("INSERT INTO numbers VALUES (1, ?)", [3.14])

        result = db.query("SELECT * FROM numbers")
        assert abs(result.rows[0]["value"] - 3.14) < 0.001

    def test_interpolate_null(self, tmp_dolt_repo: Path):
        """Test NULL parameter interpolation."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")
        db.execute("INSERT INTO users VALUES (?, ?)", [1, None])

        result = db.query("SELECT * FROM users")
        # Dolt JSON output omits NULL columns, so 'name' is not in the result
        assert result.rows[0]["id"] == 1
        assert "name" not in result.rows[0]  # NULL columns are omitted

    def test_interpolate_boolean(self, tmp_dolt_repo: Path):
        """Test boolean parameter interpolation."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE flags (id INT PRIMARY KEY, active BOOLEAN)")
        db.execute("INSERT INTO flags VALUES (?, ?)", [1, True])
        db.execute("INSERT INTO flags VALUES (?, ?)", [2, False])

        result = db.query("SELECT * FROM flags ORDER BY id")
        assert result.rows[0]["active"] == 1  # MySQL stores as 1/0
        assert result.rows[1]["active"] == 0


# =============================================================================
# DoltDB Transaction Tests
# =============================================================================


class TestDoltDBTransaction:
    """Tests for DoltDB transaction context manager."""

    def test_transaction_commits_on_success(self, tmp_dolt_repo: Path):
        """Test transaction commits on successful exit."""
        db = DoltDB(tmp_dolt_repo)
        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")

        with db.transaction() as tx:
            tx.execute("INSERT INTO users VALUES (?, ?)", [1, "Alice"])
            tx.execute("INSERT INTO users VALUES (?, ?)", [2, "Bob"])

        result = db.query("SELECT * FROM users ORDER BY id")
        assert len(result) == 2

    def test_transaction_rollback_on_exception(self, tmp_dolt_repo: Path):
        """Test transaction rolls back on exception."""
        db = DoltDB(tmp_dolt_repo)
        db.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))")
        db.execute("INSERT INTO users VALUES (1, 'Existing')")

        with pytest.raises(Exception):
            with db.transaction() as tx:
                tx.execute("INSERT INTO users VALUES (?, ?)", [2, "New"])
                raise Exception("Simulated error")

        # Only the original row should exist
        # Note: In embedded mode, statements are executed on commit,
        # so rollback means statements are discarded before execution
        result = db.query("SELECT * FROM users")
        assert len(result) == 1


# =============================================================================
# DoltDB Branch Tests
# =============================================================================


class TestDoltDBBranch:
    """Tests for DoltDB branch operations."""

    def test_branch_current_returns_main(self, tmp_dolt_repo: Path):
        """Test branch_current returns main initially."""
        db = DoltDB(tmp_dolt_repo)
        # Dolt defaults to 'main' branch
        assert db.branch_current() == "main"

    def test_branch_list_includes_main(self, tmp_dolt_repo: Path):
        """Test branch_list includes main branch."""
        db = DoltDB(tmp_dolt_repo)

        branches = db.branch_list()

        assert len(branches) >= 1
        names = [b.name for b in branches]
        assert "main" in names

    def test_branch_create_and_list(self, tmp_dolt_repo: Path):
        """Test creating a branch and listing it."""
        db = DoltDB(tmp_dolt_repo)

        db.branch_create("feature/test")

        branches = db.branch_list()
        names = [b.name for b in branches]
        assert "feature/test" in names

    def test_branch_switch(self, tmp_dolt_repo: Path):
        """Test switching branches."""
        db = DoltDB(tmp_dolt_repo)

        db.branch_create("feature/test")
        db.branch_switch("feature/test")

        assert db.branch_current() == "feature/test"

    def test_branch_switch_back_to_main(self, tmp_dolt_repo: Path):
        """Test switching back to main."""
        db = DoltDB(tmp_dolt_repo)

        db.branch_create("feature/test")
        db.branch_switch("feature/test")
        db.branch_switch("main")

        assert db.branch_current() == "main"

    def test_branch_delete(self, tmp_dolt_repo: Path):
        """Test deleting a branch."""
        db = DoltDB(tmp_dolt_repo)

        db.branch_create("feature/to-delete")
        db.branch_delete("feature/to-delete", force=True)

        branches = db.branch_list()
        names = [b.name for b in branches]
        assert "feature/to-delete" not in names

    def test_branch_create_from_start_point(self, tmp_dolt_repo: Path):
        """Test creating branch from specific commit."""
        db = DoltDB(tmp_dolt_repo)

        # Create some data and commit
        db.execute("CREATE TABLE test (id INT PRIMARY KEY)")
        db.commit("Initial commit")

        # Create branch from main
        db.branch_create("feature/from-main", "main")

        branches = db.branch_list()
        names = [b.name for b in branches]
        assert "feature/from-main" in names


# =============================================================================
# DoltDB Commit Tests
# =============================================================================


class TestDoltDBCommit:
    """Tests for DoltDB version control commits."""

    def test_commit_with_message(self, tmp_dolt_repo: Path):
        """Test creating a commit with message."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE test (id INT PRIMARY KEY)")
        commit_hash = db.commit("Add test table")

        # Should return a hash (might be empty string if nothing to commit)
        assert isinstance(commit_hash, str)

    def test_commit_with_author(self, tmp_dolt_repo: Path):
        """Test creating a commit with custom author."""
        db = DoltDB(tmp_dolt_repo)

        db.execute("CREATE TABLE test2 (id INT PRIMARY KEY)")
        commit_hash = db.commit("Add test2 table", author="Custom User <custom@example.com>")

        assert isinstance(commit_hash, str)


# =============================================================================
# DoltDB Error Handling Tests
# =============================================================================


class TestDoltDBErrors:
    """Tests for DoltDB error handling."""

    def test_query_invalid_sql_raises(self, tmp_dolt_repo: Path):
        """Test invalid SQL raises DoltQueryError."""
        db = DoltDB(tmp_dolt_repo)

        with pytest.raises(DoltQueryError):
            db.query("SELECT * FROM nonexistent_table")

    def test_branch_switch_nonexistent_raises(self, tmp_dolt_repo: Path):
        """Test switching to nonexistent branch raises DoltBranchError."""
        db = DoltDB(tmp_dolt_repo)

        with pytest.raises(DoltBranchError, match="Failed to switch"):
            db.branch_switch("nonexistent-branch")


# =============================================================================
# ConnectionPool Tests
# =============================================================================


class TestConnectionPool:
    """Tests for ConnectionPool (server mode)."""

    def test_pool_raises_when_no_mysql_lib(self):
        """Test pool raises when no MySQL library available."""
        pool = ConnectionPool(
            host="localhost",
            port=3306,
            user="root",
            password="",
            database="test",
            pool_size=5,
        )

        # Mock both mysql libraries as unavailable
        with patch.dict("sys.modules", {"mysql.connector": None, "pymysql": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(DoltConnectionError, match="requires mysql-connector-python"):
                    pool._create_connection()


# =============================================================================
# DoltDB Context Manager Tests
# =============================================================================


class TestDoltDBContextManager:
    """Tests for DoltDB context manager."""

    def test_context_manager_closes_pool(self):
        """Test context manager closes pool on exit."""
        with patch("shutil.which", return_value=None):
            db = DoltDB("/tmp/test", mode="server")
            mock_pool = MagicMock()
            db._pool = mock_pool

            with db:
                pass

            # Pool is set to None after close, so check the mock directly
            mock_pool.close_all.assert_called_once()
            assert db._pool is None

    def test_context_manager_without_pool(self, dolt_available: bool):
        """Test context manager works without pool."""
        if not dolt_available:
            pytest.skip("Dolt CLI not installed")

        db = DoltDB("/tmp/test")

        # Should not raise
        with db:
            pass
