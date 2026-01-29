"""Unified API key management for engines.

Provides a standard pattern for API key handling across all engines:
- Environment variables (highest priority)
- kurt.config file (medium priority)
- Error with helpful setup instructions (default)

Supports multiple keys per engine for rotation strategies.
"""

import os
from typing import Dict, List, Optional


class APIKeyError(Exception):
    """Raised when API key is missing or invalid."""

    pass


class APIKeyManager:
    """Manages API keys for multiple engines.

    Provides consistent API key resolution with helpful error messages
    for setup and configuration.
    """

    def __init__(self):
        """Initialize the API key manager."""
        self._keys: Dict[str, List[str]] = {}
        self._env_var_map: Dict[str, str] = {}
        self._config_key_map: Dict[str, str] = {}
        self._setup_instructions: Dict[str, str] = {}

    def register_engine(
        self,
        engine: str,
        env_var: str,
        config_key: Optional[str] = None,
        setup_instructions: Optional[str] = None,
    ) -> None:
        """Register an engine and its API key sources.

        Args:
            engine: Engine name (e.g., 'apify', 'firecrawl')
            env_var: Environment variable name (e.g., 'APIFY_API_KEY')
            config_key: Key path in kurt.config (e.g., 'INTEGRATIONS.APIFY.KEY')
            setup_instructions: Setup help text to show on error
        """
        self._env_var_map[engine] = env_var
        if config_key:
            self._config_key_map[engine] = config_key
        if setup_instructions:
            self._setup_instructions[engine] = setup_instructions
        if engine not in self._keys:
            self._keys[engine] = []

    def add_key(self, engine: str, key: str) -> None:
        """Add an API key for an engine (for rotation strategies).

        Args:
            engine: Engine name
            key: API key value

        Raises:
            ValueError: If engine not registered
        """
        if engine not in self._env_var_map:
            raise ValueError(f"Engine not registered: {engine}")

        if key and key not in self._keys[engine]:
            self._keys[engine].append(key)

    def get_key(self, engine: str, raise_on_missing: bool = True) -> Optional[str]:
        """Get primary API key for an engine.

        Resolution order:
        1. Environment variable
        2. Previously loaded keys (from config)
        3. Error with setup instructions

        Args:
            engine: Engine name
            raise_on_missing: Raise APIKeyError if key not found

        Returns:
            API key string or None

        Raises:
            APIKeyError: If key not found and raise_on_missing=True
        """
        if engine not in self._env_var_map:
            raise ValueError(f"Engine not registered: {engine}")

        env_var = self._env_var_map[engine]

        # Check environment variable first
        env_key = os.environ.get(env_var)
        if env_key:
            return env_key

        # Check loaded keys
        if engine in self._keys and self._keys[engine]:
            return self._keys[engine][0]

        # Not found
        if raise_on_missing:
            raise self._create_api_key_error(engine)

        return None

    def get_all_keys(self, engine: str) -> List[str]:
        """Get all API keys for an engine (for rotation).

        Args:
            engine: Engine name

        Returns:
            List of API keys, primary first
        """
        if engine not in self._env_var_map:
            raise ValueError(f"Engine not registered: {engine}")

        env_var = self._env_var_map[engine]
        env_key = os.environ.get(env_var)

        if env_key:
            # Return env key first, then any loaded keys
            return [env_key] + [k for k in self._keys.get(engine, []) if k != env_key]

        return self._keys.get(engine, [])

    def load_from_config(
        self,
        config: Dict,
    ) -> None:
        """Load API keys from a config dictionary.

        Args:
            config: Configuration dictionary (typically from kurt.config)
        """
        for engine, config_key in self._config_key_map.items():
            try:
                # Navigate nested keys (e.g., 'INTEGRATIONS.APIFY.KEY')
                parts = config_key.split(".")
                value = config
                for part in parts:
                    value = value.get(part, {})
                    if isinstance(value, dict) and part != parts[-1]:
                        continue
                    elif not isinstance(value, dict):
                        break

                if isinstance(value, str) and value:
                    self.add_key(engine, value)
            except (AttributeError, TypeError, KeyError):
                # Skip if config structure doesn't match
                pass

    def validate_key(
        self,
        engine: str,
        key: str,
        validation_fn: Optional[callable] = None,
    ) -> bool:
        """Validate an API key.

        Args:
            engine: Engine name
            key: API key to validate
            validation_fn: Optional custom validation function

        Returns:
            True if valid, False otherwise
        """
        if not key or not isinstance(key, str):
            return False

        if validation_fn:
            try:
                return validation_fn(key)
            except Exception:
                return False

        # Basic validation: keys should be non-empty strings
        return len(key.strip()) > 0

    def _create_api_key_error(self, engine: str) -> APIKeyError:
        """Create detailed API key error with setup instructions."""
        env_var = self._env_var_map[engine]
        config_key = self._config_key_map.get(engine, "N/A")

        error_msg = (
            f"API key for '{engine}' not found.\n\n"
            f"Set the key using one of these methods:\n\n"
            f"1. Environment variable:\n"
            f"   export {env_var}=<your-key>\n\n"
        )

        if config_key != "N/A":
            error_msg += (
                f"2. In kurt.config:\n"
                f"   {config_key}=<your-key>\n\n"
            )

        if engine in self._setup_instructions:
            error_msg += f"Setup instructions:\n{self._setup_instructions[engine]}\n"

        return APIKeyError(error_msg)

    def list_engines(self) -> List[str]:
        """List all registered engines."""
        return list(self._env_var_map.keys())

    def is_configured(self, engine: str) -> bool:
        """Check if an engine has a configured API key.

        Args:
            engine: Engine name

        Returns:
            True if key is available, False otherwise
        """
        try:
            key = self.get_key(engine, raise_on_missing=False)
            return key is not None
        except ValueError:
            return False


