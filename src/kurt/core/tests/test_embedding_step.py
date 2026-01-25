"""
Unit tests for EmbeddingStep.

Tests embedding generation with mocked LiteLLM calls.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from kurt.core.embedding_step import (
    EmbeddingStep,
    bytes_to_embedding,
    embedding_step,
    embedding_to_bytes,
    generate_document_embedding,
    generate_embeddings,
)
from kurt.core.hooks import StepHooks
from kurt.core.mocking import mock_embeddings

# ============================================================================
# Byte Conversion Tests
# ============================================================================


class TestByteConversion:
    """Tests for embedding <-> bytes conversion."""

    def test_embedding_to_bytes(self):
        """Test converting embedding to bytes."""
        embedding = [1.0, 2.0, 3.0, 4.0]
        result = embedding_to_bytes(embedding)

        assert isinstance(result, bytes)
        assert len(result) == 16  # 4 floats * 4 bytes each

    def test_bytes_to_embedding(self):
        """Test converting bytes back to embedding."""
        embedding = [1.0, 2.0, 3.0, 4.0]
        as_bytes = embedding_to_bytes(embedding)
        result = bytes_to_embedding(as_bytes)

        assert len(result) == 4
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(2.0)
        assert result[2] == pytest.approx(3.0)
        assert result[3] == pytest.approx(4.0)

    def test_roundtrip_conversion(self):
        """Test roundtrip embedding -> bytes -> embedding."""
        original = [0.1, 0.2, 0.3, 0.4, 0.5]
        as_bytes = embedding_to_bytes(original)
        restored = bytes_to_embedding(as_bytes)

        for orig, rest in zip(original, restored):
            assert rest == pytest.approx(orig, rel=1e-6)


# ============================================================================
# generate_embeddings Tests
# ============================================================================


class TestGenerateEmbeddings:
    """Tests for generate_embeddings function."""

    def test_generate_embeddings_with_mock(self):
        """Test embedding generation with mock_embeddings context manager."""
        with mock_embeddings(dimensions=3) as mock_litellm:
            result = generate_embeddings(
                ["hello", "world"],
                model="openai/text-embedding-3-large",
                api_base="http://localhost:8080",
                api_key="test-key",
            )

            assert len(result) == 2
            assert len(result[0]) == 3  # 3 dimensions
            assert len(result[1]) == 3
            mock_litellm.embedding.assert_called_once()

    def test_generate_embeddings_returns_correct_count(self):
        """Test that we get one embedding per input text."""
        with mock_embeddings(dimensions=10):
            result = generate_embeddings(
                ["one", "two", "three"],
                model="test-model",
            )

            assert len(result) == 3
            for emb in result:
                assert len(emb) == 10


# ============================================================================
# generate_document_embedding Tests
# ============================================================================


class TestGenerateDocumentEmbedding:
    """Tests for generate_document_embedding function."""

    def test_generate_document_embedding_returns_bytes(self):
        """Test document embedding returns bytes."""
        with mock_embeddings(dimensions=4):
            result = generate_document_embedding(
                "Test document content",
                module_name="TEST",  # Explicit to skip config
            )

            assert isinstance(result, bytes)
            # 4 floats * 4 bytes = 16 bytes
            assert len(result) == 16

    def test_generate_document_embedding_truncates(self):
        """Test that long content is truncated to max_chars."""
        with mock_embeddings(dimensions=4) as mock_litellm:
            long_content = "x" * 5000
            generate_document_embedding(long_content, max_chars=1000, module_name="TEST")

            call_args = mock_litellm.embedding.call_args
            input_texts = call_args[1]["input"]
            assert len(input_texts[0]) == 1000

    def test_generate_document_embedding_roundtrip(self):
        """Test document embedding can be converted back."""
        with mock_embeddings(dimensions=4):
            result_bytes = generate_document_embedding("test", module_name="TEST")
            result_list = bytes_to_embedding(result_bytes)

            assert len(result_list) == 4
            assert all(isinstance(v, float) for v in result_list)


# ============================================================================
# EmbeddingStep Tests
# ============================================================================


class TestEmbeddingStep:
    """Tests for EmbeddingStep class."""

    def test_embedding_step_creation(self, mock_dbos):
        """Test EmbeddingStep can be created."""
        step = EmbeddingStep(
            name="test_embed",
            input_column="text",
            output_column="embedding",
            max_chars=500,
            batch_size=50,
            concurrency=2,
        )

        assert step.name == "test_embed"
        assert step.input_column == "text"
        assert step.output_column == "embedding"
        assert step.max_chars == 500
        assert step.batch_size == 50
        assert step.concurrency == 2

    def test_embedding_step_decorator(self, mock_dbos):
        """Test @embedding_step decorator syntax."""

        @embedding_step(
            input_column="content",
            output_column="vector",
            max_chars=1000,
        )
        def preprocess(text: str) -> str:
            return text.lower().strip()

        assert isinstance(preprocess, EmbeddingStep)
        assert preprocess.name == "preprocess"
        assert preprocess.input_column == "content"
        assert preprocess.output_column == "vector"


class TestEmbeddingStepRun:
    """Tests for EmbeddingStep.run() method."""

    def test_embedding_step_run_basic(self, mock_dbos):
        """Test running EmbeddingStep on DataFrame."""
        with mock_embeddings(dimensions=3):
            step = EmbeddingStep(
                name="embed_basic",
                input_column="text",
                model="text-embedding-3-small",
                batch_size=10,
                concurrency=1,
                as_bytes=False,
            )

            df = pd.DataFrame({"text": ["hello", "world"]})
            result = step.run(df)

            assert "embedding" in result.columns
            assert "embed_basic_status" in result.columns
            assert result["embed_basic_status"].iloc[0] == "success"

    def test_embedding_step_run_as_bytes(self, mock_dbos):
        """Test EmbeddingStep returns bytes when as_bytes=True."""
        with mock_embeddings(dimensions=3):
            step = EmbeddingStep(
                name="embed_bytes",
                input_column="text",
                model="text-embedding-3-small",
                batch_size=10,
                concurrency=1,
                as_bytes=True,
            )

            df = pd.DataFrame({"text": ["hello"]})
            result = step.run(df)

            assert isinstance(result["embedding"].iloc[0], bytes)

    def test_embedding_step_truncates_long_text(self, mock_dbos):
        """Test that EmbeddingStep truncates text to max_chars."""
        with mock_embeddings(dimensions=3) as mock_litellm:
            step = EmbeddingStep(
                name="embed_truncate",
                input_column="text",
                model="text-embedding-3-small",
                max_chars=100,
                batch_size=10,
                concurrency=1,
            )

            long_text = "x" * 500
            df = pd.DataFrame({"text": [long_text]})
            step.run(df)

            # Check the input to litellm was truncated
            call_args = mock_litellm.embedding.call_args
            input_texts = call_args[1]["input"]
            assert len(input_texts[0]) == 100

    def test_embedding_step_tracks_batch_metrics(self, mock_dbos, monkeypatch):
        """Test that EmbeddingStep passes batch metrics to hooks."""
        from unittest.mock import MagicMock

        captured: dict[str, float] = {}

        class CaptureHooks(StepHooks):
            def on_row_success(
                self,
                *,
                step_name: str,
                idx: int,
                total: int,
                latency_ms: int,
                prompt: str,
                tokens_in: int,
                tokens_out: int,
                cost: float,
                result: dict[str, Any],
            ) -> None:
                captured["tokens_in"] = tokens_in
                captured["tokens_out"] = tokens_out
                captured["cost"] = cost

        class DummyResponse:
            def __init__(self) -> None:
                self.data = [{"embedding": [0.1, 0.2, 0.3]}]
                self.usage = {"prompt_tokens": 12, "total_tokens": 12}

        def fake_embedding(**kwargs):
            return DummyResponse()

        def fake_cost_calc(**kwargs):
            return 0.02

        import importlib

        embedding_step_module = importlib.import_module("kurt.core.embedding_step")

        # Create a mock litellm module since the real one may not be installed
        mock_litellm = MagicMock()
        mock_litellm.embedding.side_effect = fake_embedding
        mock_litellm.response_cost_calculator.side_effect = fake_cost_calc

        # Replace the entire litellm module in the embedding_step module
        monkeypatch.setattr(embedding_step_module, "litellm", mock_litellm)

        step = EmbeddingStep(
            name="embed_metrics",
            input_column="text",
            model="text-embedding-3-small",
            batch_size=1,
            concurrency=1,
            as_bytes=False,
            hooks=CaptureHooks(),
        )

        df = pd.DataFrame({"text": ["hello"]})
        step.run(df)

        assert captured["tokens_in"] == 12
        assert captured["tokens_out"] == 0
        assert captured["cost"] == pytest.approx(0.02)


# ============================================================================
# Import Tests
# ============================================================================


class TestImports:
    """Test that all exports are importable."""

    def test_import_from_core(self):
        """Test importing from kurt.core."""
        from kurt.core import (
            EmbeddingStep,
            bytes_to_embedding,
            embedding_step,
            embedding_to_bytes,
            generate_document_embedding,
            generate_embeddings,
        )

        assert EmbeddingStep is not None
        assert embedding_step is not None
        assert generate_embeddings is not None
        assert generate_document_embedding is not None
        assert embedding_to_bytes is not None
        assert bytes_to_embedding is not None


# ============================================================================
# Embedding Trace Tests
# ============================================================================


class TestEmbeddingTracing:
    """Tests for embedding cost/token tracking via LLMTrace table."""

    def test_generate_embeddings_records_trace(self, tmp_database):
        """Test that generate_embeddings records a trace to LLMTrace table."""
        from sqlmodel import select

        from kurt.db import managed_session
        from kurt.db.models import LLMTrace

        with mock_embeddings(dimensions=4):
            # Call generate_embeddings with tracing enabled (default)
            generate_embeddings(
                ["hello", "world"],
                model="text-embedding-3-small",
                step_name="test_embedding",
            )

        # Verify trace was recorded
        with managed_session() as session:
            traces = session.exec(select(LLMTrace)).all()
            assert len(traces) == 1

            trace = traces[0]
            assert trace.step_name == "test_embedding"
            assert trace.model == "text-embedding-3-small"
            assert trace.provider == "openai"
            assert "2 texts" in trace.prompt
            assert trace.input_tokens > 0

    def test_generate_embeddings_no_trace_when_disabled(self, tmp_database):
        """Test that generate_embeddings doesn't record trace when disabled."""
        from sqlmodel import select

        from kurt.db import managed_session
        from kurt.db.models import LLMTrace

        with mock_embeddings(dimensions=4):
            generate_embeddings(
                ["hello", "world"],
                model="text-embedding-3-small",
                record_trace=False,
            )

        # Verify no trace was recorded
        with managed_session() as session:
            traces = session.exec(select(LLMTrace)).all()
            assert len(traces) == 0

    def test_generate_embeddings_trace_includes_module_name(self, tmp_database):
        """Test that module_name is included in step_name."""
        from sqlmodel import select

        from kurt.db import managed_session
        from kurt.db.models import LLMTrace

        with mock_embeddings(dimensions=4):
            generate_embeddings(
                ["test"],
                model="text-embedding-3-small",
                module_name="FETCH",
                step_name="embed_content",
            )

        with managed_session() as session:
            traces = session.exec(select(LLMTrace)).all()
            assert len(traces) == 1
            assert traces[0].step_name == "FETCH.embed_content"

    def test_embedding_step_with_tracing_hooks(self, mock_dbos, tmp_database):
        """Test EmbeddingStep with TracingHooks persists to LLMTrace."""
        from sqlmodel import select

        from kurt.core.tracing import LLMTracer, TracingHooks
        from kurt.db import managed_session
        from kurt.db.models import LLMTrace

        # Create TracingHooks that persist to database
        hooks = TracingHooks(
            tracer=LLMTracer(auto_init=False),
            model_name="text-embedding-3-small",
            provider="openai",
        )

        with mock_embeddings(dimensions=4):
            step = EmbeddingStep(
                name="embed_with_hooks",
                input_column="text",
                model="text-embedding-3-small",
                batch_size=10,
                concurrency=1,
                as_bytes=False,
                hooks=hooks,
            )

            df = pd.DataFrame({"text": ["hello", "world"]})
            step.run(df)

        # Verify trace was recorded via hooks
        with managed_session() as session:
            traces = session.exec(select(LLMTrace)).all()
            assert len(traces) >= 1

            # Find the trace from our step
            step_trace = next((t for t in traces if "embed_with_hooks" in t.step_name), None)
            assert step_trace is not None
            assert step_trace.model == "text-embedding-3-small"
            assert step_trace.provider == "openai"

    def test_generate_document_embedding_records_trace(self, tmp_database):
        """Test that generate_document_embedding records a trace."""
        from sqlmodel import select

        from kurt.db import managed_session
        from kurt.db.models import LLMTrace

        with mock_embeddings(dimensions=4):
            generate_document_embedding(
                "Test document content for embedding",
                module_name="FETCH",
                step_name="doc_embed",
            )

        with managed_session() as session:
            traces = session.exec(select(LLMTrace)).all()
            assert len(traces) == 1
            assert traces[0].step_name == "FETCH.doc_embed"
            assert "1 texts" in traces[0].prompt

    def test_tracer_stats_includes_embedding_calls(self, tmp_database):
        """Test that LLMTracer.stats() includes embedding API calls."""
        from kurt.core.tracing import LLMTracer

        with mock_embeddings(dimensions=4):
            # Generate multiple embedding batches
            generate_embeddings(["text1", "text2"], model="text-embedding-3-small")
            generate_embeddings(["text3"], model="text-embedding-3-small")

        tracer = LLMTracer(auto_init=False)
        stats = tracer.stats()

        assert stats["total_calls"] == 2
        assert stats["total_tokens_in"] > 0
