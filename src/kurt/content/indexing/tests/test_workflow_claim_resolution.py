"""Tests for claim resolution workflow.

Tests the claim resolution process including entity mapping, duplicate detection,
conflict detection, and confidence scoring.
"""

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from kurt.content.indexing.workflow_claim_resolution import (
    create_claims_step,
    detect_conflicts_step,
    detect_duplicates_step,
    map_claim_entities_step,
    update_confidence_scores_step,
)
from kurt.db.claim_models import Claim, ClaimEntity, ClaimType
from kurt.db.database import get_session
from kurt.db.models import Document, Entity, IngestionStatus, SourceType


@pytest.fixture
def db_session(tmp_project):
    """Provide a database session for tests."""
    session = get_session()
    yield session
    session.close()


@pytest.fixture
def test_document(db_session):
    """Create a test document."""
    doc = Document(
        id=uuid.uuid4(),
        title="Test Document",
        source_type=SourceType.URL,
        source_url="https://example.com/test",
        ingestion_status=IngestionStatus.FETCHED,
    )
    db_session.add(doc)
    db_session.commit()
    return doc


@pytest.fixture
def test_entities(db_session):
    """Create test entities."""
    entities = [
        Entity(
            id=uuid.uuid4(),
            name="PostgreSQL",
            entity_type="Database",
            embedding=b"",
        ),
        Entity(
            id=uuid.uuid4(),
            name="Python",
            entity_type="Language",
            embedding=b"",
        ),
        Entity(
            id=uuid.uuid4(),
            name="Docker",
            entity_type="Platform",
            embedding=b"",
        ),
    ]
    db_session.add_all(entities)
    db_session.commit()
    return entities


@pytest.fixture
def entity_resolution_results(test_entities):
    """Mock entity resolution results."""
    return {
        "existing_entities": [
            {"id": str(test_entities[0].id), "name": "PostgreSQL"},
            {"id": str(test_entities[1].id), "name": "Python"},
            {"id": str(test_entities[2].id), "name": "Docker"},
        ],
        "created_entities": [],
        "linked_entity_names": [],
    }


@pytest.fixture
def claims_data():
    """Test claims data."""
    return {
        "extracted_claims": [
            {
                "statement": "PostgreSQL is a powerful database",
                "claim_type": "capability",
                "primary_entity": "PostgreSQL",
                "referenced_entities": ["Python"],
                "source_quote": "PostgreSQL is a powerful database",
                "quote_start_offset": 0,
                "quote_end_offset": 35,
                "extraction_confidence": 0.9,
            },
            {
                "statement": "Docker is required for deployment",
                "claim_type": "requirement",
                "primary_entity": "Docker",
                "referenced_entities": [],
                "source_quote": "Docker is required for deployment",
                "quote_start_offset": 40,
                "quote_end_offset": 75,
                "extraction_confidence": 0.85,
            },
            {
                "statement": "Python integrates well with databases",
                "claim_type": "integration",
                "primary_entity": "Python",
                "referenced_entities": ["PostgreSQL"],
                "source_quote": "Python integrates well with databases",
                "quote_start_offset": 80,
                "quote_end_offset": 118,
                "extraction_confidence": 0.8,
            },
        ]
    }


@pytest.fixture
def test_embeddings():
    """Load test embeddings from JSON."""
    embeddings_file = Path(__file__).parent / "test_embeddings.json"
    with open(embeddings_file, "r") as f:
        return json.load(f)


