"""Tests for testing utilities."""

import pandas as pd
import pytest
from pydantic import BaseModel

from kurt.content.indexing_new.framework.testing import (
    MockDSPySignature,
    MockTableReader,
    MockTableWriter,
    create_test_db_model,
    mock_dspy,
    mock_embeddings,
)


class TestMockDSPySignature:
    """Tests for MockDSPySignature."""

    def test_mock_signature_returns_response(self):
        """Test that mock signature returns configured response."""
        response = {"entities": ["test1", "test2"]}
        mock_sig = MockDSPySignature(response=response)

        result = mock_sig(input_text="test")

        assert result == response
        assert mock_sig.call_count == 1
        assert mock_sig.call_args_list[0] == {"input_text": "test"}

    def test_mock_signature_raises_error(self):
        """Test that mock signature raises configured error."""
        error = ValueError("Test error")
        mock_sig = MockDSPySignature(error=error)

        with pytest.raises(ValueError, match="Test error"):
            mock_sig(input_text="test")

        assert mock_sig.call_count == 1

    def test_mock_signature_default_response(self):
        """Test mock signature with default response."""
        mock_sig = MockDSPySignature()
        result = mock_sig(input_text="test")

        # Should return a mock prediction
        assert hasattr(result, "prompt_tokens")
        assert hasattr(result, "completion_tokens")


class TestMockDSPy:
    """Tests for mock_dspy context manager."""

    def test_mock_dspy_context(self):
        """Test mock_dspy context manager."""
        import dspy

        responses = {
            "TestSignature": {"output": "mocked"},
        }

        with mock_dspy(responses):
            # Create a mock signature class
            class TestSignature:
                pass

            executor = dspy.ChainOfThought(TestSignature)
            result = executor(input="test")

            assert result == {"output": "mocked"}


class TestMockTableReader:
    """Tests for MockTableReader."""

    def test_mock_reader_returns_data(self):
        """Test that mock reader returns configured data."""
        test_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "value": [10, 20],
            }
        )

        reader = MockTableReader({"test_table": test_df})
        df = reader.load("test_table")

        assert len(df) == 2
        assert list(df["id"]) == ["1", "2"]

    def test_mock_reader_column_selection(self):
        """Test mock reader with column selection."""
        test_df = pd.DataFrame(
            {
                "id": ["1", "2"],
                "value": [10, 20],
                "extra": ["a", "b"],
            }
        )

        reader = MockTableReader({"test_table": test_df})
        df = reader.load("test_table", columns=["id", "value"])

        assert list(df.columns) == ["id", "value"]

    def test_mock_reader_empty_table(self):
        """Test mock reader with non-existent table."""
        reader = MockTableReader()
        df = reader.load("nonexistent")

        assert len(df) == 0
        assert isinstance(df, pd.DataFrame)


class TestMockTableWriter:
    """Tests for MockTableWriter."""

    def test_mock_writer_stores_data(self):
        """Test that mock writer stores written data."""
        writer = MockTableWriter()
        writer._current_model = "test.model"

        rows = [{"id": "1", "value": 10}]
        result = writer.write(rows)

        assert result["rows_written"] == 1
        assert "test_model" in writer.written_data

        # Check stored data
        df = writer.get_written_data("test_model")
        assert len(df) == 1
        assert df.iloc[0]["id"] == "1"

    def test_mock_writer_multiple_writes(self):
        """Test mock writer with multiple writes."""
        writer = MockTableWriter()

        rows1 = [{"id": "1"}]
        rows2 = [{"id": "2"}]

        writer.write(rows1, table_name="test_table")
        writer.write(rows2, table_name="test_table")

        # Should have both writes
        assert len(writer.written_data["test_table"]) == 2
        assert len(writer.write_calls) == 2

        # get_written_data should concatenate
        df = writer.get_written_data("test_table")
        assert len(df) == 2

    def test_mock_writer_tracks_calls(self):
        """Test that mock writer tracks call details."""
        writer = MockTableWriter()

        rows = [{"id": "1"}]
        writer.write(rows, table_name="test", strategy="merge", deduplicate=False)

        assert len(writer.write_calls) == 1
        call = writer.write_calls[0]
        assert call["table_name"] == "test"
        assert call["strategy"] == "merge"
        assert call["rows"] == 1
        assert call["deduplicate"] is False


class TestCreateTestDbModel:
    """Tests for create_test_db_model."""

    def test_create_db_model(self):
        """Test dynamic model creation."""
        TestModel = create_test_db_model(  # noqa: N806
            {
                "id": str,
                "value": int,
                "optional": (str, None),  # Optional field
            }
        )

        # Should be a valid Pydantic model
        assert issubclass(TestModel, BaseModel)

        # Test instantiation
        instance = TestModel(id="1", value=10)
        assert instance.id == "1"
        assert instance.value == 10
        assert instance.optional is None

        # Test with optional
        instance2 = TestModel(id="2", value=20, optional="test")
        assert instance2.optional == "test"


class TestMockEmbeddings:
    """Tests for mock_embeddings context manager."""

    def test_mock_embeddings_returns_configured(self):
        """Test that mock embeddings returns configured vectors."""
        embeddings = {
            "test text": [0.1, 0.2, 0.3],
            "another": [0.4, 0.5, 0.6],
        }

        with mock_embeddings(embeddings):
            from kurt.content.embeddings import generate_embeddings

            result = generate_embeddings("test text")
            assert result == [0.1, 0.2, 0.3]

    def test_mock_embeddings_default(self):
        """Test mock embeddings returns default for unknown text."""
        with mock_embeddings({}):
            from kurt.content.embeddings import generate_embeddings

            result = generate_embeddings("unknown text")
            assert len(result) == 768  # Default size
            assert all(v == 0.0 for v in result)
