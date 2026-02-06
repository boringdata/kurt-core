"""Folder discovery helper - thin wrapper around engines/folder.py.

This module provides backward compatibility for existing code using
discover_from_folder(). New code should use FolderEngine from engines/folder.py.
"""

from __future__ import annotations

from pathlib import Path


def discover_from_folder(
    folder_path: str,
    *,
    include_patterns: tuple[str, ...] = (),
    exclude_patterns: tuple[str, ...] = (),
) -> dict:
    """Discover markdown files from a local folder.

    This is a backward-compatible wrapper around the canonical implementation
    in engines/folder.py. New code should use FolderEngine directly.

    Args:
        folder_path: Path to folder to discover from
        include_patterns: Glob patterns to include
        exclude_patterns: Glob patterns to exclude

    Returns:
        Dict with discovered files and metadata
    """
    from kurt.tools.map.engines.folder import discover_from_folder_impl

    return discover_from_folder_impl(
        folder_path=folder_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )


# Re-export helper functions for backward compatibility
def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file content for deduplication.

    Backward-compatible wrapper. Import from engines/folder.py for new code.
    """
    from kurt.tools.map.engines.folder import compute_file_hash as _compute_file_hash

    return _compute_file_hash(file_path)


def discover_markdown_files(directory: Path, recursive: bool = True) -> list[Path]:
    """Discover markdown files in a directory.

    Backward-compatible wrapper. Import from engines/folder.py for new code.
    """
    from kurt.tools.map.engines.folder import discover_markdown_files as _discover_markdown_files

    return _discover_markdown_files(directory, recursive=recursive)


def _extract_title(file_path: Path) -> str:
    """Extract title from markdown file.

    Backward-compatible wrapper. Import from engines/folder.py for new code.
    """
    from kurt.tools.map.engines.folder import _extract_title as _impl_extract_title

    return _impl_extract_title(file_path)
