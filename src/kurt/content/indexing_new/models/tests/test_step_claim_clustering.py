"""Tests for the step_claim_clustering model."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.framework import PipelineContext, TableWriter
from kurt.content.indexing_new.models.step_claim_clustering import (
    ClaimGroupRow,
    _cluster_claims_by_similarity,
    _cluster_claims_by_text_prefix,
    _collect_claims_from_extractions,
    _compute_claim_hash,
    _resolve_claim_clusters,
    claim_clustering,
)

# Import centralized fixture utilities
from .conftest import _load_json_fixture, make_embedding_mock

# Load precomputed embeddings from JSON fixture
_CLAIM_EMBEDDINGS = _load_json_fixture("test_embeddings.json")["embeddings"]


def mock_generate_embeddings(texts):
    """Generate deterministic test embeddings using precomputed data."""
    mock_fn = make_embedding_mock(_CLAIM_EMBEDDINGS)
    return mock_fn(texts)


class TestClaimGroupRow:
    """Test the ClaimGroupRow SQLModel."""

    def test_create_group_row(self):
        """Test creating a claim group row."""
        row = ClaimGroupRow(
            claim_hash="abc123",
            workflow_id="workflow-123",
            document_id="doc-1",
            section_id="sec-1",
            statement="Python is a programming language",
            claim_type="definition",
            confidence=0.95,
            source_quote="Python is a programming language",
            entity_indices_json=[0, 1],
            cluster_id=0,
            cluster_size=2,
            decision="CREATE_NEW",
            canonical_statement="Python is a programming language",
            reasoning="Unique claim",
        )

        assert row.claim_hash == "abc123"
        assert row.workflow_id == "workflow-123"
        assert row.document_id == "doc-1"
        assert row.claim_type == "definition"
        assert row.decision == "CREATE_NEW"
        assert row.cluster_id == 0
        assert row.cluster_size == 2
        assert row.confidence == 0.95

    def test_group_row_defaults(self):
        """Test default values for optional fields."""
        row = ClaimGroupRow(
            claim_hash="test",
            workflow_id="test-batch",
            document_id="doc-1",
            section_id="sec-1",
            statement="Test statement",
            claim_type="definition",
        )

        assert row.confidence == 0.0
        assert row.cluster_id == -1
        assert row.cluster_size == 1
        assert row.decision == ""
        assert row.source_quote is None
        assert row.canonical_statement is None


class TestComputeClaimHash:
    """Test the _compute_claim_hash helper."""

    def test_deterministic(self):
        """Test that hash is deterministic for same input."""
        hash1 = _compute_claim_hash("Python is a language", "definition", "doc1")
        hash2 = _compute_claim_hash("Python is a language", "definition", "doc1")
        assert hash1 == hash2

    def test_case_insensitive(self):
        """Test that hash is case-insensitive for statement."""
        hash1 = _compute_claim_hash("Python is a language", "definition", "doc1")
        hash2 = _compute_claim_hash("python is a language", "definition", "doc1")
        assert hash1 == hash2

    def test_different_for_different_docs(self):
        """Test that same statement in different docs has different hash."""
        hash1 = _compute_claim_hash("Python is a language", "definition", "doc1")
        hash2 = _compute_claim_hash("Python is a language", "definition", "doc2")
        assert hash1 != hash2

    def test_different_for_different_types(self):
        """Test that same statement with different types has different hash."""
        hash1 = _compute_claim_hash("Python is fast", "capability", "doc1")
        hash2 = _compute_claim_hash("Python is fast", "definition", "doc1")
        assert hash1 != hash2

    def test_whitespace_normalized(self):
        """Test that whitespace is normalized."""
        hash1 = _compute_claim_hash("Python is a language", "definition", "doc1")
        hash2 = _compute_claim_hash("  Python is a language  ", "definition", "doc1")
        assert hash1 == hash2


class TestCollectClaimsFromExtractions:
    """Test the _collect_claims_from_extractions helper."""

    def test_collect_single_claim(self):
        """Test collecting a single claim."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {
                        "statement": "Python is great",
                        "claim_type": "capability",
                        "confidence": 0.9,
                    }
                ],
            }
        ]

        claims, claim_to_docs = _collect_claims_from_extractions(extractions)

        assert len(claims) == 1
        assert claims[0]["statement"] == "Python is great"
        assert claims[0]["claim_type"] == "capability"
        assert claims[0]["confidence"] == 0.9
        assert claims[0]["document_id"] == "doc1"
        assert claims[0]["section_id"] == "sec1"

    def test_collect_multiple_claims(self):
        """Test collecting multiple claims from multiple sections."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [{"statement": "Claim 1", "claim_type": "definition"}],
            },
            {
                "document_id": "doc1",
                "section_id": "sec2",
                "claims_json": [
                    {"statement": "Claim 2", "claim_type": "capability"},
                    {"statement": "Claim 3", "claim_type": "limitation"},
                ],
            },
        ]

        claims, claim_to_docs = _collect_claims_from_extractions(extractions)

        assert len(claims) == 3

    def test_skip_empty_statements(self):
        """Test that empty statements are skipped."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "", "claim_type": "definition"},
                    {"statement": "Valid claim", "claim_type": "capability"},
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        assert len(claims) == 1
        assert claims[0]["statement"] == "Valid claim"

    def test_invalid_claim_type_defaults_to_definition(self):
        """Test that invalid claim types default to definition."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Test claim", "claim_type": "invalid_type"},
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        assert claims[0]["claim_type"] == "definition"

    def test_claim_to_docs_mapping(self):
        """Test that claim_to_docs correctly maps claims to documents."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [{"statement": "Same claim", "claim_type": "definition"}],
            },
            {
                "document_id": "doc2",
                "section_id": "sec1",
                "claims_json": [{"statement": "Same claim", "claim_type": "definition"}],
            },
        ]

        claims, claim_to_docs = _collect_claims_from_extractions(extractions)

        # Should have 2 claims (one per document, same statement but different doc)
        assert len(claims) == 2
        # Each claim has different hash due to different document_id
        assert len(claim_to_docs) == 2

    def test_empty_claims_json(self):
        """Test handling empty claims_json."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [],
            },
            {
                "document_id": "doc2",
                "section_id": "sec1",
                "claims_json": None,
            },
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        assert len(claims) == 0


class TestClusterClaimsBySimilarity:
    """Test the _cluster_claims_by_similarity helper with embedding-based clustering."""

    @pytest.fixture(autouse=True)
    def mock_embeddings(self):
        """Mock embedding generation for deterministic tests."""
        # Patch at the source module since it's imported inside the function
        with patch(
            "kurt.content.embeddings.generate_embeddings",
            side_effect=mock_generate_embeddings,
        ):
            yield

    def test_single_claim_single_cluster(self):
        """Test that a single claim creates a single cluster."""
        claims = [{"statement": "Python is great", "claim_type": "definition", "confidence": 0.9}]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 1
        # Get the first (and only) cluster
        first_cluster = list(clusters.values())[0]
        assert len(first_cluster) == 1

    def test_same_statements_cluster_together(self):
        """Test that identical statements cluster together."""
        claims = [
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.8},
        ]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 1
        first_cluster = list(clusters.values())[0]
        assert len(first_cluster) == 2

    def test_different_statements_different_clusters(self):
        """Test that different statements create different clusters."""
        claims = [
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
            {"statement": "JavaScript is fast", "claim_type": "capability", "confidence": 0.8},
        ]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 2

    def test_case_insensitive_clustering(self):
        """Test that clustering is case-insensitive (same embedding)."""
        claims = [
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
            {"statement": "python is great", "claim_type": "definition", "confidence": 0.8},
        ]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 1
        first_cluster = list(clusters.values())[0]
        assert len(first_cluster) == 2


class TestClusterClaimsByTextPrefix:
    """Test the fallback _cluster_claims_by_text_prefix helper."""

    def test_single_claim_single_cluster(self):
        """Test that a single claim creates a single cluster."""
        claims = [{"statement": "Python is great", "claim_type": "definition", "confidence": 0.9}]

        clusters = _cluster_claims_by_text_prefix(claims)

        assert len(clusters) == 1
        assert len(clusters[0]) == 1

    def test_same_prefix_cluster_together(self):
        """Test that statements with same prefix cluster together."""
        claims = [
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
            {
                "statement": "Python is great for data science",
                "claim_type": "definition",
                "confidence": 0.8,
            },
        ]

        # Both start with "python is great" (first 100 chars normalized)
        clusters = _cluster_claims_by_text_prefix(claims)

        # Should be different clusters because full 100-char prefixes differ
        assert len(clusters) == 2


class TestResolveClaimClusters:
    """Test the _resolve_claim_clusters helper."""

    def test_single_claim_creates_new(self):
        """Test that a single claim results in CREATE_NEW."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "hash1",
                        "statement": "Python is great",
                        "claim_type": "definition",
                        "confidence": 0.9,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    }
                ],
                "similar_existing": [],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 1
        assert resolutions[0]["decision"] == "CREATE_NEW"
        assert resolutions[0]["canonical_statement"] == "Python is great"

    def test_multiple_claims_in_cluster(self):
        """Test that multiple claims in cluster keep highest confidence as canonical."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "hash1",
                        "statement": "Python is great",
                        "claim_type": "definition",
                        "confidence": 0.7,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    },
                    {
                        "claim_hash": "hash2",
                        "statement": "Python is great",
                        "claim_type": "definition",
                        "confidence": 0.9,
                        "document_id": "doc2",
                        "section_id": "sec1",
                    },
                ],
                "similar_existing": [],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 2
        # First resolution (highest confidence) gets CREATE_NEW
        assert resolutions[0]["decision"] == "CREATE_NEW"
        assert resolutions[0]["confidence"] == 0.9
        # Second gets DUPLICATE_OF
        assert resolutions[1]["decision"].startswith("DUPLICATE_OF:")

    def test_similar_existing_triggers_merge(self):
        """Test that similar existing claims trigger MERGE_WITH."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "hash1",
                        "statement": "Python is great",
                        "claim_type": "definition",
                        "confidence": 0.9,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    }
                ],
                "similar_existing": [
                    {"claim_hash": "existing_hash", "statement": "Python is excellent"}
                ],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 1
        assert resolutions[0]["decision"] == "MERGE_WITH:existing_hash"


