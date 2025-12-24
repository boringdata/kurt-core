"""Tests for CAG (Cache-Augmented Generation) retrieval."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from kurt.retrieval.cag import (
    CAGResult,
    TopicContextData,
    cosine_similarity,
    estimate_tokens,
    format_agent_context,
    load_topic_context,
    retrieve_cag,
    route_to_topics_via_entities,
)

# Import fixtures from main conftest
from tests.conftest import reset_dbos_state, tmp_project  # noqa: F401

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

        assert "# Knowledge Context" in result
        assert "test query" in result
        assert "Topics:** None matched" in result

    def test_with_entities(self):
        """Context with entities should format correctly."""
        data = TopicContextData(
            topics=["Topic A"],
            entities=[
                {"name": "Entity1", "type": "Product", "description": "Desc1", "matched": True},
                {"name": "Entity2", "type": "Feature", "description": "Desc2", "matched": False},
            ],
            relationships=[],
            claims=[],
            sources=[],
        )
        result = format_agent_context("test query", data)

        assert "### Entities" in result
        assert "**Entity1**" in result
        assert "Matched from query" in result
        assert "Entity2" in result

    def test_with_relationships(self):
        """Context with relationships should format correctly."""
        data = TopicContextData(
            topics=["Topic A"],
            entities=[],
            relationships=[
                {"source": "A", "type": "uses", "target": "B"},
            ],
            claims=[],
            sources=[],
        )
        result = format_agent_context("test query", data)

        assert "### Relationships" in result
        assert "A --[uses]--> B" in result

    def test_with_claims(self):
        """Context with claims should format correctly."""
        data = TopicContextData(
            topics=["Topic A"],
            entities=[],
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
            sources=[],
        )
        result = format_agent_context("test query", data)

        assert "## Claims" in result
        assert "### Product X" in result
        assert "Product X supports feature Y" in result
        assert "[conf: 0.95]" in result
        assert "Doc Title" in result

    def test_with_sources(self):
        """Context with sources should format correctly."""
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

        assert "## Sources" in result
        assert "[1] Doc 1 - https://example.com/1" in result
        assert "[2] Doc 2" in result


# ============================================================================
# Integration Tests (with mocked DB)
# ============================================================================


class TestRouteToTopicsViaEntities:
    """Tests for entity-based topic routing."""

    @patch("kurt.retrieval.cag.get_session")
    @patch("kurt.retrieval.cag.generate_embeddings")
    def test_no_entities_with_embeddings(self, mock_embeddings, mock_session):
        """Should return empty when no entities have embeddings."""
        mock_embeddings.return_value = [[0.1, 0.2, 0.3]]
        mock_session.return_value.query.return_value.filter.return_value.all.return_value = []

        topics, entities = route_to_topics_via_entities("test query")

        assert topics == []
        assert entities == []

    @patch("kurt.retrieval.cag.get_session")
    @patch("kurt.retrieval.cag.generate_embeddings")
    def test_matches_similar_entities(self, mock_embeddings, mock_session):
        """Should match entities with high similarity."""
        # Mock query embedding
        mock_embeddings.return_value = [[1.0, 0.0, 0.0]]

        # Mock entity with similar embedding
        mock_entity = MagicMock()
        mock_entity.id = uuid4()
        mock_entity.name = "Test Entity"
        mock_entity.embedding = np.array([0.9, 0.1, 0.0], dtype=np.float32).tobytes()

        session = MagicMock()
        mock_session.return_value = session

        # First query returns entities
        session.query.return_value.filter.return_value.all.return_value = [mock_entity]

        # Topic query returns topics
        mock_topic = MagicMock()
        mock_topic.cluster_name = "Test Topic"
        session.query.return_value.distinct.return_value.join.return_value.join.return_value.filter.return_value.filter.return_value.all.return_value = [
            mock_topic
        ]

        topics, entities = route_to_topics_via_entities("test query", min_similarity=0.5)

        assert "Test Entity" in entities


class TestLoadTopicContext:
    """Tests for topic context loading."""

    @patch("kurt.retrieval.cag.get_session")
    def test_empty_topics(self, mock_session):
        """Empty topics should return empty context."""
        result = load_topic_context([], [])

        assert result.topics == []
        assert result.entities == []
        assert result.relationships == []
        assert result.claims == []
        assert result.sources == []

    @patch("kurt.retrieval.cag.get_session")
    def test_no_documents_in_topic(self, mock_session):
        """Topic with no documents should return empty context."""
        session = MagicMock()
        mock_session.return_value = session
        session.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        result = load_topic_context(["Topic A"], [])

        assert result.topics == ["Topic A"]
        assert result.entities == []


# ============================================================================
# CAG Result Tests
# ============================================================================


class TestCAGResult:
    """Tests for CAGResult dataclass."""

    def test_default_values(self):
        """CAGResult should have sensible defaults."""
        result = CAGResult(query="test")

        assert result.query == "test"
        assert result.topics == []
        assert result.matched_entities == []
        assert result.context_markdown == ""
        assert result.token_estimate == 0
        assert result.sources == []
        assert result.telemetry == {}

    def test_with_values(self):
        """CAGResult should store provided values."""
        result = CAGResult(
            query="test",
            topics=["Topic A"],
            matched_entities=["Entity 1"],
            context_markdown="# Context",
            token_estimate=100,
            sources=[{"doc_id": "123", "title": "Doc"}],
            telemetry={"key": "value"},
        )

        assert result.topics == ["Topic A"]
        assert result.matched_entities == ["Entity 1"]
        assert result.context_markdown == "# Context"
        assert result.token_estimate == 100


# ============================================================================
# End-to-End Tests (with full mocking)
# ============================================================================


class TestRetrieveCAG:
    """End-to-end tests for retrieve_cag."""

    @pytest.mark.asyncio
    @patch("kurt.retrieval.cag.route_to_topics_via_entities")
    @patch("kurt.retrieval.cag.load_topic_context")
    async def test_full_retrieval_flow(self, mock_load, mock_route):
        """Full CAG retrieval should work end-to-end."""
        # Mock routing
        mock_route.return_value = (["Topic A"], ["Entity 1"])

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

        result = await retrieve_cag("test query")

        assert result.query == "test query"
        assert result.topics == ["Topic A"]
        assert result.matched_entities == ["Entity 1"]
        assert "# Knowledge Context" in result.context_markdown
        assert result.token_estimate > 0
        assert len(result.sources) == 1
        assert result.telemetry["topics_matched"] == 1

    @pytest.mark.asyncio
    @patch("kurt.retrieval.cag.route_to_topics_via_entities")
    @patch("kurt.retrieval.cag.load_topic_context")
    async def test_no_matches(self, mock_load, mock_route):
        """Should handle no matches gracefully."""
        mock_route.return_value = ([], [])
        mock_load.return_value = TopicContextData(
            topics=[],
            entities=[],
            relationships=[],
            claims=[],
            sources=[],
        )

        result = await retrieve_cag("unknown query")

        assert result.topics == []
        assert result.matched_entities == []
        assert "None matched" in result.context_markdown

    @pytest.mark.asyncio
    @patch("kurt.retrieval.cag.route_to_topics_via_entities")
    @patch("kurt.retrieval.cag.load_topic_context")
    async def test_multiple_topics(self, mock_load, mock_route):
        """Should handle multiple matched topics."""
        mock_route.return_value = (["Topic A", "Topic B"], ["Entity 1", "Entity 2"])
        mock_load.return_value = TopicContextData(
            topics=["Topic A", "Topic B"],
            entities=[
                {"name": "Entity 1", "type": "Product", "description": "First", "matched": True},
                {"name": "Entity 2", "type": "Feature", "description": "Second", "matched": True},
                {"name": "Entity 3", "type": "Topic", "description": "Related", "matched": False},
            ],
            relationships=[
                {"source": "Entity 1", "type": "uses", "target": "Entity 2"},
            ],
            claims=[
                {
                    "statement": "Entity 1 supports Entity 2",
                    "type": "capability",
                    "confidence": 0.9,
                    "entity": "Entity 1",
                    "source_doc_id": "123",
                    "source_doc_title": "Doc 1",
                },
                {
                    "statement": "Entity 2 is fast",
                    "type": "performance",
                    "confidence": 0.85,
                    "entity": "Entity 2",
                    "source_doc_id": "456",
                    "source_doc_title": "Doc 2",
                },
            ],
            sources=[
                {"doc_id": "123", "title": "Doc 1", "url": "https://example.com/1"},
                {"doc_id": "456", "title": "Doc 2", "url": "https://example.com/2"},
            ],
        )

        result = await retrieve_cag("test query about Entity 1 and Entity 2")

        assert len(result.topics) == 2
        assert len(result.matched_entities) == 2
        assert "Topic A" in result.context_markdown
        assert "Topic B" in result.context_markdown
        assert "Entity 1" in result.context_markdown
        assert "Entity 2" in result.context_markdown
        assert "Entity 1 --[uses]--> Entity 2" in result.context_markdown
        assert result.telemetry["topics_matched"] == 2
        assert result.telemetry["entities_matched"] == 2

    @pytest.mark.asyncio
    @patch("kurt.retrieval.cag.route_to_topics_via_entities")
    @patch("kurt.retrieval.cag.load_topic_context")
    async def test_with_custom_parameters(self, mock_load, mock_route):
        """Should respect custom top_k and min_similarity parameters."""
        mock_route.return_value = (["Topic A"], ["Entity 1"])
        mock_load.return_value = TopicContextData(
            topics=["Topic A"],
            entities=[],
            relationships=[],
            claims=[],
            sources=[],
        )

        await retrieve_cag(
            "test query",
            top_k_entities=10,
            min_similarity=0.5,
            max_claims=100,
        )

        # Verify routing was called with custom parameters
        mock_route.assert_called_once_with(
            "test query",
            top_k_entities=10,
            min_similarity=0.5,
        )

        # Verify context loading was called with custom max_claims
        mock_load.assert_called_once()
        call_args = mock_load.call_args
        assert call_args[1]["max_claims"] == 100


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

    @patch("kurt.retrieval.cag.generate_embeddings")
    def test_route_to_topics_integration(self, mock_embeddings, tmp_project, cag_test_data):
        """Test entity routing with real database."""
        # Query embedding similar to "Segment" entity
        mock_embeddings.return_value = [[0.85, 0.15, 0.0] + [0.0] * 1533]

        topics, entities = route_to_topics_via_entities(
            "Tell me about Segment",
            top_k_entities=5,
            min_similarity=0.3,
        )

        assert "Segment" in entities
        assert "Customer Data Platforms" in topics

    @patch("kurt.retrieval.cag.generate_embeddings")
    def test_load_context_integration(self, mock_embeddings, tmp_project, cag_test_data):
        """Test context loading with real database."""
        context = load_topic_context(
            topics=["Customer Data Platforms"],
            matched_entity_names=["Segment"],
            max_claims=10,
        )

        assert "Customer Data Platforms" in context.topics
        assert len(context.entities) > 0
        assert any(e["name"] == "Segment" for e in context.entities)
        assert len(context.claims) > 0
        assert any("300+ integrations" in c["statement"] for c in context.claims)
        assert len(context.sources) == 2

    @pytest.mark.asyncio
    @patch("kurt.retrieval.cag.generate_embeddings")
    async def test_full_cag_flow_integration(self, mock_embeddings, tmp_project, cag_test_data):
        """Full end-to-end CAG flow with real database."""
        # Query embedding similar to "Segment"
        mock_embeddings.return_value = [[0.85, 0.15, 0.0] + [0.0] * 1533]

        result = await retrieve_cag(
            "What integrations does Segment support?",
            top_k_entities=5,
            min_similarity=0.3,
        )

        # Verify result structure
        assert result.query == "What integrations does Segment support?"
        assert len(result.topics) > 0
        assert len(result.matched_entities) > 0

        # Verify context content
        assert "# Knowledge Context" in result.context_markdown
        assert "Segment" in result.context_markdown
        assert result.token_estimate > 0

        # Verify telemetry
        assert result.telemetry["topics_matched"] > 0
        assert result.telemetry["entities_matched"] > 0
        assert result.telemetry["claims_loaded"] > 0

    @pytest.mark.asyncio
    @patch("kurt.retrieval.cag.generate_embeddings")
    async def test_cag_no_match_integration(self, mock_embeddings, tmp_project, cag_test_data):
        """CAG should handle no matches gracefully with real database."""
        # Query embedding very different from any entity
        mock_embeddings.return_value = [[0.0, 0.0, 1.0] + [0.0] * 1533]

        result = await retrieve_cag(
            "Something completely unrelated to the data",
            top_k_entities=5,
            min_similarity=0.8,  # High threshold
        )

        # Should still return valid result, just empty
        assert result.query == "Something completely unrelated to the data"
        assert result.topics == []
        assert result.matched_entities == []
        assert "None matched" in result.context_markdown
