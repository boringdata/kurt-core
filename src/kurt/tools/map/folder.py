from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from .utils import filter_items

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file content for deduplication."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def discover_from_folder(
    folder_path: str,
    *,
    include_patterns: tuple[str, ...] = (),
    exclude_patterns: tuple[str, ...] = (),
) -> dict:
    """
    Discover markdown files from a local folder.
    """
    folder = Path(folder_path)
    files = discover_markdown_files(folder, recursive=True)

    files = filter_items(
        files,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        to_string=lambda f: str(f.relative_to(folder)),
    )

    results = []
    for file_path in files:
        try:
            title = _extract_title(file_path)
            content_hash = compute_file_hash(file_path)
            results.append(
                {
                    "path": str(file_path),
                    "title": title,
                    "content_hash": content_hash,
                    "created": True,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "path": str(file_path),
                    "error": str(exc),
                    "created": False,
                }
            )

    return {
        "discovered": results,
        "total": len(results),
        "method": "folder",
    }


def discover_markdown_files(directory: Path, recursive: bool = True) -> list[Path]:
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    if recursive:
        md_files = list(directory.rglob("*.md"))
        mdx_files = list(directory.rglob("*.mdx"))
        all_files = md_files + mdx_files
    else:
        md_files = list(directory.glob("*.md"))
        mdx_files = list(directory.glob("*.mdx"))
        all_files = md_files + mdx_files

    all_files = [f for f in all_files if not any(part.startswith(".") for part in f.parts)]
    return sorted(all_files)


def _extract_title(file_path: Path) -> str:
    with file_path.open("r", encoding="utf-8") as handle:
        content = handle.read()

    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()

    return file_path.stem.replace("-", " ").replace("_", " ").title()