class TestClaimResolutionSteps:
    """Test individual claim resolution workflow steps."""

    def test_map_claim_entities(self, claims_data, entity_resolution_results):
        """Test mapping claim entities to resolved entity IDs."""
        entity_map = map_claim_entities_step(claims_data, entity_resolution_results)

        # Should have all three entities mapped
        assert len(entity_map) == 3
        assert "PostgreSQL" in entity_map
        assert "Python" in entity_map
        assert "Docker" in entity_map

        # All should be UUIDs
        for entity_name, entity_id in entity_map.items():
            assert isinstance(entity_id, uuid.UUID)

    def test_detect_duplicates(
        self, db_session, test_entities, test_document, claims_data, test_embeddings
    ):
        """Test duplicate claim detection."""
        # Create an existing claim with real embedding
        embedding_python = np.array(
            test_embeddings["embeddings"]["Product supports Python"], dtype=np.float32
        )

        existing_claim = Claim(
            statement="PostgreSQL supports Python",
            claim_type=ClaimType.CAPABILITY,
            subject_entity_id=test_entities[0].id,  # PostgreSQL
            source_document_id=test_document.id,
            source_quote="PostgreSQL supports Python",
            source_location_start=0,
            source_location_end=27,
            embedding=embedding_python.tobytes(),
        )
        db_session.add(existing_claim)
        db_session.commit()

        # Create entity map
        entity_name_to_id_map = {
            "PostgreSQL": test_entities[0].id,
            "Python": test_entities[1].id,
            "Docker": test_entities[2].id,
        }

        # Add a duplicate claim to claims_data
        duplicate_claims_data = {
            "extracted_claims": [
                {
                    "statement": "PostgreSQL supports Python",  # Duplicate
                    "claim_type": "capability",
                    "primary_entity": "PostgreSQL",
                    "referenced_entities": ["Python"],
                    "source_quote": "PostgreSQL supports Python",
                    "quote_start_offset": 200,
                    "quote_end_offset": 227,
                    "extraction_confidence": 0.9,
                },
                {
                    "statement": "Docker is a container platform",  # New claim
                    "claim_type": "feature",
                    "primary_entity": "Docker",
                    "referenced_entities": [],
                    "source_quote": "Docker is a container platform",
                    "quote_start_offset": 300,
                    "quote_end_offset": 331,
                    "extraction_confidence": 0.85,
                },
            ]
        }

        # Mock embeddings
        with patch("kurt.db.claim_operations.get_embeddings") as mock_embeddings:
            # Return similar embedding for duplicate
            mock_embeddings.side_effect = [
                [test_embeddings["embeddings"]["Product supports Python"]],
                [[0.2] * 1536],  # Different embedding for Docker claim
            ]

            claims_to_process, duplicates = detect_duplicates_step(
                duplicate_claims_data, entity_name_to_id_map
            )

            # Should detect 1 duplicate
            assert len(duplicates) == 1
            assert len(claims_to_process) == 1
            assert claims_to_process[0]["statement"] == "Docker is a container platform"

    def test_create_claims(self, db_session, test_document, test_entities, claims_data):
        """Test creating claim records."""
        entity_name_to_id_map = {
            "PostgreSQL": test_entities[0].id,
            "Python": test_entities[1].id,
            "Docker": test_entities[2].id,
        }

        # Add resolved IDs to claims
        for claim in claims_data["extracted_claims"]:
            claim["primary_entity_id"] = entity_name_to_id_map[claim["primary_entity"]]

        with patch("kurt.db.claim_operations.get_embeddings") as mock_embeddings:
            # Return embeddings for each claim
            mock_embeddings.side_effect = [
                [[0.1] * 1536],
                [[0.2] * 1536],
                [[0.3] * 1536],
            ]

            created_claims = create_claims_step(
                str(test_document.id),
                claims_data["extracted_claims"],
                entity_name_to_id_map,
                "test_commit",
            )

            assert len(created_claims) == 3

            # Verify claims were created in database
            claims_in_db = db_session.query(Claim).all()
            assert len(claims_in_db) == 3

            # Verify entity links
            entity_links = db_session.query(ClaimEntity).all()
            assert len(entity_links) >= 2  # At least Python and PostgreSQL references


