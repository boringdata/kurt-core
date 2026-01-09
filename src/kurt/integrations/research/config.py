"""
Research configuration management for Kurt.

Loads research API credentials from kurt.config file.
Research configs are stored with RESEARCH_<SOURCE>_<KEY> format.
Example: RESEARCH_PERPLEXITY_API_KEY=pplx_abc123
"""

from typing import Any

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


def load_research_config() -> dict[str, dict[str, Any]]:
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
      }
    }

    Returns:
        Dictionary with research API configurations organized by source

    Raises:
        FileNotFoundError: If kurt.config doesn't exist
    """
    return load_prefixed_config(_PREFIX, _LEVELS)


def save_research_config(research_config: dict[str, dict[str, Any]]) -> None:
    """
    Save research configuration to kurt.config.

    Args:
        research_config: Research configuration dictionary organized by source
            Example: {"perplexity": {"api_key": "pplx_123", "default_model": "sonar-reasoning"}}
    """
    save_prefixed_config(_PREFIX, research_config, _LEVELS)


def get_source_config(source: str) -> dict[str, Any]:
    """
    Get configuration for a specific research source.

    Args:
        source: Research source name (e.g., 'perplexity')

    Returns:
        Source-specific configuration dictionary

    Raises:
        ValueError: If source not configured
    """
    config = load_research_config()

    if source not in config:
        available = ", ".join(config.keys()) if config else "none configured"
        raise ValueError(
            f"No configuration found for research source '{source}'.\n"
            f"Available sources: {available}\n"
            f"\n"
            f"To configure {source}, add to kurt.config:\n"
            f"  RESEARCH_{source.upper()}_API_KEY=your_api_key_here"
        )

    # Check for placeholder API key
    source_config = config[source]
    api_key = source_config.get("api_key", "")
    if "YOUR_" in api_key or "PLACEHOLDER" in api_key:
        raise ValueError(
            f"API key not configured for '{source}'.\n"
            f"\n"
            f"Edit kurt.config and update:\n"
            f"  RESEARCH_{source.upper()}_API_KEY=your_actual_api_key"
        )

    return source_config


def add_source_config(source: str, source_config: dict[str, Any]) -> None:
    """
    Add or update configuration for a research source.

    Args:
        source: Research source name (e.g., 'perplexity')
        source_config: Source-specific configuration dictionary
    """
    config = load_research_config()
    config[source] = source_config
    save_research_config(config)


def create_template_config(source: str) -> dict[str, Any]:
    """
    Get template configuration structure for a research source.

    Args:
        source: Research source name

    Returns:
        Template configuration dictionary with placeholder values
    """
    if source == "perplexity":
        return {
            "api_key": "YOUR_PERPLEXITY_API_KEY",
            "default_model": "sonar-reasoning",
            "default_recency": "day",
            "max_tokens": "4000",
            "temperature": "0.2",
        }
    else:
        return {
            "api_key": "YOUR_API_KEY",
        }


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
    except Exception:
        return False


def list_sources() -> list[str]:
    """
    List all configured research sources.

    Returns:
        List of source names
    """
    try:
        config = load_research_config()
        return list(config.keys())
    except Exception:
        return []
