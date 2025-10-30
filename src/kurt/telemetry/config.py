"""Telemetry configuration and opt-out management."""

import json
import os
import uuid
from pathlib import Path
from typing import Optional

# PostHog configuration
POSTHOG_API_KEY = "phc_your_api_key_here"  # Replace with actual key
POSTHOG_HOST = "https://us.i.posthog.com"  # US region


def get_telemetry_dir() -> Path:
    """Get the directory for telemetry configuration.

    Returns:
        Path to ~/.kurt directory
    """
    home = Path.home()
    telemetry_dir = home / ".kurt"
    telemetry_dir.mkdir(exist_ok=True)
    return telemetry_dir


def get_telemetry_config_path() -> Path:
    """Get the path to telemetry configuration file.

    Returns:
        Path to telemetry.json
    """
    return get_telemetry_dir() / "telemetry.json"


def get_machine_id() -> str:
    """Get or create a unique machine ID for analytics.

    This is a hashed identifier, not tied to any personal information.
    Stored in ~/.kurt/machine_id

    Returns:
        UUID string identifying this machine
    """
    machine_id_path = get_telemetry_dir() / "machine_id"

    if machine_id_path.exists():
        return machine_id_path.read_text().strip()

    # Generate new machine ID
    machine_id = str(uuid.uuid4())
    machine_id_path.write_text(machine_id)
    return machine_id


def is_ci_environment() -> bool:
    """Check if running in a CI/CD environment.

    Returns:
        True if running in CI
    """
    ci_env_vars = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "BUILD_NUMBER",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "CIRCLECI",
        "TRAVIS",
        "JENKINS_HOME",
    ]
    return any(os.getenv(var) for var in ci_env_vars)


def is_telemetry_enabled() -> bool:
    """Check if telemetry is enabled.

    Telemetry is disabled if:
    1. DO_NOT_TRACK environment variable is set
    2. KURT_TELEMETRY_DISABLED environment variable is set
    3. User has explicitly disabled via config file

    Returns:
        True if telemetry should be collected
    """
    # Check DO_NOT_TRACK (universal opt-out)
    if os.getenv("DO_NOT_TRACK"):
        return False

    # Check KURT_TELEMETRY_DISABLED (Kurt-specific opt-out)
    if os.getenv("KURT_TELEMETRY_DISABLED"):
        return False

    # Check user config file
    config_path = get_telemetry_config_path()
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            return config.get("enabled", True)
        except (json.JSONDecodeError, KeyError):
            # If config is malformed, default to enabled
            return True

    # Default: enabled (with first-run notice shown by CLI)
    return True


def set_telemetry_enabled(enabled: bool) -> None:
    """Enable or disable telemetry.

    Args:
        enabled: Whether to enable telemetry
    """
    config_path = get_telemetry_config_path()

    # Load existing config or create new one
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except json.JSONDecodeError:
            config = {}

    config["enabled"] = enabled

    # Write config
    config_path.write_text(json.dumps(config, indent=2))


def get_telemetry_status() -> dict:
    """Get current telemetry status and configuration.

    Returns:
        Dictionary with telemetry status information
    """
    enabled = is_telemetry_enabled()
    config_path = get_telemetry_config_path()

    # Determine why telemetry is disabled (if it is)
    disabled_reason: Optional[str] = None
    if not enabled:
        if os.getenv("DO_NOT_TRACK"):
            disabled_reason = "DO_NOT_TRACK environment variable"
        elif os.getenv("KURT_TELEMETRY_DISABLED"):
            disabled_reason = "KURT_TELEMETRY_DISABLED environment variable"
        elif config_path.exists():
            disabled_reason = f"User config ({config_path})"

    return {
        "enabled": enabled,
        "disabled_reason": disabled_reason,
        "config_path": str(config_path),
        "machine_id": get_machine_id() if enabled else None,
        "is_ci": is_ci_environment(),
    }
