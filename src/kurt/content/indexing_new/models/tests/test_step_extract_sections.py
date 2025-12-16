"""Tests for the step_extract_sections model."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.framework import PipelineContext, TableWriter, _serialize
from kurt.content.indexing_new.framework.dspy_helpers import DSPyResult
from kurt.content.indexing_new.models.step_extract_sections import (
    SectionExtractionRow,
    section_extractions,
)


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


class TestSectionExtractions:
    """Test the section_extractions function."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {
            "rows_written": 0,
            "table_name": "indexing_section_extractions",
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

    def _create_mock_reference(self, sections: list[dict]):
        """Create a mock Reference that returns the sections DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(sections)
        return mock_ref

    @patch("kurt.config.load_config")
    @patch("kurt.db.graph_queries.get_documents_entities")
    @patch("kurt.db.get_session")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    def test_successful_extraction(
        self,
        mock_run_batch,
        mock_get_session,
        mock_get_entities,
        mock_load_config,
        mock_writer,
        mock_ctx,
    ):
        """Test successful extraction from sections."""
        # Mock the session context manager
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock existing entities lookup (empty for this test)
        mock_get_entities.return_value = []

        # Mock extraction results
        mock_result = MagicMock()
        mock_result.metadata = {"content_type": "tutorial"}
        mock_result.entities = [{"name": "Python", "entity_type": "Technology"}]
        mock_result.relationships = []
        mock_result.claims = [{"statement": "Python is versatile"}]

        mock_run_batch.return_value = [
            DSPyResult(
                payload={},
                result=mock_result,
                error=None,
                telemetry={
                    "tokens_prompt": 150,
                    "tokens_completion": 250,
                    "model_name": "gpt-4",
                    "execution_time": 2.5,
                },
            )
        ]

        # Create mock reference with section data
        mock_sections = self._create_mock_reference(
            [
                {
                    "document_id": "doc123",
                    "section_id": "sec456",
                    "section_number": 1,
                    "heading": "Introduction",
                    "content": "Python is a versatile programming language.",
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_section_extractions",
        }

        # Run extraction with new API
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

    @patch("kurt.config.load_config")
    @patch("kurt.db.graph_queries.get_documents_entities")
    @patch("kurt.db.get_session")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    def test_extraction_with_error(
        self,
        mock_run_batch,
        mock_get_session,
        mock_get_entities,
        mock_load_config,
        mock_writer,
        mock_ctx,
    ):
        """Test extraction that encounters an error."""
        # Mock the session context manager
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock existing entities lookup
        mock_get_entities.return_value = []

        # Mock extraction error
        mock_run_batch.return_value = [
            DSPyResult(
                payload={},
                result=None,
                error=Exception("LLM timeout"),
                telemetry={"error": "LLM timeout", "execution_time": 0},
            )
        ]

        # Create mock reference with section data
        mock_sections = self._create_mock_reference(
            [
                {
                    "document_id": "doc123",
                    "section_id": "sec456",
                    "section_number": 1,
                    "content": "Test content",
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_section_extractions",
        }

        # Run extraction
        result = section_extractions(ctx=mock_ctx, sections=mock_sections, writer=mock_writer)

        # Verify error handling
        assert result["rows_written"] == 1
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].error == "LLM timeout"

    def test_no_sections_found(self, mock_writer, mock_ctx):
        """Test when no sections are found for the given filters."""
        # Create empty mock reference
        mock_sections = self._create_mock_reference([])

        # Run extraction
        result = section_extractions(ctx=mock_ctx, sections=mock_sections, writer=mock_writer)

        # Verify no rows written
        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    @patch("kurt.config.load_config")
    @patch("kurt.db.graph_queries.get_documents_entities")
    @patch("kurt.db.get_session")
    @patch("kurt.content.indexing_new.models.step_extract_sections.run_batch_sync")
    def test_multiple_sections(
        self,
        mock_run_batch,
        mock_get_session,
        mock_get_entities,
        mock_load_config,
        mock_writer,
        mock_ctx,
    ):
        """Test extraction with multiple sections."""
        # Mock the session context manager
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock existing entities lookup
        mock_get_entities.return_value = []

        # Mock extraction results for all sections
        mock_result = MagicMock()
        mock_result.metadata = {"content_type": "documentation"}
        mock_result.entities = []
        mock_result.relationships = []
        mock_result.claims = []

        mock_run_batch.return_value = [
            DSPyResult(payload={}, result=mock_result, error=None, telemetry={}),
            DSPyResult(payload={}, result=mock_result, error=None, telemetry={}),
            DSPyResult(payload={}, result=mock_result, error=None, telemetry={}),
        ]

        # Create mock reference with multiple sections from different docs
        mock_sections = self._create_mock_reference(
            [
                {
                    "document_id": "doc1",
                    "section_id": "sec1",
                    "section_number": 1,
                    "content": "Content 1",
                },
                {
                    "document_id": "doc2",
                    "section_id": "sec2",
                    "section_number": 1,
                    "content": "Content 2",
                },
                {
                    "document_id": "doc3",
                    "section_id": "sec3",
                    "section_number": 1,
                    "content": "Content 3",
                },
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 3,
            "table_name": "indexing_section_extractions",
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
