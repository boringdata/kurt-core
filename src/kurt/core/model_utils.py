"""
Model utilities for dynamic SQLModel discovery and table creation.

Provides functions for:
- Finding SQLModel classes by table name from workflow models.py files
- Ensuring tables exist in the database

Used by SaveStep and agent tools to work with user-defined workflow tables.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from sqlmodel import SQLModel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def get_model_by_table_name(
    table: str,
    *,
    workflow_dir: Path | str | None = None,
) -> type[SQLModel] | None:
    """
    Find SQLModel class by __tablename__ from workflow's models.py.

    Searches for a models.py file in the workflow directory and returns
    the SQLModel class that has the matching __tablename__.

    Args:
        table: The table name to search for (e.g., "competitor_analysis")
        workflow_dir: Optional path to the workflow directory containing models.py.
                     If not provided, uses current working directory.

    Returns:
        The SQLModel class if found, None otherwise.

    Raises:
        ImportError: If models.py cannot be imported due to syntax errors
        ValueError: If multiple models have the same table name

    Example:
        # Find model by table name
        model = get_model_by_table_name("competitor_analysis")
        if model:
            instance = model(company="Acme", products=["Widget"])
    """
    if workflow_dir is None:
        workflow_dir = Path.cwd()
    else:
        workflow_dir = Path(workflow_dir)

    # Look for models.py in workflow directory
    models_path = workflow_dir / "models.py"

    if not models_path.exists():
        logger.debug(f"No models.py found at {models_path}")
        return None

    # Load the module dynamically
    module = _load_module_from_path(models_path)
    if module is None:
        return None

    # Search for SQLModel class with matching __tablename__
    return _find_model_in_module(module, table)


def _load_module_from_path(path: Path) -> object | None:
    """
    Dynamically load a Python module from a file path.

    Args:
        path: Path to the Python module file

    Returns:
        The loaded module, or None if loading fails
    """
    module_name = f"_workflow_models_{path.parent.name}_{id(path)}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            logger.warning(f"Could not create module spec for {path}")
            return None

        module = importlib.util.module_from_spec(spec)

        # Temporarily add parent directory to sys.path for imports
        parent_dir = str(path.parent)
        original_path = sys.path.copy()

        try:
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            spec.loader.exec_module(module)
        finally:
            sys.path = original_path

        return module

    except Exception as e:
        logger.warning(f"Failed to load module from {path}: {e}")
        raise ImportError(f"Cannot import models.py: {e}") from e


def _find_model_in_module(module: object, table_name: str) -> type[SQLModel] | None:
    """
    Find a SQLModel class with the given __tablename__ in a module.

    Args:
        module: The loaded Python module
        table_name: The table name to search for

    Returns:
        The SQLModel class if found, None otherwise

    Raises:
        ValueError: If multiple models have the same table name
    """
    matches: list[type[SQLModel]] = []

    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue

        attr = getattr(module, attr_name)

        # Check if it's a SQLModel table class
        if not isinstance(attr, type):
            continue
        if not issubclass(attr, SQLModel):
            continue
        if attr is SQLModel:
            continue

        # Check __tablename__
        if hasattr(attr, "__tablename__") and attr.__tablename__ == table_name:
            matches.append(attr)

    if len(matches) > 1:
        model_names = [m.__name__ for m in matches]
        raise ValueError(
            f"Multiple models found with table name '{table_name}': {model_names}"
        )

    return matches[0] if matches else None


def ensure_table_exists(model: type[SQLModel]) -> None:
    """
    Create table if not exists via SQLModel.metadata.create_all.

    Uses the database engine from kurt.db to create the table for the
    provided SQLModel class. Safe to call multiple times - will not
    error if table already exists.

    Args:
        model: The SQLModel class to create a table for

    Example:
        from myworkflow.models import CompetitorAnalysis
        ensure_table_exists(CompetitorAnalysis)
        # Table is now created and ready for use
    """
    from kurt.db import ensure_tables

    ensure_tables([model])


def find_models_in_workflow(
    workflow_dir: Path | str | None = None,
) -> list[type[SQLModel]]:
    """
    Find all SQLModel classes defined in a workflow's models.py.

    Useful for initializing all workflow tables at once.

    Args:
        workflow_dir: Path to the workflow directory containing models.py.
                     If not provided, uses current working directory.

    Returns:
        List of SQLModel classes found in models.py

    Example:
        models = find_models_in_workflow("/path/to/my_workflow")
        for model in models:
            ensure_table_exists(model)
    """
    if workflow_dir is None:
        workflow_dir = Path.cwd()
    else:
        workflow_dir = Path(workflow_dir)

    models_path = workflow_dir / "models.py"

    if not models_path.exists():
        return []

    module = _load_module_from_path(models_path)
    if module is None:
        return []

    models: list[type[SQLModel]] = []

    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue

        attr = getattr(module, attr_name)

        # Check if it's a SQLModel table class
        if not isinstance(attr, type):
            continue
        if not issubclass(attr, SQLModel):
            continue
        if attr is SQLModel:
            continue

        # Only include actual table models (have __tablename__)
        if hasattr(attr, "__tablename__"):
            models.append(attr)

    return models


def ensure_all_workflow_tables(workflow_dir: Path | str | None = None) -> int:
    """
    Create all tables defined in a workflow's models.py.

    Convenience function to initialize all workflow tables at once.

    Args:
        workflow_dir: Path to the workflow directory containing models.py.
                     If not provided, uses current working directory.

    Returns:
        Number of tables created/ensured

    Example:
        count = ensure_all_workflow_tables("/path/to/my_workflow")
        print(f"Ensured {count} tables exist")
    """
    models = find_models_in_workflow(workflow_dir)

    for model in models:
        ensure_table_exists(model)

    return len(models)