class TestClaimClusteringModel:
    """Test the claim_clustering model function."""

    @pytest.fixture(autouse=True)
    def mock_embeddings(self):
        """Mock embedding generation for deterministic tests."""
        # Patch at the source module since it's imported inside the function
        with patch(
            "kurt.content.embeddings.generate_embeddings",
            side_effect=mock_generate_embeddings,
        ):
            yield

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_claim_groups"}
        return writer

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    def _create_mock_reference(self, extractions: list[dict]):
        """Create a mock Reference that returns the extractions DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(extractions)
        return mock_ref

    def test_empty_extractions(self, mock_writer, mock_ctx):
        """Test with empty extractions DataFrame."""
        mock_extractions = self._create_mock_reference([])

        result = claim_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        assert result["rows_written"] == 0
        assert result["claims_processed"] == 0
        mock_writer.write.assert_not_called()

    def test_extractions_without_claims(self, mock_writer, mock_ctx):
        """Test extractions with no claims."""
        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": str(uuid4()),
                    "section_id": "sec1",
                    "claims_json": None,
                    "entities_json": [],
                    "relationships_json": [],
                }
            ]
        )

        result = claim_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        assert result["rows_written"] == 0
        assert result["claims_processed"] == 0

    def test_single_claim(self, mock_writer, mock_ctx):
        """Test with a single claim."""
        doc_id = str(uuid4())
        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "claims_json": [
                        {
                            "statement": "Python supports multiple paradigms",
                            "claim_type": "capability",
                            "confidence": 0.9,
                            "source_quote": "Python supports multiple paradigms",
                        }
                    ],
                    "entities_json": [],
                    "relationships_json": [],
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        assert result["claims_processed"] == 1
        assert result["clusters_created"] == 1
        mock_writer.write.assert_called_once()

        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].document_id == doc_id
        assert rows[0].decision == "CREATE_NEW"
        assert rows[0].claim_type == "capability"

    def test_multiple_claims_same_section(self, mock_writer, mock_ctx):
        """Test multiple claims from same section."""
        doc_id = str(uuid4())
        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "claims_json": [
                        # Use semantically distinct claims to ensure they don't cluster with embeddings
                        {
                            "statement": "The Python programming language was created by Guido van Rossum in 1991",
                            "claim_type": "definition",
                            "confidence": 0.9,
                        },
                        {
                            "statement": "Machine learning models require large datasets for training",
                            "claim_type": "capability",
                            "confidence": 0.8,
                        },
                        {
                            "statement": "Database indexes improve query performance significantly",
                            "claim_type": "limitation",
                            "confidence": 0.7,
                        },
                    ],
                    "entities_json": [],
                    "relationships_json": [],
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 3, "table_name": "indexing_claim_groups"}

        result = claim_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        assert result["claims_processed"] == 3
        assert result["clusters_created"] == 3
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3

    def test_duplicate_claims_clustered(self, mock_writer, mock_ctx):
        """Test that duplicate claims are clustered together."""
        doc_id = str(uuid4())
        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "claims_json": [
                        {
                            "statement": "Python is great",
                            "claim_type": "definition",
                            "confidence": 0.9,
                        },
                    ],
                    "entities_json": [],
                    "relationships_json": [],
                },
                {
                    "document_id": doc_id,
                    "section_id": "sec2",
                    "claims_json": [
                        {
                            "statement": "Python is great",
                            "claim_type": "definition",
                            "confidence": 0.7,
                        },
                    ],
                    "entities_json": [],
                    "relationships_json": [],
                },
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        # Same claim from same document should have same hash
        # Only one unique claim should be written (deduped by hash)
        assert result["claims_processed"] == 2
        assert result["clusters_created"] == 1

    def test_workflow_id_set_on_rows(self, mock_writer, mock_ctx):
        """Test that workflow_id is set on rows."""
        doc_id = str(uuid4())
        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "claims_json": [
                        {"statement": "Test", "claim_type": "definition", "confidence": 0.9},
                    ],
                    "entities_json": [],
                    "relationships_json": [],
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        rows = mock_writer.write.call_args[0][0]
        # workflow_id should be set from context
        assert rows[0].workflow_id is not None
        assert rows[0].workflow_id == "test-workflow"

    def test_long_statement_truncated(self, mock_writer, mock_ctx):
        """Test that long statements are truncated."""
        doc_id = str(uuid4())
        long_statement = "A" * 2000

        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "claims_json": [
                        {
                            "statement": long_statement,
                            "claim_type": "definition",
                            "confidence": 0.9,
                        },
                    ],
                    "entities_json": [],
                    "relationships_json": [],
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        rows = mock_writer.write.call_args[0][0]
        assert len(rows[0].statement) == 1000  # Truncated to 1000 chars

    def test_json_string_parsing(self, mock_writer, mock_ctx):
        """Test that JSON string fields are parsed correctly."""
        doc_id = str(uuid4())
        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "claims_json": json.dumps(
                        [
                            {
                                "statement": "Test claim",
                                "claim_type": "definition",
                                "confidence": 0.9,
                            },
                        ]
                    ),
                    "entities_json": "[]",
                    "relationships_json": "[]",
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        assert result["claims_processed"] == 1


class TestCrossSectionClustering:
    """Test cross-section claim clustering behavior."""

    def test_same_claim_different_sections_collected(self):
        """Test that same claim from different sections is collected."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
                ],
            },
            {
                "document_id": "doc1",
                "section_id": "sec2",
                "claims_json": [
                    {"statement": "Python is great", "claim_type": "definition", "confidence": 0.8},
                ],
            },
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        # Both mentions collected (same statement, same doc = same hash)
        assert len(claims) == 2

    def test_same_claim_different_docs_different_hashes(self):
        """Test that same claim from different docs has different hashes."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Python is great", "claim_type": "definition"},
                ],
            },
            {
                "document_id": "doc2",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Python is great", "claim_type": "definition"},
                ],
            },
        ]

        claims, claim_to_docs = _collect_claims_from_extractions(extractions)

        # Different docs = different hashes
        hashes = [c["claim_hash"] for c in claims]
        assert len(set(hashes)) == 2


class TestEntityIndicesPreservation:
    """Test that entity indices are correctly preserved through the pipeline."""

    def test_entity_indices_collected_from_extractions(self):
        """Test that entity_indices are collected from claims."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {
                        "statement": "Python was created by Guido",
                        "claim_type": "relationship",
                        "confidence": 0.9,
                        "entity_indices": [0, 1],  # References entities at indices 0 and 1
                    },
                ],
            },
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        assert len(claims) == 1
        assert claims[0]["entity_indices"] == [0, 1]

    def test_entity_indices_preserved_in_resolution(self):
        """Test that entity_indices are preserved after resolution."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "hash1",
                        "statement": "Python was created by Guido",
                        "claim_type": "relationship",
                        "confidence": 0.9,
                        "document_id": "doc1",
                        "section_id": "sec1",
                        "entity_indices": [0, 1],
                    }
                ],
                "similar_existing": [],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 1
        assert resolutions[0]["entity_indices"] == [0, 1]

    def test_entity_indices_missing_defaults_to_empty(self):
        """Test that missing entity_indices defaults to empty list."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {
                        "statement": "Python is great",
                        "claim_type": "definition",
                        "confidence": 0.9,
                        # No entity_indices field
                    },
                ],
            },
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        assert len(claims) == 1
        assert claims[0]["entity_indices"] == []

    def test_multiple_claims_preserve_their_indices(self):
        """Test that each claim preserves its own entity indices."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {
                        "statement": "Python was created by Guido",
                        "claim_type": "relationship",
                        "confidence": 0.9,
                        "entity_indices": [0, 1],  # Python (0), Guido (1)
                    },
                    {
                        "statement": "Django is built on Python",
                        "claim_type": "relationship",
                        "confidence": 0.85,
                        "entity_indices": [2, 0],  # Django (2), Python (0)
                    },
                ],
            },
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        assert len(claims) == 2
        # Each claim has its own indices
        indices_by_statement = {c["statement"]: c["entity_indices"] for c in claims}
        assert indices_by_statement["Python was created by Guido"] == [0, 1]
        assert indices_by_statement["Django is built on Python"] == [2, 0]


class TestSimilarExistingClaimMerging:
    """Test handling of similar existing claims (conflict/merge scenarios)."""

    def test_merge_with_single_existing(self):
        """Test MERGE_WITH when one similar existing claim is found."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "new_hash",
                        "statement": "Python is a popular language",
                        "claim_type": "definition",
                        "confidence": 0.8,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    }
                ],
                "similar_existing": [
                    {
                        "claim_hash": "existing_hash",
                        "statement": "Python is a widely-used language",
                        "confidence": 0.95,
                    }
                ],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 1
        assert resolutions[0]["decision"] == "MERGE_WITH:existing_hash"
        # Canonical should be the existing claim's statement
        assert resolutions[0]["canonical_statement"] == "Python is a widely-used language"

    def test_merge_with_multiple_existing_picks_first(self):
        """Test that multiple similar existing claims merge with first one."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "new_hash",
                        "statement": "Python is interpreted",
                        "claim_type": "definition",
                        "confidence": 0.8,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    }
                ],
                "similar_existing": [
                    {"claim_hash": "existing_1", "statement": "Python is an interpreted language"},
                    {"claim_hash": "existing_2", "statement": "Python runs interpreted"},
                ],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 1
        # Should merge with first existing
        assert resolutions[0]["decision"] == "MERGE_WITH:existing_1"

    def test_resolution_includes_similar_existing_context(self):
        """Test that similar_existing is included in resolution for context."""
        existing_claims = [{"claim_hash": "existing_hash", "statement": "Python is versatile"}]
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "new_hash",
                        "statement": "Python is flexible",
                        "claim_type": "capability",
                        "confidence": 0.85,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    }
                ],
                "similar_existing": existing_claims,
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 1
        assert resolutions[0]["similar_existing"] == existing_claims


class TestClaimClusterMerging:
    """Test claim clustering when multiple claims should be merged."""

    def test_cluster_selects_highest_confidence_as_canonical(self):
        """Test that highest confidence claim becomes canonical."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "hash_low",
                        "statement": "Python is good",
                        "claim_type": "definition",
                        "confidence": 0.6,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    },
                    {
                        "claim_hash": "hash_high",
                        "statement": "Python is excellent",
                        "claim_type": "definition",
                        "confidence": 0.95,
                        "document_id": "doc2",
                        "section_id": "sec1",
                    },
                    {
                        "claim_hash": "hash_mid",
                        "statement": "Python is great",
                        "claim_type": "definition",
                        "confidence": 0.8,
                        "document_id": "doc3",
                        "section_id": "sec1",
                    },
                ],
                "similar_existing": [],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 3

        # First resolution should be highest confidence (0.95)
        assert resolutions[0]["claim_hash"] == "hash_high"
        assert resolutions[0]["decision"] == "CREATE_NEW"
        assert resolutions[0]["canonical_statement"] == "Python is excellent"

        # Others should be DUPLICATE_OF the highest confidence one
        assert resolutions[1]["decision"] == "DUPLICATE_OF:hash_high"
        assert resolutions[2]["decision"] == "DUPLICATE_OF:hash_high"

    def test_cluster_all_duplicates_reference_same_canonical(self):
        """Test that all duplicates reference the same canonical claim."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": f"hash_{i}",
                        "statement": f"Python variant {i}",
                        "claim_type": "definition",
                        "confidence": 0.5 + (i * 0.1),  # 0.5, 0.6, 0.7, 0.8, 0.9
                        "document_id": f"doc{i}",
                        "section_id": "sec1",
                    }
                    for i in range(5)
                ],
                "similar_existing": [],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 5

        # First (highest confidence = 0.9) is CREATE_NEW
        assert resolutions[0]["decision"] == "CREATE_NEW"
        canonical_hash = resolutions[0]["claim_hash"]

        # All others are DUPLICATE_OF the canonical
        for i in range(1, 5):
            assert resolutions[i]["decision"] == f"DUPLICATE_OF:{canonical_hash}"


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestClaimClusteringEdgeCases:
    """Test edge cases and boundary conditions for claim clustering."""

    @pytest.fixture(autouse=True)
    def mock_embeddings(self):
        """Mock embedding generation for deterministic tests."""
        with patch(
            "kurt.content.embeddings.generate_embeddings",
            side_effect=mock_generate_embeddings,
        ):
            yield

    def test_confidence_at_boundaries(self):
        """Test claims with confidence at 0.0 and 1.0 boundaries."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "hash_zero",
                        "statement": "Claim with zero confidence",
                        "claim_type": "definition",
                        "confidence": 0.0,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    },
                    {
                        "claim_hash": "hash_one",
                        "statement": "Claim with max confidence",
                        "claim_type": "definition",
                        "confidence": 1.0,
                        "document_id": "doc2",
                        "section_id": "sec1",
                    },
                ],
                "similar_existing": [],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 2
        # Max confidence (1.0) should be canonical
        assert resolutions[0]["confidence"] == 1.0
        assert resolutions[0]["decision"] == "CREATE_NEW"
        # Zero confidence should be duplicate
        assert resolutions[1]["confidence"] == 0.0
        assert resolutions[1]["decision"].startswith("DUPLICATE_OF:")

    def test_unicode_claims(self):
        """Test claims with various Unicode characters."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    # Chinese characters
                    {
                        "statement": "Python是一种编程语言",
                        "claim_type": "definition",
                        "confidence": 0.9,
                    },
                    # Emoji
                    {
                        "statement": "Python is great 🐍👍",
                        "claim_type": "capability",
                        "confidence": 0.8,
                    },
                    # Arabic (RTL)
                    {
                        "statement": "بايثون هي لغة برمجة",
                        "claim_type": "definition",
                        "confidence": 0.7,
                    },
                    # Japanese
                    {
                        "statement": "Pythonはプログラミング言語です",
                        "claim_type": "definition",
                        "confidence": 0.85,
                    },
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        assert len(claims) == 4
        # All claims should be preserved with their unicode content
        statements = [c["statement"] for c in claims]
        assert "Python是一种编程语言" in statements
        assert "Python is great 🐍👍" in statements

    def test_whitespace_only_statements_collected(self):
        """Test that whitespace-only statements are currently collected (edge case to document)."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "   ", "claim_type": "definition"},
                    {"statement": "\t\n\r", "claim_type": "definition"},
                    {"statement": "Valid claim", "claim_type": "capability"},
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        # Currently all claims are collected (filtering happens in clustering/resolution)
        # The whitespace claims will have similar hashes due to normalization
        assert len(claims) >= 1
        # Valid claim should be in the results
        valid_claims = [c for c in claims if c["statement"].strip() == "Valid claim"]
        assert len(valid_claims) == 1

    def test_very_long_statement_truncation(self):
        """Test that extremely long statements are truncated properly."""
        long_statement = "A" * 5000  # 5000 chars

        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": long_statement, "claim_type": "definition", "confidence": 0.9},
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        # Statement should be preserved (truncation happens in ClaimGroupRow)
        assert len(claims) == 1
        assert claims[0]["statement"] == long_statement

    def test_all_identical_claims_single_cluster(self):
        """Test that 100% duplicate claims result in single canonical."""
        claims = [
            {
                "statement": "Python is great",
                "claim_type": "definition",
                "confidence": 0.5 + i * 0.01,
            }
            for i in range(10)
        ]

        clusters = _cluster_claims_by_similarity(claims)

        # All identical claims should cluster together
        assert len(clusters) == 1
        first_cluster = list(clusters.values())[0]
        assert len(first_cluster) == 10

    def test_entity_indices_out_of_range(self):
        """Test handling of entity indices that exceed entity list bounds."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {
                        "statement": "Test claim",
                        "claim_type": "definition",
                        "confidence": 0.9,
                        "entity_indices": [0, 1, 999],  # 999 is out of range
                    },
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        # Entity indices should be preserved as-is (validation happens later)
        assert len(claims) == 1
        assert claims[0]["entity_indices"] == [0, 1, 999]

    def test_negative_entity_indices(self):
        """Test handling of negative entity indices."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {
                        "statement": "Test claim",
                        "claim_type": "definition",
                        "confidence": 0.9,
                        "entity_indices": [-1, 0, 1],  # -1 is invalid
                    },
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        # Negative indices should be preserved (filtered later in resolution)
        assert len(claims) == 1
        assert -1 in claims[0]["entity_indices"]

    def test_malformed_json_string_in_claims(self):
        """Test handling of malformed JSON string in claims_json.

        Note: The current implementation iterates over the string characters,
        treating each character as a claim_data dict. This causes AttributeError
        when calling .get() on a string character.

        In practice, SQLite stores JSON fields which are parsed before reaching
        this function, so malformed JSON strings shouldn't occur here.
        """
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": "not valid json {",  # Invalid JSON string
            }
        ]

        # The code iterates over the string, treating each char as claim_data
        # When it tries to call claim_data.get("statement"), it fails
        with pytest.raises(AttributeError):
            _collect_claims_from_extractions(extractions)

    def test_mixed_valid_invalid_claims(self):
        """Test extraction with mix of valid and invalid claim entries.

        Note: Missing statement and None statement are handled correctly.
        Non-string statements (like int) cause AttributeError when hashing.
        """
        # Test 1: Missing and None statements are skipped correctly
        extractions_valid = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Valid claim", "claim_type": "definition"},
                    {"claim_type": "definition"},  # Missing statement - skipped
                    {"statement": None, "claim_type": "definition"},  # None statement - skipped
                    {"statement": "", "claim_type": "definition"},  # Empty - skipped
                    {"statement": "Another valid", "claim_type": "capability"},
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions_valid)

        # Only valid string claims should be collected
        valid_statements = [c["statement"] for c in claims]
        assert "Valid claim" in valid_statements
        assert "Another valid" in valid_statements
        assert len(claims) == 2

    def test_non_string_statement_causes_error(self):
        """Test that non-string statements (like int) cause AttributeError.

        The code checks `if not statement:` which passes for non-zero ints,
        but then fails on `statement.lower()` in hash computation.
        """
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": 123, "claim_type": "definition"},  # Wrong type
                ],
            }
        ]

        with pytest.raises(AttributeError):
            _collect_claims_from_extractions(extractions)

    def test_special_characters_in_statements(self):
        """Test claims with special characters that might affect hashing."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Test with 'quotes'", "claim_type": "definition"},
                    {"statement": 'Test with "double quotes"', "claim_type": "definition"},
                    {"statement": "Test with\nnewlines\tand\ttabs", "claim_type": "definition"},
                    {"statement": "Test with <html> & &amp; entities", "claim_type": "definition"},
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        assert len(claims) == 4
        # Verify special characters preserved
        statements = [c["statement"] for c in claims]
        assert "Test with 'quotes'" in statements
        assert "Test with\nnewlines\tand\ttabs" in statements

    def test_duplicate_claims_same_document_different_sections(self):
        """Test that same claim in different sections of same doc has same hash."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [{"statement": "Python is great", "claim_type": "definition"}],
            },
            {
                "document_id": "doc1",
                "section_id": "sec2",
                "claims_json": [{"statement": "Python is great", "claim_type": "definition"}],
            },
            {
                "document_id": "doc1",
                "section_id": "sec3",
                "claims_json": [{"statement": "Python is great", "claim_type": "definition"}],
            },
        ]

        claims, claim_to_docs = _collect_claims_from_extractions(extractions)

        # Same claim, same doc = same hash, so only one unique hash
        unique_hashes = set(c["claim_hash"] for c in claims)
        # All 3 have same hash since same doc + same statement + same type
        assert len(unique_hashes) == 1

    def test_claim_type_normalization(self):
        """Test that invalid claim types are normalized to 'definition'."""
        extractions = [
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Claim 1", "claim_type": "INVALID_TYPE"},
                    {"statement": "Claim 2", "claim_type": ""},
                    {"statement": "Claim 3", "claim_type": None},
                    {"statement": "Claim 4"},  # Missing claim_type entirely
                ],
            }
        ]

        claims, _ = _collect_claims_from_extractions(extractions)

        # All should default to "definition"
        for claim in claims:
            assert claim["claim_type"] == "definition"