class TestConflictDetection:
    """Test conflict detection step."""

    def test_detect_conflicts_capability_vs_limitation(
        self, db_session, test_entities, test_document
    ):
        """Test detecting conflicts between capability and limitation claims."""
        # Create conflicting claims
        claim1 = Claim(
            id=uuid.uuid4(),
            statement="PostgreSQL supports real-time replication",
            claim_type=ClaimType.CAPABILITY,
            subject_entity_id=test_entities[0].id,
            source_document_id=test_document.id,
            source_quote="supports real-time replication",
            source_location_start=0,
            source_location_end=31,
            embedding=b"",
        )

        claim2 = Claim(
            id=uuid.uuid4(),
            statement="PostgreSQL cannot support real-time replication",
            claim_type=ClaimType.LIMITATION,
            subject_entity_id=test_entities[0].id,
            source_document_id=test_document.id,
            source_quote="cannot support real-time replication",
            source_location_start=100,
            source_location_end=137,
            embedding=b"",
        )

        db_session.add_all([claim1, claim2])
        db_session.commit()

        created_claims = [
            {
                "id": str(claim2.id),
            }
        ]

        conflicts = detect_conflicts_step(created_claims)

        # Should detect conflict due to word overlap (real-time, replication)
        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "contradictory"
        assert conflicts[0]["confidence"] == 0.75  # Word overlap confidence

    def test_detect_version_conflicts(self, db_session, test_entities, test_document):
        """Test detecting version-based conflicts."""
        claim1 = Claim(
            id=uuid.uuid4(),
            statement="PostgreSQL supports JSON",
            claim_type=ClaimType.CAPABILITY,
            subject_entity_id=test_entities[0].id,
            source_document_id=test_document.id,
            source_quote="supports JSON",
            source_location_start=0,
            source_location_end=13,
            version_info="v9.2",
            embedding=b"",
        )

        db_session.add(claim1)
        db_session.commit()

        # Create new claim with different version
        claim2 = Claim(
            id=uuid.uuid4(),
            statement="PostgreSQL supports JSON",
            claim_type=ClaimType.CAPABILITY,
            subject_entity_id=test_entities[0].id,
            source_document_id=test_document.id,
            source_quote="supports JSON",
            source_location_start=100,
            source_location_end=113,
            version_info="v14",
            embedding=b"",
        )
        db_session.add(claim2)
        db_session.commit()

        created_claims = [
            {
                "id": str(claim2.id),
            }
        ]

        conflicts = detect_conflicts_step(created_claims)

        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "version_difference"
        assert conflicts[0]["confidence"] == 0.8


class TestConfidenceScoring:
    """Test confidence score updates."""

    def test_update_confidence_with_corroboration(self, db_session, test_entities, test_document):
        """Test updating confidence scores based on corroborating claims."""
        # Create multiple claims about same entity with same type
        claims = []
        for i in range(3):
            claim = Claim(
                id=uuid.uuid4(),
                statement=f"PostgreSQL is highly scalable (claim {i})",
                claim_type=ClaimType.PERFORMANCE,
                subject_entity_id=test_entities[0].id,
                source_document_id=test_document.id,
                source_quote=f"highly scalable {i}",
                source_location_start=i * 100,
                source_location_end=i * 100 + 20,
                extraction_confidence=0.8,
                source_authority=0.7,
                corroboration_score=0.0,
                overall_confidence=0.56,  # Initial: 0.8 * 0.7
                embedding=b"",
            )
            claims.append(claim)

        db_session.add_all(claims)
        db_session.commit()

        created_claims = [
            {
                "id": str(claim.id),
            }
            for claim in claims
        ]

        updated_count = update_confidence_scores_step(created_claims)

        # Each claim should have 2 corroborating claims
        assert updated_count == 3

        # Verify confidence scores were updated
        # Refresh the session to get the updated values
        db_session.expire_all()

        for claim_info in created_claims:
            claim = db_session.query(Claim).filter(Claim.id == uuid.UUID(claim_info["id"])).first()
            assert claim.corroboration_score > 0
            # With 2 corroborating claims: min(1.0, log(1+2) / 3.0) ≈ 0.366
            assert 0.3 < claim.corroboration_score < 0.4
            # Overall confidence: 0.8 * 0.4 + 0.7 * 0.3 + 0.366 * 0.3 ≈ 0.64
            # Expect it to be around 0.64 (higher than initial 0.56)
            assert 0.6 < claim.overall_confidence < 0.7


