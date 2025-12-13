"""End-to-end tests for claim extraction and resolution.

Tests that claims are correctly:
1. Extracted with entities
2. Linked to entities after resolution
3. Detect conflicts between claims
"""

import uuid
from unittest.mock import MagicMock, patch

from kurt.content.indexing.models import (
from kurt.db.models import ResolutionStatus
    ClaimExtraction,
    DocumentMetadataOutput,
    EntityExtraction,
    RelationshipExtraction,
)


class TestClaimsEndToEnd:
    """End-to-end tests for claim extraction through entity resolution."""

    @patch("kurt.content.document.load_document_content")
    @patch("kurt.db.database.get_session")
    @patch("dspy.ChainOfThought")
    def test_claims_extraction_with_entities(self, mock_chain, mock_get_session, mock_load_content):
        """Test that claims are extracted and correctly linked to entities."""
        from kurt.content.indexing.extract import extract_document_metadata
        from kurt.db.models import Document, IngestionStatus, SourceType

        # Setup mock session and document
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_doc = Document(
            id=uuid.uuid4(),
            title="PostgreSQL Documentation",
            source_type=SourceType.FILE_UPLOAD,
            source_url="test.md",
            ingestion_status=IngestionStatus.FETCHED,
            hash_content="test_hash",
        )
        mock_session.exec.return_value.all.return_value = [mock_doc]

        # Mock content loading
        mock_load_content.return_value = """
        # PostgreSQL Documentation

        PostgreSQL is a powerful database. It supports JSON since version 9.2.
        PostgreSQL can handle over 1 million transactions per second.
        """

        # Create mock DSPy result with claims
        mock_result = MagicMock()
        mock_result.metadata = DocumentMetadataOutput(
            content_type="reference",
            extracted_title="PostgreSQL Documentation",
            has_code_examples=False,
            has_step_by_step_procedures=False,
            has_narrative_structure=True,
        )

        # Entities that will be extracted
        mock_result.entities = [
            EntityExtraction(
                name="PostgreSQL",
                entity_type="Technology",
                description="Database system",
                aliases=["Postgres"],
                confidence=0.95,
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                quote="PostgreSQL is a powerful database",
            ),
            EntityExtraction(
                name="JSON",
                entity_type="Technology",
                description="Data format",
                aliases=[],
                confidence=0.9,
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                quote="supports JSON",
            ),
        ]

        # Claims referencing the entities by index
        mock_result.claims = [
            ClaimExtraction(
                statement="PostgreSQL supports JSON since version 9.2",
                claim_type="capability",
                entity_indices=[0, 1],  # PostgreSQL and JSON
                source_quote="supports JSON since version 9.2",
                quote_start_offset=50,
                quote_end_offset=82,
                confidence=0.9,
                version_info="9.2",
            ),
            ClaimExtraction(
                statement="PostgreSQL can handle over 1 million transactions per second",
                claim_type="performance",
                entity_indices=[0],  # Just PostgreSQL
                source_quote="handle over 1 million transactions per second",
                quote_start_offset=100,
                quote_end_offset=146,
                confidence=0.85,
            ),
        ]

        mock_result.relationships = [
            RelationshipExtraction(
                source_entity="PostgreSQL",
                target_entity="JSON",
                relationship_type="integrates_with",
                context="PostgreSQL supports JSON",
                confidence=0.9,
            )
        ]

        # Configure mock
        mock_instance = MagicMock()
        mock_instance.return_value = mock_result
        mock_chain.return_value = mock_instance

        # Run extraction - use partial UUID
        result = extract_document_metadata(str(mock_doc.id)[:8])

        # Verify claims were extracted
        assert "claims_data" in result
        claims = result["claims_data"]["extracted_claims"]
        assert len(claims) == 2

        # Verify first claim
        claim1 = claims[0]
        assert claim1["statement"] == "PostgreSQL supports JSON since version 9.2"
        assert claim1["claim_type"] == "capability"
        assert claim1["version_info"] == "9.2"

        # Verify second claim
        claim2 = claims[1]
        assert claim2["statement"] == "PostgreSQL can handle over 1 million transactions per second"
        assert claim2["claim_type"] == "performance"

        # Verify entities in kg_data
        assert "kg_data" in result
        assert len(result["kg_data"]["new_entities"]) == 2

    def test_claim_entity_resolution_mapping(self):
        """Test that claims maintain correct entity links after resolution."""
        from kurt.content.indexing.workflow_claim_resolution import map_claim_entities_step

        # Simulate claims data from extraction
        claims_data = {
            "extracted_claims": [
                {
                    "statement": "React works with TypeScript",
                    "claim_type": "compatibility",
                    "primary_entity": "React",
                    "referenced_entities": ["TypeScript"],
                    "source_quote": "React works with TypeScript",
                    "quote_start_offset": 0,
                    "quote_end_offset": 27,
                    "extraction_confidence": 0.9,
                }
            ]
        }

        # Simulate entity resolution results
        entity_resolution_results = {
            "created_entities": [
                {"name": "React", "id": str(uuid.uuid4())},
                {"name": "TypeScript", "id": str(uuid.uuid4())},
            ]
        }

        # Run mapping
        entity_map = map_claim_entities_step(claims_data, entity_resolution_results)

        # Verify mapping
        assert "React" in entity_map
        assert "TypeScript" in entity_map
        assert isinstance(entity_map["React"], uuid.UUID)
        assert isinstance(entity_map["TypeScript"], uuid.UUID)

    @patch("kurt.db.claim_operations.detect_conflicting_claims")
    @patch("kurt.db.claim_operations.create_claim")
    @patch("kurt.db.database.get_session")
    def test_claim_conflict_detection(
        self, mock_get_session, mock_create_claim, mock_detect_conflicts
    ):
        """Test that conflicting claims are detected."""
        from kurt.content.indexing.workflow_claim_resolution import (
            create_claims_step,
            detect_conflicts_step,
        )

        # Setup mock session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Setup entity map
        entity_id = uuid.uuid4()
        entity_map = {"PostgreSQL": entity_id}

        # Create two conflicting claims
        claims_to_process = [
            {
                "statement": "PostgreSQL supports JSON",
                "claim_type": "capability",
                "primary_entity_id": entity_id,
                "source_quote": "supports JSON",
                "quote_start_offset": 0,
                "quote_end_offset": 13,
                "extraction_confidence": 0.9,
            }
        ]

        # Mock claim creation
        mock_claim = MagicMock()
        mock_claim.id = uuid.uuid4()
        mock_claim.statement = "PostgreSQL supports JSON"
        mock_claim.claim_type = "capability"
        mock_claim.subject_entity_id = entity_id
        mock_create_claim.return_value = mock_claim

        # Create claims
        document_id = str(uuid.uuid4())
        created_claims = create_claims_step(document_id, claims_to_process, entity_map)

        assert len(created_claims) == 1
        assert created_claims[0]["statement"] == "PostgreSQL supports JSON"

        # Now test conflict detection
        mock_session.query().filter().first.return_value = mock_claim

        # Mock a conflicting claim
        conflicting_claim = MagicMock()
        conflicting_claim.id = uuid.uuid4()
        conflicting_claim.statement = "PostgreSQL does not support JSON"
        conflicting_claim.claim_type = "limitation"

        mock_detect_conflicts.return_value = [(conflicting_claim, "contradictory", 0.95)]

        # Detect conflicts
        detect_conflicts_step(created_claims)

        # Verify conflict detected
        mock_detect_conflicts.assert_called_once()
        # Note: The actual conflict creation is mocked, but in real scenario
        # it would create the conflict relationship

    def test_claims_survive_entity_merging(self):
        """Test that claims correctly update when entities are merged."""
        # This would test that when entities are merged during resolution,
        # the claims pointing to those entities are updated correctly
        # This is handled by the entity resolution workflow maintaining
        # a mapping of entity names to final IDs

        from kurt.content.indexing.workflow_claim_resolution import map_claim_entities_step

        # Simulate entity merging scenario
        claims_data = {
            "extracted_claims": [
                {
                    "statement": "Postgres is fast",
                    "claim_type": "performance",
                    "primary_entity": "Postgres",  # Alias
                    "referenced_entities": [],
                    "source_quote": "Postgres is fast",
                    "quote_start_offset": 0,
                    "quote_end_offset": 16,
                    "extraction_confidence": 0.8,
                }
            ]
        }

        # After resolution, Postgres merged into PostgreSQL
        entity_resolution_results = {
            "existing_entities": [{"name": "PostgreSQL", "id": str(uuid.uuid4())}],
            "linked_entity_names": ["Postgres"],  # Postgres was linked to PostgreSQL
        }

        # Mock the database lookup for linked entity
        with patch("kurt.db.database.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            # Mock entity lookup
            mock_entity = MagicMock()
            mock_entity.id = uuid.uuid4()
            mock_entity.name = "PostgreSQL"
            mock_session.query().filter().first.return_value = mock_entity

            # Run mapping
            entity_map = map_claim_entities_step(claims_data, entity_resolution_results)

            # Verify Postgres maps to the PostgreSQL entity ID
            assert "Postgres" in entity_map
            assert entity_map["Postgres"] == mock_entity.id

    @patch("kurt.db.claim_operations.detect_duplicate_claims")
    @patch("kurt.db.database.get_session")
    def test_duplicate_claim_detection(self, mock_get_session, mock_detect_duplicates):
        """Test that duplicate claims are detected and skipped."""
        from kurt.content.indexing.workflow_claim_resolution import detect_duplicates_step

        # Setup mock session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Setup entity map
        entity_id = uuid.uuid4()

        # Claims data with potential duplicate
        claims_data = {
            "extracted_claims": [
                {
                    "statement": "PostgreSQL is ACID compliant",
                    "primary_entity": "PostgreSQL",
                    "referenced_entities": [],
                    "source_quote": "ACID compliant",
                    "quote_start_offset": 0,
                    "quote_end_offset": 14,
                    "extraction_confidence": 0.9,
                }
            ]
        }

        entity_map = {"PostgreSQL": entity_id}

        # Mock existing duplicate claim
        existing_claim = MagicMock()
        existing_claim.id = uuid.uuid4()
        existing_claim.statement = "PostgreSQL is ACID-compliant"  # Similar statement
        mock_detect_duplicates.return_value = [existing_claim]

        # Run duplicate detection
        claims_to_process, duplicates = detect_duplicates_step(claims_data, entity_map)

        # Verify duplicate was detected
        assert len(duplicates) == 1
        assert len(claims_to_process) == 0  # Claim was skipped as duplicate
        assert duplicates[0]["new_claim"] == "PostgreSQL is ACID compliant"

    @patch("kurt.db.claim_operations.update_claim_confidence")
    @patch("kurt.db.database.get_session")
    def test_confidence_score_update(self, mock_get_session, mock_update_confidence):
        """Test that confidence scores are updated based on corroboration."""
        from kurt.content.indexing.workflow_claim_resolution import update_confidence_scores_step

        # Setup mock session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        claim_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        # Created claims
        created_claims = [
            {
                "id": str(claim_id),
                "statement": "PostgreSQL supports replication",
                "claim_type": "capability",
                "subject_entity_id": str(entity_id),
            }
        ]

        # Mock the claim lookup
        mock_claim = MagicMock()
        mock_claim.id = claim_id
        mock_claim.subject_entity_id = entity_id
        mock_claim.claim_type = "capability"
        mock_session.query().filter().first.return_value = mock_claim

        # Mock supporting claims (corroboration)
        supporting_claim1 = MagicMock()
        supporting_claim1.statement = "PostgreSQL has master-slave replication"
        supporting_claim2 = MagicMock()
        supporting_claim2.statement = "PostgreSQL supports streaming replication"

        mock_session.query().filter().all.return_value = [supporting_claim1, supporting_claim2]

        # Run confidence update
        updated_count = update_confidence_scores_step(created_claims)

        # Verify confidence was updated
        assert updated_count == 1
        mock_update_confidence.assert_called_once_with(
            mock_session, claim_id, 2
        )  # 2 supporting claims

    def test_temporal_and_version_qualifiers(self):
        """Test that temporal and version qualifiers are preserved through the pipeline."""
        from kurt.content.indexing.workflow_claim_resolution import create_claims_step

        with (
            patch("kurt.db.database.get_session") as mock_get_session,
            patch("kurt.db.claim_operations.create_claim") as mock_create_claim,
        ):
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            entity_id = uuid.uuid4()

            # Claims with temporal and version info
            claims_to_process = [
                {
                    "statement": "PostgreSQL added JSON support",
                    "claim_type": "feature",
                    "primary_entity_id": entity_id,
                    "source_quote": "added JSON support in version 9.2",
                    "quote_start_offset": 0,
                    "quote_end_offset": 34,
                    "extraction_confidence": 0.95,
                    "temporal_qualifier": "since 2012",
                    "version_info": "9.2",
                    "source_context": "PostgreSQL added JSON support in version 9.2, released in 2012",
                }
            ]

            entity_map = {"PostgreSQL": entity_id}
            document_id = str(uuid.uuid4())

            # Mock claim creation
            mock_claim = MagicMock()
            mock_claim.id = uuid.uuid4()
            mock_claim.statement = claims_to_process[0]["statement"]
            mock_claim.claim_type = claims_to_process[0]["claim_type"]
            mock_claim.subject_entity_id = entity_id
            mock_create_claim.return_value = mock_claim

            # Create claims
            create_claims_step(document_id, claims_to_process, entity_map)

            # Verify temporal and version info was passed
            mock_create_claim.assert_called_once()
            call_args = mock_create_claim.call_args[1]
            assert call_args["temporal_qualifier"] == "since 2012"
            assert call_args["version_info"] == "9.2"
            assert (
                call_args["source_context"]
                == "PostgreSQL added JSON support in version 9.2, released in 2012"
            )

    def test_claim_types_preservation(self):
        """Test that different claim types are correctly preserved."""
        claim_types = [
            "capability",
            "limitation",
            "requirement",
            "compatibility",
            "performance",
            "statistic",
            "feature",
            "other",
        ]

        for claim_type in claim_types:
            claim = ClaimExtraction(
                statement=f"Test {claim_type} claim",
                claim_type=claim_type,
                entity_indices=[0],
                source_quote=f"test {claim_type}",
                quote_start_offset=0,
                quote_end_offset=10,
                confidence=0.8,
            )
            assert claim.claim_type == claim_type
