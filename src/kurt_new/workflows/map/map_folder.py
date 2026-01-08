from __future__ import annotations

import logging
from fnmatch import fnmatch
from pathlib import Path

logger = logging.getLogger(__name__)


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

    if include_patterns:
        files = [
            f
            for f in files
            if any(fnmatch(str(f.relative_to(folder)), p) for p in include_patterns)
        ]

    if exclude_patterns:
        files = [
            f
            for f in files
            if not any(fnmatch(str(f.relative_to(folder)), p) for p in exclude_patterns)
        ]

    results = []
    for file_path in files:
        try:
            title = _extract_title(file_path)
            results.append(
                {
                    "path": str(file_path),
                    "title": title,
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