class TestClaimResolutionWorkflow:
    """Test the complete claim resolution workflow."""

    def test_complete_workflow_integration(
        self,
        tmp_project,
        reset_dbos_state,
        db_session,
        test_entities,
        test_document,
        entity_resolution_results,
        claims_data,
        test_embeddings,
    ):
        """Test the complete claim resolution workflow end-to-end."""
        from unittest.mock import patch

        import numpy as np
        from dbos import DBOS

        from kurt.db.claim_models import Claim, ClaimType
        from kurt.workflows import init_dbos

        # Initialize and launch DBOS
        init_dbos()
        DBOS.launch()

        try:
            # Create some existing claims for duplicate/conflict detection
            embedding_python = np.array(
                test_embeddings["embeddings"]["Product supports Python"], dtype=np.float32
            )

            existing_claim = Claim(
                statement="PostgreSQL supports Python",
                claim_type=ClaimType.CAPABILITY,
                subject_entity_id=test_entities[0].id,
                source_document_id=test_document.id,
                source_quote="PostgreSQL supports Python",
                source_location_start=0,
                source_location_end=27,
                embedding=embedding_python.tobytes(),
            )
            db_session.add(existing_claim)
            db_session.commit()

            # Mock embeddings for new claims
            with patch("kurt.db.claim_operations.get_embeddings") as mock_embeddings:
                # Return different embeddings for each claim
                mock_embeddings.side_effect = [
                    [test_embeddings["embeddings"]["Product supports Python"]],
                    [test_embeddings["embeddings"]["Product requires Docker"]],
                    [[0.1] * 1536],  # Generic embedding for third claim
                ]

                # Call the workflow synchronously (DBOS handles the async part)
                from kurt.content.indexing.workflow_claim_resolution import (
                    claim_resolution_workflow,
                )

                result = claim_resolution_workflow(
                    str(test_document.id),
                    claims_data,
                    entity_resolution_results,
                    git_commit="test_commit",
                )

                # Verify the workflow result structure
                assert "claims_processed" in result
                assert "duplicates_skipped" in result
                assert "conflicts_detected" in result
                assert "confidence_updated" in result

                # Should process 2 claims (1 duplicate skipped)
                assert result["claims_processed"] == 2
                assert result["duplicates_skipped"] == 1

                # Verify claims were created in database
                all_claims = db_session.query(Claim).all()
                assert len(all_claims) >= 3  # Existing + 2 new claims

                # Verify entity links were created
                claim_entities = db_session.query(ClaimEntity).all()
                assert len(claim_entities) > 0

        finally:
            DBOS.destroy()


class TestErrorHandling:
    """Test error handling in workflow steps."""

    @patch("kurt.content.indexing.workflow_claim_resolution.create_claim")
    def test_create_claims_handles_errors(self, mock_create_claim, db_session, test_document):
        """Test error handling in create_claims_step."""
        # Mock create_claim to raise an error
        mock_create_claim.side_effect = Exception("Database error")

        entity_name_to_id_map = {
            "TestEntity": uuid.uuid4(),
        }

        claims_to_process = [
            {
                "statement": "Test claim",
                "claim_type": "capability",
                "primary_entity": "TestEntity",
                "primary_entity_id": entity_name_to_id_map["TestEntity"],
                "referenced_entities": [],
                "source_quote": "Test quote",
                "quote_start_offset": 0,
                "quote_end_offset": 10,
                "extraction_confidence": 0.9,
            }
        ]

        # Should raise the exception
        with pytest.raises(Exception, match="Database error"):
            create_claims_step(
                str(test_document.id), claims_to_process, entity_name_to_id_map, "test_commit"
            )
