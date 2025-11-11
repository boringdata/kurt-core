"""
Tests for metadata sync queue and trigger functionality.

Tests various update scenarios:
1. Updates via kurt CLI (Python ORM)
2. Updates via direct SQL
3. Queue population and processing
4. Queue cleanup after direct sync
"""

import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from sqlmodel import Session, SQLModel, create_engine

from kurt.db.metadata_sync import process_metadata_sync_queue, write_frontmatter_to_file
from kurt.db.models import (
    ContentType,
    Document,
    IngestionStatus,
    MetadataSyncQueue,
    SourceType,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db_with_queue(temp_project_dir, monkeypatch):
    """Create a test database with metadata_sync_queue table and trigger."""
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

    # Create database
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, echo=False)
    SQLModel.metadata.create_all(engine)

    # Setup trigger (using pure SQL - must match migration trigger)
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

    session = Session(engine)

    try:
        yield session, sources_dir, db_path
    finally:
        session.close()
        # Restore original working directory
        import os

        os.chdir(original_cwd)


def test_queue_populated_via_orm_update(test_db_with_queue):
    """Test that queue is populated when updating via Python ORM."""
    session, sources_dir, db_path = test_db_with_queue

    # Create a document
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test",
        ingestion_status=IngestionStatus.FETCHED,
        content_path="example.com/test.md",
    )
    session.add(doc)
    session.commit()

    # Queue should be empty
    queue_items = session.query(MetadataSyncQueue).all()
    assert len(queue_items) == 0

    # Update metadata via ORM
    doc.content_type = ContentType.TUTORIAL
    doc.primary_topics = ["Python", "Testing"]
    session.add(doc)
    session.commit()

    # Queue should now have 1 entry
    queue_items = session.query(MetadataSyncQueue).all()
    assert len(queue_items) == 1
    assert queue_items[0].document_id == doc_id


