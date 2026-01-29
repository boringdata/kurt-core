"""Fetch engines module - content extraction engines."""

from typing import Dict, Type

from kurt.tools.fetch.core import BaseFetcher


class EngineRegistry:
    """Registry for fetching engines."""

    _engines: Dict[str, Type[BaseFetcher]] = {}

    @classmethod
    def register(cls, name: str, engine_class: Type[BaseFetcher]) -> None:
        """Register an engine.

        Args:
            name: Engine name
            engine_class: Engine class (subclass of BaseFetcher)
        """
        cls._engines[name] = engine_class

    @classmethod
    def get(cls, name: str) -> Type[BaseFetcher]:
        """Get an engine by name.

        Args:
            name: Engine name

        Returns:
            Engine class

        Raises:
            KeyError: If engine not found
        """
        if name not in cls._engines:
            raise KeyError(f"Unknown engine: {name}")
        return cls._engines[name]

    @classmethod
    def list_engines(cls) -> list[str]:
        """List available engines.

        Returns:
            List of engine names
        """
        return list(cls._engines.keys())

    @classmethod
    def is_available(cls, name: str) -> bool:
        """Check if engine is available.

        Args:
            name: Engine name

        Returns:
            True if engine is registered
        """
        return name in cls._engines


__all__ = ["EngineRegistry"]
