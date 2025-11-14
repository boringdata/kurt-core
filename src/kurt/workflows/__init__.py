"""
DBOS Workflows for Kurt

This module provides durable, resumable workflows for long-running operations
like content fetching, metadata extraction, and CMS syncing.

DBOS automatically:
- Checkpoints workflow state after each step
- Resumes from last completed step on crash/restart
- Provides priority queues and concurrency control
- Uses SQLite by default (no external dependencies)
"""

# Try to import DBOS, but make it optional
try:
    from dbos import DBOS

    DBOS_AVAILABLE = True
except ImportError:
    DBOS = None
    DBOS_AVAILABLE = False

# Suppress DBOS logging
import logging

logging.getLogger("dbos").setLevel(logging.ERROR)

# Global DBOS instance
_dbos_initialized = False


def init_dbos(db_path: str | None = None) -> None:
    """
    Initialize DBOS with Kurt's SQLite database.

    Args:
        db_path: Path to SQLite database. If None, uses KURT_DB_PATH env var
                or defaults to .kurt/kurt.sqlite

    Note:
        DBOS will create its own system tables in the same database:
        - dbos_workflow_status
        - dbos_workflow_inputs
        - dbos_workflow_outputs
        - dbos_workflow_events
    """
    global _dbos_initialized

    if not DBOS_AVAILABLE:
        return  # DBOS not installed, skip initialization

    if _dbos_initialized:
        return

    # Get database URL from Kurt's database client
    from dbos import DBOSConfig

    from kurt.db.database import get_database_client

    db_client = get_database_client()
    db_url = db_client.get_database_url()

    # Create DBOS configuration
    config = DBOSConfig(
        name="kurt",
        database_url=db_url,
        log_level="ERROR",  # Suppress INFO/WARNING logs
        run_admin_server=False,  # Disable admin server to avoid port conflicts
    )

    # Create DBOS instance and launch it
    try:
        import contextlib
        import io

        # Suppress DBOS stdout messages during initialization
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            _dbos_instance = DBOS(config=config)
            DBOS.launch()  # Launch the system database

        _dbos_initialized = True

        # Register cleanup handler to shutdown DBOS properly
        import atexit

        def cleanup_dbos():
            try:
                # Shutdown the executor WITHOUT canceling futures
                # This allows enqueued workflows to complete
                if hasattr(_dbos_instance, "_executor"):
                    _dbos_instance._executor.shutdown(wait=False, cancel_futures=False)
            except Exception:  # noqa: S110
                pass  # Ignore cleanup errors

        atexit.register(cleanup_dbos)

    except Exception as e:
        # DBOS may already be initialized in tests
        if "already" in str(e).lower():
            _dbos_initialized = True
        else:
            raise


def get_dbos():
    """
    Get the initialized DBOS instance.

    Returns:
        DBOS instance or None if DBOS not available

    Raises:
        RuntimeError: If DBOS is not available
    """
    if not DBOS_AVAILABLE:
        raise RuntimeError(
            "DBOS is not installed. Install it with: uv sync\n"
            "Workflows functionality requires DBOS to be installed."
        )

    if not _dbos_initialized:
        init_dbos()

    return DBOS


def is_initialized():
    """
    Check if DBOS has been initialized.

    Returns:
        bool: True if DBOS is initialized, False otherwise
    """
    return _dbos_initialized


# Auto-initialize DBOS when module is imported (if available)
# This ensures DBOS is ready for CLI commands
# Gracefully skip if database doesn't exist yet (e.g., during kurt init)
if DBOS_AVAILABLE:
    try:
        init_dbos()
    except Exception:
        # Database may not exist yet (e.g., running kurt init)
        # DBOS will be initialized on-demand later via get_dbos()
        pass


__all__ = ["init_dbos", "get_dbos", "is_initialized", "DBOS", "DBOS_AVAILABLE", "_dbos_initialized"]
