"""
Model decorator for the indexing pipeline.

Models declare dependencies using Reference() in function signatures.
References provide SQLAlchemy Query objects - no prefetching, user filters in code.

Decorators:
    @table(schema) - Generate SQLModel from Pydantic schema (timestamps at END)
    @model(...) - Define pipeline model with dependencies

Utilities:
    apply_dspy_on_df(df, signature, ...) - Apply DSPy to DataFrame rows (explicit, not decorator)

Example with @table:
    class DocumentSchema(BaseModel):
        title: str
        source_url: Optional[str] = None

    @model(name="indexing.documents", primary_key=["id"])
    @table(DocumentSchema)
    def documents(ctx: PipelineContext, writer: TableWriter):
        ...

Example with apply_dspy_on_df:
    @model(name="indexing.summaries", primary_key=["id"])
    @table(SummarySchema)
    def summaries(ctx, sections=Reference("indexing.sections"), writer):
        # Get data with user-controlled filtering
        query = sections.query.filter(sections.model_class.document_id.in_(ctx.document_ids))
        df = sections.df(query)

        # Apply DSPy explicitly (not automatic via decorator)
        df = apply_dspy_on_df(
            df,
            SummarizeDoc,
            input_fields={"text": "content"},
            output_fields={"summary": "summary"},
        )

        writer.write(df)
"""

import functools
import inspect
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional, Type

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from .dbos_events import get_event_emitter
from .display import display
from .references import Reference, resolve_references
from .registry import ModelRegistry

if TYPE_CHECKING:
    import pandas as pd

    from kurt.config import ModelConfig

logger = logging.getLogger(__name__)

# =============================================================================
# Table Registry (for @table decorator)
# =============================================================================

_table_registry: dict[str, Type[SQLModel]] = {}


def _pluralize(name: str) -> str:
    """Convert function name to pluralized snake_case table name.

    Examples:
        document -> documents
        entity -> entities
        document_analytics -> document_analytics (already plural-ish)
    """
    # Already snake_case (function names)
    snake = name.lower()

    # Don't double-pluralize
    if snake.endswith("s"):
        return snake

    # Simple pluralization
    if snake.endswith("y") and not snake.endswith(("ay", "ey", "iy", "oy", "uy")):
        return snake[:-1] + "ies"
    elif snake.endswith(("x", "z", "ch", "sh")):
        return snake + "es"
    return snake + "s"


def _create_sqlmodel_from_schema(
    schema: Type[BaseModel],
    tablename: str,
    uuid_pk: bool = True,
    timestamps: bool = True,
) -> Type[SQLModel]:
    """Dynamically create SQLModel from Pydantic schema.

    Column ordering:
    1. Primary key (id: UUID) - if uuid_pk=True
    2. User-defined fields - from schema
    3. Timestamps (created_at, updated_at) - ALWAYS at end
    """
    from uuid import UUID, uuid4

    # Build annotations and defaults in order
    annotations = {}
    namespace = {"__tablename__": tablename, "__module__": schema.__module__}

    # 1. UUID primary key first
    if uuid_pk:
        annotations["id"] = UUID
        namespace["id"] = Field(default_factory=uuid4, primary_key=True)

    # 2. User fields from schema
    for field_name, field_info in schema.model_fields.items():
        annotations[field_name] = field_info.annotation
        if field_info.default is not None:
            namespace[field_name] = Field(default=field_info.default)
        elif not field_info.is_required:
            namespace[field_name] = Field(default=None)
        else:
            namespace[field_name] = Field()

    # 3. Timestamps at END
    if timestamps:
        annotations["created_at"] = datetime
        annotations["updated_at"] = datetime
        namespace["created_at"] = Field(default_factory=datetime.utcnow)
        namespace["updated_at"] = Field(default_factory=datetime.utcnow)

    namespace["__annotations__"] = annotations

    # Create SQLModel class
    return type(schema.__name__, (SQLModel,), namespace, table=True)


