"""File hash tracking for detecting modifications."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_installed_files_path() -> Path:
    """Get path to installed_files.json tracking file."""
    return Path.cwd() / ".kurt" / "installed_files.json"


def load_installed_files() -> dict[str, dict[str, Any]]:
    """
    Load installed file tracking data.

    Returns:
        Dict mapping relative file paths to metadata:
        {
            ".claude/CLAUDE.md": {
                "hash": "abc123...",
                "version": "0.2.7",
                "installed_at": "2024-01-15T10:30:00Z"
            }
        }
    """
    tracking_file = get_installed_files_path()
    if not tracking_file.exists():
        return {}

    try:
        with open(tracking_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_installed_files(data: dict[str, dict[str, Any]]) -> None:
    """Save installed file tracking data."""
    tracking_file = get_installed_files_path()
    tracking_file.parent.mkdir(parents=True, exist_ok=True)

    with open(tracking_file, "w") as f:
        json.dump(data, f, indent=2)


def record_installed_file(rel_path: str, file_path: Path, version: str | None = None) -> None:
    """
    Record a file's installation metadata.

    Args:
        rel_path: Relative path from project root (e.g., ".claude/CLAUDE.md")
        file_path: Absolute path to the installed file
        version: Kurt version that installed this file
    """
    if not file_path.exists():
        return

    data = load_installed_files()
    file_hash = compute_file_hash(file_path)

    data[rel_path] = {
        "hash": file_hash,
        "version": version or "unknown",
        "installed_at": datetime.utcnow().isoformat() + "Z",
    }

    save_installed_files(data)


def was_file_modified(rel_path: str, file_path: Path) -> bool:
    """
    Check if a file was modified since installation.

    Args:
        rel_path: Relative path from project root
        file_path: Absolute path to the file

    Returns:
        True if file was modified by user, False if unchanged or not tracked
    """
    if not file_path.exists():
        return False

    data = load_installed_files()
    if rel_path not in data:
        # Not tracked, consider it user-created
        return True

    original_hash = data[rel_path]["hash"]
    current_hash = compute_file_hash(file_path)

    return original_hash != current_hash


def get_file_version(rel_path: str) -> str | None:
    """Get the Kurt version that installed a file."""
    data = load_installed_files()
    if rel_path in data:
        return data[rel_path].get("version")
    return None


def remove_tracked_file(rel_path: str) -> None:
    """Remove a file from tracking (e.g., when deleted)."""
    data = load_installed_files()
    if rel_path in data:
        del data[rel_path]
        save_installed_files(data)
