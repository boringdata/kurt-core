"""Tests for the step_claim_clustering model."""

import json
from unittest.mock import MagicMock
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.indexing_new.framework import TableWriter
from kurt.content.indexing_new.models.step_claim_clustering import (
    ClaimGroupRow,
    claim_clustering,
    _collect_claims_from_extractions,
    _cluster_claims_by_similarity,
    _compute_claim_hash,
    _resolve_claim_clusters,
)


class TestClaimGroupRow:
    """Test the ClaimGroupRow SQLModel."""

    def test_create_group_row(self):
        """Test creating a claim group row."""
        row = ClaimGroupRow(
            claim_hash="abc123",
            batch_id="workflow-123",
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
        assert row.batch_id == "workflow-123"
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
            batch_id="test-batch",
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
    """Test the _cluster_claims_by_similarity helper."""

    def test_single_claim_single_cluster(self):
        """Test that a single claim creates a single cluster."""
        claims = [
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9}
        ]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 1
        assert len(clusters[0]) == 1

    def test_same_statements_cluster_together(self):
        """Test that identical statements cluster together."""
        claims = [
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.8},
        ]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 1
        assert len(clusters[0]) == 2

    def test_different_statements_different_clusters(self):
        """Test that different statements create different clusters."""
        claims = [
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
            {"statement": "JavaScript is fast", "claim_type": "capability", "confidence": 0.8},
        ]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 2

    def test_case_insensitive_clustering(self):
        """Test that clustering is case-insensitive."""
        claims = [
            {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
            {"statement": "python is great", "claim_type": "definition", "confidence": 0.8},
        ]

        clusters = _cluster_claims_by_similarity(claims)

        assert len(clusters) == 1
        assert len(clusters[0]) == 2


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

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_claim_groups"}
        return writer

    def _create_sources(self, extractions: list[dict]) -> dict[str, pd.DataFrame]:
        """Create sources dict with extractions DataFrame."""
        return {"extractions": pd.DataFrame(extractions)}

    def test_empty_extractions(self, mock_writer):
        """Test with empty extractions DataFrame."""
        sources = {"extractions": pd.DataFrame()}

        result = claim_clustering(sources=sources, writer=mock_writer, workflow_id="test")

        assert result["rows_written"] == 0
        assert result["claims_processed"] == 0
        mock_writer.write.assert_not_called()

    def test_extractions_without_claims(self, mock_writer):
        """Test extractions with no claims."""
        sources = self._create_sources([
            {
                "document_id": str(uuid4()),
                "section_id": "sec1",
                "claims_json": None,
                "entities_json": [],
                "relationships_json": [],
            }
        ])

        result = claim_clustering(sources=sources, writer=mock_writer, workflow_id="test")

        assert result["rows_written"] == 0
        assert result["claims_processed"] == 0

    def test_single_claim(self, mock_writer):
        """Test with a single claim."""
        doc_id = str(uuid4())
        sources = self._create_sources([
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
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(sources=sources, writer=mock_writer, workflow_id="test_wf")

        assert result["claims_processed"] == 1
        assert result["clusters_created"] == 1
        mock_writer.write.assert_called_once()

        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].document_id == doc_id
        assert rows[0].decision == "CREATE_NEW"
        assert rows[0].claim_type == "capability"

    def test_multiple_claims_same_section(self, mock_writer):
        """Test multiple claims from same section."""
        doc_id = str(uuid4())
        sources = self._create_sources([
            {
                "document_id": doc_id,
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Claim 1", "claim_type": "definition", "confidence": 0.9},
                    {"statement": "Claim 2", "claim_type": "capability", "confidence": 0.8},
                    {"statement": "Claim 3", "claim_type": "limitation", "confidence": 0.7},
                ],
                "entities_json": [],
                "relationships_json": [],
            }
        ])

        mock_writer.write.return_value = {"rows_written": 3, "table_name": "indexing_claim_groups"}

        result = claim_clustering(sources=sources, writer=mock_writer, workflow_id="test")

        assert result["claims_processed"] == 3
        assert result["clusters_created"] == 3
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3

    def test_duplicate_claims_clustered(self, mock_writer):
        """Test that duplicate claims are clustered together."""
        doc_id = str(uuid4())
        sources = self._create_sources([
            {
                "document_id": doc_id,
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Python is great", "claim_type": "definition", "confidence": 0.9},
                ],
                "entities_json": [],
                "relationships_json": [],
            },
            {
                "document_id": doc_id,
                "section_id": "sec2",
                "claims_json": [
                    {"statement": "Python is great", "claim_type": "definition", "confidence": 0.7},
                ],
                "entities_json": [],
                "relationships_json": [],
            },
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(sources=sources, writer=mock_writer, workflow_id="test")

        # Same claim from same document should have same hash
        # Only one unique claim should be written (deduped by hash)
        assert result["claims_processed"] == 2
        assert result["clusters_created"] == 1

    def test_batch_id_set_on_rows(self, mock_writer):
        """Test that batch_id is set on rows (uses workflow_id when available)."""
        doc_id = str(uuid4())
        sources = self._create_sources([
            {
                "document_id": doc_id,
                "section_id": "sec1",
                "claims_json": [
                    {"statement": "Test", "claim_type": "definition", "confidence": 0.9},
                ],
                "entities_json": [],
                "relationships_json": [],
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(sources=sources, writer=mock_writer)

        rows = mock_writer.write.call_args[0][0]
        # batch_id should be set (defaults to "unknown" when workflow_id not passed through decorator)
        assert rows[0].batch_id is not None
        assert len(rows[0].batch_id) > 0

    def test_long_statement_truncated(self, mock_writer):
        """Test that long statements are truncated."""
        doc_id = str(uuid4())
        long_statement = "A" * 2000

        sources = self._create_sources([
            {
                "document_id": doc_id,
                "section_id": "sec1",
                "claims_json": [
                    {"statement": long_statement, "claim_type": "definition", "confidence": 0.9},
                ],
                "entities_json": [],
                "relationships_json": [],
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(sources=sources, writer=mock_writer, workflow_id="test")

        rows = mock_writer.write.call_args[0][0]
        assert len(rows[0].statement) == 1000  # Truncated to 1000 chars

    def test_json_string_parsing(self, mock_writer):
        """Test that JSON string fields are parsed correctly."""
        doc_id = str(uuid4())
        sources = self._create_sources([
            {
                "document_id": doc_id,
                "section_id": "sec1",
                "claims_json": json.dumps([
                    {"statement": "Test claim", "claim_type": "definition", "confidence": 0.9},
                ]),
                "entities_json": "[]",
                "relationships_json": "[]",
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_groups"}

        result = claim_clustering(sources=sources, writer=mock_writer, workflow_id="test")

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
        existing_claims = [
            {"claim_hash": "existing_hash", "statement": "Python is versatile"}
        ]
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
