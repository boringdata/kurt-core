"""Local file fetching."""

from __future__ import annotations

import hashlib
from pathlib import Path


def fetch_from_file(file_path: str) -> tuple[str, dict]:
    """
    Fetch content from a local file.

    Args:
        file_path: Path to local file

    Returns:
        Tuple of (content, metadata_dict)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not readable
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {file_path}")

    # Read file content
    content = path.read_text(encoding="utf-8")

    # Compute fingerprint
    fingerprint = hashlib.md5(content.encode()).hexdigest()

    # Build metadata
    metadata = {
        "fingerprint": fingerprint,
        "file_path": str(path.resolve()),
        "file_name": path.name,
        "file_extension": path.suffix.lstrip("."),
        "file_size": path.stat().st_size,
    }

    return content, metadata
