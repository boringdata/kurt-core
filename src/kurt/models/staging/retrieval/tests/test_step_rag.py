"""Tests for the unified RAG pipeline step (step_rag.py).

Uses tmp_project fixture for real database isolation and mocks for embeddings.
"""

import json
from uuid import uuid4

import numpy as np
import pytest

from kurt.models.staging.retrieval.step_rag import RAGConfig
from kurt.models.staging.retrieval.tests.conftest import mock_retrieval_llm  # noqa: F401
from kurt.utils.retrieval import (
    cosine_similarity,
    cosine_similarity_batch,
    extract_entities_from_query,
    reciprocal_rank_fusion,
    semantic_search,
)
from kurt.utils.retrieval.formatting import format_rag_context as format_context

# Import fixtures
from tests.conftest import reset_dbos_state, tmp_project  # noqa: F401

# ============================================================================
# Unit Tests
# ============================================================================


class TestCosineSimilarity:
    """Tests for cosine_similarity helper function."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity 1.0."""
        vec = np.array([1.0, 2.0, 3.0])
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity 0.0."""
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_zero_vector_returns_zero(self):
        """Zero vector should return 0.0 similarity."""
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 2.0, 3.0])
        assert cosine_similarity(a, b) == 0.0


class TestCosineSimilarityBatch:
    """Tests for batch cosine similarity computation."""

    def test_empty_embeddings(self):
        """Empty embeddings should return empty array."""
        query = np.array([1.0, 2.0, 3.0])
        embeddings = np.array([])
        result = cosine_similarity_batch(query, embeddings)
        assert len(result) == 0

    def test_single_embedding(self):
        """Single embedding batch computation."""
        query = np.array([1.0, 0.0, 0.0])
        embeddings = np.array([[1.0, 0.0, 0.0]])
        result = cosine_similarity_batch(query, embeddings)
        assert len(result) == 1
        assert result[0] == pytest.approx(1.0)

    def test_multiple_embeddings(self):
        """Multiple embeddings batch computation."""
        query = np.array([1.0, 0.0, 0.0])
        embeddings = np.array(
            [
                [1.0, 0.0, 0.0],  # Identical - sim 1.0
                [0.0, 1.0, 0.0],  # Orthogonal - sim 0.0
                [-1.0, 0.0, 0.0],  # Opposite - sim -1.0
            ]
        )
        result = cosine_similarity_batch(query, embeddings)
        assert len(result) == 3
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(-1.0)

    def test_zero_query_vector(self):
        """Zero query vector should return zeros."""
        query = np.array([0.0, 0.0, 0.0])
        embeddings = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        result = cosine_similarity_batch(query, embeddings)
        assert all(r == 0.0 for r in result)


class TestRAGConfig:
    """Tests for RAGConfig configuration."""

    def test_default_values(self):
        """Config should have sensible defaults."""
        config = RAGConfig()
        # ConfigParam returns actual values when accessed on instance
        assert config.semantic_top_k == 10
        assert config.graph_top_k == 20
        assert config.claim_top_k == 15
        assert config.min_similarity == 0.5
        assert config.max_documents == 500
        assert config.max_claims == 500

    def test_custom_values(self):
        """Config should accept custom values when instantiated properly."""
        config = RAGConfig(semantic_top_k=20, min_similarity=0.7)
        assert config.semantic_top_k == 20
        assert config.min_similarity == 0.7


class TestReciprocalRankFusion:
    """Tests for RRF ranking algorithm."""

    def test_empty_rankings(self):
        """Empty rankings should return empty result."""
        result = reciprocal_rank_fusion([])
        assert result == []

    def test_single_ranking(self):
        """Single ranking should preserve order."""
        rankings = [["doc1", "doc2", "doc3"]]
        result = reciprocal_rank_fusion(rankings)
        doc_ids = [doc_id for doc_id, _ in result]
        assert doc_ids == ["doc1", "doc2", "doc3"]

    def test_multiple_rankings_same_order(self):
        """Multiple rankings with same order should boost scores."""
        rankings = [
            ["doc1", "doc2", "doc3"],
            ["doc1", "doc2", "doc3"],
        ]
        result = reciprocal_rank_fusion(rankings)
        doc_ids = [doc_id for doc_id, _ in result]
        assert doc_ids[0] == "doc1"  # doc1 ranked first in both

    def test_multiple_rankings_different_order(self):
        """Multiple rankings with different orders should merge correctly."""
        rankings = [
            ["doc1", "doc2", "doc3"],
            ["doc3", "doc2", "doc1"],
        ]
        result = reciprocal_rank_fusion(rankings)
        # doc2 is ranked 2nd in both, so should have highest combined score
        doc_ids = [doc_id for doc_id, _ in result]
        assert "doc2" in doc_ids

    def test_overlapping_rankings(self):
        """Rankings with partial overlap should combine correctly."""
        rankings = [
            ["doc1", "doc2"],
            ["doc2", "doc3"],
            ["doc1", "doc3"],
        ]
        result = reciprocal_rank_fusion(rankings)
        # All docs should appear
        doc_ids = [doc_id for doc_id, _ in result]
        assert set(doc_ids) == {"doc1", "doc2", "doc3"}


class TestFormatContext:
    """Tests for context formatting."""

    def test_empty_context(self):
        """Empty context should produce valid output."""
        result = format_context(
            query="test query",
            ranked_docs=[],
            entities=[],
            relationships=[],
            claims=[],
            doc_metadata={},
        )

        assert "=== CONTEXT FOR: test query ===" in result
        assert "Retrieved: 0 documents, 0 claims" in result

    def test_with_entities(self):
        """Context with entities should format correctly."""
        result = format_context(
            query="test query",
            ranked_docs=[],
            entities=["Entity1", "Entity2"],
            relationships=[],
            claims=[],
            doc_metadata={},
        )

        assert "## Entities" in result
        assert "- Entity1" in result
        assert "- Entity2" in result

    def test_with_relationships(self):
        """Context with relationships should format correctly."""
        result = format_context(
            query="test query",
            ranked_docs=[],
            entities=[],
            relationships=[
                {"source_entity": "A", "target_entity": "B", "relationship_type": "uses"},
            ],
            claims=[],
            doc_metadata={},
        )

        assert "## Relationships" in result
        assert "A --[uses]--> B" in result

    def test_with_claims(self):
        """Context with claims should format correctly."""
        result = format_context(
            query="test query",
            ranked_docs=[],
            entities=[],
            relationships=[],
            claims=[
                {
                    "statement": "Test claim statement",
                    "entity": "Entity1",
                    "confidence": 0.95,
                },
            ],
            doc_metadata={},
        )

        assert "## Claims" in result
        assert "[Entity1] Test claim statement" in result
        assert "confidence: 0.95" in result

    def test_with_citations(self):
        """Context with citations should format correctly."""
        result = format_context(
            query="test query",
            ranked_docs=[("doc1", 0.9), ("doc2", 0.8)],
            entities=[],
            relationships=[],
            claims=[],
            doc_metadata={
                "doc1": {"title": "Doc 1", "url": "https://example.com/1"},
                "doc2": {"title": "Doc 2", "url": ""},
            },
        )

        assert "## Citations" in result
        assert "[1] Doc 1 (https://example.com/1)" in result
        assert "[2] Doc 2" in result


# ============================================================================
# Integration Tests with tmp_project
# ============================================================================


class TestRAGStepIntegration:
    """Integration tests with real database fixtures."""

    @pytest.fixture
    def rag_step_test_data(self, tmp_project):
        """Set up test data for RAG step integration tests."""
        from kurt.db.claim_models import Claim, ClaimType
        from kurt.db.database import get_session
        from kurt.db.models import (
            Document,
            DocumentEntity,
            Entity,
            EntityRelationship,
            IngestionStatus,
            SourceType,
        )

        session = get_session()

        # Create test entities with embeddings
        entity1 = Entity(
            name="Segment",
            entity_type="Product",
            description="Customer data platform",
            embedding=np.array([0.9, 0.1, 0.0] + [0.0] * 1533, dtype=np.float32).tobytes(),
            source_mentions=10,
        )
        entity2 = Entity(
            name="Integration",
            entity_type="Feature",
            description="Connect with other tools",
            embedding=np.array([0.1, 0.9, 0.0] + [0.0] * 1533, dtype=np.float32).tobytes(),
            source_mentions=5,
        )
        session.add_all([entity1, entity2])
        session.flush()

        entity1_id = str(entity1.id)
        entity2_id = str(entity2.id)

        # Create test documents with embeddings
        doc1 = Document(
            title="Segment Overview",
            source_type=SourceType.URL,
            source_url="https://segment.com/docs/overview",
            description="Overview of Segment CDP",
            ingestion_status=IngestionStatus.FETCHED,
            embedding=np.array([0.8, 0.2, 0.0] + [0.0] * 1533, dtype=np.float32).tobytes(),
        )
        doc2 = Document(
            title="Segment Integrations",
            source_type=SourceType.URL,
            source_url="https://segment.com/docs/integrations",
            description="Integration guide",
            ingestion_status=IngestionStatus.FETCHED,
            embedding=np.array([0.3, 0.7, 0.0] + [0.0] * 1533, dtype=np.float32).tobytes(),
        )
        session.add_all([doc1, doc2])
        session.flush()

        doc1_id = str(doc1.id)
        doc2_id = str(doc2.id)

        # Create document-entity edges
        doc_entity1 = DocumentEntity(document_id=doc1.id, entity_id=entity1.id, mention_count=5)
        doc_entity2 = DocumentEntity(document_id=doc2.id, entity_id=entity1.id, mention_count=3)
        doc_entity3 = DocumentEntity(document_id=doc2.id, entity_id=entity2.id, mention_count=8)
        session.add_all([doc_entity1, doc_entity2, doc_entity3])
        session.flush()

        # Create entity relationship
        rel = EntityRelationship(
            source_entity_id=entity1.id,
            target_entity_id=entity2.id,
            relationship_type="provides",
            confidence=0.9,
        )
        session.add(rel)
        session.flush()

        # Create claims
        claim1 = Claim(
            statement="Segment offers 300+ integrations",
            claim_type=ClaimType.CAPABILITY,
            source_document_id=doc1.id,
            subject_entity_id=entity1.id,
            source_quote="Segment offers 300+ integrations out of the box",
            source_location_start=0,
            source_location_end=50,
            extraction_confidence=0.95,
            overall_confidence=0.9,
        )
        claim2 = Claim(
            statement="Integrations are easy to set up",
            claim_type=ClaimType.CAPABILITY,
            source_document_id=doc2.id,
            subject_entity_id=entity2.id,
            source_quote="Setting up integrations takes minutes",
            source_location_start=100,
            source_location_end=150,
            extraction_confidence=0.85,
            overall_confidence=0.8,
        )
        session.add_all([claim1, claim2])
        session.commit()
        session.close()

        return {
            "entity_ids": [entity1_id, entity2_id],
            "doc_ids": [doc1_id, doc2_id],
        }

    def test_extract_entities_with_real_db(self, tmp_project, rag_step_test_data):
        """Test entity extraction with real database."""
        # Query embedding similar to "Segment" entity
        query_embedding = [0.85, 0.15, 0.0] + [0.0] * 1533

        entities = extract_entities_from_query("test query", query_embedding, top_k=5)

        assert "Segment" in entities

    def test_semantic_search_with_real_db(self, tmp_project, rag_step_test_data):
        """Test semantic search with real database."""
        # Query embedding similar to doc1
        query_embedding = [0.75, 0.25, 0.0] + [0.0] * 1533

        results = semantic_search(
            query_embedding,
            top_k=10,
            min_similarity=0.3,
            max_docs=100,
        )

        assert len(results) > 0
        # Results should be (doc_id, similarity, title, url)
        assert len(results[0]) == 4

    @pytest.mark.asyncio
    async def test_rag_retrieve_step_full_flow(
        self, tmp_project, mock_retrieval_llm, rag_step_test_data
    ):
        """Test full RAG retrieve step with real database using run_model."""
        from sqlalchemy import text

        from kurt.core.model_runner import PipelineContext, run_model
        from kurt.db.database import get_session
        from kurt.utils.filtering import DocumentFilters

        # Create pipeline context
        workflow_id = str(uuid4())
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=workflow_id,
            metadata={"query": "What integrations does Segment support?"},
        )

        # Run the step via run_model
        result = await run_model("retrieval.rag", ctx)

        # Verify result
        assert "error" not in result or result.get("error") is None

        # Check data was written to the table
        session = get_session()
        rows = session.execute(
            text("SELECT * FROM retrieval_rag_context WHERE query_id = :qid"),
            {"qid": workflow_id},
        ).fetchall()
        session.close()

        assert len(rows) == 1
        row = rows[0]
        assert "=== CONTEXT FOR:" in row.context_text

    @pytest.mark.asyncio
    async def test_rag_retrieve_step_no_query(self, tmp_project, mock_retrieval_llm):
        """Test RAG step with no query provided."""
        from kurt.core.model_runner import PipelineContext, run_model
        from kurt.utils.filtering import DocumentFilters

        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=str(uuid4()),
            metadata={},  # No query
        )

        result = await run_model("retrieval.rag", ctx)

        assert result.get("error") == "no_query"
        assert result.get("rows_written") == 0

    @pytest.mark.asyncio
    async def test_rag_retrieve_step_result_structure(
        self, tmp_project, mock_retrieval_llm, rag_step_test_data
    ):
        """Test that RAG step output has correct structure."""
        from sqlalchemy import text

        from kurt.core.model_runner import PipelineContext, run_model
        from kurt.db.database import get_session
        from kurt.utils.filtering import DocumentFilters

        workflow_id = str(uuid4())
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=workflow_id,
            metadata={"query": "test query"},
        )

        await run_model("retrieval.rag", ctx)

        # Check written data structure
        session = get_session()
        rows = session.execute(
            text("SELECT * FROM retrieval_rag_context WHERE query_id = :qid"),
            {"qid": workflow_id},
        ).fetchall()
        session.close()

        assert len(rows) == 1
        row = rows[0]

        # Verify JSON fields are valid
        doc_ids = json.loads(row.doc_ids)
        entities = json.loads(row.entities)
        claims = json.loads(row.claims)
        citations = json.loads(row.citations)
        telemetry = json.loads(row.telemetry)

        assert isinstance(doc_ids, list)
        assert isinstance(entities, list)
        assert isinstance(claims, list)
        assert isinstance(citations, list)
        assert isinstance(telemetry, dict)
