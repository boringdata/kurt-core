"""Tests for the step_extract_sections model."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from kurt.core import PipelineContext, TableWriter, _serialize
from kurt.models.staging.indexing.step_extract_sections import (
    SectionExtractionRow,
    section_extractions,
)
from kurt.utils.filtering import DocumentFilters


class TestSectionExtractionRow:
    """Test the SectionExtractionRow SQLModel."""

    def test_create_extraction_row(self):
        """Test creating a section extraction row."""
        row = SectionExtractionRow(
            document_id="doc123",
            section_id="sec456",
            section_number=1,
            section_heading="Introduction",
            metadata_json={"content_type": "tutorial"},
            entities_json=[{"name": "Python", "type": "Technology"}],
            relationships_json=[],
            claims_json=[{"statement": "Python is a programming language"}],
            tokens_prompt=100,
            tokens_completion=200,
            llm_model_name="gpt-4",
        )

        assert row.document_id == "doc123"
        assert row.section_id == "sec456"
        assert row.section_number == 1
        assert row.metadata_json["content_type"] == "tutorial"
        assert len(row.entities_json) == 1
        assert len(row.claims_json) == 1

    def test_error_extraction_row(self):
        """Test creating an extraction row with an error."""
        row = SectionExtractionRow(
            document_id="doc123",
            section_id="sec456",
            section_number=1,
            error="Extraction failed: timeout",
        )

        assert row.error == "Extraction failed: timeout"
        assert row.metadata_json is None
        assert row.entities_json is None

    def test_model_validator_from_source_and_dspy(self):
        """Test model_validator transforms source + DSPy result correctly."""
        # Create mock DSPy result
        mock_result = MagicMock()
        mock_result.metadata = {"content_type": "tutorial"}
        mock_result.entities = [{"name": "Python", "entity_type": "Technology"}]
        mock_result.relationships = []
        mock_result.claims = [{"statement": "Python is versatile"}]

        # Create row with source data and dspy_result
        row = SectionExtractionRow(
            document_id="doc123",
            section_id="sec456",
            section_number=1,
            heading="Introduction",  # Should be renamed to section_heading
            dspy_result=mock_result,
            dspy_telemetry={
                "tokens_prompt": 150,
                "tokens_completion": 250,
                "model_name": "gpt-4",
                "execution_time": 2.5,
            },
        )

        # Verify field renames worked
        assert row.section_heading == "Introduction"

        # Verify DSPy result was serialized
        assert row.metadata_json == {"content_type": "tutorial"}
        assert len(row.entities_json) == 1
        assert len(row.claims_json) == 1

        # Verify telemetry was extracted
        assert row.tokens_prompt == 150
        assert row.tokens_completion == 250
        assert row.llm_model_name == "gpt-4"


def create_mock_reference(data: list[dict], workflow_id: str = None):
    """Create a mock Reference that works with pd.read_sql pattern."""
    mock_ref = MagicMock()
    df = pd.DataFrame(data)

    # Mock the query object
    mock_query = MagicMock()
    mock_query.statement = MagicMock()

    # Mock filter to return itself
    def mock_filter(*args, **kwargs):
        return mock_query

    mock_query.filter = mock_filter

    mock_ref.query = mock_query

    # Mock model_class
    mock_model_class = MagicMock()
    mock_model_class.workflow_id = "workflow_id"
    mock_ref.model_class = mock_model_class

    # Mock session and bind for pd.read_sql
    mock_session = MagicMock()
    mock_ref.session = mock_session

    return mock_ref, df


class TestSectionExtractions:
    """Test the section_extractions function."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {
            "rows_written": 0,
            "table_name": "staging_section_extractions",
        }
        return writer

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
    def test_successful_extraction(
        self,
        mock_read_sql,
        mock_apply_dspy,
        mock_get_entities,
        mock_writer,
        mock_ctx,
    ):
        """Test successful extraction from sections."""
        # Setup mock data
        input_df = pd.DataFrame(
            [
                {
                    "document_id": "doc123",
                    "section_id": "sec456",
                    "section_number": 1,
                    "heading": "Introduction",
                    "content": "Python is a versatile programming language.",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                }
            ]
        )
        mock_read_sql.return_value = input_df

        # Mock existing entities lookup (empty for this test)
        mock_get_entities.return_value = {}

        # Mock DSPy result - apply_dspy_on_df adds columns
        output_df = input_df.copy()
        output_df["metadata"] = [{"content_type": "tutorial"}]
        output_df["entities"] = [[{"name": "Python", "entity_type": "Technology"}]]
        output_df["relationships"] = [[]]
        output_df["claims"] = [[{"statement": "Python is versatile"}]]
        mock_apply_dspy.return_value = output_df

        # Create mock reference
        mock_sections, _ = create_mock_reference([])

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "staging_section_extractions",
        }

        # Run extraction
        result = section_extractions(ctx=mock_ctx, sections=mock_sections, writer=mock_writer)

        # Verify results
        assert result["rows_written"] == 1
        mock_writer.write.assert_called_once()
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        row = rows[0]
        assert row.document_id == "doc123"
        assert row.section_id == "sec456"
        assert row.metadata_json["content_type"] == "tutorial"

    @patch("kurt.models.staging.indexing.step_extract_sections.get_entities_by_document")
    @patch("kurt.models.staging.indexing.step_extract_sections.apply_dspy_on_df")
    @patch("pandas.read_sql")
    def test_extraction_with_error(
        self,
        mock_read_sql,
        mock_apply_dspy,
        mock_get_entities,
        mock_writer,
        mock_ctx,
    ):
        """Test extraction that encounters an error."""
        # Setup mock data
        input_df = pd.DataFrame(
            [
                {
                    "document_id": "doc123",
                    "section_id": "sec456",
                    "section_number": 1,
                    "content": "Test content",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                }
            ]
        )
        mock_read_sql.return_value = input_df

        # Mock existing entities lookup
        mock_get_entities.return_value = {}

        # Mock DSPy result with error
        output_df = input_df.copy()
        output_df["metadata"] = [None]
        output_df["entities"] = [None]
        output_df["relationships"] = [None]
        output_df["claims"] = [None]
        output_df["error"] = ["LLM timeout"]
        mock_apply_dspy.return_value = output_df

        # Create mock reference
        mock_sections, _ = create_mock_reference([])

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "staging_section_extractions",
        }

        # Run extraction
        result = section_extractions(ctx=mock_ctx, sections=mock_sections, writer=mock_writer)

        # Verify error handling
        assert result["rows_written"] == 1

    @patch("pandas.read_sql")
    def test_no_sections_found(self, mock_read_sql, mock_writer, mock_ctx):
        """Test when no sections are found for the given filters."""
        # Empty DataFrame
        mock_read_sql.return_value = pd.DataFrame()

        # Create mock reference
        mock_sections, _ = create_mock_reference([])

        # Run extraction
        result = section_extractions(ctx=mock_ctx, sections=mock_sections, writer=mock_writer)

        # Verify no rows written
        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    @patch("kurt.models.staging.indexing.step_extract_sections.get_entities_by_document")
    @patch("kurt.models.staging.indexing.step_extract_sections.apply_dspy_on_df")
    @patch("pandas.read_sql")
    def test_multiple_sections(
        self,
        mock_read_sql,
        mock_apply_dspy,
        mock_get_entities,
        mock_writer,
        mock_ctx,
    ):
        """Test extraction with multiple sections."""
        # Setup mock data
        input_df = pd.DataFrame(
            [
                {
                    "document_id": "doc1",
                    "section_id": "sec1",
                    "section_number": 1,
                    "content": "Content 1",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                },
                {
                    "document_id": "doc2",
                    "section_id": "sec2",
                    "section_number": 1,
                    "content": "Content 2",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                },
                {
                    "document_id": "doc3",
                    "section_id": "sec3",
                    "section_number": 1,
                    "content": "Content 3",
                    "overlap_prefix": None,
                    "overlap_suffix": None,
                },
            ]
        )
        mock_read_sql.return_value = input_df

        # Mock existing entities lookup
        mock_get_entities.return_value = {}

        # Mock DSPy result
        output_df = input_df.copy()
        output_df["metadata"] = [{"content_type": "documentation"}] * 3
        output_df["entities"] = [[]] * 3
        output_df["relationships"] = [[]] * 3
        output_df["claims"] = [[]] * 3
        mock_apply_dspy.return_value = output_df

        # Create mock reference
        mock_sections, _ = create_mock_reference([])

        mock_writer.write.return_value = {
            "rows_written": 3,
            "table_name": "staging_section_extractions",
        }

        # Run extraction
        result = section_extractions(ctx=mock_ctx, sections=mock_sections, writer=mock_writer)

        # Verify all sections processed
        assert result["rows_written"] == 3
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3

        # Verify each section was processed
        doc_ids = {row.document_id for row in rows}
        assert doc_ids == {"doc1", "doc2", "doc3"}


class TestSerialize:
    """Test the _serialize helper function."""

    def test_serialize_none(self):
        """Test serializing None value."""
        assert _serialize(None, {}) == {}
        assert _serialize(None, []) == []

    def test_serialize_json_string(self):
        """Test serializing JSON string."""
        data = '{"key": "value"}'
        result = _serialize(data, {})
        assert result == {"key": "value"}

    def test_serialize_invalid_json(self):
        """Test serializing invalid JSON string."""
        data = "not json"
        result = _serialize(data, {})
        assert result == {}

    def test_serialize_dict(self):
        """Test serializing dict directly."""
        data = {"key": "value"}
        result = _serialize(data, {})
        assert result == {"key": "value"}

    def test_serialize_list(self):
        """Test serializing list directly."""
        data = [{"key": "value"}]
        result = _serialize(data, [])
        assert result == [{"key": "value"}]

    def test_serialize_pydantic_model(self):
        """Test serializing Pydantic model."""
        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"key": "value"}

        result = _serialize(mock_model, {})
        assert result == {"key": "value"}
        mock_model.model_dump.assert_called_once()
