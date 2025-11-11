"""
Research configuration management for Kurt.

Loads research API credentials from kurt.config file.
Research configs are stored with RESEARCH_<SOURCE>_<KEY> format.
Example: RESEARCH_PERPLEXITY_API_KEY=pplx_abc123
"""

from typing import Any, Dict

from kurt.config import (
    config_exists_for_prefix,
    get_nested_value,
    has_placeholder_values,
    load_prefixed_config,
    save_prefixed_config,
)

# Research configs have 1 level: SOURCE
# Format: RESEARCH_<SOURCE>_<KEY>
_PREFIX = "RESEARCH"
_LEVELS = 1


def load_research_config() -> Dict[str, Any]:
    """
    Load research configuration from kurt.config.

    Returns research configurations organized by source:
    {
      "perplexity": {
        "api_key": "pplx-...",
        "default_model": "sonar-reasoning",
        "default_recency": "day",
        "max_tokens": 4000,
        "temperature": 0.2
      },
      "tavily": {...},
      "exa": {...}
    }

    Returns:
        Dictionary with research API configurations organized by source

    Raises:
        FileNotFoundError: If no research config found
    """
    config = load_prefixed_config(_PREFIX, _LEVELS)

    if len(config) == 0:
        # Provide helpful error message if no research config found
        from kurt.config import get_config_file_path

        config_path = get_config_file_path()
        raise FileNotFoundError(
            f"Research configuration file not found: {config_path}\n"
            f"Create this file with your research API credentials.\n"
            f"See .kurt/README.md for setup instructions."
        )

    return config


def save_research_config(research_config: Dict[str, Any]) -> None:
    """
    Save research configuration to kurt.config.

    Args:
        research_config: Research configuration dictionary organized by source
            Example: {"perplexity": {"api_key": "pplx_123", "default_model": "sonar-reasoning"}}
    """
    save_prefixed_config(_PREFIX, research_config, _LEVELS)


def get_source_config(source: str) -> Dict[str, Any]:
    """
    Get configuration for a specific research source.

    Args:
        source: Research source name (e.g., 'perplexity', 'tavily')

    Returns:
        Source-specific configuration dictionary

    Raises:
        ValueError: If source not configured
    """
    config = load_research_config()

    if source not in config:
        available = ", ".join(config.keys()) if config else "none configured"
        from kurt.config import get_config_file_path

        config_file = get_config_file_path()
        raise ValueError(
            f"No configuration found for research source '{source}'.\n"
            f"Available sources: {available}\n"
            f"\n"
            f"To configure {source}, add to {config_file}:\n"
            f"  RESEARCH_{source.upper()}_API_KEY=your_api_key_here"
        )

    # Check for placeholder API key
    source_config = config[source]
    api_key = source_config.get("api_key", "")
    if "YOUR_" in api_key or "PLACEHOLDER" in api_key:
        from kurt.config import get_config_file_path

        config_file = get_config_file_path()
        raise ValueError(
            f"API key not configured for '{source}'.\n"
            f"\n"
            f"Edit {config_file} and update:\n"
            f"  RESEARCH_{source.upper()}_API_KEY=your_actual_api_key"
        )

    return source_config


def research_config_exists() -> bool:
    """Check if any research configuration exists in kurt.config."""
    return config_exists_for_prefix(_PREFIX, _LEVELS)


def source_configured(source: str) -> bool:
    """
    Check if a specific source is configured.

    Args:
        source: Research source name

    Returns:
        True if source is configured with valid API key
    """
    try:
        config = load_research_config()
        source_config = get_nested_value(config, [source])

        if not source_config:
            return False

        # Check for placeholder values
        if has_placeholder_values(source_config):
            return False

        # Check for empty API key
        api_key = source_config.get("api_key", "")
        if not api_key:
            return False

        return True
    except (FileNotFoundError, ValueError):
        return False
