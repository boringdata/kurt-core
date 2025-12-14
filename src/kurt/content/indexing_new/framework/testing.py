"""
Testing utilities for the indexing framework.

Provides mock helpers, fixtures, and utilities for testing models.
"""

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from unittest.mock import MagicMock, patch

import dspy
import pandas as pd
from pydantic import BaseModel

from .table_io import TableReader, TableWriter


class MockDSPySignature:
    """Mock DSPy signature for testing."""

    def __init__(self, response: Any = None, error: Exception = None):
        """
        Initialize mock signature.

        Args:
            response: Response to return when called
            error: Exception to raise when called
        """
        self.response = response
        self.error = error
        self.call_count = 0
        self.call_args_list = []

    def __call__(self, **kwargs):
        """Mock execution."""
        self.call_count += 1
        self.call_args_list.append(kwargs)

        if self.error:
            raise self.error

        # Return response or create a mock prediction
        if self.response:
            return self.response

        # Create a default mock prediction
        prediction = MagicMock(spec=dspy.Prediction)
        prediction.prompt_tokens = 100
        prediction.completion_tokens = 50
        return prediction


@contextmanager
def mock_dspy(signature_responses: Dict[str, Any]):
    """
    Context manager to mock DSPy signatures.

    Args:
        signature_responses: Dict mapping signature names to responses

    Example:
        with mock_dspy({"IndexDocumentSignature": {"entities": ["test"]}}):
            # DSPy calls will return mocked responses
            pass
    """

    def mock_chain_of_thought(signature):
        """Mock ChainOfThought constructor."""
        sig_name = signature.__name__ if hasattr(signature, "__name__") else str(signature)

        if sig_name in signature_responses:
            return MockDSPySignature(signature_responses[sig_name])

        # Return a default mock
        return MockDSPySignature()

    with patch("dspy.ChainOfThought", side_effect=mock_chain_of_thought):
        yield


class MockTableReader(TableReader):
    """Mock TableReader for testing."""

    def __init__(self, data: Optional[Dict[str, pd.DataFrame]] = None):
        """
        Initialize mock reader.

        Args:
            data: Dict mapping table names to DataFrames
        """
        # Don't call super().__init__() to avoid config requirements
        self.db_path = None
        self.filters = None
        self.workflow_id = None
        self._cache = {}
        self._mock_data = data or {}

    def load(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        cache: bool = False,
    ) -> pd.DataFrame:
        """Load mock data."""
        if table_name not in self._mock_data:
            # Return empty DataFrame
            return pd.DataFrame()

        df = self._mock_data[table_name].copy()

        # Apply column selection if specified
        if columns:
            available_cols = [c for c in columns if c in df.columns]
            df = df[available_cols]

        return df


class MockTableWriter(TableWriter):
    """Mock TableWriter for testing."""

    def __init__(self):
        """Initialize mock writer."""
        # Don't call super().__init__() to avoid config requirements
        self.db_path = None
        self.workflow_id = None
        self.run_id = None
        self._current_model = None
        self._db_model = None
        self._primary_key = None
        self._default_strategy = "replace"
        self.written_data: Dict[str, List[pd.DataFrame]] = {}
        self.write_calls: List[Dict[str, Any]] = []

    def write(
        self,
        rows: Any,
        table_name: Optional[str] = None,
        strategy: Optional[str] = None,
        deduplicate: bool = True,
    ) -> Dict[str, Any]:
        """Mock write operation."""
        # Convert to DataFrame
        if isinstance(rows, list):
            df = pd.DataFrame(rows)
        else:
            df = rows.copy()

        # Determine table name
        if table_name is None:
            table_name = self._current_model.replace(".", "_") if self._current_model else "unknown"

        # Store the write
        if table_name not in self.written_data:
            self.written_data[table_name] = []
        self.written_data[table_name].append(df)

        # Record call
        self.write_calls.append(
            {
                "table_name": table_name,
                "strategy": strategy or self._default_strategy,
                "rows": len(df),
                "deduplicate": deduplicate,
            }
        )

        return {
            "rows_written": len(df),
            "rows_deduplicated": 0,
            "table_name": table_name,
            "strategy": strategy or self._default_strategy,
        }

    def get_written_data(self, table_name: str) -> Optional[pd.DataFrame]:
        """Get all data written to a table."""
        if table_name not in self.written_data:
            return None

        if len(self.written_data[table_name]) == 1:
            return self.written_data[table_name][0]

        # Concatenate multiple writes
        return pd.concat(self.written_data[table_name], ignore_index=True)


def load_fixture(fixture_path: str) -> Any:
    """
    Load a JSON fixture file.

    Args:
        fixture_path: Path to fixture file relative to tests/data/indexing_new/

    Returns:
        Loaded JSON data
    """
    base_path = Path(__file__).parent.parent.parent.parent / "tests" / "data" / "indexing_new"
    full_path = base_path / fixture_path

    if not full_path.exists():
        # Try without the base path
        full_path = Path(fixture_path)

    with open(full_path, "r") as f:
        return json.load(f)


def create_test_db_model(fields: Dict[str, Type]) -> Type[BaseModel]:
    """
    Create a Pydantic model for testing.

    Args:
        fields: Dict mapping field names to types

    Returns:
        Dynamically created Pydantic model class
    """
    from pydantic import create_model

    return create_model("TestModel", **fields)


@contextmanager
def mock_embeddings(embeddings: Dict[str, List[float]]):
    """
    Mock embedding generation.

    Args:
        embeddings: Dict mapping text to embedding vectors

    Example:
        with mock_embeddings({"test": [0.1, 0.2, 0.3]}):
            # Embedding calls will return mocked vectors
            pass
    """

    def mock_generate(*args, **kwargs):
        text = args[0] if args else kwargs.get("text", "")
        if text in embeddings:
            return embeddings[text]
        # Return default embedding
        return [0.0] * 768  # Default embedding size

    with patch("kurt.content.embeddings.generate_embeddings", side_effect=mock_generate):
        yield
