"""
Local folder discovery functionality for Kurt.

This module handles discovering markdown files from local folders.
"""

import logging
import shutil
from fnmatch import fnmatch
from pathlib import Path
from uuid import uuid4

from sqlmodel import select

from kurt.config import load_config
from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType
from kurt.utils.file_utils import compute_file_hash
from kurt.utils.source_detection import discover_markdown_files, validate_file_extension

logger = logging.getLogger(__name__)


def _add_single_file_to_db(file_path: Path) -> dict:
    """
    Internal function: Add a single markdown file to the database.

    Args:
        file_path: Path to .md file

    Returns:
        Dict with keys: doc_id, created, skipped, reason (if skipped)
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
        return {
            "doc_id": str(existing_doc.id),
            "created": False,
            "skipped": True,
            "reason": "Content already exists",
        }

    # Copy file to sources directory
    config = load_config()
    sources_dir = config.get_absolute_sources_path()
    target_path = sources_dir / file_path.name
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, target_path)
    relative_content_path = str(target_path.relative_to(sources_dir))

    # Read file content for title extraction
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract title from first heading or filename
    title = None
    for line in content.split("\n"):
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = file_path.stem.replace("-", " ").replace("_", " ").title()

    # Create document record
    doc = Document(
        id=uuid4(),
        title=title,
        source_type=SourceType.FILE_UPLOAD,
        source_url=f"file://{file_path.absolute()}",
        content_path=relative_content_path,
        ingestion_status=IngestionStatus.FETCHED,
        content_hash=content_hash,
    )

    session.add(doc)
    session.commit()
    session.refresh(doc)

    return {
        "doc_id": str(doc.id),
        "created": True,
        "skipped": False,
    }


def map_folder_content(
    folder_path: str,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
    dry_run: bool = False,
    cluster_urls: bool = False,
    progress=None,
) -> dict:
    """
    High-level folder mapping function - discover content from local files.

    Args:
        folder_path: Path to folder to scan
        include_patterns: Include file patterns (glob)
        exclude_patterns: Exclude file patterns (glob)
        dry_run: If True, discover files but don't save to database
        cluster_urls: If True, automatically cluster documents after mapping

    Returns:
        dict with:
            - discovered: List of file paths (strings if dry_run, dicts otherwise)
            - total: Total count
            - new: Count of new files (0 if dry_run)
            - existing: Count of existing files (0 if dry_run)
            - dry_run: Boolean indicating if this was a dry run
            - clusters: List of clusters (if cluster_urls=True)
            - cluster_count: Number of clusters (if cluster_urls=True)
    """
    folder = Path(folder_path)
    md_files = discover_markdown_files(folder, recursive=True)

    # Apply filters
    if include_patterns:
        filtered = []
        for file_path in md_files:
            rel_path = str(file_path.relative_to(folder))
            if any(fnmatch(rel_path, pattern) for pattern in include_patterns):
                filtered.append(file_path)
        md_files = filtered

    if exclude_patterns:
        filtered = []
        for file_path in md_files:
            rel_path = str(file_path.relative_to(folder))
            if not any(fnmatch(rel_path, pattern) for pattern in exclude_patterns):
                filtered.append(file_path)
        md_files = filtered

    # Handle dry-run mode
    if dry_run:
        # Update progress
        task_id = None
        if progress:
            task_id = progress.add_task(
                "Scanning files...", total=len(md_files), completed=len(md_files)
            )

        # Return file paths as strings without saving to database
        return {
            "discovered": [str(file_path) for file_path in md_files],
            "total": len(md_files),
            "new": 0,
            "existing": 0,
            "dry_run": True,
        }

    # Add files to database (normal mode)
    task_id = None
    if progress:
        task_id = progress.add_task("Adding files to database...", total=len(md_files), completed=0)

    results = []
    for idx, file_path in enumerate(md_files):
        try:
            result = _add_single_file_to_db(file_path)
            results.append(
                {
                    "path": str(file_path),
                    "doc_id": result["doc_id"],
                    "created": result["created"],
                }
            )
        except Exception as e:
            results.append(
                {
                    "path": str(file_path),
                    "error": str(e),
                    "created": False,
                }
            )

        # Update progress
        if progress and task_id is not None:
            progress.update(task_id, completed=idx + 1)

    new_count = sum(1 for r in results if r.get("created", False))
    existing_count = len(results) - new_count

    result_dict = {
        "discovered": results,
        "total": len(results),
        "new": new_count,
        "existing": existing_count,
        "dry_run": False,
    }

    # Auto-cluster if requested
    if cluster_urls and len(results) > 0:
        from kurt.content.cluster import compute_topic_clusters

        if progress and task_id is not None:
            progress.update(
                task_id,
                description=f"Clustering {len(results)} documents...",
                completed=0,
                total=None,
            )

            def progress_callback(message):
                progress.update(task_id, description=message)

            cluster_result = compute_topic_clusters(progress_callback=progress_callback)
        else:
            cluster_result = compute_topic_clusters()

        result_dict["clusters"] = cluster_result["clusters"]
        result_dict["cluster_count"] = len(cluster_result["clusters"])

        if progress and task_id is not None:
            progress.update(task_id, description="Clustering complete", completed=1, total=1)

    return result_dict