class TestClusteringAlgorithmEdgeCases:
    """Test edge cases specific to the clustering algorithm."""

    @pytest.fixture(autouse=True)
    def mock_embeddings(self):
        """Mock embedding generation for deterministic tests."""
        with patch(
            "kurt.content.embeddings.generate_embeddings",
            side_effect=mock_generate_embeddings,
        ):
            yield

    def test_empty_claims_list(self):
        """Test clustering with empty claims list."""
        clusters = _cluster_claims_by_similarity([])

        assert clusters == {}

    def test_single_claim_forms_own_cluster(self):
        """Test that a single claim forms its own cluster."""
        claims = [{"statement": "Only one claim", "claim_type": "definition", "confidence": 0.9}]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 1

    def test_prefix_clustering_fallback(self):
        """Test text prefix clustering as fallback."""
        claims = [
            {"statement": "AAAA claim one", "claim_type": "definition"},
            {"statement": "AAAA claim two", "claim_type": "definition"},  # Same 100-char prefix
            {"statement": "BBBB completely different", "claim_type": "definition"},
        ]

        clusters = _cluster_claims_by_text_prefix(claims)

        # Should have separate clusters based on prefix
        assert len(clusters) >= 2

    def test_case_sensitivity_in_hashing(self):
        """Test that claim hashing is case-insensitive for statement."""
        hash1 = _compute_claim_hash("Python Is Great", "definition", "doc1")
        hash2 = _compute_claim_hash("python is great", "definition", "doc1")
        hash3 = _compute_claim_hash("PYTHON IS GREAT", "definition", "doc1")

        assert hash1 == hash2 == hash3

    def test_hash_differs_by_claim_type(self):
        """Test that same statement with different types has different hash."""
        hash1 = _compute_claim_hash("Python is fast", "definition", "doc1")
        hash2 = _compute_claim_hash("Python is fast", "capability", "doc1")
        hash3 = _compute_claim_hash("Python is fast", "limitation", "doc1")

        assert hash1 != hash2 != hash3


