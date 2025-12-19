"""
Model decorator for the indexing pipeline.

Models declare dependencies using Reference() in function signatures.
References are lazy-loaded when accessed.

Decorators:
    @table(schema) - Generate SQLModel from Pydantic schema (timestamps at END)
    @llm(signature) - Apply DSPy signature to process rows
    @model(...) - Define pipeline model with dependencies

Example with @table (NEW):
    class DocumentSchema(BaseModel):
        title: str
        source_url: Optional[str] = None

    @table(DocumentSchema)  # Generates SQLModel with id, title, source_url, created_at, updated_at
    @model(name="indexing.documents", primary_key=["id"])
    def documents(ctx: PipelineContext, writer: TableWriter):
        ...

Example with @llm (NEW):
    class ExtractEntities(dspy.Signature):
        content: str = dspy.InputField()
        entities: list[str] = dspy.OutputField()

    @table(DocumentSchema)
    @llm(ExtractEntities, input_fields={"content": "content"}, output_field="entities")
    @model(name="indexing.documents", primary_key=["id"])
    def documents(ctx: PipelineContext, writer: TableWriter):
        ...

Legacy example (still works):
    @model(name="indexing.extractions", db_model=SectionExtractionRow, primary_key=[...])
    def extractions(
        ctx: PipelineContext,
        sections=Reference("indexing.document_sections"),
        writer: TableWriter,
    ):
        df = sections.df
        ...
"""

import functools
import inspect
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Optional, Type

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from .dbos_events import get_event_emitter
from .display import display
from .references import Reference, resolve_references
from .registry import ModelRegistry

if TYPE_CHECKING:
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
# @table decorator
# =============================================================================


def table(
    schema: Type[BaseModel],
    *,
    tablename: str = None,
    timestamps: bool = True,
    uuid_pk: bool = True,
) -> Callable:
    """Decorator that maps a Pydantic schema to a SQLModel table.

    Column ordering:
    1. id (UUID primary key) - if uuid_pk=True
    2. User-defined fields - from schema
    3. created_at, updated_at - if timestamps=True, ALWAYS at end

    Args:
        schema: Pydantic BaseModel class
        tablename: Override table name (default: pluralized function name)
        timestamps: Add created_at/updated_at at END (default: True)
        uuid_pk: Add UUID primary key at START (default: True)

    Usage:
        class DocumentSchema(BaseModel):
            title: str
            source_url: Optional[str] = None

        @table(DocumentSchema)
        @model(name="indexing.documents", primary_key=["id"])
        def documents(ctx, writer):
            ...
    """

    def decorator(func: Callable) -> Callable:
        name = tablename or _pluralize(func.__name__)
        sqlmodel_class = _create_sqlmodel_from_schema(schema, name, uuid_pk, timestamps)

        _table_registry[name] = sqlmodel_class

        # Attach to function for @model to pick up
        func._table_schema = schema
        func._table_sqlmodel = sqlmodel_class
        func._table_name = name
        func._table_timestamps = timestamps

        logger.debug(f"Registered table '{name}' from schema {schema.__name__}")
        return func

    return decorator


# =============================================================================
# @llm decorator
# =============================================================================


def llm(
    signature: Type,
    *,
    input_fields: dict[str, str] = None,
    output_field: str = None,
    pre_hook: Callable = None,
    post_hook: Callable = None,
    batch: bool = False,
    on_create: bool = True,
    on_update: bool = False,
) -> Callable:
    """Decorator that applies a DSPy signature to process rows.

    Args:
        signature: DSPy Signature class
        input_fields: Map signature inputs to model fields {"sig_field": "model_field"}
        output_field: Model field to store result
        pre_hook: lambda row: preprocess(row) before LLM
        post_hook: lambda row, result: postprocess(row, result) after LLM
        batch: Process in batches (default: False)
        on_create: Run on create (default: True)
        on_update: Run on update (default: False)

    Usage:
        class SummarizeDoc(dspy.Signature):
            text: str = dspy.InputField()
            summary: str = dspy.OutputField()

        @table(DocumentSchema)
        @llm(SummarizeDoc, input_fields={"text": "content"}, output_field="summary")
        @model(name="indexing.documents", primary_key=["id"])
        def documents(ctx, writer):
            ...
    """

    def decorator(func: Callable) -> Callable:
        func._llm_config = {
            "signature": signature,
            "input_fields": input_fields or {},
            "output_field": output_field,
            "pre_hook": pre_hook,
            "post_hook": post_hook,
            "batch": batch,
            "on_create": on_create,
            "on_update": on_update,
        }
        logger.debug(f"Attached LLM config to {func.__name__}: {signature.__name__}")
        return func

    return decorator


def apply_llm_processing(row: Any, llm_config: dict) -> Any:
    """Apply LLM processing to a row. Called by pipeline framework."""
    import dspy

    sig = llm_config["signature"]
    input_fields = llm_config["input_fields"]
    output_field = llm_config["output_field"]
    pre_hook = llm_config["pre_hook"]
    post_hook = llm_config["post_hook"]

    # 1. Pre-hook
    if pre_hook:
        row = pre_hook(row)

    # 2. Build inputs
    inputs = {sig_f: getattr(row, model_f, None) for sig_f, model_f in input_fields.items()}

    # 3. Call DSPy
    predictor = dspy.Predict(sig)
    result = predictor(**inputs)

    # 4. Post-hook or default storage
    if post_hook:
        row = post_hook(row, result)
    elif output_field:
        # Get first output field from signature
        for field_name in sig.model_fields:
            field = sig.model_fields[field_name]
            if hasattr(field, "json_schema_extra") and field.json_schema_extra:
                setattr(row, output_field, getattr(result, field_name, None))
                break

    return row


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

    Looks up in both:
    - _table_registry (for @table decorated models)
    - ModelRegistry (for registered pipeline models)
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

    Example with @llm:
        @model(name="indexing.documents", primary_key=["id"])
        @llm(ExtractEntities, input_fields={"content": "content"})
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

        # Get LLM config from @llm decorator if present
        llm_config = getattr(func, "_llm_config", None)

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
            "db_model": actual_db_model,
            "primary_key": primary_key,
            "description": description,
            "references": references,
            "writes_to": writes_to or [],
            "write_strategy": write_strategy,
            "config_schema": config_schema,
            "function": wrapper,
            "table_name": table_name,
            "llm_config": llm_config,  # NEW: LLM processing config
            "table_schema": getattr(func, "_table_schema", None),  # NEW: original Pydantic schema
        }

        # Register the model
        ModelRegistry.register(name, wrapper._model_metadata)

        return wrapper

    return decorator
