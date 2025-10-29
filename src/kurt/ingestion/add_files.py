"""File-based content ingestion for Kurt."""

import asyncio
import hashlib
import shutil
from pathlib import Path
from uuid import uuid4

from sqlmodel import select

from kurt.config import load_config
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus
from kurt.db.models import SourceType as DbSourceType
from kurt.ingestion.index import batch_extract_document_metadata, extract_document_metadata
from kurt.ingestion.source_detection import (
    discover_markdown_files,
    get_relative_path_from_source,
    validate_file_extension,
)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file content."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def copy_file_to_sources(file_path: Path, relative_path: str = None) -> str:
    """
    Copy file to SOURCES_PATH directory.

    Args:
        file_path: Original file path
        relative_path: Optional relative path to preserve directory structure

    Returns:
        Relative path from SOURCES_PATH to copied file
    """
    config = load_config()
    sources_dir = config.get_absolute_sources_path()

    # Create target path
    if relative_path:
        # Preserve directory structure
        target_path = sources_dir / relative_path
    else:
        # Just use filename
        target_path = sources_dir / file_path.name

    # Ensure target directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(file_path, target_path)

    # Return relative path from sources_dir
    return str(target_path.relative_to(sources_dir))


def add_single_file(
    file_path: Path,
    *,
    index: bool = True,
) -> dict:
    """
    Add a single markdown file to Kurt.

    Args:
        file_path: Path to .md file
        index: Whether to index content with LLM

    Returns:
        Dict with keys: doc_id, created, indexed, file_path, content_length
    """
    # Validate file
    is_valid, error_msg = validate_file_extension(file_path)
    if not is_valid:
        raise ValueError(error_msg)

    # Compute content hash
    content_hash = compute_file_hash(file_path)

    # Check if document already exists (by content hash)
    session = get_session()
    stmt = select(Document).where(Document.content_hash == content_hash)
    existing_doc = session.exec(stmt).first()

    if existing_doc:
        # Document with same content already exists
        return {
            "doc_id": str(existing_doc.id),
            "created": False,
            "indexed": False,
            "skipped": True,
            "reason": "Content already exists",
            "file_path": str(file_path),
        }

    # Copy file to sources directory
    relative_content_path = copy_file_to_sources(file_path)

    # Read file content for metadata
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract title from first heading or filename
    lines = content.split("\n")
    title = None
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    if not title:
        title = file_path.stem.replace("-", " ").replace("_", " ").title()

    # Create document record
    doc = Document(
        id=uuid4(),
        title=title,
        source_type=DbSourceType.FILE_UPLOAD,
        source_url=f"file://{file_path.absolute()}",  # Store original path as "URL"
        content_path=relative_content_path,
        ingestion_status=IngestionStatus.FETCHED,  # File is already "fetched"
        content_hash=content_hash,
    )

    session.add(doc)
    session.commit()
    session.refresh(doc)

    doc_id = str(doc.id)
    result = {
        "doc_id": doc_id,
        "created": True,
        "indexed": False,
        "file_path": str(file_path),
        "title": title,
        "content_length": len(content),
    }

    # Index if requested
    if index:
        try:
            index_result = extract_document_metadata(doc_id, force=False)
            result["indexed"] = True
            result["index_result"] = index_result
        except Exception as e:
            result["indexed"] = False
            result["index_error"] = str(e)

    return result


def add_directory(
    directory: Path,
    *,
    recursive: bool = True,
    index: bool = True,
) -> dict:
    """
    Add all markdown files from a directory to Kurt.

    Args:
        directory: Path to directory
        recursive: Process subdirectories recursively
        index: Whether to index content with LLM

    Returns:
        Dict with keys: total, created, skipped, indexed, errors, files
    """
    # Discover markdown files
    md_files = discover_markdown_files(directory, recursive=recursive)

    if not md_files:
        return {
            "total": 0,
            "created": 0,
            "skipped": 0,
            "indexed": 0,
            "errors": 0,
            "files": [],
        }

    result = {
        "total": len(md_files),
        "created": 0,
        "skipped": 0,
        "indexed": 0,
        "errors": 0,
        "files": [],
    }

    # Process each file
    for file_path in md_files:
        try:
            file_result = add_single_file(file_path, index=False)  # Batch index later

            result["files"].append(
                {
                    "path": str(file_path),
                    "relative_path": get_relative_path_from_source(file_path, directory),
                    "doc_id": file_result["doc_id"],
                    "created": file_result["created"],
                    "title": file_result.get("title"),
                }
            )

            if file_result["created"]:
                result["created"] += 1
            elif file_result.get("skipped"):
                result["skipped"] += 1

        except Exception as e:
            result["errors"] += 1
            result["files"].append(
                {
                    "path": str(file_path),
                    "error": str(e),
                }
            )

    # Batch index all created documents
    if index and result["created"] > 0:
        try:
            created_doc_ids = [
                f["doc_id"] for f in result["files"] if f.get("created") and "error" not in f
            ]

            if created_doc_ids:
                batch_result = asyncio.run(
                    batch_extract_document_metadata(created_doc_ids, max_concurrent=5, force=False)
                )
                result["indexed"] = batch_result["succeeded"]
        except Exception as e:
            result["index_error"] = str(e)

    return result


def should_confirm_file_batch(file_count: int, force: bool = False) -> bool:
    """
    Determine if user confirmation is needed for large file batches.

    Args:
        file_count: Number of files to process
        force: If True, skip confirmation

    Returns:
        True if confirmation needed, False otherwise
    """
    if force:
        return False

    batch_threshold = 20
    return file_count > batch_threshold
