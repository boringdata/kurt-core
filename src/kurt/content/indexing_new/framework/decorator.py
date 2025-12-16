"""
Model decorator and registry for the indexing pipeline.

With configuration:
    @model(
        name="indexing.section_extractions",
        db_model=SectionExtractionRow,
        primary_key=["document_id", "section_id"],
        config_schema=SectionExtractionsConfig,
    )
    def section_extractions(
        ctx: PipelineContext,
        reader: TableReader,
        writer: TableWriter,
        config: SectionExtractionsConfig,  # auto-injected
        ...
    ):
        batch_size = config.batch_size
        ...
"""

import functools
import inspect
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional, Type

from sqlmodel import SQLModel

from .dbos_events import get_event_emitter
from .display import display
from .references import Reference, resolve_references
from .registry import ModelRegistry

if TYPE_CHECKING:
    from kurt.config import ModelConfig

logger = logging.getLogger(__name__)


def model(
    *,
    name: str,
    db_model: Type[SQLModel],
    primary_key: list[str],
    description: str = "",
    writes_to: Optional[list[str]] = None,
    write_strategy: str = "replace",
    config_schema: Optional[Type["ModelConfig"]] = None,
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
        config_schema: Optional ModelConfig subclass for step configuration.
            If provided, config is auto-loaded and passed to the function.

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

    Example with config:
        class SectionExtractionsConfig(ModelConfig):
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")
            batch_size: int = ConfigParam(default=50, ge=1, le=200)

        @model(
            name="indexing.section_extractions",
            db_model=SectionExtractionRow,
            primary_key=["document_id", "section_id"],
            config_schema=SectionExtractionsConfig,
        )
        def execute(reader, writer, config: SectionExtractionsConfig, ...):
            batch_size = config.batch_size
            ...

    The decorated function signature should be:
        (reader: TableReader, writer: TableWriter, payloads: List[dict], incremental_mode: str, **kwargs) -> dict
    """
    if write_strategy not in ("append", "merge", "replace"):
        raise ValueError(f"Invalid write_strategy: {write_strategy}")

    def decorator(func: Callable) -> Callable:
        # Validate function signature
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # Extract Reference declarations from function signature
        references = resolve_references(func)

        # Expected parameters for models (ctx is the new standard)
        expected = ["ctx", "writer"]
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
                # Get ctx and reader from kwargs for Reference binding
                ctx = kwargs.get("ctx")
                reader = kwargs.get("reader")

                # Bind References with context (if ctx and reader are available)
                if ctx is not None and reader is not None and references:
                    for param_name, ref_template in references.items():
                        # Create a new Reference instance and bind it
                        bound_ref = Reference(
                            model_name=ref_template.model_name,
                            load_content=ref_template.load_content,
                            columns=ref_template.columns,
                            filter=ref_template.filter,
                        )
                        bound_ref._bind(reader, ctx)
                        kwargs[param_name] = bound_ref

                # Load and inject config if schema is provided
                if config_schema is not None and "config" in params:
                    try:
                        config_instance = config_schema.load(name)
                        kwargs["config"] = config_instance
                        logger.debug(f"Loaded config for {name}: {config_instance}")
                    except Exception as e:
                        logger.warning(f"Failed to load config for {name}: {e}")
                        # Continue without config - use defaults from schema
                        kwargs["config"] = config_schema()

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
            "config_schema": config_schema,
            "references": references,
            "function": wrapper,
            "table_name": table_name,
        }

        # Register the model
        ModelRegistry.register(name, wrapper._model_metadata)

        return wrapper

    return decorator
