"""
Model decorator for the indexing pipeline.

Models declare dependencies using Reference() in function signatures.
References are lazy-loaded when accessed.

Example:
    @model(name="indexing.extractions", db_model=..., primary_key=[...])
    def extractions(
        ctx: PipelineContext,
        sections=Reference("indexing.document_sections"),
        writer: TableWriter,
    ):
        # sections.df triggers lazy load
        df = sections.df
        # Access context
        doc_ids = ctx.document_ids

With configuration:
    @model(
        name="indexing.section_extractions",
        db_model=SectionExtractionRow,
        primary_key=["document_id", "section_id"],
        config_schema=SectionExtractionsConfig,
    )
    def section_extractions(
        ctx: PipelineContext,
        sections=Reference("indexing.document_sections"),
        writer: TableWriter,
        config: SectionExtractionsConfig,  # auto-injected
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
        )
        def section_extractions(
            ctx: PipelineContext,
            sections=Reference("indexing.document_sections"),
            writer: TableWriter,
        ):
            # sections is a lazy Reference - data loaded when accessed
            df = sections.df  # triggers load

            # Or iterate directly
            for row in sections:
                process(row)

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
        def section_extractions(
            ctx: PipelineContext,
            sections=Reference("indexing.document_sections"),
            writer: TableWriter,
            config: SectionExtractionsConfig,  # auto-injected
        ):
            batch_size = config.batch_size
            ...
    """
    if write_strategy not in ("append", "merge", "replace"):
        raise ValueError(f"Invalid write_strategy: {write_strategy}")

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())

        # Extract Reference declarations from function signature
        references = resolve_references(func)

        # Expected parameters for models (ctx is the new standard)
        expected = ["ctx", "writer"]
        for exp in expected:
            if exp not in params:
                logger.warning(f"Model {name} missing parameter: {exp}")

        # Derive table name from model name (convention: indexing.foo -> indexing_foo)
        table_name = name.replace(".", "_")

        # Override the table name on the SQLModel to match the model name convention
        # This ensures consistency between model names and table names for DAG building
        db_model.__tablename__ = table_name

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            event_emitter = get_event_emitter()

            if event_emitter:
                event_emitter.emit_model_started(name, description)

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
                    logger.debug(
                        f"Bound {len(references)} lazy references: {list(references.keys())}"
                    )

                # Load and inject config if schema is provided and not already passed
                if config_schema is not None and "config" in params and "config" not in kwargs:
                    try:
                        config_instance = config_schema.load(name)
                        kwargs["config"] = config_instance
                        logger.debug(f"Loaded config for {name}: {config_instance}")
                    except Exception as e:
                        logger.warning(f"Failed to load config for {name}: {e}")
                        # Continue without config - use defaults from _param_metadata
                        # Only include params that have non-None defaults (skip fallback-only params)
                        defaults = {
                            param_name: param.default
                            for param_name, param in config_schema._param_metadata.items()
                            if param.default is not None
                        }
                        kwargs["config"] = config_schema(**defaults)

                # Filter kwargs to only include parameters the function accepts
                filtered_kwargs = {k: v for k, v in kwargs.items() if k in params}

                # Execute the model function
                result = func(*args, **filtered_kwargs)

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

                if event_emitter:
                    rows_written = result.get("rows_written", 0)
                    event_emitter.emit_model_completed(
                        name, rows_written, result.get("table_name", table_name)
                    )

                # Build stats summary for display - pass through all result keys
                # Framework stays generic, steps define what stats they return
                display_summary = {
                    "status": "completed",
                    "rows_written": result.get("rows_written", 0),
                    "execution_time": f"{result.get('execution_time', 0):.2f}s",
                }
                # Pass through all stats from result (except internal keys)
                internal_keys = {
                    "rows_written",
                    "rows_deduplicated",
                    "table_name",
                    "model_name",
                    "execution_time",
                    "result",
                }
                for key, value in result.items():
                    if key not in internal_keys and isinstance(value, (int, float, str)):
                        display_summary[key] = value

                display.end_step(name, display_summary)

                return result

            except Exception as e:
                if event_emitter:
                    event_emitter.emit_model_failed(name, str(e))

                display.end_step(name, {"status": "failed", "error": str(e)})
                logger.error(f"Model failed: {name}")
                raise

        # Store metadata for registry
        wrapper._model_metadata = {
            "name": name,
            "db_model": db_model,
            "primary_key": primary_key,
            "description": description,
            "references": references,
            "writes_to": writes_to or [],
            "write_strategy": write_strategy,
            "config_schema": config_schema,
            "function": wrapper,
            "table_name": table_name,
        }

        # Register the model
        ModelRegistry.register(name, wrapper._model_metadata)

        return wrapper

    return decorator
