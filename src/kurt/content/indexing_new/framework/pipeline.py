"""
Pipeline discovery and configuration.

Instead of YAML, pipelines can be discovered automatically from registered models.
Models declare their namespace via their name prefix (e.g., "indexing.document_sections").
"""

import logging
from dataclasses import dataclass, field
from typing import List

from .references import build_dependency_graph, topological_sort
from .registry import ModelRegistry

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Pipeline configuration.

    Can be created explicitly or discovered from registered models.

    Attributes:
        name: Pipeline name for logging
        models: List of model names (order determined by DAG)
        stop_on_error: Whether to stop pipeline on first error
    """

    name: str
    models: List[str] = field(default_factory=list)
    stop_on_error: bool = True

    @classmethod
    def discover(cls, namespace: str, stop_on_error: bool = True) -> "PipelineConfig":
        """
        Discover a pipeline from registered models in a namespace.

        Finds all models whose names start with the namespace prefix,
        then orders them by their dependencies.

        Args:
            namespace: Model name prefix (e.g., "indexing")
            stop_on_error: Whether to stop on first error

        Returns:
            PipelineConfig with models ordered by dependency graph

        Example:
            # Discovers all "indexing.*" models and orders by dependencies
            pipeline = PipelineConfig.discover("indexing")
        """
        # Find all models in the namespace
        all_models = ModelRegistry.list_all()
        prefix = f"{namespace}."
        namespace_models = [name for name in all_models if name.startswith(prefix)]

        if not namespace_models:
            logger.warning(f"No models found in namespace '{namespace}'")
            return cls(name=namespace, models=[], stop_on_error=stop_on_error)

        logger.info(f"Discovered {len(namespace_models)} models in namespace '{namespace}'")

        # Build dependency graph and topological sort
        try:
            dep_graph = build_dependency_graph(namespace_models)
            levels = topological_sort(dep_graph)
            # Flatten levels into ordered list
            ordered_models = [model for level in levels for model in level]
        except ValueError as e:
            logger.error(f"Failed to order models: {e}")
            # Fall back to alphabetical order
            ordered_models = sorted(namespace_models)

        logger.info(f"Execution order: {' → '.join(ordered_models)}")

        return cls(
            name=namespace,
            models=ordered_models,
            stop_on_error=stop_on_error,
        )


def get_pipeline(namespace: str) -> PipelineConfig:
    """
    Get a pipeline for a namespace, discovering models automatically.

    This is the main entry point for getting a pipeline configuration.
    Models must be imported before calling this to ensure they're registered.

    Args:
        namespace: Model name prefix (e.g., "indexing")

    Returns:
        PipelineConfig ready for execution

    Example:
        # First, ensure models are imported
        import kurt.content.indexing_new.models  # noqa: F401

        # Then get the pipeline
        pipeline = get_pipeline("indexing")

        # Run it
        result = await run_workflow(pipeline, filters)
    """
    return PipelineConfig.discover(namespace)
