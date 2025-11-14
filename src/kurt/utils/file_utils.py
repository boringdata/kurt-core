"""File utility functions."""

import hashlib
from pathlib import Path


def compute_file_hash(file_path: Path) -> str:
    """
    Compute SHA256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        SHA256 hash as hex string

    Example:
        >>> from pathlib import Path
        >>> compute_file_hash(Path("/path/to/file.md"))
        'a1b2c3d4e5f6...'
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
