from __future__ import annotations

import atexit
import contextlib
import io

from dbos import DBOS, DBOSConfig

from kurt.db import get_database_client, init_database

_dbos_initialized = False


def _dbos_has_instance() -> bool:
    try:
        import dbos._dbos as dbos_module

        instance = getattr(dbos_module, "_dbos_global_instance", None)
        return instance is not None and getattr(instance, "_initialized", False)
    except Exception:
        return False


def init_dbos() -> None:
    """
    Initialize DBOS using kurt's database configuration.
    """
    global _dbos_initialized

    if _dbos_initialized or _dbos_has_instance():
        _dbos_initialized = True
        return

    init_database()
    db_url = get_database_client().get_database_url()

    config = DBOSConfig(
        name="kurt",
        database_url=db_url,
        log_level="ERROR",
        run_admin_server=False,
    )

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            DBOS(config=config)
            DBOS.launch()
        _dbos_initialized = True
    except Exception as exc:
        if "already" in str(exc).lower():
            _dbos_initialized = True
        else:
            raise

    atexit.register(destroy_dbos)


def destroy_dbos() -> None:
    """Best-effort cleanup for DBOS."""
    try:
        DBOS.destroy(workflow_completion_timeout_sec=0)
    except Exception:
        pass
