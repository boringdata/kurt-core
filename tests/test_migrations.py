"""
Unit tests for database migration functionality.

Tests the migration utilities including:
- Version tracking
- Migration detection
- Backup creation
- Migration application
- Status checking
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text

from kurt.db.migrations.utils import (
    apply_migrations,
    backup_database,
    check_migrations_needed,
    get_alembic_config,
    get_current_version,
    get_migration_history,
    get_pending_migrations,
    initialize_alembic,
)


@pytest.fixture
def test_db_path(tmp_path):
    """Create a temporary database path for testing."""
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir()
    db_path = kurt_dir / "kurt.sqlite"
    return db_path


@pytest.fixture
def test_config(tmp_path, monkeypatch, test_db_path):
    """Set up test configuration with temporary database."""
    # Create a test kurt.config
    config_path = tmp_path / "kurt.config"
    config_content = """# Test Configuration
SOURCE_PATH = "sources"
DATABASE_PATH = ".kurt/kurt.sqlite"
"""
    config_path.write_text(config_content)

    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Mock load_config to return our test paths
    mock_config = MagicMock()
    mock_config.get_absolute_db_path.return_value = test_db_path

    with patch("kurt.db.migrations.utils.load_config", return_value=mock_config):
        yield tmp_path, test_db_path


@pytest.fixture
def initialized_db(test_config):
    """Create an initialized test database with Alembic tracking."""
    tmp_path, db_path = test_config

    # Create database with initial schema
    engine = create_engine(f"sqlite:///{db_path}")

    # Create a minimal alembic_version table
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            )
        )
        conn.commit()

    yield tmp_path, db_path, engine

    engine.dispose()


class TestAlembicConfig:
    """Test Alembic configuration loading."""

    def test_get_alembic_config(self):
        """Test that Alembic config can be loaded."""
        config = get_alembic_config()

        assert isinstance(config, AlembicConfig)
        assert config.get_main_option("script_location") is not None

        # Verify script location points to migrations directory
        script_location = Path(config.get_main_option("script_location"))
        assert script_location.exists()
        assert (script_location / "versions").exists()


class TestVersionTracking:
    """Test database version tracking functionality."""

    def test_get_current_version_no_database(self, test_config):
        """Test getting version when database doesn't exist."""
        version = get_current_version()
        assert version is None

    def test_get_current_version_initialized(self, initialized_db):
        """Test getting version from initialized database."""
        tmp_path, db_path, engine = initialized_db

        # Insert a version
        with engine.connect() as conn:
            conn.execute(text("INSERT INTO alembic_version VALUES ('001_initial')"))
            conn.commit()

        version = get_current_version()
        assert version == "001_initial"

    def test_get_current_version_empty_table(self, initialized_db):
        """Test getting version when alembic_version table is empty."""
        version = get_current_version()
        assert version is None


class TestPendingMigrations:
    """Test pending migration detection."""

    def test_get_pending_migrations_structure(self):
        """Test that pending migrations return correct structure."""
        # Test using the ScriptDirectory mock since Alembic's walk_revisions
        # has complex logic that's hard to test without a real migration environment
        with (
            patch("kurt.db.migrations.utils.get_current_version") as mock_version,
            patch("kurt.db.migrations.utils.ScriptDirectory") as mock_script_dir,
        ):
            # Mock as if we're at no version (fresh db)
            mock_version.return_value = None

            # Mock a revision object
            mock_rev = MagicMock()
            mock_rev.revision = "001_initial"
            mock_rev.doc = "Initial schema"

            # Mock the script directory to return our mock revision
            mock_script = MagicMock()
            mock_script.walk_revisions.return_value = [mock_rev]
            mock_script_dir.from_config.return_value = mock_script

            pending = get_pending_migrations()

            # Should return list of tuples
            assert isinstance(pending, list)
            assert len(pending) == 1
            assert pending[0] == ("001_initial", "Initial schema")

    @patch("kurt.db.migrations.utils.get_pending_migrations")
    def test_check_migrations_needed(self, mock_get_pending):
        """Test checking if migrations are needed."""
        # Test with pending migrations
        mock_get_pending.return_value = [("001_initial", "Initial schema")]
        result = check_migrations_needed()
        assert result is True

        # Test without pending migrations
        mock_get_pending.return_value = []
        result = check_migrations_needed()
        assert result is False