def _generate_timestamp_triggers(tablename: str) -> list[str]:
    """Generate SQL triggers for auto-updating timestamps."""
    return [
        f"""
        CREATE TRIGGER IF NOT EXISTS {tablename}_set_created_at
        AFTER INSERT ON {tablename}
        FOR EACH ROW WHEN NEW.created_at IS NULL
        BEGIN
            UPDATE {tablename} SET created_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END;
        """,
        f"""
        CREATE TRIGGER IF NOT EXISTS {tablename}_set_updated_at
        AFTER UPDATE ON {tablename}
        FOR EACH ROW
        BEGIN
            UPDATE {tablename} SET updated_at = CURRENT_TIMESTAMP WHERE rowid = NEW.rowid;
        END;
        """,
    ]


# =============================================================================
# @table decorator (two forms)
# =============================================================================


def table(
    schema_or_class: Type[BaseModel] | Type[SQLModel],
    *,
    tablename: str = None,
    timestamps: bool = True,
    uuid_pk: bool = True,
) -> Callable:
    """Decorator that creates or registers a SQLModel table.

    Two usage patterns:

    1. Generate SQLModel from Pydantic schema (new code):
        class DocumentSchema(BaseModel):
            title: str

        @model(name="indexing.documents", primary_key=["id"])
        @table(DocumentSchema)
        def documents(ctx, writer):
            ...

    2. Register existing SQLModel class (existing code):
        class DocumentRow(SQLModel, table=True):
            __tablename__ = "documents"
            id: str = Field(primary_key=True)
            title: str

        @model(name="indexing.documents", primary_key=["id"])
        @table(DocumentRow)
        def documents(ctx, writer):
            ...

    Column ordering (for generated tables):
    1. id (UUID primary key) - if uuid_pk=True
    2. User-defined fields - from schema
    3. created_at, updated_at - if timestamps=True, ALWAYS at end

    Args:
        schema_or_class: Pydantic BaseModel (to generate) or SQLModel class (to register)
        tablename: Override table name (default: pluralized function name or class __tablename__)
        timestamps: Add created_at/updated_at at END (default: True, only for generated)
        uuid_pk: Add UUID primary key at START (default: True, only for generated)
    """

    def decorator(func: Callable) -> Callable:
        # Check if it's an existing SQLModel table class
        if isinstance(schema_or_class, type) and issubclass(schema_or_class, SQLModel):
            # Check if it has table=True (has __tablename__)
            if hasattr(schema_or_class, "__tablename__"):
                # It's an existing SQLModel table - register it directly
                name = tablename or schema_or_class.__tablename__
                sqlmodel_class = schema_or_class
                schema = None
                logger.debug(f"Registered existing table '{name}' from {schema_or_class.__name__}")
            else:
                # SQLModel without table=True - treat as schema to generate from
                name = tablename or _pluralize(func.__name__)
                sqlmodel_class = _create_sqlmodel_from_schema(
                    schema_or_class, name, uuid_pk, timestamps
                )
                schema = schema_or_class
                logger.debug(
                    f"Generated table '{name}' from SQLModel schema {schema_or_class.__name__}"
                )
        elif isinstance(schema_or_class, type) and issubclass(schema_or_class, BaseModel):
            # Pydantic BaseModel - generate SQLModel from it
            name = tablename or _pluralize(func.__name__)
            sqlmodel_class = _create_sqlmodel_from_schema(
                schema_or_class, name, uuid_pk, timestamps
            )
            schema = schema_or_class
            logger.debug(f"Registered table '{name}' from schema {schema_or_class.__name__}")
        else:
            raise ValueError(
                f"@table requires a Pydantic BaseModel or SQLModel class, got {type(schema_or_class)}"
            )

        _table_registry[name] = sqlmodel_class

        # Attach to function for @model to pick up
        func._table_schema = schema
        func._table_sqlmodel = sqlmodel_class
        func._table_name = name
        func._table_timestamps = timestamps

        return func

    return decorator


# =============================================================================
# DSPy utilities (explicit function, not decorator)
# =============================================================================


