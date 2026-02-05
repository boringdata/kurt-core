"""Folder-based content mapping engine."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

from kurt.tools.map.core import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.models import DocType

logger = logging.getLogger(__name__)


class FolderMapperConfig(MapperConfig):
    """Configuration for folder mapper.

    Attributes:
        recursive: Whether to search recursively (default: True)
        file_extensions: File extensions to include (default: [".md", ".mdx"])
    """

    recursive: bool = True
    file_extensions: list[str] = [".md", ".mdx"]


class FolderEngine(BaseMapper):
    """Maps content by discovering files from local folders.

    Discovers markdown files from a directory with filtering support.
    """

    def __init__(self, config: Optional[FolderMapperConfig] = None):
        """Initialize folder mapper.

        Args:
            config: Folder mapper configuration
        """
        super().__init__(config or FolderMapperConfig())
        self._config: FolderMapperConfig = self.config  # type: ignore

    def map(
        self,
        source: str,
        doc_type: DocType = DocType.DOC,
    ) -> MapperResult:
        """Map files from a local folder.

        Args:
            source: Path to folder to discover from
            doc_type: Type of documents to map

        Returns:
            MapperResult with discovered file paths
        """
        try:
            result = discover_from_folder_impl(
                folder_path=source,
                include_patterns=(self._config.include_pattern,) if self._config.include_pattern else (),
                exclude_patterns=(self._config.exclude_pattern,) if self._config.exclude_pattern else (),
                recursive=self._config.recursive,
                file_extensions=self._config.file_extensions,
            )

            # Extract paths from discovered items
            urls = [item["path"] for item in result.get("discovered", []) if item.get("created")]

            return MapperResult(
                urls=urls,
                count=len(urls),
                metadata={
                    "engine": "folder",
                    "source": source,
                    "method": "folder",
                },
            )

        except Exception as e:
            logger.error("Folder mapping failed: %s", e)
            return MapperResult(
                urls=[],
                count=0,
                errors=[str(e)],
                metadata={"engine": "folder", "source": source},
            )


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file content for deduplication.

    Args:
        file_path: Path to file

    Returns:
        Hex digest of SHA256 hash
    """
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def discover_markdown_files(
    directory: Path,
    recursive: bool = True,
    file_extensions: list[str] | None = None,
) -> list[Path]:
    """Discover markdown files in a directory.

    Args:
        directory: Directory to search
        recursive: Whether to search recursively
        file_extensions: File extensions to include (default: [".md", ".mdx"])

    Returns:
        List of discovered file paths

    Raises:
        ValueError: If directory does not exist
    """
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    extensions = file_extensions or [".md", ".mdx"]
    all_files: list[Path] = []

    for ext in extensions:
        pattern = f"*{ext}"
        if recursive:
            all_files.extend(directory.rglob(pattern))
        else:
            all_files.extend(directory.glob(pattern))

    # Filter out hidden directories
    all_files = [f for f in all_files if not any(part.startswith(".") for part in f.parts)]

    return sorted(all_files)


def _extract_title(file_path: Path) -> str:
    """Extract title from markdown file.

    Looks for first H1 heading, falls back to filename.

    Args:
        file_path: Path to markdown file

    Returns:
        Extracted or generated title
    """
    with file_path.open("r", encoding="utf-8") as handle:
        content = handle.read()

    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()

    return file_path.stem.replace("-", " ").replace("_", " ").title()


def discover_from_folder_impl(
    folder_path: str,
    *,
    include_patterns: tuple[str, ...] = (),
    exclude_patterns: tuple[str, ...] = (),
    recursive: bool = True,
    file_extensions: list[str] | None = None,
) -> dict:
    """
    Discover markdown files from a local folder.

    This is the core implementation used by both FolderEngine and the
    backward-compatible discover_from_folder() function.

    Args:
        folder_path: Path to folder to discover from
        include_patterns: Glob patterns to include
        exclude_patterns: Glob patterns to exclude
        recursive: Whether to search recursively
        file_extensions: File extensions to include

    Returns:
        Dict with discovered files and metadata
    """
    from kurt.tools.map.utils import filter_items

    folder = Path(folder_path)
    files = discover_markdown_files(folder, recursive=recursive, file_extensions=file_extensions)

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


# Backward compatibility alias
FolderMapper = FolderEngine
