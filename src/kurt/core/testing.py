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
def mock_embeddings(embeddings: Optional[Dict[str, List[float]]] = None):
    """
    Mock embedding generation across all locations where embeddings are used.

    Args:
        embeddings: Optional dict mapping text to embedding vectors.
                   If None, generates deterministic embeddings based on text hash.

    Example:
        with mock_embeddings({"test": [0.1, 0.2, 0.3]}):
            # Embedding calls will return mocked vectors
            pass

        # Or without predefined embeddings (generates unique per-text):
        with mock_embeddings():
            # Uses hash-based deterministic embeddings
            pass
    """
    import random

    embeddings = embeddings or {}

    def mock_generate(texts: List[str]) -> List[List[float]]:
        """Generate embeddings - predefined or hash-based deterministic."""
        results = []
        for text in texts:
            if text in embeddings:
                results.append(embeddings[text])
            else:
                # Generate deterministic but unique embedding based on text hash
                rng = random.Random(hash(text.lower().strip()))
                results.append([rng.random() for _ in range(1536)])
        return results

    # Patch all locations where embeddings are used
    with (
        patch("kurt.utils.embeddings.generate_embeddings", side_effect=mock_generate),
        patch("kurt.db.graph_entities.generate_embeddings", side_effect=mock_generate),
        patch("kurt.db.graph_similarity.generate_embeddings", side_effect=mock_generate),
    ):
        yield


@contextmanager
def mock_run_batch(response_factory: Optional[Any] = None):
    """
    Mock DSPy batch execution at the run_batch_sync boundary.

    This is the recommended way to mock DSPy calls in tests - it intercepts
    at the LLM boundary (run_batch_sync) rather than patching framework internals.

    Args:
        response_factory: Either:
            - A callable(items) -> List[DSPyResult] that generates responses
            - A list of DSPyResult objects to return directly
            - None to return empty successful results

    Example:
        # Simple mock with factory function
        def make_responses(items):
            return [
                DSPyResult(
                    payload=item,
                    result=MockExtraction(entities=[...]),
                    error=None,
                    telemetry={}
                )
                for item in items
            ]

        with mock_run_batch(make_responses):
            # run_batch_sync calls will use factory
            result = run_pipeline(...)

        # Or use the helper function for extraction results:
        with mock_run_batch(extraction_response_factory):
            result = run_pipeline(...)
    """
    from .dspy_helpers import DSPyResult

    def mock_run_batch_sync(
        *,
        signature,
        items,
        max_concurrent=1,
        context=None,
        timeout=None,
        on_progress=None,
        llm_model=None,
    ):
        """Mock implementation of run_batch_sync."""
        # Call progress callback with start (0/N)
        if on_progress:
            try:
                on_progress(0, len(items), None)
            except Exception:
                pass

        # Generate results
        if response_factory is None:
            # Return empty successful results
            results = [
                DSPyResult(
                    payload=item,
                    result=MagicMock(),
                    error=None,
                    telemetry={"tokens_prompt": 100, "tokens_completion": 50},
                )
                for item in items
            ]
        elif callable(response_factory):
            # Call factory with items
            results = response_factory(items)
        else:
            # Use provided list directly
            results = response_factory

        # Call progress callback for each result
        if on_progress:
            for i, result in enumerate(results, 1):
                try:
                    on_progress(i, len(items), result)
                except Exception:
                    pass

        return results

    with (
        patch(
            "kurt.core.dspy_helpers.run_batch_sync",
            side_effect=mock_run_batch_sync,
        ),
        patch(
            "kurt.core.dspy_helpers.configure_dspy_model",
        ),
    ):
        yield


def create_extraction_response_factory(
    entities_per_section: int = 2,
    claims_per_section: int = 1,
    entity_prefix: str = "Entity",
):
    """
    Create a response factory for section extraction tests.

    Args:
        entities_per_section: Number of entities to extract per section
        claims_per_section: Number of claims to extract per section
        entity_prefix: Prefix for generated entity names

    Returns:
        Factory function suitable for mock_run_batch

    Example:
        factory = create_extraction_response_factory(entities_per_section=3)
        with mock_run_batch(factory):
            # Each section extraction will return 3 entities
            pass
    """
    from .dspy_helpers import DSPyResult

    def factory(items: List[Dict[str, Any]]) -> List[DSPyResult]:
        results = []
        for i, item in enumerate(items):
            # Generate entities
            entities = [
                {
                    "name": f"{entity_prefix}{i}_{j}",
                    "entity_type": "Technology",
                    "description": f"Description for {entity_prefix}{i}_{j}",
                    "aliases": [],
                    "confidence": 0.9,
                    "resolution_status": "NEW",
                    "quote": f"Quote for {entity_prefix}{i}_{j}",
                }
                for j in range(entities_per_section)
            ]

            # Generate claims referencing entities
            claims = [
                {
                    "statement": f"Claim {i}_{j} about {entity_prefix}{i}_0",
                    "claim_type": "capability",
                    "entity_indices": [0],  # Reference first entity
                    "source_quote": f"Source quote for claim {i}_{j}",
                    "quote_start_offset": 0,
                    "quote_end_offset": 30,
                    "confidence": 0.85,
                }
                for j in range(claims_per_section)
            ]

            # Create mock result object
            mock_result = MagicMock()
            mock_result.metadata = {
                "content_type": "reference",
                "has_code_examples": False,
                "has_step_by_step_procedures": False,
                "has_narrative_structure": False,
            }
            mock_result.entities = entities
            mock_result.relationships = []
            mock_result.claims = claims

            results.append(
                DSPyResult(
                    payload=item,
                    result=mock_result,
                    error=None,
                    telemetry={"tokens_prompt": 100, "tokens_completion": 50},
                )
            )

        return results

    return factory
