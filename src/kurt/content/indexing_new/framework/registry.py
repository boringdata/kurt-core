"""
Model registry for tracking and managing all registered models.
"""

from typing import Any, Dict, Optional


class ModelRegistry:
    """Registry for all decorated models in the indexing pipeline."""

    _models: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, metadata: Dict[str, Any]) -> None:
        """
        Register a model with its metadata.

        Args:
            name: Unique model identifier
            metadata: Model metadata including db_model, primary_key, etc.
        """
        if name in cls._models:
            raise ValueError(f"Model {name} already registered")
        cls._models[name] = metadata

    @classmethod
    def get(cls, name: str) -> Optional[Dict[str, Any]]:
        """Get model metadata by name."""
        return cls._models.get(name)

    @classmethod
    def list_models(cls) -> list[str]:
        """List all registered model names."""
        return list(cls._models.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered models (mainly for testing)."""
        cls._models.clear()

    @classmethod
    def get_dependency_graph(cls) -> Dict[str, list[str]]:
        """
        Build a dependency graph from model metadata.

        Returns a dict mapping model name to list of models it depends on
        (based on tables it reads from).
        """
        graph = {}
        for model_name, metadata in cls._models.items():
            # For now, dependencies must be specified explicitly in workflows
            # Future enhancement: auto-detect based on reader.load() calls
            graph[model_name] = []
        return graph
