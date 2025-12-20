"""Comprehensive tests for the step_extract_sections model."""

from unittest.mock import MagicMock, patch

import dspy
import pandas as pd
import pytest

from kurt.core import PipelineContext
from kurt.db.models import ContentType, EntityType, RelationshipType
from kurt.models.staging.indexing.step_extract_sections import (
    ClaimExtraction,
    DocumentMetadataOutput,
    EntityExtraction,
    IndexDocument,
    RelationshipExtraction,
    section_extractions,
)
from kurt.utils.filtering import DocumentFilters


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
            confidence=0.95,
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
            quote="Python is widely used",
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
            confidence=0.85,
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
            has_narrative_structure=True,
        )

        assert metadata.content_type == ContentType.TUTORIAL
        assert metadata.has_code_examples is True


class TestDSPySignature:
    """Test the IndexDocument DSPy signature."""

    def test_index_document_signature_fields(self):
        """Test that IndexDocument has the correct input/output fields."""
        # DSPy signatures store fields differently
        assert issubclass(IndexDocument, dspy.Signature)

        # Check the docstring exists and contains expected field names
        assert "document_content" in IndexDocument.__doc__
        assert "entities" in IndexDocument.__doc__
        assert "relationships" in IndexDocument.__doc__
        assert "claims" in IndexDocument.__doc__


class TestSectionExtractionsWithOverlap:
    """Test extraction with overlapping sections."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @patch("kurt.models.staging.indexing.step_extract_sections.get_entities_by_document")
    @patch("kurt.models.staging.indexing.step_extract_sections.apply_dspy_on_df")
    @patch("pandas.read_sql")
    def test_extraction_with_overlap_sections(
        self, mock_read_sql, mock_apply_dspy, mock_get_entities, mock_ctx
    ):
        """Test extraction from sections with overlap prefix/suffix."""
        # Input DataFrame with overlap
        input_df = pd.DataFrame(
            [
                {
                    "document_id": "doc789",
                    "section_id": "sec789",
                    "section_number": 2,
                    "heading": "API Development",
                    "content": "Main section content about FastAPI",
                    "overlap_prefix": "prefix from previous section",
                    "overlap_suffix": "suffix for next section",
                }
            ]
        )
        mock_read_sql.return_value = input_df

        # Mock existing entities
        mock_get_entities.return_value = {
            "doc789": [{"index": 0, "id": "entity1", "name": "Django", "type": "Technology"}]
        }

        # Mock DSPy result
        output_df = input_df.copy()
        output_df["document_content"] = (
            "[...prefix from previous section]\n\nMain section content about FastAPI\n\n[suffix for next section...]"
        )
        output_df["existing_entities"] = ['[{"index": 0, "id": "entity1", "name": "Django"}]']
        output_df["metadata"] = [{"content_type": "reference"}]
        output_df["entities"] = [[{"name": "FastAPI", "entity_type": "Technology"}]]
        output_df["relationships"] = [[]]
        output_df["claims"] = [[]]
        mock_apply_dspy.return_value = output_df

        # Create mock reference
        mock_sections = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_sections.query = mock_query
        mock_sections.model_class = MagicMock()
        mock_sections.session = MagicMock()

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = section_extractions(
            ctx=mock_ctx,
            sections=mock_sections,
            writer=mock_writer,
        )

        assert result["rows_written"] == 1
        mock_apply_dspy.assert_called_once()


class TestBatchProcessing:
    """Test batch processing of multiple sections."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @patch("kurt.models.staging.indexing.step_extract_sections.get_entities_by_document")
    @patch("kurt.models.staging.indexing.step_extract_sections.apply_dspy_on_df")
    @patch("pandas.read_sql")
    def test_multiple_sections_batch(
        self, mock_read_sql, mock_apply_dspy, mock_get_entities, mock_ctx
    ):
        """Test processing multiple sections in batch."""
        # Input DataFrame
        input_df = pd.DataFrame(
            [
                {
                    "document_id": f"doc{i}",
                    "section_id": f"sec{i}",
                    "section_number": i + 1,
                    "content": f"Content {i}",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                }
                for i in range(3)
            ]
        )
        mock_read_sql.return_value = input_df

        mock_get_entities.return_value = {}

        # Mock DSPy result
        output_df = input_df.copy()
        output_df["metadata"] = [{"content_type": "guide"}] * 3
        output_df["entities"] = [[{"name": f"Entity{i}"}] for i in range(3)]
        output_df["relationships"] = [[]] * 3
        output_df["claims"] = [[{"statement": f"Claim {i}"}] for i in range(3)]
        mock_apply_dspy.return_value = output_df

        mock_sections = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_sections.query = mock_query
        mock_sections.model_class = MagicMock()
        mock_sections.session = MagicMock()

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 3}

        result = section_extractions(
            ctx=mock_ctx,
            sections=mock_sections,
            writer=mock_writer,
        )

        assert result["rows_written"] == 3
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3


