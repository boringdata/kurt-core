"""Integration tests for the retrieval module using motherduck mock data.

These tests verify the retrieval pipeline works end-to-end with
real data from the MotherDuck knowledge graph dump.
"""

from unittest.mock import MagicMock, patch

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

    @patch("kurt.models.staging.retrieval.step_cag.generate_embeddings")
    def test_retrieve_cag_mode(self, mock_embeddings, motherduck_project):
        """Test CAG retrieval pipeline step."""
        from kurt.models.staging.retrieval.step_cag import CAGConfig, cag_retrieve

        # Mock embeddings to return vectors similar to DuckDB
        mock_embeddings.return_value = [[0.9, 0.1, 0.0] + [0.0] * 1533]

        config = CAGConfig(
            top_k_entities=5,
            min_similarity=0.3,
        )

        mock_ctx = MagicMock()
        mock_ctx.metadata = {
            "query": "What is DuckDB and how does it work with MotherDuck?",
            "model_configs": {"retrieval.cag": config},
        }
        mock_ctx.workflow_id = "test-retrieve-graph"

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = cag_retrieve(ctx=mock_ctx, writer=mock_writer)

        # Verify result structure
        assert "rows_written" in result
        assert "entities_matched" in result
        mock_writer.write.assert_called_once()

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

    def test_cag_config_defaults(self):
        """Test CAGConfig default values."""
        from kurt.models.staging.retrieval.step_cag import CAGConfig

        config = CAGConfig()

        # Access default values
        assert config.top_k_entities == 5
        assert config.min_similarity == 0.3
        assert config.max_claims == 50

    def test_rag_config_defaults(self):
        """Test RAGConfig default values."""
        from kurt.models.staging.retrieval.step_rag import RAGConfig

        config = RAGConfig()

        assert config.semantic_top_k == 10
        assert config.graph_top_k == 20
        assert config.min_similarity == 0.5

    def test_cag_config_custom_values(self):
        """Test CAGConfig with custom values."""
        from kurt.models.staging.retrieval.step_cag import CAGConfig

        config = CAGConfig(
            top_k_entities=10,
            min_similarity=0.5,
            max_claims=100,
        )

        assert config.top_k_entities == 10
        assert config.min_similarity == 0.5
        assert config.max_claims == 100


class TestRetrievalOutputSchemas:
    """Test retrieval output schema definitions."""

    def test_cag_context_row_schema(self):
        """Test CAGContextRow output schema."""
        from kurt.models.staging.retrieval.step_cag import CAGContextRow

        # Verify required fields exist
        assert hasattr(CAGContextRow, "query_id")
        assert hasattr(CAGContextRow, "query")
        assert hasattr(CAGContextRow, "matched_entities")
        assert hasattr(CAGContextRow, "topics")
        assert hasattr(CAGContextRow, "context_markdown")
        assert hasattr(CAGContextRow, "token_estimate")
        assert hasattr(CAGContextRow, "sources")
        assert hasattr(CAGContextRow, "telemetry")

    def test_rag_context_row_schema(self):
        """Test RAGContextRow output schema."""
        from kurt.models.staging.retrieval.step_rag import RAGContextRow

        # Verify required fields exist
        assert hasattr(RAGContextRow, "query_id")
        assert hasattr(RAGContextRow, "query")
        assert hasattr(RAGContextRow, "context_text")
        assert hasattr(RAGContextRow, "doc_ids")
        assert hasattr(RAGContextRow, "entities")
        assert hasattr(RAGContextRow, "claims")
        assert hasattr(RAGContextRow, "citations")
        assert hasattr(RAGContextRow, "telemetry")