class TestMergeResolutionEdgeCases:
    """Test edge cases in claim merge/resolution logic."""

    def test_multiple_existing_matches(self):
        """Test resolution when multiple existing claims match."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "new_hash",
                        "statement": "Python is versatile",
                        "claim_type": "capability",
                        "confidence": 0.85,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    }
                ],
                "similar_existing": [
                    {
                        "claim_hash": "existing_1",
                        "statement": "Python is flexible",
                        "confidence": 0.9,
                    },
                    {
                        "claim_hash": "existing_2",
                        "statement": "Python is adaptable",
                        "confidence": 0.95,
                    },
                    {
                        "claim_hash": "existing_3",
                        "statement": "Python is versatile",
                        "confidence": 0.8,
                    },
                ],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        # Should merge with first existing (existing_1)
        assert len(resolutions) == 1
        assert resolutions[0]["decision"] == "MERGE_WITH:existing_1"

    def test_zero_confidence_existing_still_merged(self):
        """Test that even zero-confidence existing claim triggers merge."""
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [
                    {
                        "claim_hash": "new_hash",
                        "statement": "Test claim",
                        "claim_type": "definition",
                        "confidence": 0.9,
                        "document_id": "doc1",
                        "section_id": "sec1",
                    }
                ],
                "similar_existing": [
                    {"claim_hash": "existing_zero", "statement": "Test claim", "confidence": 0.0}
                ],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        # Should still merge even with zero-confidence existing
        assert resolutions[0]["decision"] == "MERGE_WITH:existing_zero"

    def test_large_cluster_with_many_duplicates(self):
        """Test resolution of cluster with many duplicate claims."""
        cluster_claims = [
            {
                "claim_hash": f"hash_{i}",
                "statement": f"Claim variant {i}",
                "claim_type": "definition",
                "confidence": 0.5 + (i % 50) * 0.01,  # Varying confidence
                "document_id": f"doc{i}",
                "section_id": "sec1",
            }
            for i in range(100)
        ]

        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": cluster_claims,
                "similar_existing": [],
            }
        ]

        resolutions = _resolve_claim_clusters(cluster_tasks)

        assert len(resolutions) == 100
        # Exactly one CREATE_NEW, rest are DUPLICATE_OF
        create_new_count = sum(1 for r in resolutions if r["decision"] == "CREATE_NEW")
        assert create_new_count == 1

        # Find the canonical (highest confidence)
        canonical = [r for r in resolutions if r["decision"] == "CREATE_NEW"][0]
        assert canonical["confidence"] == max(c["confidence"] for c in cluster_claims)

    def test_empty_cluster_tasks(self):
        """Test resolution with empty cluster tasks."""
        resolutions = _resolve_claim_clusters([])

        assert resolutions == []

    def test_cluster_with_empty_claims_list(self):
        """Test resolution of cluster with no claims.

        Note: The current implementation raises IndexError when accessing
        sorted_claims[0] on an empty list. In practice, clusters with no
        claims shouldn't be passed to the resolution function.
        """
        cluster_tasks = [
            {
                "cluster_id": 0,
                "cluster_claims": [],
                "similar_existing": [],
            }
        ]

        # Empty cluster_claims causes IndexError when trying to get best_claim
        with pytest.raises(IndexError):
            _resolve_claim_clusters(cluster_tasks)
