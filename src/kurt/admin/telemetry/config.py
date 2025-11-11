"""Telemetry configuration and opt-out management."""

import os
import uuid
from pathlib import Path
from typing import Optional

# PostHog configuration (hardcoded for CLI telemetry)
# Note: This is different from analytics config in .kurt/analytics-config.json
# which is for tracking user website analytics (e.g., docs site pageviews)
POSTHOG_API_KEY = "phc_N5KayyK6mLeh4U2hrdAxbhyaLN31E2q41OKv9DbWEGf"
POSTHOG_HOST = "https://us.i.posthog.com"  # US region


def get_telemetry_dir() -> Path:
    """Get the directory for telemetry-specific files (machine_id).

    Returns:
        Path to ~/.kurt directory for machine ID storage
    """
    home = Path.home()
    telemetry_dir = home / ".kurt"
    telemetry_dir.mkdir(exist_ok=True)
    return telemetry_dir


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
    3. User has explicitly disabled via kurt.config (TELEMETRY_ENABLED=False)

    Returns:
        True if telemetry should be collected
    """
    # Check DO_NOT_TRACK (universal opt-out)
    if os.getenv("DO_NOT_TRACK"):
        return False

    # Check KURT_TELEMETRY_DISABLED (Kurt-specific opt-out)
    if os.getenv("KURT_TELEMETRY_DISABLED"):
        return False

    # Check user config file (kurt.config)
    try:
        from kurt.config import get_config_or_default

        config = get_config_or_default()
        return config.TELEMETRY_ENABLED
    except Exception:
        # If config can't be loaded, default to enabled
        return True


def set_telemetry_enabled(enabled: bool) -> None:
    """Enable or disable telemetry by updating kurt.config.

    Args:
        enabled: Whether to enable telemetry
    """
    from kurt.config import config_exists, get_config_or_default, update_config

    # Get or create config
    config = get_config_or_default()

    # Update telemetry setting
    config.TELEMETRY_ENABLED = enabled

    # Save config
    if config_exists():
        update_config(config)
    else:
        # If no config exists, we can't save telemetry preference
        # User should run 'kurt init' first
        raise RuntimeError(
            "No kurt.config found. Run 'kurt init' to initialize a Kurt project first."
        )


def get_telemetry_status() -> dict:
    """Get current telemetry status and configuration.

    Returns:
        Dictionary with telemetry status information
    """
    enabled = is_telemetry_enabled()

    # Determine why telemetry is disabled (if it is)
    disabled_reason: Optional[str] = None
    config_path: Optional[str] = None

    # Determine disabled reason (check env vars first, before trying to load config)
    if not enabled:
        if os.getenv("DO_NOT_TRACK"):
            disabled_reason = "DO_NOT_TRACK environment variable"
        elif os.getenv("KURT_TELEMETRY_DISABLED"):
            disabled_reason = "KURT_TELEMETRY_DISABLED environment variable"

    try:
        from kurt.config import config_exists, get_config_file_path

        if config_exists():
            config_path = str(get_config_file_path())
            # If still no reason and config exists, check config file
            if not enabled and not disabled_reason:
                disabled_reason = f"TELEMETRY_ENABLED=False in {config_path}"
    except Exception:
        config_path = "No kurt.config found"

    return {
        "enabled": enabled,
        "disabled_reason": disabled_reason,
        "config_path": config_path,
        "machine_id": get_machine_id() if enabled else None,
        "is_ci": is_ci_environment(),
    }
