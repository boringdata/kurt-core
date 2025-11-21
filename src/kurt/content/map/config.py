"""
Configuration management for content map updates.

This module handles configuration for:
- Auto-fetch settings
- Update schedules
- Source priorities
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_update_config_path() -> Path:
    """Get path to update configuration file."""
    return Path.cwd() / ".kurt" / "update-config.yaml"


def create_default_update_config() -> dict[str, Any]:
    """
    Create default update configuration.

    Returns:
        dict with default settings
    """
    return {
        "auto_fetch": {
            "enabled": False,
            "max_new_documents": 50,
            "strategy": "sample",  # "sample" or "all"
            "priority_new": True,
        },
        "sources": {
            "cms": {
                "enabled": True,
                "refresh_on_update": True,
            },
            "websites": {
                "enabled": True,
                "refresh_on_update": True,
                "max_pages_per_source": 1000,
            },
        },
        "schedule": {
            "enabled": False,
            "cron": "0 2 * * *",  # Daily at 2am
            "timezone": "UTC",
        },
    }


def load_update_config() -> dict[str, Any]:
    """
    Load update configuration from file.

    If file doesn't exist, returns default config.

    Returns:
        dict with configuration settings
    """
    import yaml

    config_path = get_update_config_path()

    if not config_path.exists():
        logger.debug("Update config not found, using defaults")
        return create_default_update_config()

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
            logger.debug(f"Loaded update config from {config_path}")
            return config
    except Exception as e:
        logger.warning(f"Could not load update config: {e}, using defaults")
        return create_default_update_config()


def save_update_config(config: dict[str, Any]) -> None:
    """
    Save update configuration to file.

    Args:
        config: Configuration dictionary to save
    """
    config_path = get_update_config_path()

    # Ensure .kurt directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved update config to {config_path}")
    except Exception as e:
        logger.error(f"Could not save update config: {e}")
        raise


def init_update_config(interactive: bool = True) -> dict[str, Any]:
    """
    Initialize update configuration with user input or defaults.

    Args:
        interactive: Whether to prompt user for values

    Returns:
        dict with configuration settings
    """
    config = create_default_update_config()

    if not interactive:
        save_update_config(config)
        return config

    from rich.console import Console

    console = Console()

    console.print("[bold]Content Map Update Configuration[/bold]\n")

    # Auto-fetch settings
    console.print("[bold cyan]Auto-Fetch Settings[/bold cyan]")
    console.print("[dim]Automatically fetch content after discovering new documents[/dim]\n")

    enable_auto_fetch = console.input("  Enable auto-fetch? [y/N]: ").strip().lower() in [
        "y",
        "yes",
    ]
    config["auto_fetch"]["enabled"] = enable_auto_fetch

    if enable_auto_fetch:
        max_docs_input = console.input("  Max documents to auto-fetch [50]: ").strip()
        if max_docs_input:
            try:
                config["auto_fetch"]["max_new_documents"] = int(max_docs_input)
            except ValueError:
                console.print("    [yellow]Invalid number, using default (50)[/yellow]")

        strategy_input = console.input("  Strategy (sample/all) [sample]: ").strip().lower()
        if strategy_input in ["all", "sample"]:
            config["auto_fetch"]["strategy"] = strategy_input

    console.print()

    # Source settings
    console.print("[bold cyan]Source Settings[/bold cyan]")
    console.print("[dim]Control which sources to refresh during updates[/dim]\n")

    refresh_cms = console.input("  Refresh CMS sources? [Y/n]: ").strip().lower() not in ["n", "no"]
    config["sources"]["cms"]["refresh_on_update"] = refresh_cms

    refresh_websites = console.input("  Refresh website sources? [Y/n]: ").strip().lower() not in [
        "n",
        "no",
    ]
    config["sources"]["websites"]["refresh_on_update"] = refresh_websites

    if refresh_websites:
        max_pages_input = console.input("  Max pages per website [1000]: ").strip()
        if max_pages_input:
            try:
                config["sources"]["websites"]["max_pages_per_source"] = int(max_pages_input)
            except ValueError:
                console.print("    [yellow]Invalid number, using default (1000)[/yellow]")

    console.print()

    # Schedule settings
    console.print("[bold cyan]Schedule Settings[/bold cyan]")
    console.print("[dim]Configure automatic periodic updates (requires scheduler)[/dim]\n")

    enable_schedule = console.input("  Enable scheduled updates? [y/N]: ").strip().lower() in [
        "y",
        "yes",
    ]
    config["schedule"]["enabled"] = enable_schedule

    if enable_schedule:
        cron_input = console.input("  Cron expression [0 2 * * *]: ").strip()
        if cron_input:
            config["schedule"]["cron"] = cron_input

        timezone_input = console.input("  Timezone [UTC]: ").strip()
        if timezone_input:
            config["schedule"]["timezone"] = timezone_input

    console.print()

    # Save configuration
    save_update_config(config)

    console.print("[green]✓ Configuration saved[/green]")
    console.print(f"  Location: [cyan]{get_update_config_path()}[/cyan]\n")

    console.print("[bold]Next steps:[/bold]")
    console.print("  • Run update: [cyan]kurt content update[/cyan]")
    console.print(
        "  • Configure sources: [cyan]kurt integrations cms onboard[/cyan] or [cyan]kurt content map[/cyan]"
    )
    console.print()

    return config


def get_auto_fetch_config() -> dict[str, Any]:
    """
    Get auto-fetch configuration (for use in workflow).

    Checks in order:
    1. Environment variables
    2. Config file
    3. Defaults

    Returns:
        dict with auto-fetch settings
    """
    import os

    # Start with config file
    config = load_update_config()
    auto_fetch = config.get("auto_fetch", {})

    # Override with environment variables
    if os.getenv("KURT_AUTO_FETCH_ENABLED"):
        auto_fetch["enabled"] = os.getenv("KURT_AUTO_FETCH_ENABLED", "").lower() in [
            "true",
            "1",
            "yes",
        ]

    if os.getenv("KURT_AUTO_FETCH_MAX_DOCUMENTS"):
        try:
            auto_fetch["max_new_documents"] = int(os.getenv("KURT_AUTO_FETCH_MAX_DOCUMENTS"))
        except ValueError:
            pass

    if os.getenv("KURT_AUTO_FETCH_STRATEGY") in ["all", "sample"]:
        auto_fetch["strategy"] = os.getenv("KURT_AUTO_FETCH_STRATEGY")

    return auto_fetch


__all__ = [
    "load_update_config",
    "save_update_config",
    "init_update_config",
    "get_auto_fetch_config",
    "create_default_update_config",
    "get_update_config_path",
]