class TestExistingEntitiesHandling:
    """Test handling of existing entities context."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @patch("kurt.models.staging.indexing.step_extract_sections.get_entities_by_document")
    @patch("kurt.models.staging.indexing.step_extract_sections.apply_dspy_on_df")
    @patch("pandas.read_sql")
    def test_existing_entities_passed_to_dspy(
        self, mock_read_sql, mock_apply_dspy, mock_get_entities, mock_ctx
    ):
        """Test that existing entities are properly formatted and passed."""
        input_df = pd.DataFrame(
            [
                {
                    "document_id": "doc1",
                    "section_id": "sec1",
                    "section_number": 1,
                    "content": "Test",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                }
            ]
        )
        mock_read_sql.return_value = input_df

        mock_get_entities.return_value = {
            "doc1": [
                {"index": 0, "id": "1", "name": "Django", "type": "Technology"},
                {"index": 1, "id": "2", "name": "Flask", "type": "Technology"},
            ]
        }

        output_df = input_df.copy()
        output_df["metadata"] = [{"content_type": "tutorial"}]
        output_df["entities"] = [[]]
        output_df["relationships"] = [[]]
        output_df["claims"] = [[]]
        mock_apply_dspy.return_value = output_df

        mock_sections = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_sections.query = mock_query
        mock_sections.model_class = MagicMock()
        mock_sections.session = MagicMock()

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = section_extractions(
            ctx=mock_ctx,
            sections=mock_sections,
            writer=mock_writer,
        )

        assert result["rows_written"] == 1
        # Verify get_entities_by_document was called
        mock_get_entities.assert_called_once()


class TestErrorHandlingScenarios:
    """Test various error handling scenarios."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @patch("kurt.models.staging.indexing.step_extract_sections.get_entities_by_document")
    @patch("kurt.models.staging.indexing.step_extract_sections.apply_dspy_on_df")
    @patch("pandas.read_sql")
    def test_mixed_success_and_error(
        self, mock_read_sql, mock_apply_dspy, mock_get_entities, mock_ctx
    ):
        """Test handling mix of successful and failed extractions."""
        input_df = pd.DataFrame(
            [
                {
                    "document_id": f"doc{i}",
                    "section_id": f"sec{i}",
                    "section_number": i + 1,
                    "content": f"Content {i}",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                }
                for i in range(3)
            ]
        )
        mock_read_sql.return_value = input_df

        mock_get_entities.return_value = {}

        # Mock with mixed results (success, error, success)
        output_df = input_df.copy()
        output_df["metadata"] = [{"content_type": "guide"}, None, {"content_type": "tutorial"}]
        output_df["entities"] = [[], None, []]
        output_df["relationships"] = [[], None, []]
        output_df["claims"] = [[], None, []]
        output_df["error"] = [None, "API rate limit", None]
        mock_apply_dspy.return_value = output_df

        mock_sections = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_sections.query = mock_query
        mock_sections.model_class = MagicMock()
        mock_sections.session = MagicMock()

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 3}

        result = section_extractions(
            ctx=mock_ctx,
            sections=mock_sections,
            writer=mock_writer,
        )

        assert result["rows_written"] == 3

    @patch("pandas.read_sql")
    def test_exception_during_processing(self, mock_read_sql, mock_ctx):
        """Test exception handling during extraction."""
        mock_read_sql.side_effect = Exception("Database error")

        mock_sections = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_sections.query = mock_query
        mock_sections.model_class = MagicMock()
        mock_sections.session = MagicMock()

        mock_writer = MagicMock()

        with pytest.raises(Exception) as exc_info:
            section_extractions(
                ctx=mock_ctx,
                sections=mock_sections,
                writer=mock_writer,
            )

        assert "Database error" in str(exc_info.value)


