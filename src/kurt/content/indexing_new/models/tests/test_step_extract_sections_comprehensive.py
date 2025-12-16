"""Comprehensive tests for the step_extract_sections model."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch
import pandas as pd

import dspy
import pytest

from kurt.content.indexing_new.models.step_extract_sections import (
    SectionExtractionRow,
    section_extractions,
    ClaimExtraction,
    DocumentMetadataOutput,
    EntityExtraction,
    RelationshipExtraction,
    IndexDocument,
)
from kurt.content.indexing_new.framework.dspy_helpers import DSPyResult
from kurt.db.models import ContentType, EntityType, RelationshipType


class TestPydanticModels:
    """Test the Pydantic models used in extraction."""

    def test_claim_extraction_model(self):
        """Test ClaimExtraction model validation."""
        claim = ClaimExtraction(
            statement="Python is a high-level programming language",
            claim_type="factual",
            entity_indices=[0, 1],
            source_quote="Python is a high-level programming language",
            quote_start_offset=100,
            quote_end_offset=145,
            confidence=0.95
        )

        assert claim.statement == "Python is a high-level programming language"
        assert claim.confidence == 0.95
        assert len(claim.entity_indices) == 2

    def test_entity_extraction_model(self):
        """Test EntityExtraction model validation."""
        entity = EntityExtraction(
            name="Python",
            entity_type=EntityType.TECHNOLOGY,
            description="A high-level programming language",
            aliases=["Python3", "CPython"],
            confidence=0.9,
            resolution_status="NEW",
            quote="Python is widely used"
        )

        assert entity.name == "Python"
        assert entity.entity_type == EntityType.TECHNOLOGY
        assert len(entity.aliases) == 2
        assert entity.resolution_status == "NEW"

    def test_relationship_extraction_model(self):
        """Test RelationshipExtraction model validation."""
        rel = RelationshipExtraction(
            source_entity="Python",
            target_entity="Machine Learning",
            relationship_type=RelationshipType.USES,
            context="Python is commonly used for machine learning",
            confidence=0.85
        )

        assert rel.source_entity == "Python"
        assert rel.relationship_type == RelationshipType.USES
        assert rel.confidence == 0.85

    def test_document_metadata_output_model(self):
        """Test DocumentMetadataOutput model validation."""
        metadata = DocumentMetadataOutput(
            content_type=ContentType.TUTORIAL,
            has_code_examples=True,
            has_step_by_step_procedures=False,
            has_narrative_structure=True
        )

        assert metadata.content_type == ContentType.TUTORIAL
        assert metadata.has_code_examples is True


class TestDSPySignature:
    """Test the IndexDocument DSPy signature."""

    def test_index_document_signature_fields(self):
        """Test that IndexDocument has the correct input/output fields."""
        # DSPy signatures store fields differently, let's check the signature is a proper DSPy Signature
        assert issubclass(IndexDocument, dspy.Signature)

        # Check the docstring exists and contains expected content
        assert "Index a document" in IndexDocument.__doc__
        assert "entities" in IndexDocument.__doc__
        assert "relationships" in IndexDocument.__doc__
        assert "claims" in IndexDocument.__doc__


class TestSectionExtractionsWithOverlap:
    """Test extraction with overlapping sections."""

    @patch("kurt.config.load_config")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    @patch("kurt.content.indexing_new.models.step_extract_sections._load_existing_entities")
    def test_extraction_with_overlap_sections(self, mock_load_entities, mock_run_batch, mock_load_config):
        """Test extraction from sections with overlap prefix/suffix."""

        # Mock existing entities
        mock_load_entities.return_value = [
            {"id": "entity1", "name": "Django", "type": "Technology", "description": "Web framework"}
        ]

        # Create mock extraction results
        mock_result = MagicMock()
        mock_result.metadata = DocumentMetadataOutput(
            content_type=ContentType.REFERENCE,
            has_code_examples=True
        )
        mock_result.entities = [
            EntityExtraction(
                name="FastAPI",
                entity_type=EntityType.TECHNOLOGY,
                description="Modern web API framework",
                confidence=0.95,
                resolution_status="NEW"
            )
        ]
        mock_result.relationships = []
        mock_result.claims = []

        mock_run_batch.return_value = [
            DSPyResult(
                payload={},
                result=mock_result,
                error=None,
                telemetry={
                    "tokens_prompt": 500,
                    "tokens_completion": 300,
                    "model_name": "claude-3",
                    "execution_time": 1.5
                }
            )
        ]

        # Create sources dict with sections DataFrame
        sections_df = pd.DataFrame([
            {
                "document_id": "doc789",
                "section_id": "sec789",
                "section_number": 2,
                "section_heading": "API Development",
                "content": "Main section content about FastAPI",
                "overlap_prefix": "prefix from previous section",
                "overlap_suffix": "suffix for next section",
            }
        ])
        sources = {"sections": sections_df}

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = section_extractions(
            sources=sources,
            writer=mock_writer,
        )

        # Verify the content was properly assembled with overlaps
        mock_run_batch.assert_called_once()
        call_args = mock_run_batch.call_args[1]
        items = call_args["items"]
        assert len(items) == 1

        # Check that overlap was included in content
        item = items[0]
        assert "[...prefix from previous section]" in item["document_content"]
        assert "[suffix for next section...]" in item["document_content"]
        assert "Main section content about FastAPI" in item["document_content"]


class TestBatchProcessing:
    """Test batch processing of multiple sections."""

    @patch("kurt.config.load_config")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    @patch("kurt.content.indexing_new.models.step_extract_sections._load_existing_entities")
    def test_multiple_sections_batch(self, mock_load_entities, mock_run_batch, mock_load_config):
        """Test processing multiple sections in batch."""

        # Mock existing entities - empty list
        mock_load_entities.return_value = []

        # Create multiple mock results
        results = []
        for i in range(3):
            mock_result = MagicMock()
            mock_result.metadata = {"content_type": "guide"}
            mock_result.entities = [{"name": f"Entity{i}", "entity_type": "Product"}]
            mock_result.relationships = []
            mock_result.claims = [{"statement": f"Claim {i}"}]

            results.append(DSPyResult(
                payload={},
                result=mock_result,
                error=None,
                telemetry={
                    "tokens_prompt": 100 + i*10,
                    "tokens_completion": 200 + i*10,
                    "model_name": "gpt-4",
                    "execution_time": 1.0 + i*0.5
                }
            ))

        mock_run_batch.return_value = results

        # Create sources dict with sections DataFrame
        sections_df = pd.DataFrame([
            {
                "document_id": f"doc{i}",
                "section_id": f"sec{i}",
                "section_number": i+1,
                "content": f"Content {i}"
            }
            for i in range(3)
        ])
        sources = {"sections": sections_df}

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 3}

        result = section_extractions(
            sources=sources,
            writer=mock_writer,
        )

        # Verify batch processing
        assert result["rows_written"] == 3
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3

        # Verify each row has correct data
        for i, row in enumerate(rows):
            assert row.document_id == f"doc{i}"
            assert row.section_id == f"sec{i}"
            assert row.tokens_prompt == 100 + i*10
            assert row.extraction_time_ms == int((1.0 + i*0.5) * 1000)


class TestExistingEntitiesHandling:
    """Test handling of existing entities context."""

    @patch("kurt.config.load_config")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    @patch("kurt.content.indexing_new.models.step_extract_sections._load_existing_entities")
    def test_existing_entities_passed_to_dspy(self, mock_load_entities, mock_run_batch, mock_load_config):
        """Test that existing entities are properly formatted and passed."""

        # Mock existing entities
        mock_load_entities.return_value = [
            {"id": "1", "name": "Django", "type": "Technology", "description": "Web framework"},
            {"id": "2", "name": "Flask", "type": "Technology", "description": "Micro framework"},
        ]

        mock_run_batch.return_value = [
            DSPyResult(
                payload={},
                result=MagicMock(
                    metadata={"content_type": "tutorial"},
                    entities=[],
                    relationships=[],
                    claims=[]
                ),
                error=None,
                telemetry={}
            )
        ]

        # Create sources dict with sections DataFrame
        sections_df = pd.DataFrame([
            {"document_id": "doc1", "section_id": "sec1", "section_number": 1, "content": "Test"}
        ])
        sources = {"sections": sections_df}

        section_extractions(
            sources=sources,
            writer=MagicMock(write=MagicMock(return_value={"rows_written": 1})),
        )

        # Verify existing entities were passed to DSPy
        call_args = mock_run_batch.call_args[1]
        items = call_args["items"]
        entities_json = items[0]["existing_entities"]
        entities = json.loads(entities_json)

        assert len(entities) == 2
        assert entities[0]["name"] == "Django"
        assert entities[1]["name"] == "Flask"


class TestErrorHandlingScenarios:
    """Test various error handling scenarios."""

    @patch("kurt.config.load_config")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    @patch("kurt.content.indexing_new.models.step_extract_sections._load_existing_entities")
    def test_mixed_success_and_error(self, mock_load_entities, mock_run_batch, mock_load_config):
        """Test handling mix of successful and failed extractions."""

        # Mock existing entities - empty list
        mock_load_entities.return_value = []

        mock_run_batch.return_value = [
            # Success
            DSPyResult(
                payload={},
                result=MagicMock(
                    metadata={"content_type": "guide"},
                    entities=[],
                    relationships=[],
                    claims=[]
                ),
                error=None,
                telemetry={"execution_time": 1.0}
            ),
            # Error
            DSPyResult(
                payload={},
                result=None,
                error=Exception("API rate limit"),
                telemetry={"error": "API rate limit"}
            ),
            # Success
            DSPyResult(
                payload={},
                result=MagicMock(
                    metadata={"content_type": "tutorial"},
                    entities=[],
                    relationships=[],
                    claims=[]
                ),
                error=None,
                telemetry={"execution_time": 2.0}
            )
        ]

        # Create sources dict with sections DataFrame
        sections_df = pd.DataFrame([
            {"document_id": f"doc{i}", "section_id": f"sec{i}", "section_number": i+1, "content": f"Content {i}"}
            for i in range(3)
        ])
        sources = {"sections": sections_df}

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 3}

        result = section_extractions(
            sources=sources,
            writer=mock_writer,
        )

        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3

        # First row should be success
        assert rows[0].error is None
        assert rows[0].metadata_json is not None

        # Second row should have error
        assert rows[1].error == "API rate limit"
        assert rows[1].metadata_json is None

        # Third row should be success
        assert rows[2].error is None
        assert rows[2].metadata_json is not None

    @patch("kurt.config.load_config")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    @patch("kurt.content.indexing_new.models.step_extract_sections._load_existing_entities")
    def test_exception_during_processing(self, mock_load_entities, mock_run_batch, mock_load_config):
        """Test handling of exceptions during result processing."""

        # Mock existing entities - empty list
        mock_load_entities.return_value = []

        # Create a result that will cause an exception during parsing
        mock_result = MagicMock()
        # Make metadata return something that will cause issues
        mock_result.metadata = MagicMock(side_effect=AttributeError("No attribute"))
        mock_result.entities = "invalid_not_a_list"
        mock_result.relationships = MagicMock()
        mock_result.claims = MagicMock()

        mock_run_batch.return_value = [
            DSPyResult(
                payload={},
                result=mock_result,
                error=None,
                telemetry={}
            )
        ]

        # Create sources dict with sections DataFrame
        sections_df = pd.DataFrame([
            {"document_id": "doc1", "section_id": "sec1", "section_number": 1, "content": "Test"}
        ])
        sources = {"sections": sections_df}

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = section_extractions(
            sources=sources,
            writer=mock_writer,
        )

        # Should still write a row, handling errors gracefully
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        # The entity parsing error is handled gracefully, entities field will be empty list
        assert rows[0].entities_json == []


class TestTelemetryAndMetadata:
    """Test telemetry data and metadata handling."""

    @patch("kurt.config.load_config")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    @patch("kurt.content.indexing_new.models.step_extract_sections._load_existing_entities")
    def test_telemetry_data_extraction(self, mock_load_entities, mock_run_batch, mock_load_config):
        """Test that telemetry data is properly extracted and stored."""

        # Mock existing entities - empty list
        mock_load_entities.return_value = []

        mock_run_batch.return_value = [
            DSPyResult(
                payload={},
                result=MagicMock(
                    metadata={"content_type": "guide"},
                    entities=[],
                    relationships=[],
                    claims=[]
                ),
                error=None,
                telemetry={
                    "tokens_prompt": 1234,
                    "tokens_completion": 567,
                    "model_name": "claude-3-sonnet",
                    "execution_time": 3.456
                }
            )
        ]

        # Create sources dict with sections DataFrame
        sections_df = pd.DataFrame([
            {"document_id": "doc1", "section_id": "sec1", "section_number": 1, "content": "Test"}
        ])
        sources = {"sections": sections_df}

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        section_extractions(
            sources=sources,
            writer=mock_writer,
        )

        rows = mock_writer.write.call_args[0][0]
        row = rows[0]

        # Verify telemetry data
        assert row.tokens_prompt == 1234
        assert row.tokens_completion == 567
        assert row.llm_model_name == "claude-3-sonnet"
        assert row.extraction_time_ms == 3456  # 3.456 * 1000

    def test_schema_has_metadata_fields(self):
        """Test that SectionExtractionRow has required metadata fields."""
        row = SectionExtractionRow(
            document_id="doc1",
            section_id="sec1",
            section_number=1,
            workflow_id="wf123"
        )

        # Verify metadata fields exist
        assert hasattr(row, 'workflow_id')
        assert hasattr(row, 'created_at')
        assert hasattr(row, 'updated_at')

        # Verify datetime fields have default values
        assert isinstance(row.created_at, datetime)
        assert isinstance(row.updated_at, datetime)


class TestEmptyPayloads:
    """Test handling of empty or missing data."""

    def test_empty_sections_in_sources(self):
        """Test that empty sections DataFrame is handled gracefully."""
        # Create sources dict with empty DataFrame
        sources = {"sections": pd.DataFrame()}

        result = section_extractions(
            sources=sources,
            writer=MagicMock(),
        )

        assert result["rows_written"] == 0

    @patch("kurt.config.load_config")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    @patch("kurt.content.indexing_new.models.step_extract_sections._load_existing_entities")
    def test_none_content_in_section(self, mock_load_entities, mock_run_batch, mock_load_config):
        """Test handling of missing content in section."""

        # Mock existing entities - empty list
        mock_load_entities.return_value = []

        mock_run_batch.return_value = [
            DSPyResult(
                payload={},
                result=MagicMock(
                    metadata={"content_type": "guide"},
                    entities=[],
                    relationships=[],
                    claims=[]
                ),
                error=None,
                telemetry={}
            )
        ]

        # Create sources dict with section that has missing content
        sections_df = pd.DataFrame([
            {
                "document_id": "doc1",
                "section_id": "sec1",
                "section_number": 1,
                # No 'section_content' or 'content' key
            }
        ])
        sources = {"sections": sections_df}

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = section_extractions(
            sources=sources,
            writer=mock_writer,
        )

        # Should handle missing content gracefully
        assert result["rows_written"] == 1


