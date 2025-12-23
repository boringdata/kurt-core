"""
Local folder discovery functionality.

Discovers markdown files from local folders.
"""

import logging
import shutil
from fnmatch import fnmatch
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlmodel import select

from kurt.config import load_config
from kurt.db.database import get_session
from kurt.db.models import Document, SourceType
from kurt.utils.file_utils import compute_file_hash
from kurt.utils.source_detection import discover_markdown_files, validate_file_extension

logger = logging.getLogger(__name__)


def discover_folder_files(
    folder_path: str,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
) -> list[dict]:
    """
    Discover markdown files from a local folder and create documents.

    Args:
        folder_path: Path to folder to scan
        include_patterns: Include file patterns (glob)
        exclude_patterns: Exclude file patterns (glob)

    Returns:
        List of dicts with keys: doc_id, path, title, created, error
    """
    folder = Path(folder_path)
    md_files = discover_markdown_files(folder, recursive=True)

    # Apply filters
    if include_patterns:
        md_files = [
            f
            for f in md_files
            if any(fnmatch(str(f.relative_to(folder)), p) for p in include_patterns)
        ]

    if exclude_patterns:
        md_files = [
            f
            for f in md_files
            if not any(fnmatch(str(f.relative_to(folder)), p) for p in exclude_patterns)
        ]

    # Process files
    results = []
    for file_path in md_files:
        try:
            result = _add_file_to_db(file_path)
            results.append(
                {
                    "doc_id": result["doc_id"],
                    "path": str(file_path),
                    "title": result.get("title"),
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

    return results


def _add_file_to_db(file_path: Path) -> dict:
    """
    Add a single markdown file to the database.

    Args:
        file_path: Path to .md file

    Returns:
        Dict with keys: doc_id, created, title
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
            "title": existing_doc.title,
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
        # Status now derived from staging tables, not stored on Document
        content_hash=content_hash,
    )

    session.add(doc)
    session.commit()
    session.refresh(doc)

    # Mark as fetched in landing_fetch (file content already available)
    _mark_file_as_fetched(session, str(doc.id), len(content), content_hash)

    return {
        "doc_id": str(doc.id),
        "created": True,
        "title": title,
    }


def _mark_file_as_fetched(
    session,
    doc_id: str,
    content_length: int,
    content_hash: str,
) -> None:
    """Mark a file-based document as fetched in landing_fetch table.

    Since file-based documents already have their content available,
    we mark them as FETCHED immediately during discovery.

    Args:
        session: Database session
        doc_id: Document UUID as string
        content_length: Length of content in chars
        content_hash: Hash of content for deduplication
    """
    try:
        session.execute(
            text("""
                INSERT OR REPLACE INTO landing_fetch
                (document_id, workflow_id, created_at, updated_at, model_name,
                 status, content_length, content_hash, fetch_engine)
                VALUES (:doc_id, 'file-discovery', datetime('now'), datetime('now'),
                        'discovery.folder', 'FETCHED', :content_length, :content_hash, 'file')
            """),
            {
                "doc_id": doc_id,
                "content_length": content_length,
                "content_hash": content_hash,
            },
        )
        session.commit()
    except Exception as e:
        # Table may not exist in some cases (tests without migrations)
        logger.debug(f"Could not insert landing_fetch record: {e}")
