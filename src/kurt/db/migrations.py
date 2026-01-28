"""
Dolt database migration utilities.

This module provides migration-related functionality for Dolt databases.
Currently serves as a placeholder for migration logic that may be extracted
from other modules or added in the future.

For Alembic-based migrations, see src/kurt/db/auto_migrate.py.
For schema initialization, see src/kurt/db/schema.py.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kurt.db.connection import DoltDBConnection

logger = logging.getLogger(__name__)


def ensure_schema_up_to_date(db: "DoltDBConnection") -> bool:
    """Check if the database schema is up to date with current models.

    Verifies that all observability tables exist and logs any missing ones.

    Args:
        db: DoltDB client instance.

    Returns:
        True if all tables exist, False if any are missing.
    """
    from kurt.db.schema import OBSERVABILITY_TABLES, check_schema_exists

    status = check_schema_exists(db)
    missing = [t for t, exists in status.items() if not exists]

    if missing:
        logger.warning(f"Missing observability tables: {missing}")
        return False

    logger.debug(f"All {len(OBSERVABILITY_TABLES)} observability tables present")
    return True