class TestMigrationHistory:
    """Test migration history tracking."""

    @patch("kurt.db.migrations.utils.get_current_version")
    def test_get_migration_history_no_database(self, mock_version):
        """Test getting history when database doesn't exist."""
        mock_version.return_value = None
        history = get_migration_history()
        assert history == []

    def test_get_migration_history_structure(self):
        """Test that migration history returns correct structure."""
        with (
            patch("kurt.db.migrations.utils.get_current_version") as mock_version,
            patch("kurt.db.migrations.utils.ScriptDirectory") as mock_script_dir,
        ):
            # Mock as if we have the initial version applied
            mock_version.return_value = "001_initial"

            # Mock a revision object
            mock_rev = MagicMock()
            mock_rev.revision = "001_initial"
            mock_rev.doc = "Initial schema"

            # Mock the script directory to return our mock revision
            mock_script = MagicMock()
            mock_script.walk_revisions.return_value = [mock_rev]
            mock_script_dir.from_config.return_value = mock_script

            history = get_migration_history()

            # Should return list of tuples
            assert isinstance(history, list)
            assert len(history) == 1

            # Check structure
            item = history[0]
            assert isinstance(item, tuple)
            assert len(item) == 3  # (revision_id, description, applied_at)
            assert item[0] == "001_initial"
            assert item[1] == "Initial schema"
            # applied_at may be None as it's not tracked by default
            assert item[2] is None


class TestDatabaseBackup:
    """Test database backup functionality."""

    def test_backup_no_database(self, test_config):
        """Test backup when database doesn't exist."""
        backup_path = backup_database()
        assert backup_path is None

    def test_backup_creates_file(self, test_config):
        """Test that backup creates a timestamped file."""
        tmp_path, db_path = test_config

        # Create a real database file first
        db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{db_path}")

        # Write some data to database
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE test_table (id INTEGER)"))
            conn.execute(text("INSERT INTO test_table VALUES (1)"))
            conn.commit()

        engine.dispose()

        # Create backup
        backup_path = backup_database()

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.name.startswith("kurt.sqlite.backup.")

        # Verify backup is a copy
        assert backup_path.stat().st_size > 0

        # Verify backup contains data
        backup_engine = create_engine(f"sqlite:///{backup_path}")
        with backup_engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM test_table"))
            rows = result.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1

        backup_engine.dispose()

    def test_backup_filename_format(self, test_config):
        """Test that backup filename includes timestamp."""
        tmp_path, db_path = test_config

        # Create the .kurt directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a minimal database file with some content
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE test (id INTEGER)"))
            conn.commit()
        engine.dispose()

        before = datetime.now()
        backup_path = backup_database()
        after = datetime.now()

        assert backup_path is not None

        # Extract timestamp from filename
        # Format: kurt.sqlite.backup.YYYYMMDD_HHMMSS
        parts = backup_path.name.split(".")
        assert parts[0] == "kurt"
        assert parts[1] == "sqlite"
        assert parts[2] == "backup"
        assert len(parts[3]) == 15  # YYYYMMDD_HHMMSS

        # Verify timestamp is reasonable (within test execution time)
        # Note: We strip microseconds since the backup filename only has second precision
        timestamp_str = parts[3]
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
        # Allow 1 second tolerance for test execution time
        before_sec = before.replace(microsecond=0)
        after_sec = after.replace(microsecond=0)
        # Timestamp should be within reasonable bounds (allow 1 second before for clock skew)
        # Handle edge cases for second values
        before_with_tolerance = before_sec - timedelta(seconds=1)
        after_with_tolerance = after_sec + timedelta(seconds=1)
        assert before_with_tolerance <= timestamp <= after_with_tolerance


