"""
Unit tests for the 'kurt content index' command.

Tests the CLI command with mocked DSPy and embedding calls to avoid API calls.
The indexing pipeline now uses a declarative model-based approach with:
- document_sections: Split documents into sections
- section_extractions: Extract entities/claims via DSPy
- entity_clustering: Cluster similar entities
- entity_resolution: Resolve entities to DB
- claim_clustering: Cluster similar claims
- claim_resolution: Resolve claims to DB

Test Strategy:
- Mock DSPy at the run_batch_sync boundary (LLM interface)
- Mock embeddings at generate_embeddings boundary
- Let the framework and model logic run with real code paths
- Use temporary SQLite DB for isolation
"""

import uuid
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from kurt.cli import main
from kurt.conftest import get_doc_status as _get_doc_status
from kurt.core.dspy_helpers import DSPyResult
from kurt.core.testing import (
    create_extraction_response_factory,
    mock_embeddings,
    mock_run_batch,
)
from kurt.db.database import get_session
from kurt.db.models import Document, SourceType


def content_aware_response_factory(items: List[Dict[str, Any]]) -> List[DSPyResult]:
    """
    Create extraction responses based on document content.

    This factory analyzes the document content and generates appropriate
    entities and claims, simulating what the LLM would extract.
    """
    results = []
    for item in items:
        content = item.get("document_content", "")

        entities = []
        claims = []

        # Extract entities based on content keywords
        if "PostgreSQL" in content or "postgresql" in content.lower():
            entities.append(
                {
                    "name": "PostgreSQL",
                    "entity_type": "Technology",
                    "description": "A powerful open-source relational database",
                    "aliases": ["Postgres", "PG"],
                    "confidence": 0.95,
                    "resolution_status": "NEW",
                    "quote": "PostgreSQL is a powerful database",
                }
            )
            claims.append(
                {
                    "statement": "PostgreSQL is a powerful database",
                    "claim_type": "capability",
                    "entity_indices": [len(entities) - 1],
                    "source_quote": "PostgreSQL is a powerful database that supports JSON",
                    "quote_start_offset": 0,
                    "quote_end_offset": 50,
                    "confidence": 0.9,
                }
            )

        if "Python" in content:
            entities.append(
                {
                    "name": "Python",
                    "entity_type": "Technology",
                    "description": "A high-level programming language",
                    "aliases": [],
                    "confidence": 0.9,
                    "resolution_status": "NEW",
                    "quote": "Python integrates well",
                }
            )

        if "Docker" in content:
            entities.append(
                {
                    "name": "Docker",
                    "entity_type": "Technology",
                    "description": "Container platform for deployment",
                    "aliases": [],
                    "confidence": 0.85,
                    "resolution_status": "NEW",
                    "quote": "Docker is useful for deploying",
                }
            )

        # Check for document number patterns (for batch tests)
        for i in range(10):
            if f"Document {i}" in content or f"technology {i}" in content:
                entities.append(
                    {
                        "name": f"Technology{i}",
                        "entity_type": "Technology",
                        "description": f"Technology number {i}",
                        "aliases": [],
                        "confidence": 0.8,
                        "resolution_status": "NEW",
                        "quote": f"Document {i} about technology {i}",
                    }
                )
                claims.append(
                    {
                        "statement": f"Technology {i} is useful",
                        "claim_type": "capability",
                        "entity_indices": [len(entities) - 1],
                        "source_quote": f"technology {i}",
                        "quote_start_offset": 0,
                        "quote_end_offset": 20,
                        "confidence": 0.8,
                    }
                )
                break

        # Default entity if nothing matches
        if not entities:
            entities.append(
                {
                    "name": "Unknown",
                    "entity_type": "Topic",
                    "description": "Unknown topic",
                    "aliases": [],
                    "confidence": 0.5,
                    "resolution_status": "NEW",
                    "quote": content[:100] if content else "No content",
                }
            )

        # Create mock result
        mock_result = MagicMock()
        mock_result.metadata = {
            "content_type": "reference",
            "has_code_examples": False,
            "has_step_by_step_procedures": False,
            "has_narrative_structure": False,
        }
        mock_result.entities = entities
        mock_result.relationships = []
        mock_result.claims = claims

        results.append(
            DSPyResult(
                payload=item,
                result=mock_result,
                error=None,
                telemetry={"tokens_prompt": 100, "tokens_completion": 50},
            )
        )

    return results


@pytest.fixture
def mock_llm_boundary():
    """
    Mock the LLM boundary (DSPy + embeddings) for indexing tests.

    This fixture mocks only the expensive nondeterministic LLM calls,
    allowing the framework and model logic to exercise their real code paths.
    """
    with mock_run_batch(content_aware_response_factory), mock_embeddings():
        yield


class TestIndexCommand:
    """Test the 'kurt content index' command with mocked LLM boundary."""

    def test_index_single_document(self, tmp_project, mock_llm_boundary):
        """Test indexing a single document with mocked LLM calls."""
        runner = CliRunner()

        # Create a test document in the database
        session = get_session()
        doc_id = uuid.uuid4()

        # Create a test markdown file
        test_file = Path(tmp_project) / "sources" / "test_doc.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("""# Test Document

This is a test document about PostgreSQL and Python.