def apply_dspy_on_df(
    df: "pd.DataFrame",
    signature: Type,
    *,
    input_fields: dict[str, str],
    output_fields: dict[str, str] = None,
    pre_hook: Callable = None,
    post_hook: Callable = None,
    max_concurrent: int = 5,
    progress: bool = True,
    llm_model: str = None,
) -> "pd.DataFrame":
    """Apply a DSPy signature to DataFrame rows in parallel.

    This is an explicit utility function - call it in your model code
    after filtering data, so you only process the rows you need.

    Uses run_batch_sync for parallel execution with proper thread safety.

    Args:
        df: Input DataFrame with rows to process
        signature: DSPy Signature class
        input_fields: Map signature inputs to df columns {"sig_field": "df_column"}
        output_fields: Map signature outputs to df columns {"sig_field": "df_column"}
                      If None, uses signature output field names as column names
        pre_hook: Optional function (row_dict) -> row_dict to preprocess each row
        post_hook: Optional function (row_dict, result) -> row_dict to postprocess
        max_concurrent: Number of parallel LLM calls (default: 5)
        progress: Show progress bar (default: True)
        llm_model: Optional LLM model name (default: uses INDEXING_LLM_MODEL)

    Returns:
        DataFrame with new columns from DSPy output

    Example:
        df = sections.df(filtered_query)

        # Process rows in parallel (5 concurrent by default)
        df = apply_dspy_on_df(
            df,
            SummarizeDoc,
            input_fields={"text": "content"},
            output_fields={"summary": "summary"},
            max_concurrent=10,  # Increase parallelism
        )

        writer.write(df)
    """
    import pandas as pd

    from .display import make_progress_callback
    from .dspy_helpers import run_batch_sync

    if df.empty:
        return df

    # Get output field names from signature if not provided
    if output_fields is None:
        output_fields = {}
        for field_name, field_info in signature.model_fields.items():
            # Check if it's an output field (has json_schema_extra with __dspy_field_type)
            if hasattr(field_info, "json_schema_extra") and field_info.json_schema_extra:
                extra = field_info.json_schema_extra
                if isinstance(extra, dict) and extra.get("__dspy_field_type") == "output":
                    output_fields[field_name] = field_name

    # Convert DataFrame rows to items for run_batch_sync
    rows = df.to_dict("records")

    # Apply pre_hook and build items with mapped input fields
    items = []
    for row in rows:
        if pre_hook:
            row = pre_hook(row)
        # Map df columns to signature input fields
        item = {sig_field: row.get(df_col) for sig_field, df_col in input_fields.items()}
        # Store original row for later merging
        item["__original_row__"] = row
        items.append(item)

    # Create progress callback if needed
    on_progress = None
    if progress:
        on_progress = make_progress_callback(prefix="Processing with DSPy")

    # Run batch in parallel
    results = run_batch_sync(
        signature=signature,
        items=[{k: v for k, v in item.items() if k != "__original_row__"} for item in items],
        max_concurrent=max_concurrent,
        on_progress=on_progress,
        llm_model=llm_model,
    )

    # Merge results back into rows
    processed_rows = []
    for item, dspy_result in zip(items, results):
        row = item["__original_row__"].copy()

        if dspy_result.error:
            logger.warning(f"DSPy processing failed for row: {dspy_result.error}")
            # Keep row as-is with None outputs
        elif dspy_result.result:
            if post_hook:
                row = post_hook(row, dspy_result.result)
            else:
                # Store outputs in row
                for sig_field, col_name in output_fields.items():
                    row[col_name] = getattr(dspy_result.result, sig_field, None)

        processed_rows.append(row)

    return pd.DataFrame(processed_rows)


# =============================================================================
# Helper functions
# =============================================================================


def get_table(name: str) -> Optional[Type[SQLModel]]:
    """Get registered table by name."""
    return _table_registry.get(name)


def get_all_tables() -> dict[str, Type[SQLModel]]:
    """Get all registered tables."""
    return _table_registry.copy()


def create_timestamp_triggers(engine) -> None:
    """Create timestamp triggers for all registered tables."""
    from sqlalchemy import text

    with engine.connect() as conn:
        for tablename in _table_registry:
            for trigger_sql in _generate_timestamp_triggers(tablename):
                conn.execute(text(trigger_sql))
        conn.commit()
    logger.info(f"Created timestamp triggers for {len(_table_registry)} tables")


