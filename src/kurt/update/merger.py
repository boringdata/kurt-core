"""Smart merge strategies for configuration files."""

import json
from pathlib import Path
from typing import Any


def merge_settings_json(local_path: Path, package_path: Path) -> dict[str, Any]:
    """
    Smart merge of Claude Code settings.json files.

    Strategy:
    - Preserve all user settings
    - Update/add Kurt's hooks from package
    - Keep other user-added hooks

    Args:
        local_path: Path to local settings.json
        package_path: Path to package settings.json

    Returns:
        Merged settings dictionary
    """
    # Load package settings (Kurt's defaults)
    with open(package_path) as f:
        kurt_settings = json.load(f)

    # Load existing settings (if exists)
    if local_path.exists():
        with open(local_path) as f:
            local_settings = json.load(f)
    else:
        local_settings = {}

    # Start with local settings as base
    merged = local_settings.copy()

    # Ensure hooks key exists
    if "hooks" not in merged:
        merged["hooks"] = {}

    # Update Kurt's hooks from package
    # This preserves user's custom hooks while updating Kurt's hooks
    kurt_hooks = kurt_settings.get("hooks", {})
    merged["hooks"].update(kurt_hooks)

    return merged


def apply_settings_merge(local_path: Path, package_path: Path) -> None:
    """
    Apply merged settings to local file.

    Args:
        local_path: Path to local settings.json
        package_path: Path to package settings.json
    """
    merged = merge_settings_json(local_path, package_path)

    # Write merged settings
    local_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_path, "w") as f:
        json.dump(merged, f, indent=2)