def test_queue_populated_via_sql_update(test_db_with_queue):
    """Test that queue is populated when updating via direct SQL."""
    session, sources_dir, db_path = test_db_with_queue

    # Create a document with initial metadata
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test",
        ingestion_status=IngestionStatus.FETCHED,
        content_path="example.com/test.md",
        content_type=ContentType.TUTORIAL,  # Start with a value
        primary_topics=["Python"],  # Start with a value
    )
    session.add(doc)
    session.commit()

    # Queue should be empty
    queue_items = session.query(MetadataSyncQueue).all()
    assert len(queue_items) == 0

    # Update directly via SQL (simulating agent or script update)
    # Note: SQLite stores UUIDs without hyphens
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE documents
        SET content_type = 'GUIDE', primary_topics = '["AI", "ML"]'
        WHERE id = ?
    """,
        (str(doc_id).replace("-", ""),),
    )
    conn.commit()
    conn.close()

    # Refresh session to see changes
    session.expire_all()

    # Queue should now have 1 entry (trigger fired)
    queue_items = session.query(MetadataSyncQueue).all()
    assert len(queue_items) == 1
    assert queue_items[0].document_id == doc_id


def test_direct_sync_cleans_queue(test_db_with_queue):
    """Test that write_frontmatter_to_file() cleans up queue entries."""
    from kurt.config import load_config

    session, sources_dir, db_path = test_db_with_queue

    # Create a document with content file in real sources directory
    doc_id = uuid4()
    content_path = "example.com/test-sync.md"

    # Use real sources directory
    config = load_config()
    real_sources_dir = config.get_absolute_sources_path()
    full_content_path = real_sources_dir / content_path
    full_content_path.parent.mkdir(parents=True, exist_ok=True)
    full_content_path.write_text("# Test Content", encoding="utf-8")

    try:
        doc = Document(
            id=doc_id,
            title="Test Doc",
            source_type=SourceType.URL,
            source_url="https://example.com/test-sync",
            ingestion_status=IngestionStatus.FETCHED,
            content_path=content_path,
            content_type=ContentType.TUTORIAL,
            primary_topics=["Python"],
        )
        session.add(doc)
        session.commit()

        # Manually add to queue (simulating trigger)
        queue_item = MetadataSyncQueue(document_id=doc_id)
        session.add(queue_item)
        session.commit()

        # Verify queue has entry
        queue_items = session.query(MetadataSyncQueue).all()
        assert len(queue_items) == 1

        # Call direct sync (pass session to use test database)
        write_frontmatter_to_file(doc, session=session)

        # Queue should now be empty
        session.expire_all()
        queue_items = session.query(MetadataSyncQueue).all()
        assert len(queue_items) == 0
    finally:
        # Clean up test file
        if full_content_path.exists():
            full_content_path.unlink()


def test_process_queue_syncs_and_clears(test_db_with_queue):
    """Test that process_metadata_sync_queue() syncs files and clears queue."""
    from kurt.config import load_config

    session, sources_dir, db_path = test_db_with_queue

    # Use real sources directory
    config = load_config()
    real_sources_dir = config.get_absolute_sources_path()

    # Create two documents with content files
    docs = []
    test_files = []
    for i in range(2):
        doc_id = uuid4()
        content_path = f"example.com/test-process{i}.md"
        full_content_path = real_sources_dir / content_path
        full_content_path.parent.mkdir(parents=True, exist_ok=True)
        full_content_path.write_text(f"# Test Content {i}", encoding="utf-8")
        test_files.append(full_content_path)

        doc = Document(
            id=doc_id,
            title=f"Test Doc {i}",
            source_type=SourceType.URL,
            source_url=f"https://example.com/test-process{i}",
            ingestion_status=IngestionStatus.FETCHED,
            content_path=content_path,
            content_type=ContentType.TUTORIAL,
            primary_topics=["Python"],
        )
        session.add(doc)
        docs.append(doc)
    session.commit()

    try:
        # Add both to queue
        for doc in docs:
            queue_item = MetadataSyncQueue(document_id=doc.id)
            session.add(queue_item)
        session.commit()

        # Verify queue has 2 entries
        queue_items = session.query(MetadataSyncQueue).all()
        assert len(queue_items) == 2

        # Process queue (pass session to use test database)
        result = process_metadata_sync_queue(session=session)

        assert result["processed"] == 2
        assert len(result["errors"]) == 0

        # Verify frontmatter was written
        for i, doc in enumerate(docs):
            full_content_path = real_sources_dir / doc.content_path
            content = full_content_path.read_text(encoding="utf-8")
            assert content.startswith("---\n")
            assert "content_type: tutorial" in content

        # Verify queue is empty
        session.expire_all()
        queue_items = session.query(MetadataSyncQueue).all()
        assert len(queue_items) == 0
    finally:
        # Clean up test files
        for test_file in test_files:
            if test_file.exists():
                test_file.unlink()


def test_trigger_only_fires_on_metadata_changes(test_db_with_queue):
    """Test that trigger only fires when metadata fields change."""
    session, sources_dir, db_path = test_db_with_queue

    # Create a document
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test",
        ingestion_status=IngestionStatus.FETCHED,
        content_path="example.com/test.md",
    )
    session.add(doc)
    session.commit()

    # Update non-metadata field (should NOT trigger)
    doc.updated_at = doc.updated_at  # Touch updated_at
    session.add(doc)
    session.commit()

    queue_items = session.query(MetadataSyncQueue).all()
    assert len(queue_items) == 0

    # Update metadata field (should trigger)
    doc.title = "Updated Title"
    session.add(doc)
    session.commit()

    queue_items = session.query(MetadataSyncQueue).all()
    assert len(queue_items) == 1


def test_sql_update_then_process_queue_syncs_file(test_db_with_queue):
    """Test that SQL update to doc1, then processing queue, syncs doc1's frontmatter."""
    from kurt.config import load_config

    session, sources_dir, db_path = test_db_with_queue

    # Use real sources directory
    config = load_config()
    real_sources_dir = config.get_absolute_sources_path()

    # Create doc1 with content file
    doc1_id = uuid4()
    doc1_content_path = "example.com/doc1-sql-queue.md"
    doc1_full_path = real_sources_dir / doc1_content_path
    doc1_full_path.parent.mkdir(parents=True, exist_ok=True)
    doc1_full_path.write_text("# Doc 1\n\nOriginal content.", encoding="utf-8")

    # Create doc2 with content file
    doc2_id = uuid4()
    doc2_content_path = "example.com/doc2-sql-queue.md"
    doc2_full_path = real_sources_dir / doc2_content_path
    doc2_full_path.parent.mkdir(parents=True, exist_ok=True)
    doc2_full_path.write_text("# Doc 2\n\nOriginal content.", encoding="utf-8")

    try:
        # Create both documents with initial metadata
        doc1 = Document(
            id=doc1_id,
            title="Doc 1",
            source_type=SourceType.URL,
            source_url="https://example.com/doc1-sql-queue",
            ingestion_status=IngestionStatus.FETCHED,
            content_path=doc1_content_path,
            content_type=ContentType.TUTORIAL,
            primary_topics=["Original Topic"],
        )
        doc2 = Document(
            id=doc2_id,
            title="Doc 2",
            source_type=SourceType.URL,
            source_url="https://example.com/doc2-sql-queue",
            ingestion_status=IngestionStatus.FETCHED,
            content_path=doc2_content_path,
            content_type=ContentType.GUIDE,
            primary_topics=["Python"],
        )
        session.add(doc1)
        session.add(doc2)
        session.commit()

        # Queue should be empty
        queue_items = session.query(MetadataSyncQueue).all()
        assert len(queue_items) == 0

        # Step 1: Update doc1 metadata via SQL (simulating agent/SQL update)
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE documents
            SET content_type = 'GUIDE', primary_topics = '["SQL Update", "Agent"]'
            WHERE id = ?
        """,
            (str(doc1_id).replace("-", ""),),
        )
        conn.commit()
        conn.close()

        # Refresh session to see changes
        session.expire_all()

        # Queue should now have 1 entry (trigger fired for doc1)
        queue_items = session.query(MetadataSyncQueue).all()
        assert len(queue_items) == 1
        assert queue_items[0].document_id == doc1_id

        # Doc1's file should NOT have frontmatter yet (queue not processed)
        doc1_content_before = doc1_full_path.read_text(encoding="utf-8")
        assert not doc1_content_before.startswith("---")

        # Step 2: Process queue (simulating what happens during "kurt index")
        result = process_metadata_sync_queue(session=session)

        # Should have processed 1 document
        assert result["processed"] == 1
        assert len(result["errors"]) == 0

        # Step 3: Check that doc1's frontmatter is now updated
        doc1_content_after = doc1_full_path.read_text(encoding="utf-8")
        assert doc1_content_after.startswith("---\n")
        assert "content_type: guide" in doc1_content_after
        assert "- SQL Update" in doc1_content_after
        assert "- Agent" in doc1_content_after

        # Queue should be empty (cleaned up)
        session.expire_all()
        queue_items = session.query(MetadataSyncQueue).all()
        assert len(queue_items) == 0

    finally:
        # Clean up test files
        if doc1_full_path.exists():
            doc1_full_path.unlink()
        if doc2_full_path.exists():
            doc2_full_path.unlink()


def test_multiple_updates_create_multiple_queue_entries(test_db_with_queue):
    """Test that multiple updates create multiple queue entries."""
    from kurt.config import load_config

    session, sources_dir, db_path = test_db_with_queue

    # Use real sources directory
    config = load_config()
    real_sources_dir = config.get_absolute_sources_path()

    # Create a document
    doc_id = uuid4()
    content_path = "example.com/test-multiple.md"
    doc = Document(
        id=doc_id,
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test-multiple",
        ingestion_status=IngestionStatus.FETCHED,
        content_path=content_path,
    )
    session.add(doc)
    session.commit()

    # Multiple updates
    for i in range(3):
        doc.title = f"Title {i}"
        session.add(doc)
        session.commit()

    # Should have 3 queue entries (one per update)
    queue_items = session.query(MetadataSyncQueue).all()
    assert len(queue_items) == 3
    assert all(item.document_id == doc_id for item in queue_items)

    # But process_metadata_sync_queue should deduplicate
    # (process unique document IDs only once)
    full_content_path = real_sources_dir / content_path
    full_content_path.parent.mkdir(parents=True, exist_ok=True)
    full_content_path.write_text("# Test", encoding="utf-8")

    try:
        doc.content_type = ContentType.TUTORIAL
        doc.primary_topics = ["Test"]
        session.add(doc)
        session.commit()

        result = process_metadata_sync_queue(session=session)
        # All 4 queue entries (3 + 1 from content_type update), but only 1 document processed
        assert result["processed"] == 1
    finally:
        # Clean up test file
        if full_content_path.exists():
            full_content_path.unlink()
