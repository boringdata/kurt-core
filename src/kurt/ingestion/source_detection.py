"""Source type detection utilities for Kurt ingestion."""

from pathlib import Path
from typing import List, Literal, Tuple

SourceType = Literal["url", "file", "directory"]


def detect_source_type(source: str) -> SourceType:
    """
    Detect if source is a URL, file, or directory.

    Args:
        source: URL or file path string

    Returns:
        "url", "file", or "directory"
    """
    # Check if it's a URL
    if source.startswith(("http://", "https://", "ftp://")):
        return "url"

    # Check if it's a path
    path = Path(source)
    if path.exists():
        if path.is_file():
            return "file"
        elif path.is_dir():
            return "directory"

    # Default: assume URL (will fail gracefully with clear error)
    return "url"


def discover_markdown_files(directory: Path, recursive: bool = True) -> List[Path]:
    """
    Discover all .md files in a directory.

    Args:
        directory: Directory to search
        recursive: If True, search recursively in subdirectories

    Returns:
        List of Path objects to .md files
    """
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    if recursive:
        # Recursive glob
        md_files = list(directory.rglob("*.md"))
    else:
        # Non-recursive glob
        md_files = list(directory.glob("*.md"))

    # Filter out hidden files and directories
    md_files = [f for f in md_files if not any(part.startswith(".") for part in f.parts)]

    return sorted(md_files)


def validate_file_extension(file_path: Path) -> Tuple[bool, str]:
    """
    Validate that file has supported extension (.md only for now).

    Args:
        file_path: Path to file

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    if not file_path.is_file():
        return False, f"Not a file: {file_path}"

    if file_path.suffix.lower() != ".md":
        return False, f"Unsupported file type: {file_path.suffix}. Only .md files are supported."

    return True, ""


def get_relative_path_from_source(file_path: Path, source_root: Path) -> str:
    """
    Get relative path from source root for display purposes.

    Args:
        file_path: Full path to file
        source_root: Root directory of source

    Returns:
        Relative path string
    """
    try:
        return str(file_path.relative_to(source_root))
    except ValueError:
        # file_path is not relative to source_root, return absolute
        return str(file_path)
