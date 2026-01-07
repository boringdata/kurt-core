"""Tests for CAG (Cache-Augmented Generation) retrieval."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from kurt.models.staging.retrieval.step_cag import CAGConfig, cag_retrieve
from kurt.utils.retrieval import (
    TopicContextData,
    cosine_similarity,
    estimate_tokens,
    format_agent_context,
    get_topics_for_entities,
    load_context_for_documents,
    search_entities_by_embedding,
)

# Fixtures tmp_project and reset_dbos_state are auto-discovered from conftest

# ============================================================================
# Unit Tests
# ============================================================================


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

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

    def test_zero_vector(self):
        """Zero vector should return 0.0 similarity."""
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 2.0, 3.0])
        assert cosine_similarity(a, b) == 0.0
        assert cosine_similarity(b, a) == 0.0


class TestEstimateTokens:
    """Tests for token estimation."""

    def test_empty_string(self):
        """Empty string should have 0 tokens."""
        assert estimate_tokens("") == 0

    def test_short_string(self):
        """Short string token estimation."""
        # 12 chars / 4 = 3 tokens
        assert estimate_tokens("Hello World!") == 3

    def test_longer_string(self):
        """Longer string token estimation."""
        text = "a" * 100
        assert estimate_tokens(text) == 25


class TestFormatAgentContext:
    """Tests for markdown context formatting."""

    def test_empty_context(self):
        """Empty context should still produce valid markdown."""
        data = TopicContextData(
            topics=[],
            entities=[],
            relationships=[],
            claims=[],
            sources=[],
        )
        result = format_agent_context("test query", data)

        assert "# Context:" in result
        assert "test query" in result
        assert "None" in result

    def test_with_entities(self):
        """Context with entities should format correctly - new claims-centric format."""
        # New format only shows entities that have claims
        data = TopicContextData(
            topics=["Topic A"],
            entities=[
                {"name": "Entity1", "type": "Product", "description": "Desc1", "matched": True},
                {"name": "Entity2", "type": "Feature", "description": "Desc2", "matched": False},
            ],
            relationships=[],
            claims=[
                {
                    "statement": "Entity1 does something",
                    "type": "capability",
                    "confidence": 0.9,
                    "entity": "Entity1",
                    "source_doc_id": "123",
                    "source_doc_title": "Doc",
                },
            ],
            sources=[{"doc_id": "123", "title": "Doc", "url": "https://example.com"}],
        )
        result = format_agent_context("test query", data)

        assert "# Context:" in result
        assert "Entity1" in result
        assert "does something" in result

    def test_with_relationships(self):
        """Context with relationships should format correctly - new format."""
        # New claims-centric format shows relationships inline with entities
        data = TopicContextData(
            topics=["Topic A"],
            entities=[
                {"name": "A", "type": "Product", "description": "", "matched": True},
            ],
            relationships=[
                {"source": "A", "type": "uses", "target": "B"},
            ],
            claims=[
                {
                    "statement": "A uses B for something",
                    "type": "capability",
                    "confidence": 0.9,
                    "entity": "A",
                    "source_doc_id": "123",
                    "source_doc_title": "Doc",
                },
            ],
            sources=[{"doc_id": "123", "title": "Doc", "url": "https://example.com"}],
        )
        result = format_agent_context("test query", data)

        # New format shows relationships as "→ B" inline with entity
        assert "# Context:" in result
        assert "A" in result
        assert "B" in result

    def test_with_claims(self):
        """Context with claims should format correctly."""
        data = TopicContextData(
            topics=["Topic A"],
            entities=[
                {"name": "Product X", "type": "Product", "description": "", "matched": True},
            ],
            relationships=[],
            claims=[
                {
                    "statement": "Product X supports feature Y",
                    "type": "capability",
                    "confidence": 0.95,
                    "entity": "Product X",
                    "source_doc_id": "123",
                    "source_doc_title": "Doc Title",
                },
            ],
            sources=[{"doc_id": "123", "title": "Doc Title", "url": "https://example.com"}],
        )
        result = format_agent_context("test query", data)

        assert "## Knowledge" in result
        assert "Product X" in result
        assert "supports feature Y" in result
        # Sources section removed to save tokens

    def test_with_sources(self):
        """Sources section removed to save tokens - sources available via API."""
        data = TopicContextData(
            topics=["Topic A"],
            entities=[],
            relationships=[],
            claims=[],
            sources=[
                {"doc_id": "123", "title": "Doc 1", "url": "https://example.com/1"},
                {"doc_id": "456", "title": "Doc 2", "url": ""},
            ],
        )
        result = format_agent_context("test query", data)

        # Sources section removed to save tokens
        assert "## Sources" not in result


# ============================================================================
# Integration Tests (with mocked DB)
# ============================================================================


class TestSearchEntitiesByEmbedding:
    """Tests for entity-based search."""

    @patch("kurt.utils.retrieval.entity_search.get_session")
    def test_no_entities_with_embeddings(self, mock_session):
        """Should return empty when no entities have embeddings."""
        mock_session.return_value.query.return_value.filter.return_value.all.return_value = []

        query_embedding = [0.1, 0.2, 0.3]
        results = search_entities_by_embedding(query_embedding)

        assert results == []

    @patch("kurt.utils.retrieval.entity_search.get_session")
    def test_matches_similar_entities(self, mock_session):
        """Should match entities with high similarity."""
        # Mock entity with similar embedding
        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        mock_entity.name = "Test Entity"
        mock_entity.embedding = np.array([0.9, 0.1, 0.0], dtype=np.float32).tobytes()

        session = MagicMock()
        mock_session.return_value = session

        # First query returns entities
        session.query.return_value.filter.return_value.all.return_value = [mock_entity]

        query_embedding = [1.0, 0.0, 0.0]
        results = search_entities_by_embedding(query_embedding, min_similarity=0.5)

        assert len(results) > 0
        assert results[0][0].name == "Test Entity"


class TestLoadContextForDocuments:
    """Tests for context loading from documents."""

    @patch("kurt.utils.retrieval.context_loading.get_session")
    def test_empty_doc_ids(self, mock_session):
        """Empty doc_ids should return empty context."""
        result = load_context_for_documents([], [])

        assert result.topics == []
        assert result.entities == []
        assert result.relationships == []
        assert result.claims == []
        assert result.sources == []

    @patch("kurt.utils.retrieval.context_loading.get_session")
    def test_with_topics_metadata(self, mock_session):
        """Should include topics in result."""
        session = MagicMock()
        mock_session.return_value = session
        session.query.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = []
        session.query.return_value.filter.return_value.all.return_value = []

        result = load_context_for_documents([], [], topics=["Topic A"])

        assert result.topics == ["Topic A"]
        assert result.entities == []


# ============================================================================
# CAG Pipeline Step Tests
# ============================================================================


class TestCAGPipelineStep:
    """Tests for the cag_retrieve pipeline step."""

    @patch("kurt.models.staging.retrieval.step_cag.search_entities_by_embedding")
    @patch("kurt.models.staging.retrieval.step_cag.get_document_ids_from_entities")
    @patch("kurt.models.staging.retrieval.step_cag.load_context_for_documents")
    @patch("kurt.models.staging.retrieval.step_cag.generate_embeddings")
    def test_cag_retrieve_step(
        self,
        mock_embed,
        mock_load,
        mock_doc_ids_entities,
        mock_entities,
    ):
        """Test the cag_retrieve pipeline step."""
        # Mock embedding
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        # Mock entity search
        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        mock_entity.name = "Entity 1"
        mock_entities.return_value = [(mock_entity, 0.9)]

        # Mock document ID lookups
        mock_doc_ids_entities.return_value = {uuid4()}

        # Mock context loading
        mock_load.return_value = TopicContextData(
            topics=["Topic A"],
            entities=[{"name": "Entity 1", "type": "Product", "description": "", "matched": True}],
            relationships=[],
            claims=[
                {
                    "statement": "Test claim",
                    "type": "capability",
                    "confidence": 0.9,
                    "entity": "Entity 1",
                    "source_doc_id": "123",
                    "source_doc_title": "Doc",
                }
            ],
            sources=[{"doc_id": "123", "title": "Doc", "url": "https://example.com"}],
        )

        # Create mock context and writer
        mock_ctx = MagicMock()
        mock_ctx.metadata = {
            "query": "test query",
            "model_configs": {"retrieval.cag": CAGConfig()},
        }
        mock_ctx.workflow_id = "test-workflow-123"

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        # Call the step (config is injected via ctx.metadata.model_configs)
        result = cag_retrieve(ctx=mock_ctx, writer=mock_writer)

        # Verify result
        assert result["rows_written"] == 1
        assert result["entities_matched"] == 1

        # Verify writer was called
        mock_writer.write.assert_called_once()

    @patch("kurt.models.staging.retrieval.step_cag.generate_embeddings")
    def test_cag_retrieve_no_query(self, mock_embed):
        """Test cag_retrieve handles missing query."""
        mock_ctx = MagicMock()
        mock_ctx.metadata = {"model_configs": {"retrieval.cag": CAGConfig()}}  # No query

        mock_writer = MagicMock()

        result = cag_retrieve(ctx=mock_ctx, writer=mock_writer)

        assert result["rows_written"] == 0
        assert result["error"] == "no_query"
        mock_embed.assert_not_called()


# ============================================================================
# End-to-End Integration Tests (with real DB fixtures)
# ============================================================================


class TestCAGIntegration:
    """Integration tests with real database fixtures."""

    @pytest.fixture
    def cag_test_data(self, tmp_project):
        """Set up test data for CAG integration tests."""
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
        session.flush()  # Get IDs without closing transaction

        # Capture IDs before any detachment
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

        # Capture doc IDs
        doc1_id = str(doc1.id)
        doc2_id = str(doc2.id)

        # Create document-entity edges
        doc_entity1 = DocumentEntity(
            document_id=doc1.id,
            entity_id=entity1.id,
            mention_count=5,
        )
        doc_entity2 = DocumentEntity(
            document_id=doc2.id,
            entity_id=entity1.id,
            mention_count=3,
        )
        doc_entity3 = DocumentEntity(
            document_id=doc2.id,
            entity_id=entity2.id,
            mention_count=8,
        )
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
        topic = TopicCluster(
            name="Customer Data Platforms",
            description="CDP and customer data tools",
        )
        session.add(topic)
        session.flush()

        # Link documents to topic cluster
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

    def test_search_entities_integration(self, tmp_project, cag_test_data):
        """Test entity search with real database."""
        # Query embedding similar to "Segment" entity
        query_embedding = [0.85, 0.15, 0.0] + [0.0] * 1533

        results = search_entities_by_embedding(
            query_embedding,
            top_k=5,
            min_similarity=0.3,
        )

        assert len(results) > 0
        entity_names = [e.name for e, _ in results]
        assert "Segment" in entity_names

    def test_get_topics_for_entities_integration(self, tmp_project, cag_test_data):
        """Test topic lookup with real database."""
        from uuid import UUID

        # Use entity IDs from fixture
        entity_ids = [UUID(eid) for eid in cag_test_data["entity_ids"]]

        topics = get_topics_for_entities(entity_ids)

        assert "Customer Data Platforms" in topics

    @patch("kurt.models.staging.retrieval.step_cag.generate_embeddings")
    def test_full_cag_flow_integration(self, mock_embeddings, tmp_project, cag_test_data):
        """Full end-to-end CAG flow with real database using pipeline step."""
        # Query embedding similar to "Segment"
        mock_embeddings.return_value = [[0.85, 0.15, 0.0] + [0.0] * 1533]

        config = CAGConfig(
            top_k_per_term=5,
            min_similarity=0.3,
        )

        # Create mock context and writer
        mock_ctx = MagicMock()
        mock_ctx.metadata = {
            "query": "What integrations does Segment support?",
            "model_configs": {"retrieval.cag": config},
        }
        mock_ctx.workflow_id = "test-integration-123"

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = cag_retrieve(ctx=mock_ctx, writer=mock_writer)

        # Verify result structure
        assert result["entities_matched"] > 0
        mock_writer.write.assert_called_once()

    @patch("kurt.models.staging.retrieval.step_cag.generate_embeddings")
    def test_cag_no_match_integration(self, mock_embeddings, tmp_project, cag_test_data):
        """CAG should handle no matches gracefully with real database."""
        # Query embedding very different from any entity
        mock_embeddings.return_value = [[0.0, 0.0, 1.0] + [0.0] * 1533]

        config = CAGConfig(
            top_k_per_term=5,
            min_similarity=0.8,  # High threshold
        )

        mock_ctx = MagicMock()
        mock_ctx.metadata = {
            "query": "Something completely unrelated to the data",
            "model_configs": {"retrieval.cag": config},
        }
        mock_ctx.workflow_id = "test-no-match-123"

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = cag_retrieve(ctx=mock_ctx, writer=mock_writer)

        # Should still return valid result, just with no/few matches
        assert "entities_matched" in result
