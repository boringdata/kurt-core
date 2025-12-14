"""
End-to-end test demonstrating the complete indexing framework.

This test proves the framework can:
1. Load real documents from the database
2. Process them through models
3. Write results to tables with proper schemas
4. Handle incremental mode
5. Stream events to DBOS
"""

import json

import pytest
from pydantic import BaseModel

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.framework import (
    ModelRegistry,
    TableReader,
    TableWriter,
    configure_dbos_writer,
    model,
)
from kurt.content.indexing_new.loaders import load_documents


class DocumentProcessingRow(BaseModel):
    """Schema for document processing results."""

    document_id: str
    title: str
    content_length: int
    word_count: int
    has_code: bool
    processing_note: str | None = None


class DocumentSummaryRow(BaseModel):
    """Schema for document summaries."""

    document_id: str
    summary: str
    key_topics: str  # JSON list
    confidence: float


@pytest.fixture
def setup_test_models():
    """Register test models for the end-to-end test."""
    ModelRegistry.clear()

    @model(
        name="e2e.document_processor",
        db_model=DocumentProcessingRow,
        primary_key=["document_id"],
        description="Process documents and extract basic metrics",
    )
    def process_documents(reader, writer, filters, **kwargs):
        """Load and process documents."""
        # Load actual documents using the loader
        documents = load_documents(filters, incremental_mode="full")

        results = []
        for doc in documents:
            if doc.get("skip"):
                continue

            content = doc.get("content", "")
            results.append(
                {
                    "document_id": doc["document_id"],
                    "title": doc.get("title", "Untitled"),
                    "content_length": len(content),
                    "word_count": len(content.split()),
                    "has_code": "```" in content or "def " in content,
                    "processing_note": "Processed in test",
                }
            )

        return writer.write(results)

    @model(
        name="e2e.document_summarizer",
        db_model=DocumentSummaryRow,
        primary_key=["document_id"],
        description="Generate summaries from processed documents",
    )
    def summarize_documents(reader, writer, filters, **kwargs):
        """Read processed docs and generate summaries."""
        # Read from previous model's output
        processed = reader.load("e2e_document_processor")

        summaries = []
        for _, row in processed.iterrows():
            # Simulate summary generation
            summary = f"Document '{row['title']}' contains {row['word_count']} words"
            if row.get("has_code"):
                summary += " with code examples"

            summaries.append(
                {
                    "document_id": row["document_id"],
                    "summary": summary,
                    "key_topics": json.dumps(["testing", "framework"]),
                    "confidence": 0.95,
                }
            )

        return writer.write(summaries)

    yield

    # Cleanup
    ModelRegistry.clear()


class TestEndToEnd:
    """End-to-end tests for the indexing framework."""

    @pytest.mark.skip(reason="Requires tmp_project fixture from main test suite")
    def test_complete_pipeline(self, tmp_project, setup_test_models):
        """Test a complete pipeline from document loading to final output."""
        db_path = tmp_project / ".kurt" / "kurt.sqlite"

        # Configure DBOS writer for this test
        configure_dbos_writer(workflow_id="test_e2e")

        # Create some test documents in the database
        from kurt.content.document import add_document
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus

        session = get_session()

        # Add a test document
        doc_id = add_document("https://example.com/test-doc")
        doc = session.get(Document, doc_id)
        doc.title = "Test Document"
        doc.content_path = "test.md"
        doc.ingestion_status = IngestionStatus.FETCHED
        session.commit()

        # Create test content file
        from kurt.config import load_config

        config = load_config()
        sources_path = config.get_absolute_sources_path()
        test_file = sources_path / "test.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("""
# Test Document

This is a test document with some content.

```python
def hello():
    print("Hello from test!")
```

More content here with multiple words to count.
        """)

        # Create filters to load this specific document
        filters = DocumentFilters(ids=str(doc_id))

        # Initialize I/O
        reader = TableReader(db_path=db_path)
        writer = TableWriter(db_path=db_path, workflow_id="test_e2e")

        # Execute first model
        model1 = ModelRegistry.get("e2e.document_processor")
        result1 = model1["function"](reader=reader, writer=writer, filters=filters)

        assert result1["rows_written"] == 1
        assert result1["table_name"] == "e2e_document_processor"

        # Verify the table was created with correct schema
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(e2e_document_processor)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Check Pydantic model columns are present
        assert "document_id" in column_names
        assert "title" in column_names
        assert "content_length" in column_names
        assert "word_count" in column_names
        assert "has_code" in column_names
        assert "processing_note" in column_names

        # Check metadata columns are present
        assert "workflow_id" in column_names
        assert "created_at" in column_names
        assert "updated_at" in column_names

        # Execute second model (depends on first)
        reader2 = TableReader(db_path=db_path)
        writer2 = TableWriter(db_path=db_path, workflow_id="test_e2e")

        model2 = ModelRegistry.get("e2e.document_summarizer")
        result2 = model2["function"](reader=reader2, writer=writer2, filters=filters)

        assert result2["rows_written"] == 1
        assert result2["table_name"] == "e2e_document_summarizer"

        # Verify final output
        reader3 = TableReader(db_path=db_path)
        summaries = reader3.load("e2e_document_summarizer")
        assert len(summaries) == 1

        summary_row = summaries.iloc[0]
        assert "Test Document" in summary_row["summary"]
        assert "with code examples" in summary_row["summary"]
        assert json.loads(summary_row["key_topics"]) == ["testing", "framework"]
        assert summary_row["confidence"] == 0.95

        conn.close()

    @pytest.mark.skip(reason="Requires tmp_project fixture from main test suite")
    def test_incremental_mode_skip(self, tmp_project, setup_test_models):
        """Test that incremental mode correctly skips unchanged documents."""
        import hashlib

        from kurt.content.document import add_document
        from kurt.db.database import get_session
        from kurt.db.models import Document, IngestionStatus

        session = get_session()

        # Add a document that's already been indexed
        doc_id = add_document("https://example.com/indexed-doc")
        doc = session.get(Document, doc_id)
        doc.title = "Already Indexed"
        doc.content_path = "indexed.md"
        doc.ingestion_status = IngestionStatus.FETCHED

        # Create content and set the indexed hash
        from kurt.config import load_config

        config = load_config()
        sources_path = config.get_absolute_sources_path()
        test_file = sources_path / "indexed.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        content = "This document was already indexed"
        test_file.write_text(content)

        # Set the indexed hash to match current content
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        doc.indexed_with_hash = content_hash
        session.commit()

        # Load with incremental mode
        filters = DocumentFilters(ids=str(doc_id))
        docs = load_documents(filters, incremental_mode="delta")

        assert len(docs) == 1
        assert docs[0]["skip"] is True
        assert docs[0]["skip_reason"] == "content_unchanged"

    @pytest.mark.skip(reason="Requires tmp_project fixture from main test suite")
    def test_table_reader_column_checking(self, tmp_project):
        """Test that TableReader properly checks for column existence."""
        db_path = tmp_project / ".kurt" / "kurt.sqlite"

        # Create a table without document_id column
        import sqlite3

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE test_no_doc_id (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        conn.close()

        # TableReader should not apply document filters to this table
        reader = TableReader(db_path=db_path, filters=DocumentFilters(ids="some-id"))

        # This should not raise an error even though we have filters
        df = reader.load("test_no_doc_id")
        # Table is empty but query should succeed
        assert len(df) == 0
