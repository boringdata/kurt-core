"""
Lazy Reference system for declaring model dependencies.

References declare upstream dependencies and provide a SQLAlchemy Query object.
NO data is prefetched - the user filters and executes the query in their code.

Example:
    @model(name="indexing.section_extractions", ...)
    @table(SectionExtractionRow)
    def section_extractions(
        ctx: PipelineContext,
        sections=Reference("indexing.document_sections"),
        writer: TableWriter,
    ):
        # Get query object (no data fetched yet)
        query = sections.query

        # Filter in user code
        filtered = query.filter(Section.document_id.in_(ctx.document_ids))

        # Execute when ready
        df = sections.df(filtered)  # or filtered.all() for list
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd
from sqlalchemy.orm import Query

if TYPE_CHECKING:
    from sqlmodel import Session

    from .model_runner import PipelineContext

logger = logging.getLogger(__name__)


@dataclass
class Reference:
    """
    Lazy reference to an upstream model's output.

    Returns a SQLAlchemy Query object for explicit filtering in user code.
    NO automatic filtering - all filtering is explicit.

    Args:
        model_name: Name of upstream model (e.g., "indexing.document_sections")
                   or table name (e.g., "documents")

    Example:
        @model(name="indexing.extractions", ...)
        @table(ExtractionRow)
        def extractions(
            ctx: PipelineContext,
            sections=Reference("indexing.document_sections"),
            writer: TableWriter,
        ):
            # Get the query (lazy - no data fetched)
            query = sections.query

            # Filter in your code
            filtered = query.filter(
                sections.model_class.document_id.in_(ctx.document_ids)
            )

            # Execute: get DataFrame
            df = sections.df(filtered)
    """

    model_name: str

    # Runtime state (set by framework before model execution)
    _session: Optional["Session"] = field(default=None, repr=False)
    _ctx: Optional["PipelineContext"] = field(default=None, repr=False)
    _model_class: Optional[Any] = field(default=None, repr=False)

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

    def _bind(self, session: "Session", ctx: "PipelineContext", model_class: Any) -> "Reference":
        """Bind runtime context (called by framework before model execution)."""
        self._session = session
        self._ctx = ctx
        self._model_class = model_class
        return self

    @property
    def query(self) -> Query:
        """Get SQLAlchemy Query object (lazy - no data fetched).

        Returns a query that you can filter and execute in your model code.

        Example:
            query = sections.query
            filtered = query.filter(Section.document_id.in_(doc_ids))
            rows = filtered.all()
        """
        if self._session is None:
            raise RuntimeError(
                f"Reference '{self.model_name}' not bound to session. "
                "This usually means you're accessing it outside model execution."
            )

        if self._model_class is None:
            raise RuntimeError(
                f"Reference '{self.model_name}' has no model class. "
                "Ensure the referenced model is registered with @table decorator."
            )

        return self._session.query(self._model_class)

    @property
    def model_class(self) -> Any:
        """Get the SQLModel class for this reference.

        Useful for building filter conditions:
            query.filter(sections.model_class.document_id.in_(doc_ids))
        """
        if self._model_class is None:
            raise RuntimeError(
                f"Reference '{self.model_name}' has no model class. "
                "Ensure the referenced model is registered with @table decorator."
            )
        return self._model_class

    def df(self, query: Optional[Query] = None) -> pd.DataFrame:
        """Execute query and return as DataFrame.

        Args:
            query: Optional filtered query. If None, uses base query (all rows).

        Example:
            # All rows
            df = sections.df()

            # Filtered
            filtered = sections.query.filter(...)
            df = sections.df(filtered)
        """
        if self._session is None:
            raise RuntimeError(
                f"Reference '{self.model_name}' not bound to session. "
                "This usually means you're accessing it outside model execution."
            )

        q = query if query is not None else self.query
        return pd.read_sql(q.statement, self._session.bind)

    def all(self, query: Optional[Query] = None) -> list:
        """Execute query and return list of model instances.

        Args:
            query: Optional filtered query. If None, uses base query (all rows).
        """
        q = query if query is not None else self.query
        return q.all()


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
            references[param_name] = Reference(model_name=ref.model_name)

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
