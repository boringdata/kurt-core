"""Provider configuration resolution.

Resolves provider-specific configuration by merging settings from multiple
sources in priority order:

    1. CLI overrides (highest priority)
    2. Project config (kurt.toml)
    3. User config (~/.kurt/config.toml)
    4. Provider defaults (from ConfigModel class attribute)

TOML Config Format
------------------
Provider config lives in two TOML files:

- **Project**: ``<project_root>/kurt.toml`` — per-project settings
- **User**: ``~/.kurt/config.toml`` — user-wide defaults

Tool-level settings serve as defaults for all providers of that tool.
Provider-specific settings override tool-level ones::

    # Tool-level defaults apply to all fetch providers
    [tool.fetch]
    timeout = 30

    # Provider-specific overrides for a single provider
    [tool.fetch.providers.firecrawl]
    formats = ["markdown"]
    timeout = 60

    # Map tool example
    [tool.map.providers.crawl]
    max_depth = 3
    max_pages = 500

Precedence (highest to lowest)::

    CLI flags  →  project kurt.toml  →  user ~/.kurt/config.toml  →  ConfigModel defaults

Each provider may declare a ``ConfigModel`` (Pydantic BaseModel) class
attribute that defines valid fields, types, and constraints. When a
``ConfigModel`` is provided to ``resolve()``, the merged dict is validated
against it and returned as a model instance.

Usage::

    resolver = get_provider_config_resolver()
    config = resolver.resolve("fetch", "firecrawl", FirecrawlConfig,
                              cli_overrides={"timeout": 120})
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def _load_toml_file(path: Path) -> dict:
    """Load a TOML file, returning empty dict if not found."""
    if not path.exists():
        return {}
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


class ProviderConfigResolver:
    """Resolves provider configuration from project, user, and CLI sources.

    Configuration is read from TOML files at two locations:
    - Project: ``<project_root>/kurt.toml``
    - User: ``~/.kurt/config.toml``

    Provider settings live under ``[tool.<tool>.providers.<provider>]``.
    Tool-level settings under ``[tool.<tool>]`` serve as defaults for all
    providers of that tool.

    Thread-safe singleton; call :func:`get_provider_config_resolver` to obtain.
    """

    _instance: ProviderConfigResolver | None = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> ProviderConfigResolver:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._project_data = None
                cls._instance._user_data = None
                cls._instance._project_root = None
            return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        tool_name: str,
        provider_name: str,
        config_model: type[T] | None = None,
        *,
        cli_overrides: dict[str, Any] | None = None,
        project_root: Path | None = None,
    ) -> T | dict[str, Any]:
        """Resolve provider configuration.

        Merges settings from (lowest to highest priority):
        4. Provider defaults (from config_model)
        3. User config  (~/.kurt/config.toml)
        2. Project config (kurt.toml)
        1. CLI overrides

        Args:
            tool_name: Tool name (e.g., "fetch").
            provider_name: Provider name (e.g., "notion").
            config_model: Optional Pydantic model for validation. If provided,
                the merged dict is validated and returned as a model instance.
                If None, returns a plain dict.
            cli_overrides: CLI argument overrides (highest priority).
            project_root: Explicit project root. If None, uses CWD or
                searches up for kurt.toml.

        Returns:
            Validated config_model instance (if config_model given),
            otherwise a plain dict.
        """
        merged: dict[str, Any] = {}

        # 4. Provider defaults (from config_model)
        if config_model is not None:
            for field_name, field_info in config_model.model_fields.items():
                if field_info.default is not None:
                    merged[field_name] = field_info.default

        # 3. User config
        user = self._get_user_data()
        user_tool = _deep_get(user, "tool", tool_name) or {}
        user_provider = _deep_get(user_tool, "providers", provider_name) or {}
        # Tool-level settings as base, provider-level overrides
        merged.update(_exclude_nested(user_tool))
        merged.update(user_provider)

        # 2. Project config
        project = self._get_project_data(project_root)
        project_tool = _deep_get(project, "tool", tool_name) or {}
        project_provider = _deep_get(project_tool, "providers", provider_name) or {}
        merged.update(_exclude_nested(project_tool))
        merged.update(project_provider)

        # 1. CLI overrides (highest priority)
        if cli_overrides:
            # Filter out None values from CLI (unset flags)
            merged.update({k: v for k, v in cli_overrides.items() if v is not None})

        # Remove internal keys that shouldn't be in provider config
        merged.pop("providers", None)
        merged.pop("provider", None)

        if config_model is not None:
            return config_model.model_validate(merged)
        return merged

    def resolve_tool_config(
        self,
        tool_name: str,
        *,
        cli_overrides: dict[str, Any] | None = None,
        project_root: Path | None = None,
    ) -> dict[str, Any]:
        """Resolve tool-level configuration (not provider-specific).

        Merges user and project ``[tool.<name>]`` sections.

        Args:
            tool_name: Tool name (e.g., "fetch").
            cli_overrides: CLI argument overrides.
            project_root: Explicit project root.

        Returns:
            Dict of merged tool configuration.
        """
        merged: dict[str, Any] = {}

        # User config
        user = self._get_user_data()
        user_tool = _deep_get(user, "tool", tool_name) or {}
        merged.update(_exclude_nested(user_tool))

        # Project config
        project = self._get_project_data(project_root)
        project_tool = _deep_get(project, "tool", tool_name) or {}
        merged.update(_exclude_nested(project_tool))

        # CLI overrides
        if cli_overrides:
            merged.update({k: v for k, v in cli_overrides.items() if v is not None})

        return merged

    def reset(self) -> None:
        """Clear cached config data (for testing)."""
        with self._lock:
            self._project_data = None
            self._user_data = None
            self._project_root = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_project_data(self, project_root: Path | None = None) -> dict:
        """Get project TOML data, caching on first load."""
        if project_root is not None:
            # Explicit root - load fresh (don't cache to avoid stale data)
            return _load_toml_file(project_root / "kurt.toml")

        if self._project_data is None:
            root = self._find_project_root()
            if root:
                self._project_data = _load_toml_file(root / "kurt.toml")
                self._project_root = root
            else:
                self._project_data = {}
        return self._project_data

    def _get_user_data(self) -> dict:
        """Get user TOML data, caching on first load."""
        if self._user_data is None:
            user_config = Path.home() / ".kurt" / "config.toml"
            self._user_data = _load_toml_file(user_config)
        return self._user_data

    def _find_project_root(self) -> Path | None:
        """Find project root by searching up for kurt.toml."""
        current = Path.cwd()
        for parent in [current, *current.parents]:
            if (parent / "kurt.toml").exists():
                return parent
        return None


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _deep_get(data: dict, *keys: str) -> Any:
    """Safely traverse nested dicts."""
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
        if data is None:
            return None
    return data


def _exclude_nested(d: dict) -> dict:
    """Return only scalar (non-dict) values from a dict."""
    return {k: v for k, v in d.items() if not isinstance(v, dict)}


# ------------------------------------------------------------------
# Public accessor
# ------------------------------------------------------------------


def get_provider_config_resolver() -> ProviderConfigResolver:
    """Get or create the global ProviderConfigResolver singleton."""
    return ProviderConfigResolver()