def _get_model_class_for_reference(model_name: str) -> Optional[Type[SQLModel]]:
    """Get SQLModel class for a reference by model name.

    Looks up in:
    - _table_registry (for @table decorated models)
    - ModelRegistry (for registered pipeline models)
    - Core DB models (for base tables like 'documents')
    """
    # Convert model name to table name (e.g., "indexing.sections" -> "indexing_sections")
    table_name = model_name.replace(".", "_")

    # Check table registry first
    if table_name in _table_registry:
        return _table_registry[table_name]

    # Check model registry
    from .registry import ModelRegistry

    metadata = ModelRegistry.get(model_name)
    if metadata and "db_model" in metadata:
        return metadata["db_model"]

    # Check core DB models for base tables
    if model_name == "documents":
        from kurt.db.models import Document

        return Document

    logger.warning(f"No model class found for reference '{model_name}'")
    return None


# =============================================================================
# @model decorator (updated to support @table)
# =============================================================================


def model(
    *,
    name: str,
    primary_key: list[str],
    description: str = "",
    writes_to: Optional[list[str]] = None,
    write_strategy: str = "replace",
    config_schema: Optional[Type["ModelConfig"]] = None,
) -> Callable:
    """
    Decorator for defining indexing pipeline models.

    IMPORTANT: Must be used with @table decorator to define the schema.

    Args:
        name: Unique model identifier (e.g., "indexing.section_extractions")
        primary_key: List of column names forming the primary key
        description: Human-readable description of the model's purpose
        writes_to: Optional list of persistent tables this model will mutate
        write_strategy: Default write strategy ("append", "merge", "replace")
        config_schema: Optional ModelConfig subclass for step configuration.
            If provided, config is auto-loaded and passed to the function.

    Example with @table:
        class DocumentSchema(BaseModel):
            title: str
            source_url: Optional[str] = None

        @model(name="indexing.documents", primary_key=["id"])
        @table(DocumentSchema)
        def documents(ctx, writer):
            ...

    Example with config:
        class SectionExtractionsConfig(ModelConfig):
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")
            batch_size: int = ConfigParam(default=50, ge=1, le=200)

        @model(
            name="indexing.section_extractions",
            primary_key=["document_id", "section_id"],
            config_schema=SectionExtractionsConfig,
        )
        @table(SectionSchema)
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
        # Get db_model from @table decorator (required)
        if not hasattr(func, "_table_sqlmodel"):
            raise ValueError(
                f"Model '{name}' requires @table decorator. "
                "Use: @model(...) @table(Schema) def func(): ..."
            )
        actual_db_model = func._table_sqlmodel

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
        actual_db_model.__tablename__ = table_name

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            event_emitter = get_event_emitter()

            if event_emitter:
                event_emitter.emit_model_started(name, description)

            display.start_step(name, description)

            try:
                # Get ctx and session from kwargs for Reference binding
                ctx = kwargs.get("ctx")
                session = kwargs.get("session")

                # Bind References with session and model class
                if ctx is not None and session is not None and references:
                    for param_name, ref_template in references.items():
                        # Look up the model class from registry
                        ref_model_class = _get_model_class_for_reference(ref_template.model_name)

                        # Create a new Reference instance and bind it
                        bound_ref = Reference(model_name=ref_template.model_name)
                        bound_ref._bind(session, ctx, ref_model_class)
                        kwargs[param_name] = bound_ref
                    logger.debug(
                        f"Bound {len(references)} lazy references: {list(references.keys())}"
                    )

                # Load and inject config if schema is provided and not already passed
                if config_schema is not None and "config" in params and "config" not in kwargs:
                    # Check if config override is provided in context metadata
                    ctx = kwargs.get("ctx")
                    config_instance = None

                    if ctx and hasattr(ctx, "metadata") and ctx.metadata:
                        model_configs = ctx.metadata.get("model_configs", {})
                        if name in model_configs:
                            config_instance = model_configs[name]
                            logger.debug(f"Using config override from context for {name}")

                    # If no override, load from config file
                    if config_instance is None:
                        try:
                            config_instance = config_schema.load(name)
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
                            config_instance = config_schema(**defaults)

                    kwargs["config"] = config_instance

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
            "db_model": actual_db_model,
            "primary_key": primary_key,
            "description": description,
            "references": references,
            "writes_to": writes_to or [],
            "write_strategy": write_strategy,
            "config_schema": config_schema,
            "function": wrapper,
            "table_name": table_name,
            "table_schema": getattr(func, "_table_schema", None),  # Original Pydantic schema
        }

        # Register the model
        ModelRegistry.register(name, wrapper._model_metadata)

        return wrapper

    return decorator
