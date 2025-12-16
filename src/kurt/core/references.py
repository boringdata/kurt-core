"""
Lazy Reference system for declaring model dependencies.

References declare upstream dependencies AND provide lazy data loading.
Data is only fetched when accessed (via .df, iteration, or .load()).

Example:
    @model(name="indexing.section_extractions", ...)
    def section_extractions(
        ctx: PipelineContext,
        sections=Reference("indexing.document_sections"),
        documents=Reference("documents", load_content=True),
        writer: TableWriter,
    ):
        # Data loaded lazily when accessed
        for section in sections:
            ...

        # Or as DataFrame
        df = documents.df

        # Access context directly
        doc_ids = ctx.document_ids
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterator, Optional

import pandas as pd

if TYPE_CHECKING:
    from .model_runner import PipelineContext
    from .table_io import TableReader

logger = logging.getLogger(__name__)


# Type alias for filter function: (df, ctx) -> df
FilterFunc = Any  # Callable[[pd.DataFrame, PipelineContext], pd.DataFrame]


@dataclass
class Reference:
    """
    Lazy reference to an upstream model's output.

    Declares a dependency AND provides lazy data loading.
    Data is only fetched when you access .df, iterate, or call .load().

    Filtering modes (explicit only, no auto-detection):
    - filter=None (default): No filtering - load full table
    - filter="column_name": Filter by column using ctx.document_ids (SQL WHERE)
    - filter={"col": lambda ctx: value}: Dict with callable - SQL WHERE with runtime value
                                          e.g., {"workflow_id": lambda ctx: ctx.workflow_id}
    - filter=lambda df, ctx: df[...]: Custom filter function (post-load)
                                       WARNING: Callable filters load entire table first!

    Content loading (for documents table):
    - load_content=False: Don't load file content (default)
    - load_content=True: Load content, use default "document_id" column in output
    - load_content={"document_id_column": "col"}: Load content with custom column name

    Args:
        model_name: Name of upstream model (e.g., "indexing.document_sections")
                   or table name (e.g., "documents")
        load_content: For documents table, load file content. Can be:
                     - False: don't load content
                     - True: load content, use "document_id" column in output
                     - dict with "document_id_column": custom column name for document ID
        columns: Optional list of columns to select
        filter: How to filter data. Can be:
                - None: no filtering (load full table)
                - str: column name to filter by using ctx.document_ids
                - callable: function (df, ctx) -> filtered_df

    Example:
        @model(name="indexing.extractions", ...)
        def extractions(
            ctx: PipelineContext,
            # Filter sections by document_id column using ctx.document_ids
            sections=Reference("indexing.document_sections", filter="document_id"),
            # Load documents with content, filter by id column
            docs=Reference(
                "documents",
                load_content={"document_id_column": "document_id"},
                filter="id",
            ),
            # Dict filter with callable - SQL pushdown with runtime value (RECOMMENDED)
            groups=Reference(
                "indexing.entity_groups",
                filter={"workflow_id": lambda ctx: ctx.workflow_id}
            ),
            writer: TableWriter,
        ):
            sections_df = sections.df
    """

    model_name: str
    load_content: bool | dict = False  # False, True, or {"document_id_column": "col"}
    columns: Optional[list[str]] = None
    filter: Optional[str | FilterFunc] = None  # None, column name, or filter function

    # Runtime state (set by framework before model execution)
    _reader: Optional["TableReader"] = field(default=None, repr=False)
    _ctx: Optional["PipelineContext"] = field(default=None, repr=False)
    _cached_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    _loaded: bool = field(default=False, repr=False)

    @property
    def table_name(self) -> str:
        """Get the table name for this reference.

        Model names like "indexing.document_sections" become "indexing_document_sections".
        Direct table names like "documents" stay as-is.
        """
        if "." in self.model_name:
            return self.model_name.replace(".", "_")
        return self.model_name

    @property
    def upstream_model(self) -> Optional[str]:
        """Get the upstream model name if this references a model (not a table)."""
        if "." in self.model_name:
            return self.model_name
        return None

    @property
    def ctx(self) -> Optional["PipelineContext"]:
        """Get the bound pipeline context."""
        return self._ctx

    def _bind(self, reader: "TableReader", ctx: "PipelineContext") -> "Reference":
        """Bind runtime context (called by framework before model execution)."""
        self._reader = reader
        self._ctx = ctx
        return self

    def load(self) -> pd.DataFrame:
        """
        Load data from the referenced table.

        Called automatically when you access .df or iterate.
        Can also be called explicitly for eager loading.

        Returns:
            DataFrame with the loaded data
        """
        if self._loaded and self._cached_df is not None:
            return self._cached_df

        if self._reader is None:
            raise RuntimeError(
                f"Reference '{self.model_name}' not bound to reader. "
                "This usually means you're accessing it outside model execution."
            )

        table_name = self.table_name
        doc_ids = self._ctx.document_ids if self._ctx else []

        # Determine filter type and build where clause
        where = None
        filter_func = None

        if isinstance(self.filter, dict):
            # Dict filter: {"column": value} or {"column": lambda ctx: value}
            # Supports SQL pushdown with runtime values
            where = {}
            for col, val in self.filter.items():
                if callable(val):
                    # Callable value - evaluate with ctx at runtime
                    where[col] = val(self._ctx)
                else:
                    # Static value
                    where[col] = val
        elif isinstance(self.filter, str):
            # String filter: column name to filter by ctx.document_ids
            where = {self.filter: doc_ids} if doc_ids else None
        elif callable(self.filter):
            # Callable filter: function (df, ctx) -> filtered_df
            # WARNING: This loads entire table first, then filters in pandas
            filter_func = self.filter

        logger.debug(f"Loading reference '{self.model_name}' from table '{table_name}'")

        # Parse load_content config
        should_load_content = bool(self.load_content)
        document_id_column = "document_id"  # Default output column name
        if isinstance(self.load_content, dict):
            document_id_column = self.load_content.get("document_id_column", "document_id")

        # Get reprocess_unchanged from context (for document loading skip logic)
        reprocess_unchanged = self._ctx.reprocess_unchanged if self._ctx else False

        df = self._reader.load(
            table_name,
            where=where,
            load_content=should_load_content,
            document_id_column=document_id_column,
            reprocess_unchanged=reprocess_unchanged,
        )

        # Apply custom filter function if provided (receives df and ctx)
        if filter_func is not None:
            df = filter_func(df, self._ctx)
            logger.debug(f"  → After filter function: {len(df)} rows")

        self._cached_df = df
        self._loaded = True

        logger.debug(f"  → Loaded {len(self._cached_df)} rows")
        return self._cached_df

    @property
    def df(self) -> pd.DataFrame:
        """Get data as DataFrame (lazy load on first access)."""
        return self.load()

    def __iter__(self) -> Iterator[dict]:
        """Iterate over rows as dicts (lazy load on first access)."""
        df = self.load()
        for _, row in df.iterrows():
            yield row.to_dict()

    def __len__(self) -> int:
        """Get row count (triggers load if not loaded)."""
        return len(self.load())

    def to_records(self) -> list[dict]:
        """Get all rows as list of dicts."""
        return self.load().to_dict("records")


def resolve_references(func) -> dict[str, Reference]:
    """
    Extract Reference declarations from function signature.

    Args:
        func: Function to inspect

    Returns:
        Dict of {param_name: Reference}
    """
    import inspect

    references = {}
    sig = inspect.signature(func)

    for param_name, param in sig.parameters.items():
        if isinstance(param.default, Reference):
            # Create a copy so each model instance has its own Reference
            ref = param.default
            references[param_name] = Reference(
                model_name=ref.model_name,
                load_content=ref.load_content,
                columns=ref.columns,
                filter=ref.filter,
            )

    return references


def build_dependency_graph(model_names: list[str]) -> dict[str, list[str]]:
    """
    Build a dependency graph from registered models.

    Extracts dependencies from Reference() declarations in function signatures.

    Args:
        model_names: List of model names to include in graph

    Returns:
        Dict mapping model_name -> list of upstream model names it depends on
    """
    from .registry import ModelRegistry

    # Build a mapping of table_name -> model_name for reverse lookup
    # Convention: "indexing.foo" -> table "indexing_foo"
    table_to_model = {}
    for name in model_names:
        table_name = name.replace(".", "_")
        table_to_model[table_name] = name

    graph = {}

    for model_name in model_names:
        metadata = ModelRegistry.get(model_name)
        if not metadata:
            graph[model_name] = []
            continue

        dependencies = set()

        # Check Reference() declarations
        references = metadata.get("references", {})
        for ref in references.values():
            # Direct model reference (e.g., "indexing.document_sections")
            upstream = ref.upstream_model
            if upstream and upstream in model_names:
                dependencies.add(upstream)

            # Table name reference (e.g., "indexing_document_sections")
            # Maps back to model name
            table_name = ref.table_name
            if table_name in table_to_model:
                dependencies.add(table_to_model[table_name])

        graph[model_name] = list(dependencies)

    return graph


def topological_sort(graph: dict[str, list[str]]) -> list[list[str]]:
    """
    Topologically sort models into execution levels.

    Models at the same level have no dependencies on each other
    and can potentially run in parallel.

    Args:
        graph: Dependency graph from build_dependency_graph()

    Returns:
        List of levels, where each level is a list of model names

    Example:
        graph = {
            "a": [],           # no deps
            "b": ["a"],        # depends on a
            "c": ["a"],        # depends on a
            "d": ["b", "c"],   # depends on b and c
        }
        # Returns: [["a"], ["b", "c"], ["d"]]
    """
    in_degree = {node: len(deps) for node, deps in graph.items()}

    dependents = {node: [] for node in graph}
    for node, deps in graph.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].append(node)

    levels = []
    remaining = set(graph.keys())

    while remaining:
        ready = [node for node in remaining if in_degree[node] == 0]

        if not ready:
            raise ValueError(f"Circular dependency detected among: {remaining}")

        levels.append(sorted(ready))  # Sort for deterministic order

        for node in ready:
            remaining.remove(node)
            for dependent in dependents.get(node, []):
                if dependent in remaining:
                    in_degree[dependent] -= 1

    return levels
