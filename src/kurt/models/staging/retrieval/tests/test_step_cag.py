"""Tests for the CAG pipeline step (step_cag.py).

Uses tmp_project fixture for real database isolation and mocks for embeddings.
"""

import json
from uuid import uuid4

import numpy as np
import pytest

from kurt.models.staging.retrieval.step_cag import CAGConfig
from kurt.models.staging.retrieval.tests.conftest import mock_retrieval_llm  # noqa: F401
from kurt.utils.retrieval import (
    cosine_similarity,
    get_topics_for_entities,
    load_context_for_documents,
    search_entities_by_embedding,
)
from kurt.utils.retrieval.formatting import format_markdown_legacy as format_markdown

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

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity -1.0."""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([-1.0, -2.0, -3.0])
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        """Zero vector should return 0.0 similarity."""
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 2.0, 3.0])
        assert cosine_similarity(a, b) == 0.0
        assert cosine_similarity(b, a) == 0.0


class TestCAGConfig:
    """Tests for CAGConfig configuration."""

    def test_default_values(self):
        """Config should have sensible defaults."""
        config = CAGConfig()
        # ConfigParam stores metadata, access .default for the value
        assert config.top_k_entities.default == 5
        assert config.min_similarity.default == 0.3
        assert config.max_claims.default == 50
        assert config.max_entities.default == 50
        assert config.max_relationships.default == 30

    def test_custom_values(self):
        """Config should accept custom values when instantiated properly."""
        # CAGConfig uses ConfigParam - test that the class is structured correctly
        config = CAGConfig()
        assert config.top_k_entities.ge == 1
        assert config.top_k_entities.le == 50
        assert config.min_similarity.ge == 0.0
        assert config.min_similarity.le == 1.0


class TestFormatMarkdown:
    """Tests for markdown context formatting."""

    def test_empty_context(self):
        """Empty context should produce valid markdown."""
        context = {
            "entities": [],
            "relationships": [],
            "claims": [],
            "sources": [],
        }
        result = format_markdown("test query", [], context)

        assert "# Knowledge Context" in result
        assert "test query" in result
        assert "Topics:** None matched" in result

    def test_with_entities(self):
        """Context with entities should format correctly."""
        context = {
            "entities": [
                {"name": "Entity1", "type": "Product", "description": "Desc1", "matched": True},
                {"name": "Entity2", "type": "Feature", "description": "Desc2", "matched": False},
            ],
            "relationships": [],
            "claims": [],
            "sources": [],
        }
        result = format_markdown("test query", ["Topic A"], context)

        assert "### Entities" in result
        assert "**Entity1**" in result
        assert "Matched from query" in result
        assert "Entity2" in result

    def test_with_relationships(self):
        """Context with relationships should format correctly."""
        context = {
            "entities": [],
            "relationships": [
                {"source": "A", "type": "uses", "target": "B"},
            ],
            "claims": [],
            "sources": [],
        }
        result = format_markdown("test query", ["Topic A"], context)

        assert "### Relationships" in result
        assert "A --[uses]--> B" in result

    def test_with_claims(self):
        """Context with claims should format correctly."""
        context = {
            "entities": [],
            "relationships": [],
            "claims": [
                {
                    "statement": "Product X supports feature Y",
                    "type": "capability",
                    "confidence": 0.95,
                    "entity": "Product X",
                    "source_doc_title": "Doc Title",
                },
            ],
            "sources": [],
        }
        result = format_markdown("test query", ["Topic A"], context)

        assert "## Claims" in result
        assert "### Product X" in result
        assert "Product X supports feature Y" in result
        assert "[conf: 0.95]" in result
        assert "Doc Title" in result

    def test_with_sources(self):
        """Context with sources should format correctly."""
        context = {
            "entities": [],
            "relationships": [],
            "claims": [],
            "sources": [
                {"doc_id": "123", "title": "Doc 1", "url": "https://example.com/1"},
                {"doc_id": "456", "title": "Doc 2", "url": ""},
            ],
        }
        result = format_markdown("test query", ["Topic A"], context)

        assert "## Sources" in result
        assert "[1] Doc 1 - https://example.com/1" in result
        assert "[2] Doc 2" in result


# ============================================================================
# Integration Tests with tmp_project
# ============================================================================


class TestCAGStepIntegration:
    """Integration tests with real database fixtures."""

    @pytest.fixture
    def cag_step_test_data(self, tmp_project):
        """Set up test data for CAG step integration tests."""
        from sqlalchemy import text

        from kurt.db.claim_models import Claim, ClaimType
        from kurt.db.database import get_session
        from kurt.db.models import (
            Document,
            DocumentClusterEdge,
            DocumentEntity,
            Entity,
            EntityRelationship,
            IngestionStatus,
            SourceType,
            TopicCluster,
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

        # Create test documents
        doc1 = Document(
            title="Segment Overview",
            source_type=SourceType.URL,
            source_url="https://segment.com/docs/overview",
            description="Overview of Segment CDP",
            ingestion_status=IngestionStatus.FETCHED,
        )
        doc2 = Document(
            title="Segment Integrations",
            source_type=SourceType.URL,
            source_url="https://segment.com/docs/integrations",
            description="Integration guide",
            ingestion_status=IngestionStatus.FETCHED,
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

        # Create topic cluster
        topic = TopicCluster(name="Customer Data Platforms", description="CDP tools")
        session.add(topic)
        session.flush()

        edge1 = DocumentClusterEdge(document_id=doc1.id, cluster_id=topic.id)
        edge2 = DocumentClusterEdge(document_id=doc2.id, cluster_id=topic.id)
        session.add_all([edge1, edge2])
        session.flush()

        # Create staging topic clustering entries
        session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS staging_topic_clustering (
                document_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                source_url TEXT,
                title TEXT,
                cluster_name TEXT,
                cluster_description TEXT,
                content_type TEXT,
                reasoning TEXT,
                PRIMARY KEY (document_id, workflow_id)
            )
        """)
        )
        session.execute(
            text("""
                INSERT INTO staging_topic_clustering
                (document_id, workflow_id, cluster_name, title)
                VALUES (:doc_id, 'test', :cluster, :title)
            """),
            {"doc_id": doc1_id, "cluster": "Customer Data Platforms", "title": "Segment Overview"},
        )
        session.execute(
            text("""
                INSERT INTO staging_topic_clustering
                (document_id, workflow_id, cluster_name, title)
                VALUES (:doc_id, 'test', :cluster, :title)
            """),
            {
                "doc_id": doc2_id,
                "cluster": "Customer Data Platforms",
                "title": "Segment Integrations",
            },
        )

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
            "topic_name": "Customer Data Platforms",
        }

    def test_search_entities_with_real_db(self, tmp_project, cag_step_test_data):
        """Test entity search with real database."""
        # Query embedding similar to "Segment" entity
        query_embedding = [0.85, 0.15, 0.0] + [0.0] * 1533

        # Search entities by embedding
        results = search_entities_by_embedding(
            query_embedding,
            top_k=5,
            min_similarity=0.3,
        )

        # Extract matched entity names and IDs
        matched_names = [entity.name for entity, _ in results]
        matched_ids = [entity.id for entity, _ in results]

        # Verify we can get topics for matched entities
        assert get_topics_for_entities(matched_ids) is not None

        assert "Segment" in matched_names
        assert len(matched_ids) > 0

    def test_load_context_with_real_db(self, tmp_project, cag_step_test_data):
        """Test context loading with real database."""

        from kurt.utils.retrieval.context_loading import get_document_ids_from_topics

        # Get document IDs from topics
        doc_ids = list(get_document_ids_from_topics(["Customer Data Platforms"]))

        context = load_context_for_documents(
            doc_ids=doc_ids,
            matched_entity_names=["Segment"],
            topics=["Customer Data Platforms"],
            max_claims=10,
            max_entities=20,
            max_relationships=10,
        )

        assert len(context.entities) > 0
        assert any(e["name"] == "Segment" for e in context.entities)
        assert len(context.claims) > 0
        assert any("300+ integrations" in c["statement"] for c in context.claims)
        assert len(context.sources) == 2

    @pytest.mark.asyncio
    async def test_cag_retrieve_step_full_flow(
        self, tmp_project, mock_retrieval_llm, cag_step_test_data
    ):
        """Test full CAG retrieve step with real database using run_model."""
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
        result = await run_model("retrieval.cag", ctx)

        # Verify result
        assert "error" not in result or result.get("error") is None

        # Check data was written to the table
        session = get_session()
        rows = session.execute(
            text("SELECT * FROM retrieval_cag_context WHERE query_id = :qid"),
            {"qid": workflow_id},
        ).fetchall()
        session.close()

        assert len(rows) == 1
        row = rows[0]
        assert "# Knowledge Context" in row.context_markdown

    @pytest.mark.asyncio
    async def test_cag_retrieve_step_no_query(self, tmp_project, mock_retrieval_llm):
        """Test CAG step with no query provided."""
        from kurt.core.model_runner import PipelineContext, run_model
        from kurt.utils.filtering import DocumentFilters

        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=str(uuid4()),
            metadata={},  # No query
        )

        result = await run_model("retrieval.cag", ctx)

        assert result.get("error") == "no_query"
        assert result.get("rows_written") == 0

    @pytest.mark.asyncio
    async def test_cag_retrieve_step_no_matches(
        self, tmp_project, mock_retrieval_llm, cag_step_test_data
    ):
        """Test CAG step when no entities match - entities don't match query."""
        from sqlalchemy import text

        from kurt.core.model_runner import PipelineContext, run_model
        from kurt.db.database import get_session
        from kurt.utils.filtering import DocumentFilters

        workflow_id = str(uuid4())
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=workflow_id,
            # Query that won't match any entities well
            metadata={"query": "xyzabc123 completely random words that won't match"},
        )

        await run_model("retrieval.cag", ctx)

        # Check written data
        session = get_session()
        rows = session.execute(
            text("SELECT * FROM retrieval_cag_context WHERE query_id = :qid"),
            {"qid": workflow_id},
        ).fetchall()
        session.close()

        assert len(rows) == 1
        row = rows[0]

        # Parse JSON fields
        matched_entities = json.loads(row.matched_entities)
        topics = json.loads(row.topics)

        # Should have empty or minimal matches for random query
        assert isinstance(matched_entities, list)
        assert isinstance(topics, list)
