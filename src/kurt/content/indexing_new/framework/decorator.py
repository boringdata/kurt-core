"""
Model decorator and registry for the indexing pipeline.
"""

import functools
import inspect
import logging
from datetime import datetime
from typing import Callable, Optional, Type

from sqlmodel import SQLModel

from .dbos_events import get_event_emitter
from .display import display
from .registry import ModelRegistry

logger = logging.getLogger(__name__)


def model(
    *,
    name: str,
    db_model: Type[SQLModel],
    primary_key: list[str],
    description: str = "",
    writes_to: Optional[list[str]] = None,
    write_strategy: str = "replace",
) -> Callable:
    """
    Decorator for defining indexing pipeline models.

    Args:
        name: Unique model identifier (e.g., "indexing.section_extractions")
        db_model: SQLModel class defining the table schema
        primary_key: List of column names forming the primary key
        description: Human-readable description of the model's purpose
        writes_to: Optional list of persistent tables this model will mutate
        write_strategy: Default write strategy ("append", "merge", "replace")

    Example:
        @model(
            name="indexing.section_extractions",
            db_model=SectionExtractionRow,
            primary_key=["document_id", "section_id"],
            description="Runs DSPy extraction per section",
        )
        def execute(reader: TableReader, writer: TableWriter, filters: DocumentFilters):
            sections = reader.load("indexing.section_llm_inputs")
            # ... process sections
            return writer.write(results)

    The decorated function signature should be:
        (reader: TableReader, writer: TableWriter, payloads: List[dict], incremental_mode: str, **kwargs) -> dict
    """
    if write_strategy not in ("append", "merge", "replace"):
        raise ValueError(f"Invalid write_strategy: {write_strategy}")

    def decorator(func: Callable) -> Callable:
        # Validate function signature
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # Expected parameters for models
        expected = ["reader", "writer", "payloads", "incremental_mode"]
        for exp in expected:
            if exp not in params:
                logger.warning(f"Model {name} missing parameter: {exp}")

        # Derive table name from model name (replace dots with underscores)
        table_name = name.replace(".", "_")

        # Set the table name on the SQLModel if not already set
        if not hasattr(db_model, "__tablename__"):
            db_model.__tablename__ = table_name

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            event_emitter = get_event_emitter()

            # Emit model started event
            if event_emitter:
                event_emitter.emit_model_started(name, description)

            # Display execution status
            display.start_step(name, description)

            try:
                # Execute the model function
                result = func(*args, **kwargs)

                # Ensure result is a dict
                if not isinstance(result, dict):
                    result = {"result": result}

                # Add metadata
                result.update(
                    {
                        "model_name": name,
                        "execution_time": (datetime.utcnow() - start_time).total_seconds(),
                        "table_name": table_name,
                    }
                )

                # Emit model completed event
                if event_emitter:
                    rows_written = result.get("rows_written", 0)
                    event_emitter.emit_model_completed(
                        name, rows_written, result.get("table_name", table_name)
                    )

                # Display success
                display.end_step(
                    name,
                    {
                        "status": "completed",
                        "rows_written": result.get("rows_written", 0),
                        "execution_time": f"{result.get('execution_time', 0):.2f}s",
                    },
                )

                return result

            except Exception as e:
                # Emit model failed event
                if event_emitter:
                    event_emitter.emit_model_failed(name, str(e))

                # Display error
                display.end_step(name, {"status": "failed", "error": str(e)})
                logger.error(f"Model failed: {name}")
                raise

        # Store the wrapper function for execution
        wrapper._model_metadata = {
            "name": name,
            "db_model": db_model,
            "primary_key": primary_key,
            "description": description,
            "writes_to": writes_to or [],
            "write_strategy": write_strategy,
            "function": wrapper,
            "table_name": table_name,
        }

        # Register the model
        ModelRegistry.register(name, wrapper._model_metadata)

        return wrapper

    return decorator