# Global API key manager instance
_global_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    """Get or create the global API key manager."""
    global _global_key_manager
    if _global_key_manager is None:
        _global_key_manager = APIKeyManager()
    return _global_key_manager


def register_engine(
    engine: str,
    env_var: str,
    config_key: Optional[str] = None,
    setup_instructions: Optional[str] = None,
) -> None:
    """Register an engine with the global key manager.

    Args:
        engine: Engine name
        env_var: Environment variable name
        config_key: Config file key path
        setup_instructions: Setup help text
    """
    get_key_manager().register_engine(
        engine=engine,
        env_var=env_var,
        config_key=config_key,
        setup_instructions=setup_instructions,
    )


def get_api_key(
    engine: str,
    raise_on_missing: bool = True,
) -> Optional[str]:
    """Get API key for an engine using the global manager.

    Args:
        engine: Engine name
        raise_on_missing: Raise error if key not found

    Returns:
        API key or None

    Raises:
        APIKeyError: If key not found and raise_on_missing=True
    """
    return get_key_manager().get_key(engine, raise_on_missing=raise_on_missing)


def configure_engines() -> None:
    """Register all known engines with the global key manager.

    Should be called during application initialization.
    """
    # Apify
    register_engine(
        engine="apify",
        env_var="APIFY_API_KEY",
        config_key="INTEGRATIONS.APIFY.API_KEY",
        setup_instructions=(
            "Get your Apify API key from: https://console.apify.com/account/integrations\n"
            "Required for: Twitter, LinkedIn, and custom scraping tasks"
        ),
    )

    # Firecrawl
    register_engine(
        engine="firecrawl",
        env_var="FIRECRAWL_API_KEY",
        config_key="INTEGRATIONS.FIRECRAWL.API_KEY",
        setup_instructions=(
            "Get your Firecrawl API key from: https://www.firecrawl.dev\n"
            "Required for: Advanced web content extraction"
        ),
    )

    # Tavily
    register_engine(
        engine="tavily",
        env_var="TAVILY_API_KEY",
        config_key="INTEGRATIONS.TAVILY.API_KEY",
        setup_instructions=(
            "Get your Tavily API key from: https://tavily.com\n"
            "Required for: Web search and research"
        ),
    )