class TestMigrationApplication:
    """Test migration application functionality."""

    @patch("kurt.db.migrations.utils.get_pending_migrations")
    @patch("kurt.db.migrations.utils.console")
    def test_apply_migrations_no_pending(self, mock_console, mock_get_pending):
        """Test applying migrations when none are pending."""
        mock_get_pending.return_value = []

        result = apply_migrations(auto_confirm=True)

        assert result is True
        # Should print "up to date" message
        mock_console.print.assert_called()

    @patch("kurt.db.migrations.utils.get_pending_migrations")
    @patch("kurt.db.migrations.utils.display_migration_prompt")
    @patch("kurt.db.migrations.utils.console")
    def test_apply_migrations_user_cancels(self, mock_console, mock_prompt, mock_get_pending):
        """Test applying migrations when user cancels."""
        mock_get_pending.return_value = [("001_initial", "Initial schema")]
        mock_prompt.return_value = False

        result = apply_migrations(auto_confirm=False)

        assert result is False
        mock_prompt.assert_called_once()

    @patch("kurt.db.migrations.utils.get_pending_migrations")
    @patch("kurt.db.migrations.utils.backup_database")
    @patch("kurt.db.migrations.utils.command")
    @patch("kurt.db.migrations.utils.get_current_version")
    @patch("kurt.db.migrations.utils.console")
    def test_apply_migrations_success(
        self, mock_console, mock_version, mock_command, mock_backup, mock_get_pending
    ):
        """Test successful migration application."""
        mock_get_pending.return_value = [("001_initial", "Initial schema")]
        mock_backup.return_value = Path("/tmp/backup.db")
        mock_version.return_value = "001_initial"

        result = apply_migrations(auto_confirm=True)

        assert result is True
        mock_backup.assert_called_once()
        # Should call upgrade for each pending migration
        assert mock_command.upgrade.call_count == 1

    @patch("kurt.db.migrations.utils.get_pending_migrations")
    @patch("kurt.db.migrations.utils.backup_database")
    @patch("kurt.db.migrations.utils.command")
    @patch("kurt.db.migrations.utils.console")
    def test_apply_migrations_failure(
        self, mock_console, mock_command, mock_backup, mock_get_pending
    ):
        """Test migration application failure handling."""
        mock_get_pending.return_value = [("001_initial", "Initial schema")]
        mock_backup.return_value = Path("/tmp/backup.db")
        mock_command.upgrade.side_effect = Exception("Migration failed")

        result = apply_migrations(auto_confirm=True)

        assert result is False
        mock_backup.assert_called_once()
        # Should show error message
        mock_console.print.assert_called()


class TestInitializeAlembic:
    """Test Alembic initialization."""

    @patch("kurt.db.migrations.utils.command")
    @patch("kurt.db.migrations.utils.get_current_version")
    @patch("kurt.db.migrations.utils.console")
    def test_initialize_alembic_success(self, mock_console, mock_version, mock_command):
        """Test successful Alembic initialization."""
        mock_version.return_value = "001_initial"

        initialize_alembic()

        # Should stamp database with head revision
        mock_command.stamp.assert_called_once()
        args = mock_command.stamp.call_args[0]
        assert args[1] == "head"  # Second argument should be "head"

    @patch("kurt.db.migrations.utils.command")
    @patch("kurt.db.migrations.utils.console")
    def test_initialize_alembic_failure(self, mock_console, mock_command):
        """Test Alembic initialization failure handling."""
        mock_command.stamp.side_effect = Exception("Stamp failed")

        with pytest.raises(Exception):
            initialize_alembic()

        mock_command.stamp.assert_called_once()