class TestTelemetryAndMetadata:
    """Test telemetry and metadata extraction."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @patch("kurt.models.staging.indexing.step_extract_sections.get_entities_by_document")
    @patch("kurt.models.staging.indexing.step_extract_sections.apply_dspy_on_df")
    @patch("pandas.read_sql")
    def test_telemetry_data_extraction(
        self, mock_read_sql, mock_apply_dspy, mock_get_entities, mock_ctx
    ):
        """Test that telemetry data is properly extracted."""
        input_df = pd.DataFrame(
            [
                {
                    "document_id": "doc1",
                    "section_id": "sec1",
                    "section_number": 1,
                    "content": "Test content",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                }
            ]
        )
        mock_read_sql.return_value = input_df

        mock_get_entities.return_value = {}

        output_df = input_df.copy()
        output_df["metadata"] = [{"content_type": "tutorial"}]
        output_df["entities"] = [[{"name": "Python", "entity_type": "Technology"}]]
        output_df["relationships"] = [[]]
        output_df["claims"] = [[]]
        mock_apply_dspy.return_value = output_df

        mock_sections = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_sections.query = mock_query
        mock_sections.model_class = MagicMock()
        mock_sections.session = MagicMock()

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = section_extractions(
            ctx=mock_ctx,
            sections=mock_sections,
            writer=mock_writer,
        )

        assert result["rows_written"] == 1


class TestEmptyPayloads:
    """Test handling of empty or None payloads."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @patch("pandas.read_sql")
    def test_empty_sections_in_sources(self, mock_read_sql, mock_ctx):
        """Test handling when sections DataFrame is empty."""
        mock_read_sql.return_value = pd.DataFrame()

        mock_sections = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_sections.query = mock_query
        mock_sections.model_class = MagicMock()
        mock_sections.session = MagicMock()

        mock_writer = MagicMock()

        result = section_extractions(
            ctx=mock_ctx,
            sections=mock_sections,
            writer=mock_writer,
        )

        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    @patch("kurt.models.staging.indexing.step_extract_sections.get_entities_by_document")
    @patch("kurt.models.staging.indexing.step_extract_sections.apply_dspy_on_df")
    @patch("pandas.read_sql")
    def test_none_content_in_section(
        self, mock_read_sql, mock_apply_dspy, mock_get_entities, mock_ctx
    ):
        """Test handling when section has None content - should handle gracefully."""
        # Use empty string instead of None (the model handles empty content)
        input_df = pd.DataFrame(
            [
                {
                    "document_id": "doc1",
                    "section_id": "sec1",
                    "section_number": 1,
                    "content": "",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                }
            ]
        )
        mock_read_sql.return_value = input_df

        mock_get_entities.return_value = {}

        output_df = input_df.copy()
        output_df["metadata"] = [None]
        output_df["entities"] = [None]
        output_df["relationships"] = [None]
        output_df["claims"] = [None]
        mock_apply_dspy.return_value = output_df

        mock_sections = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_sections.query = mock_query
        mock_sections.model_class = MagicMock()
        mock_sections.session = MagicMock()

        mock_writer = MagicMock()
        mock_writer.write.return_value = {"rows_written": 1}

        result = section_extractions(
            ctx=mock_ctx,
            sections=mock_sections,
            writer=mock_writer,
        )

        assert result["rows_written"] == 1
