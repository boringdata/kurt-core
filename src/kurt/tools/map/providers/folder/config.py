"""Configuration for folder map provider."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FolderProviderConfig(BaseModel):
    """Configuration for local folder discovery provider.

    Discovers content files from local filesystem directories.
    """

    recursive: bool = Field(
        default=True,
        description="Recurse into subdirectories",
    )
    file_extensions: list[str] = Field(
        default=[".md", ".mdx"],
        description="File extensions to include",
    )
    include_pattern: Optional[str] = Field(
        default=None,
        description="Glob pattern to include files",
    )
    exclude_pattern: Optional[str] = Field(
        default=None,
        description="Glob pattern to exclude files",
    )
    max_urls: int = Field(
        default=1000,
        ge=1,
        description="Maximum files to collect",
    )