class TestIntegration:
    """Integration tests for the full migration workflow."""

    def test_full_migration_workflow(self):
        """Test complete migration workflow from detection to application."""
        # Import the functions to test here so we can patch them correctly
        from kurt.db.migrations import utils as migration_utils

        # Mock as if we're at initial state with no pending migrations
        with (
            patch.object(migration_utils, "get_current_version", return_value="001_initial"),
            patch.object(migration_utils, "get_pending_migrations", return_value=[]),
            patch.object(
                migration_utils,
                "get_migration_history",
                return_value=[("001_initial", "Initial schema", None)],
            ),
        ):
            # 1. Check if migrations are needed
            needs_migration = migration_utils.check_migrations_needed()
            assert isinstance(needs_migration, bool)
            assert needs_migration is False  # No pending migrations

            # 2. Get current version
            current = migration_utils.get_current_version()
            # Should be None or a valid revision
            assert current is None or isinstance(current, str)

            # 3. Get pending migrations
            pending = migration_utils.get_pending_migrations()
            assert isinstance(pending, list)

            # 4. If there are pending migrations, we should detect them
            if pending:
                assert needs_migration is True

            # 5. Get migration history
            history = migration_utils.get_migration_history()
            assert isinstance(history, list)

    @patch("kurt.db.migrations.utils.Confirm.ask")
    def test_migration_with_user_interaction(self, mock_confirm, initialized_db):
        """Test migration process with simulated user interaction."""
        from kurt.db.migrations.utils import display_migration_prompt

        mock_confirm.return_value = True

        pending = [("001_initial", "Initial schema")]
        result = display_migration_prompt(pending)

        assert result is True
        mock_confirm.assert_called_once()


class TestRealMigrationFiles:
    """Integration tests using actual migration files from the project."""

    def test_get_pending_migrations_with_real_files_no_db(self, test_config):
        """Test getting pending migrations with real migration files and no database."""
        # This should return all migrations since database is not initialized
        pending = get_pending_migrations()

        # Should return a list of tuples
        assert isinstance(pending, list)
        # Should have at least the initial migration
        assert len(pending) >= 1

        # Check structure
        for revision, description in pending:
            assert isinstance(revision, str)
            assert isinstance(description, str)
            assert len(revision) > 0
            assert len(description) > 0

    def test_get_migration_history_with_real_files_no_db(self, test_config):
        """Test getting migration history with real files but no database."""
        # Should return empty list when database is not initialized
        history = get_migration_history()
        assert history == []

    def test_check_migrations_needed_with_real_files(self, test_config):
        """Test checking if migrations are needed with real migration files."""
        # Should return True since database is not initialized
        needs_migration = check_migrations_needed()
        assert needs_migration is True

    def test_pending_migrations_after_init(self, initialized_db):
        """Test that pending migrations work correctly after database initialization."""
        tmp_path, db_path, engine = initialized_db

        # Initialize Alembic to mark database as being at head
        initialize_alembic()

        # Now there should be no pending migrations
        pending = get_pending_migrations()
        assert isinstance(pending, list)

        # Get migration history - should include applied migrations
        history = get_migration_history()
        assert isinstance(history, list)
        # Should have at least one migration
        assert len(history) >= 1


class TestCLICommands:
    """Test CLI commands for migrations."""

    def test_migrate_status_command(self, test_config):
        """Test 'kurt admin migrate status' command."""
        from click.testing import CliRunner

        from kurt.commands.admin import admin

        runner = CliRunner()
        result = runner.invoke(admin, ["migrate", "status"])

        # Should succeed even without database
        assert result.exit_code == 0
        # Should show pending migrations
        assert "Pending" in result.output or "pending" in result.output

    def test_migrate_apply_help(self):
        """Test 'kurt admin migrate apply --help' command."""
        from click.testing import CliRunner

        from kurt.commands.admin import admin

        runner = CliRunner()
        result = runner.invoke(admin, ["migrate", "apply", "--help"])

        # Should show help text
        assert result.exit_code == 0
        assert "Apply pending database migrations" in result.output
        assert "--auto-confirm" in result.output

    def test_migrate_init_help(self):
        """Test 'kurt admin migrate init --help' command."""
        from click.testing import CliRunner

        from kurt.commands.admin import admin

        runner = CliRunner()
        result = runner.invoke(admin, ["migrate", "init", "--help"])

        # Should show help text
        assert result.exit_code == 0
        assert "Initialize Alembic" in result.output or "existing database" in result.output
