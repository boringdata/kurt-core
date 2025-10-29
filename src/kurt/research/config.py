"""
Research configuration management for Kurt.

Loads research API credentials from .kurt/research-config.json.
"""

import json
from pathlib import Path
from typing import Any, Dict

from kurt.config import load_config


def get_research_config_path() -> Path:
    """
    Get the path to the research configuration file.

    Returns:
        Path to .kurt/research-config.json in the Kurt project directory
    """
    project_config = load_config()
    kurt_dir = project_config.get_db_directory()
    return kurt_dir / "research-config.json"


def load_research_config() -> Dict[str, Any]:
    """
    Load research configuration from .kurt/research-config.json.

    The config file format:
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
        Dictionary with research API configurations

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid JSON
    """
    config_path = get_research_config_path()

    if not config_path.exists():
        raise FileNotFoundError(
            f"Research configuration file not found: {config_path}\n"
            f"Create this file with your research API credentials.\n"
            f"See .kurt/README.md for setup instructions."
        )

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in research config file: {config_path}\n{e}")

    return config


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
        raise ValueError(
            f"No configuration found for research source '{source}'.\n"
            f"Available sources: {', '.join(config.keys())}\n"
            f"Add configuration to .kurt/research-config.json"
        )

    # Check for placeholder API key
    source_config = config[source]
    api_key = source_config.get("api_key", "")
    if "YOUR_" in api_key or "PLACEHOLDER" in api_key:
        raise ValueError(
            f"API key not configured for '{source}'.\n"
            f"Edit .kurt/research-config.json and add your API key.\n"
            f"See .kurt/README.md for setup instructions."
        )

    return source_config


def research_config_exists() -> bool:
    """Check if research configuration file exists."""
    return get_research_config_path().exists()


def source_configured(source: str) -> bool:
    """
    Check if a specific source is configured.

    Args:
        source: Research source name

    Returns:
        True if source is configured with valid API key
    """
    if not research_config_exists():
        return False

    try:
        config = load_research_config()
        if source not in config:
            return False

        source_config = config[source]
        api_key = source_config.get("api_key", "")

        # Check for placeholder values
        if "YOUR_" in api_key or "PLACEHOLDER" in api_key or not api_key:
            return False

        return True
    except (FileNotFoundError, ValueError):
        return False
