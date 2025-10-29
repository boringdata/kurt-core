"""
Monitoring configuration management for project-based research.
"""

from pathlib import Path
from typing import Any, Dict, List

import yaml


def get_monitoring_config_path(project_path: str) -> Path:
    """
    Get the monitoring config path for a project.

    Args:
        project_path: Path to project directory

    Returns:
        Path to monitoring-config.yaml
    """
    return Path(project_path) / "monitoring-config.yaml"


def load_monitoring_config(project_path: str) -> Dict[str, Any]:
    """
    Load monitoring configuration for a project.

    Args:
        project_path: Path to project directory

    Returns:
        Dictionary with monitoring configuration

    Raises:
        FileNotFoundError: If config doesn't exist
        ValueError: If config is invalid
    """
    config_path = get_monitoring_config_path(project_path)

    if not config_path.exists():
        raise FileNotFoundError(
            f"Monitoring config not found: {config_path}\n"
            f"Create monitoring-config.yaml in your project directory.\n"
            f"See projects/.monitoring-config-template.yaml for example."
        )

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in monitoring config: {config_path}\n{e}")

    return config


def monitoring_config_exists(project_path: str) -> bool:
    """Check if monitoring config exists for a project."""
    return get_monitoring_config_path(project_path).exists()


def get_project_research_dir(project_path: str) -> Path:
    """
    Get the research directory for a project.

    Args:
        project_path: Path to project directory

    Returns:
        Path to research/ directory (creates if doesn't exist)
    """
    research_dir = Path(project_path) / "research"
    research_dir.mkdir(parents=True, exist_ok=True)
    return research_dir


def get_project_signals_dir(project_path: str) -> Path:
    """
    Get the signals directory for a project.

    Args:
        project_path: Path to project directory

    Returns:
        Path to research/signals/ directory (creates if doesn't exist)
    """
    signals_dir = get_project_research_dir(project_path) / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)
    return signals_dir


def get_enabled_sources(config: Dict[str, Any]) -> List[str]:
    """
    Get list of enabled monitoring sources from config.

    Args:
        config: Monitoring configuration dictionary

    Returns:
        List of enabled source names (e.g., ["reddit", "hackernews"])
    """
    sources = config.get("sources", {})
    enabled = []

    for source_name, source_config in sources.items():
        if isinstance(source_config, dict) and source_config.get("enabled", False):
            enabled.append(source_name)

    return enabled


def validate_monitoring_config(config: Dict[str, Any]) -> List[str]:
    """
    Validate monitoring configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of validation warnings (empty if valid)
    """
    warnings = []

    # Check for project_name
    if not config.get("project_name"):
        warnings.append("Missing project_name")

    # Check sources
    sources = config.get("sources", {})
    if not sources:
        warnings.append("No monitoring sources configured")

    enabled_sources = get_enabled_sources(config)
    if not enabled_sources:
        warnings.append("No monitoring sources enabled")

    # Validate Reddit config
    if "reddit" in enabled_sources:
        reddit_config = sources.get("reddit", {})
        if not reddit_config.get("subreddits"):
            warnings.append("Reddit enabled but no subreddits specified")

    # Validate feeds config
    if "feeds" in enabled_sources:
        feeds_config = sources.get("feeds", {})
        if not feeds_config.get("urls"):
            warnings.append("Feeds enabled but no URLs specified")

    return warnings
