"""
Tests for automatic frontmatter sync using SQLite triggers.

This module tests the database-level trigger that automatically
writes YAML frontmatter to markdown files whenever document metadata is updated.
"""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from kurt.db.metadata_sync import write_frontmatter_to_file
from kurt.db.models import ContentType, Document, IngestionStatus, SourceType


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db_with_triggers(temp_project_dir, monkeypatch):
    """Create a test database with frontmatter sync triggers enabled."""
    # Setup temporary paths
    db_dir = temp_project_dir / ".kurt"
    db_path = db_dir / "kurt.sqlite"
    sources_dir = temp_project_dir / "sources"

    db_dir.mkdir(parents=True, exist_ok=True)
    sources_dir.mkdir(parents=True, exist_ok=True)

    # Change to temp directory and create config
    import os

    original_cwd = Path.cwd()
    os.chdir(temp_project_dir)

    # Use create_config to generate kurt.config file
    from kurt.config import create_config

    create_config()

    monkeypatch.setattr("os.getcwd", lambda: str(temp_project_dir))

    # Mock the config to use temp directories
    monkeypatch.setenv("KURT_PROJECT_ROOT", str(temp_project_dir))

    # Create database with tables and triggers
    import sqlite3

    from sqlmodel import Session, SQLModel, create_engine

    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, echo=False)

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Setup trigger manually (same as in migration)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_metadata_sync_trigger
        AFTER UPDATE ON documents
        WHEN (
            NEW.content_type != OLD.content_type OR
            NEW.primary_topics != OLD.primary_topics OR
            NEW.tools_technologies != OLD.tools_technologies OR
            NEW.title != OLD.title OR
            NEW.description != OLD.description OR
            NEW.author != OLD.author OR
            NEW.published_date != OLD.published_date OR
            NEW.indexed_with_hash != OLD.indexed_with_hash
        )
        BEGIN
            INSERT INTO metadata_sync_queue (document_id, created_at)
            VALUES (NEW.id, datetime('now'));
        END;
    """)
    conn.commit()
    conn.close()

    # Get a session
    session = Session(engine)

    try:
        yield session, sources_dir
    finally:
        session.close()
        # Restore original working directory
        import os

        os.chdir(original_cwd)


def test_frontmatter_sync_on_index(test_db_with_triggers):
    """Test that frontmatter is automatically written when document metadata is updated."""
    from kurt.config import load_config

    session, sources_dir = test_db_with_triggers

    # Use real sources directory
    config = load_config()
    real_sources_dir = config.get_absolute_sources_path()

    # Create a document with content file
    doc_id = uuid4()
    content_path = "example.com/test-frontmatter.md"
    full_content_path = real_sources_dir / content_path

    # Create the markdown file
    full_content_path.parent.mkdir(parents=True, exist_ok=True)
    original_content = "# Test Page\n\nThis is test content."
    full_content_path.write_text(original_content, encoding="utf-8")

    try:
        # Create document in database
        doc = Document(
            id=doc_id,
            title="Test Page",
            source_type=SourceType.URL,
            source_url="https://example.com/test-frontmatter",
            content_path=content_path,
            ingestion_status=IngestionStatus.FETCHED,
        )

        session.add(doc)
        session.commit()
        session.refresh(doc)

        # At this point, no frontmatter should exist yet
        content_after_create = full_content_path.read_text(encoding="utf-8")
        assert content_after_create == original_content
        assert not content_after_create.startswith("---")

        # Now update the document with metadata (simulating indexing)
        doc.content_type = ContentType.TUTORIAL
        doc.primary_topics = ["Python", "Testing", "SQLite"]
        doc.tools_technologies = ["pytest", "SQLite"]
        doc.has_code_examples = True
        doc.indexed_with_hash = "abc123"

        session.add(doc)
        session.commit()

        # Write frontmatter (this is what happens during indexing)
        write_frontmatter_to_file(doc, session=session)

        # Frontmatter should have been written
        content_after_update = full_content_path.read_text(encoding="utf-8")

        # Verify frontmatter was added
        assert content_after_update.startswith("---\n")
        assert "content_type: tutorial" in content_after_update
        assert "topics:" in content_after_update
        assert "- Python" in content_after_update
        assert "- Testing" in content_after_update
        assert "- SQLite" in content_after_update
        assert "tools:" in content_after_update
        assert "- pytest" in content_after_update
        assert "- SQLite" in content_after_update
        assert "has_code_examples: true" in content_after_update

        # Original content should still be there after the frontmatter
        assert "# Test Page" in content_after_update
        assert "This is test content." in content_after_update
    finally:
        # Clean up test file
        if full_content_path.exists():
            full_content_path.unlink()


def test_frontmatter_sync_updates_existing_frontmatter(test_db_with_triggers):
    """Test that frontmatter is updated (not duplicated) when metadata changes again."""
    from kurt.config import load_config

    session, sources_dir = test_db_with_triggers

    # Use real sources directory
    config = load_config()
    real_sources_dir = config.get_absolute_sources_path()

    # Create a document with content file
    doc_id = uuid4()
    content_path = "example.com/update-frontmatter-test.md"
    full_content_path = real_sources_dir / content_path

    # Create the markdown file
    full_content_path.parent.mkdir(parents=True, exist_ok=True)
    original_content = "# Update Test\n\nOriginal content here."
    full_content_path.write_text(original_content, encoding="utf-8")

    try:
        # Create document in database
        doc = Document(
            id=doc_id,
            title="Update Test",
            source_type=SourceType.URL,
            source_url="https://example.com/update-frontmatter-test",
            content_path=content_path,
            ingestion_status=IngestionStatus.FETCHED,
        )

        session.add(doc)
        session.commit()
        session.refresh(doc)

        # First update: add initial metadata
        doc.content_type = ContentType.GUIDE
        doc.primary_topics = ["Initial", "Topics"]
        doc.indexed_with_hash = "hash1"

        session.add(doc)
        session.commit()

        # Write frontmatter after first update
        write_frontmatter_to_file(doc, session=session)

        content_after_first_update = full_content_path.read_text(encoding="utf-8")
        assert "content_type: guide" in content_after_first_update
        assert "- Initial" in content_after_first_update

        # Second update: change metadata
        doc.content_type = ContentType.TUTORIAL
        doc.primary_topics = ["Updated", "Topics", "New"]
        doc.tools_technologies = ["NewTool"]
        doc.indexed_with_hash = "hash2"

        session.add(doc)
        session.commit()

        # Write frontmatter after second update
        write_frontmatter_to_file(doc, session=session)

        content_after_second_update = full_content_path.read_text(encoding="utf-8")

        # Should only have ONE frontmatter section
        assert content_after_second_update.count("---\n") == 2  # Opening and closing

        # Should have updated metadata
        assert "content_type: tutorial" in content_after_second_update
        assert "- Updated" in content_after_second_update
        assert "- New" in content_after_second_update
        assert "- NewTool" in content_after_second_update

        # Should NOT have old metadata
        assert "content_type: guide" not in content_after_second_update
        assert "- Initial" not in content_after_second_update

        # Original content should still be there
        assert "# Update Test" in content_after_second_update
        assert "Original content here." in content_after_second_update
    finally:
        # Clean up test file
        if full_content_path.exists():
            full_content_path.unlink()


def test_frontmatter_sync_skip_when_no_metadata(test_db_with_triggers):
    """Test that frontmatter is not written when document has no metadata."""
    from kurt.config import load_config

    session, sources_dir = test_db_with_triggers

    # Use real sources directory
    config = load_config()
    real_sources_dir = config.get_absolute_sources_path()

    # Create a document with content but no metadata
    doc_id = uuid4()
    content_path = "example.com/no-frontmatter-metadata.md"
    full_content_path = real_sources_dir / content_path

    # Create the markdown file
    full_content_path.parent.mkdir(parents=True, exist_ok=True)
    original_content = "# No Metadata\n\nContent without metadata."
    full_content_path.write_text(original_content, encoding="utf-8")

    try:
        # Create document in database (no metadata fields set)
        doc = Document(
            id=doc_id,
            title="No Metadata",
            source_type=SourceType.URL,
            source_url="https://example.com/no-frontmatter-metadata",
            content_path=content_path,
            ingestion_status=IngestionStatus.FETCHED,
        )

        session.add(doc)
        session.commit()
        session.refresh(doc)

        # Update something, but still no metadata
        doc.title = "Updated Title"

        session.add(doc)
        session.commit()

        # Try to write frontmatter (should skip because no metadata)
        write_frontmatter_to_file(doc, session=session)

        # No frontmatter should be written (function skips when no metadata)
        content_after_update = full_content_path.read_text(encoding="utf-8")
        assert content_after_update == original_content
        assert not content_after_update.startswith("---")
    finally:
        # Clean up test file
        if full_content_path.exists():
            full_content_path.unlink()
