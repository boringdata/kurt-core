"""Integration tests for the retrieval module using motherduck mock data.

These tests verify the retrieval pipeline works end-to-end with
real data from the MotherDuck knowledge graph dump.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from kurt.db.database import get_session


class TestRetrievalPipelineIntegration:
    """Test retrieval pipeline with motherduck mock data."""

    def test_graph_search_finds_duckdb_documents(self, motherduck_project):
        """Test that graph search finds documents mentioning DuckDB."""
        from kurt.db.graph_queries import find_documents_with_entity

        # Verify motherduck data is loaded
        session = get_session()
        entity_count = session.execute(text("SELECT COUNT(*) FROM entities")).scalar()
        assert entity_count > 0, "Entities should be loaded"

        # Search for DuckDB entity
        doc_ids = find_documents_with_entity("DuckDB")
        assert len(doc_ids) > 0, "Should find documents mentioning DuckDB"

    def test_graph_search_returns_knowledge_graph(self, motherduck_project):
        """Test that we can retrieve knowledge graphs for documents."""
        from kurt.db.graph_queries import find_documents_with_entity, get_document_knowledge_graph

        # Find a document with entities
        doc_ids = find_documents_with_entity("DuckDB")
        assert len(doc_ids) > 0

        doc_id = list(doc_ids)[0]
        kg = get_document_knowledge_graph(str(doc_id))

        assert "entities" in kg
        assert "relationships" in kg or "edges" in kg

    @pytest.mark.asyncio
    async def test_retrieve_graph_mode(self, motherduck_project, mock_retrieval_llm):
        """Test full retrieval pipeline in graph-only mode."""
        from kurt.retrieval import RetrievalContext, retrieve

        # Mock the LLM call for query analysis
        with patch("dspy.ChainOfThought") as mock_cot:
            mock_module = MagicMock()
            mock_result = MagicMock()
            mock_result.intent = "technical_question"
            mock_result.entities = ["DuckDB", "MotherDuck"]
            mock_result.keywords = ["database", "analytics"]
            mock_module.return_value = mock_result
            mock_cot.return_value = mock_module

            # Also mock dspy.configure to avoid LM initialization
            with patch("dspy.configure"):
                ctx = RetrievalContext(
                    query="What is DuckDB and how does it work with MotherDuck?",
                    query_type="graph",  # Use graph-only mode (no embeddings needed)
                )

                result = await retrieve(ctx)

                # Verify result structure
                assert hasattr(result, "context_text")
                assert hasattr(result, "citations")
                assert hasattr(result, "graph_payload")
                assert hasattr(result, "telemetry")

    def test_entities_in_database(self, motherduck_project):
        """Verify expected entities exist in the mock database."""
        session = get_session()

        # Query for key entities
        result = session.execute(
            text(
                "SELECT name, entity_type FROM entities WHERE name IN ('DuckDB', 'MotherDuck', 'SQLite')"
            )
        ).fetchall()

        entity_names = [r[0] for r in result]
        assert "DuckDB" in entity_names, "DuckDB should be in entities"

    def test_document_entity_relationships(self, motherduck_project):
        """Verify document-entity relationships are loaded."""
        session = get_session()

        # Count relationships
        count = session.execute(text("SELECT COUNT(*) FROM document_entities")).scalar()
        assert count > 0, "Document-entity relationships should be loaded"

        # Verify we can join documents to entities
        result = session.execute(
            text("""
                SELECT d.title, e.name
                FROM documents d
                JOIN document_entities de ON d.id = de.document_id
                JOIN entities e ON e.id = de.entity_id
                LIMIT 5
            """)
        ).fetchall()

        assert len(result) > 0, "Should be able to join documents to entities"


class TestRetrievalSteps:
    """Test individual retrieval steps."""

    def test_cag_step_output_schema(self, motherduck_project):
        """Verify CAG step output schema."""
        from kurt.models.staging.retrieval.step_cag import CAGContextRow

        # SQLModel may alter __tablename__, so check actual table name
        assert hasattr(CAGContextRow, "__table__")
        assert CAGContextRow.__table__.name == "retrieval_cag_context"

    def test_rag_step_output_schema(self, motherduck_project):
        """Verify RAG step output schema."""
        from kurt.models.staging.retrieval.step_rag import RAGContextRow

        assert RAGContextRow.__table__.name == "retrieval_rag_context"


class TestRetrievalConfig:
    """Test retrieval configuration."""

    def test_default_config(self):
        """Test default retrieval config values."""
        from kurt.retrieval.config import RetrievalConfig

        config = RetrievalConfig()

        # ConfigParam stores metadata, access .default for the value
        assert config.default_query_type.default == "hybrid"
        assert config.semantic_top_k.default == 10
        assert config.graph_top_k.default == 20
        assert config.max_context_tokens.default == 4000

    def test_config_validation(self):
        """Test config validation."""
        from kurt.retrieval.config import RetrievalConfig

        # Check config structure
        config = RetrievalConfig()
        assert config.semantic_top_k.ge == 1
        assert config.semantic_top_k.le == 50


class TestRetrievalTypes:
    """Test retrieval type definitions."""

    def test_retrieval_context_creation(self):
        """Test RetrievalContext dataclass."""
        from kurt.retrieval.types import RetrievalContext

        ctx = RetrievalContext(
            query="test query",
            query_type="hybrid",
            deep_mode=True,
            session_id="test-session",
        )

        assert ctx.query == "test query"
        assert ctx.query_type == "hybrid"
        assert ctx.deep_mode is True
        assert ctx.session_id == "test-session"

    def test_retrieval_result_creation(self):
        """Test RetrievalResult dataclass."""
        from kurt.retrieval.types import Citation, RetrievalResult

        result = RetrievalResult(
            context_text="Test context",
            citations=[
                Citation(
                    doc_id="1",
                    title="Test",
                    source_url="http://test.com",
                    snippet="test snippet",
                    confidence=0.9,
                )
            ],
        )

        assert result.context_text == "Test context"
        assert len(result.citations) == 1
        assert result.citations[0].title == "Test"
