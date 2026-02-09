"""
Provider registry and discovery.

Provides:
- ProviderRegistry: Singleton registry for tool providers
- get_provider_registry(): Access the singleton instance

Providers are discovered from three locations (later overrides earlier):
1. Built-in: src/kurt/tools/{tool}/providers/
2. User global: ~/.kurt/tools/{tool}/providers/
3. Project local: <project>/kurt/tools/{tool}/providers/

Each provider is a Python class in a `provider.py` file within a named
subdirectory under `providers/`. Provider classes must have a `name`
attribute and optionally `version`, `url_patterns`, and `requires_env`.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import logging
import os
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Singleton registry for tool providers.

    Handles:
    - Provider discovery from built-in, user, and project locations
    - Lazy loading (providers imported on first access)
    - URL pattern matching for auto-selection
    - Environment variable validation
    """

    _instance: ProviderRegistry | None = None
    _lock = threading.RLock()

    def __new__(cls) -> ProviderRegistry:
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._providers: dict[str, dict[str, type]] = {}
                inst._provider_meta: dict[str, dict[str, dict[str, Any]]] = {}
                inst._discovered = False
                cls._instance = inst
            return cls._instance

    def discover(self) -> None:
        """Discover all providers from filesystem.

        Scans built-in, user, and project tool directories for providers.
        Safe to call multiple times (idempotent after first run).
        """
        if self._discovered:
            return

        with self._lock:
            if self._discovered:
                return
            self._discover_providers()
            self._discovered = True

    def discover_from(self, dirs: list[tuple[Path, str]]) -> None:
        """Discover providers from explicit directories (for testing).

        Args:
            dirs: List of (path, source_label) tuples to scan.
        """
        with self._lock:
            for path, source in dirs:
                self._scan_tools_dir(path, source=source)
            self._discovered = True

    def _discover_providers(self) -> None:
        """Scan all provider locations in priority order."""
        # 1. Built-in tools (lowest priority)
        builtin_dir = Path(__file__).parent.parent
        self._scan_tools_dir(builtin_dir, source="builtin")

        # 2. User tools (medium priority)
        user_dir = Path.home() / ".kurt" / "tools"
        self._scan_tools_dir(user_dir, source="user")

        # 3. Project tools (highest priority)
        project_root = os.environ.get("KURT_PROJECT_ROOT", ".")
        project_dir = Path(project_root) / "kurt" / "tools"
        self._scan_tools_dir(project_dir, source="project")

    def _scan_tools_dir(self, base: Path, source: str) -> None:
        """Scan a directory for tools and their providers."""
        if not base.exists() or not base.is_dir():
            return

        for tool_dir in sorted(base.iterdir()):
            if not tool_dir.is_dir() or tool_dir.name.startswith((".", "_")):
                continue

            tool_name = tool_dir.name
            providers_dir = tool_dir / "providers"

            if providers_dir.exists() and providers_dir.is_dir():
                self._scan_providers(tool_name, providers_dir, source)

    def _scan_providers(
        self, tool_name: str, providers_dir: Path, source: str
    ) -> None:
        """Scan providers directory for a specific tool."""
        if tool_name not in self._providers:
            self._providers[tool_name] = {}
            self._provider_meta[tool_name] = {}

        for provider_dir in sorted(providers_dir.iterdir()):
            if not provider_dir.is_dir() or provider_dir.name.startswith((".", "_")):
                continue

            provider_py = provider_dir / "provider.py"
            if not provider_py.exists():
                continue

            provider_class = self._import_provider(provider_py)
            if provider_class is None:
                continue

            provider_name = getattr(provider_class, "name", "") or provider_dir.name

            # Later source overrides earlier (project > user > builtin)
            self._providers[tool_name][provider_name] = provider_class
            self._provider_meta[tool_name][provider_name] = {
                "name": provider_name,
                "version": getattr(provider_class, "version", "1.0.0"),
                "url_patterns": getattr(provider_class, "url_patterns", []),
                "requires_env": getattr(provider_class, "requires_env", []),
                "description": (provider_class.__doc__ or "").strip(),
                "_path": str(provider_dir),
                "_source": source,
            }

    def _import_provider(self, path: Path) -> type | None:
        """Import a provider class from a Python file.

        Looks for a class with a `name` attribute that also has
        `url_patterns` or `requires_env` attributes (provider interface).

        Returns None if import fails or no provider class is found.
        """
        try:
            module_name = f"_kurt_provider_{path.parent.parent.name}_{path.parent.name}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find provider class: must have 'name' and provider-like attributes
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                attr = getattr(module, attr_name, None)
                if not isinstance(attr, type):
                    continue
                # Check for provider interface markers
                if hasattr(attr, "name") and (
                    hasattr(attr, "url_patterns") or hasattr(attr, "requires_env")
                ):
                    name_val = getattr(attr, "name", "")
                    if name_val:  # Must have a non-empty name
                        return attr

            return None
        except Exception as e:
            logger.warning("Failed to import provider from %s: %s", path, e)
            return None

    # =========================================================================
    # Public API
    # =========================================================================

    def get_provider(self, tool_name: str, provider_name: str) -> Any | None:
        """Get an instantiated provider by tool and provider name.

        Args:
            tool_name: Tool name (e.g., "fetch", "map")
            provider_name: Provider name (e.g., "trafilatura", "notion")

        Returns:
            Instantiated provider, or None if not found.
        """
        self.discover()
        providers = self._providers.get(tool_name, {})
        provider_class = providers.get(provider_name)
        if provider_class is not None:
            return provider_class()
        return None

    def get_provider_class(self, tool_name: str, provider_name: str) -> type | None:
        """Get a provider class (not instantiated) by tool and provider name.

        Args:
            tool_name: Tool name
            provider_name: Provider name

        Returns:
            Provider class, or None if not found.
        """
        self.discover()
        return self._providers.get(tool_name, {}).get(provider_name)

    def list_providers(self, tool_name: str) -> list[dict[str, Any]]:
        """List all providers for a tool with their metadata.

        Args:
            tool_name: Tool name (e.g., "fetch", "map")

        Returns:
            List of provider metadata dicts.
        """
        self.discover()
        return list(self._provider_meta.get(tool_name, {}).values())

    def list_tools_with_providers(self) -> dict[str, list[str]]:
        """List all tools that have providers, with their provider names.

        Returns:
            Dict mapping tool name to list of provider names.
        """
        self.discover()
        return {
            tool: sorted(providers.keys())
            for tool, providers in self._providers.items()
            if providers
        }

    def match_provider(self, tool_name: str, url: str) -> str | None:
        """Find a provider matching a URL pattern.

        Checks specific patterns first, then falls back to wildcard ("*").

        Args:
            tool_name: Tool name (e.g., "fetch")
            url: URL to match against provider patterns

        Returns:
            Provider name, or None if no match.
        """
        self.discover()
        providers = self._provider_meta.get(tool_name, {})
        if not providers:
            return None

        parsed = urlparse(url)
        test_string = f"{parsed.netloc}{parsed.path}"

        # First pass: specific patterns (not "*")
        for name, meta in providers.items():
            patterns = meta.get("url_patterns", [])
            for pattern in patterns:
                if pattern == "*":
                    continue
                if fnmatch.fnmatch(test_string, pattern):
                    return name
                if fnmatch.fnmatch(url, pattern):
                    return name

        # Second pass: wildcard fallback
        for name, meta in providers.items():
            if "*" in meta.get("url_patterns", []):
                return name

        return None

    def validate_provider(self, tool_name: str, provider_name: str) -> list[str]:
        """Validate provider requirements.

        Checks that all required environment variables are set.

        Args:
            tool_name: Tool name
            provider_name: Provider name

        Returns:
            List of missing environment variable names. Empty if all met.
        """
        self.discover()
        meta = self._provider_meta.get(tool_name, {}).get(provider_name, {})
        requires_env = meta.get("requires_env", [])

        return [var for var in requires_env if not os.environ.get(var)]

    def validate_all(self) -> dict[str, dict[str, list[str]]]:
        """Validate all providers and return a requirements report.

        Returns:
            Dict of {tool_name: {provider_name: [missing_env_vars]}}.
            Only includes providers that have missing requirements.
        """
        self.discover()
        report: dict[str, dict[str, list[str]]] = {}

        for tool_name, providers in self._provider_meta.items():
            for provider_name, meta in providers.items():
                missing = [
                    var
                    for var in meta.get("requires_env", [])
                    if not os.environ.get(var)
                ]
                if missing:
                    if tool_name not in report:
                        report[tool_name] = {}
                    report[tool_name][provider_name] = missing

        return report

    def get_provider_checked(
        self, tool_name: str, provider_name: str
    ) -> Any:
        """Get provider with requirements validation.

        Like get_provider(), but raises ProviderRequirementsError if
        the provider's required env vars are missing, and
        ProviderNotFoundError if the provider doesn't exist.

        Args:
            tool_name: Tool name
            provider_name: Provider name

        Returns:
            Instantiated provider.

        Raises:
            ProviderNotFoundError: If provider not found.
            ProviderRequirementsError: If required env vars missing.
        """
        from kurt.tools.core.errors import (
            ProviderNotFoundError,
            ProviderRequirementsError,
        )

        self.discover()
        providers = self._providers.get(tool_name, {})
        provider_class = providers.get(provider_name)

        if provider_class is None:
            available = sorted(providers.keys()) if providers else []
            raise ProviderNotFoundError(tool_name, provider_name, available)

        missing = self.validate_provider(tool_name, provider_name)
        if missing:
            raise ProviderRequirementsError(
                provider_name=provider_name,
                missing=missing,
                tool_name=tool_name,
            )

        return provider_class()

    def reset(self) -> None:
        """Reset the registry state. Primarily for testing."""
        with self._lock:
            self._providers.clear()
            self._provider_meta.clear()
            self._discovered = False


def get_provider_registry() -> ProviderRegistry:
    """Get the singleton provider registry."""
    return ProviderRegistry()