PostgreSQL is a powerful database that supports JSON.
Python integrates well with PostgreSQL using psycopg2.
Docker is useful for deploying both.
""")

        # Add document to database as FETCHED
        content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
        content_file.parent.mkdir(exist_ok=True)
        content_file.write_text(test_file.read_text())

        doc = Document(
            id=doc_id,
            source_type=SourceType.FILE_UPLOAD,
            source_url=f"file://{test_file}",
            source_path=str(test_file),
            content_path=str(content_file),
            title="Test Document",
            raw_content=test_file.read_text(),
        )
        session.add(doc)
        session.commit()

        # Run the index command using document ID prefix
        doc_id_prefix = str(doc_id)[:8]
        result = runner.invoke(main, ["content", "index", doc_id_prefix, "--force"])

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify document still exists and is indexed
        session.expire_all()
        doc = session.get(Document, doc_id)
        assert doc is not None
        # After indexing, status should be INDEXED (has section extractions)
        assert _get_doc_status(doc.id) == "INDEXED"

    def test_index_batch_documents(self, tmp_project, mock_llm_boundary):
        """Test indexing multiple documents using the batch workflow."""
        from kurt.conftest import mark_document_as_fetched

        runner = CliRunner()
        session = get_session()

        # Create multiple test documents
        doc_ids = []
        for i in range(3):
            test_file = Path(tmp_project) / "sources" / f"doc_{i}.md"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(f"Document {i} about technology {i}")

            doc_id = uuid.uuid4()
            content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
            content_file.parent.mkdir(parents=True, exist_ok=True)
            content_file.write_text(test_file.read_text())

            doc = Document(
                id=doc_id,
                source_type=SourceType.FILE_UPLOAD,
                source_url=f"file://{test_file}",
                source_path=str(test_file),
                content_path=str(content_file),
                title=f"Document {i}",
                raw_content=test_file.read_text(),
            )
            session.add(doc)
            doc_ids.append(doc_id)

        session.commit()

        # Mark all documents as FETCHED (status now derived from staging tables)
        for doc_id in doc_ids:
            mark_document_as_fetched(doc_id, session)

        # Index all documents
        result = runner.invoke(main, ["content", "index", "--all", "--force"])
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify all documents still exist
        for doc_id in doc_ids:
            doc = session.get(Document, doc_id)
            assert doc is not None
            # After indexing, status should be INDEXED (has section extractions)
            assert _get_doc_status(doc.id) == "INDEXED"

    def test_index_error_handling(self, tmp_project):
        """Test that indexing handles errors gracefully (no content file)."""
        from kurt.conftest import mark_document_as_fetched

        runner = CliRunner()
        session = get_session()

        # Create a document without content file
        doc = Document(
            id=uuid.uuid4(),
            source_type=SourceType.FILE_UPLOAD,
            source_url="file:///nonexistent.md",
            source_path="/nonexistent.md",
            content_path="/nonexistent/content.md",
            title="Missing Content",
        )
        session.add(doc)
        session.commit()

        # Mark as FETCHED (status now derived from staging tables)
        mark_document_as_fetched(doc.id, session)

        # Try to index - should handle the error gracefully
        result = runner.invoke(main, ["content", "index", str(doc.id)[:8], "--force"])

        # Should complete without crashing
        assert result.exit_code in [0, 1]

        # Document should remain in FETCHED status (indexing failed due to missing content)
        session.expire_all()
        doc = session.get(Document, doc.id)
        assert _get_doc_status(doc.id) == "FETCHED"

    def test_index_no_documents_found(self, tmp_project):
        """Test indexing when no documents match the criteria."""
        runner = CliRunner()

        # Try to index with a non-existent ID
        result = runner.invoke(main, ["content", "index", "nonexist"])

        # Should report no documents found
        assert "No documents found" in result.output or result.exit_code == 1

    def test_index_help(self):
        """Test that index command help is available."""
        runner = CliRunner()
        result = runner.invoke(main, ["content", "index", "--help"])

        assert result.exit_code == 0
        assert "Index documents" in result.output
        assert "--force" in result.output
        assert "--all" in result.output


class TestIndexCommandWithSimpleFactory:
    """Test using the simple extraction response factory."""

    def test_index_with_factory(self, tmp_project):
        """Test indexing using create_extraction_response_factory."""
        runner = CliRunner()
        session = get_session()

        doc_id = uuid.uuid4()
        test_file = Path(tmp_project) / "sources" / "factory_test.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Test content for factory")

        content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
        content_file.parent.mkdir(exist_ok=True)
        content_file.write_text(test_file.read_text())

        doc = Document(
            id=doc_id,
            source_type=SourceType.FILE_UPLOAD,
            source_url=f"file://{test_file}",
            source_path=str(test_file),
            content_path=str(content_file),
            title="Factory Test",
            raw_content=test_file.read_text(),
        )
        session.add(doc)
        session.commit()

        # Use the simple factory that generates predictable entities
        factory = create_extraction_response_factory(
            entities_per_section=3,
            claims_per_section=2,
            entity_prefix="TestEntity",
        )

        with mock_run_batch(factory), mock_embeddings():
            result = runner.invoke(main, ["content", "index", str(doc_id)[:8], "--force"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
