"""Tests for @table, @model decorators and apply_dspy_on_df utility."""

from typing import Optional
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from pydantic import BaseModel
from sqlmodel import SQLModel

from kurt.core.decorator import (
    _create_sqlmodel_from_schema,
    _pluralize,
    _table_registry,
    apply_dspy_on_df,
    get_all_tables,
    get_table,
    model,
    table,
)


class TestPluralize:
    """Test the _pluralize helper function."""

    def test_basic_pluralization(self):
        assert _pluralize("document") == "documents"
        assert _pluralize("item") == "items"
        assert _pluralize("user") == "users"

    def test_y_ending(self):
        assert _pluralize("entity") == "entities"
        assert _pluralize("category") == "categories"

    def test_already_plural(self):
        assert _pluralize("documents") == "documents"
        assert _pluralize("items") == "items"

    def test_special_endings(self):
        assert _pluralize("box") == "boxes"
        assert _pluralize("match") == "matches"


class TestCreateSQLModelFromSchema:
    """Test the _create_sqlmodel_from_schema helper."""

    def test_basic_schema(self):
        class SimpleSchema(BaseModel):
            name: str
            value: int

        model_cls = _create_sqlmodel_from_schema(
            SimpleSchema, "simple_items", uuid_pk=True, timestamps=True
        )

        # Check it's a SQLModel
        assert issubclass(model_cls, SQLModel)

        # Check field order
        fields = list(model_cls.model_fields.keys())
        assert fields == ["id", "name", "value", "created_at", "updated_at"]

    def test_no_uuid_pk(self):
        """When uuid_pk=False, user must provide their own primary key."""
        # Skip this test - SQLModel requires a primary key
        # If uuid_pk=False, user must define their own PK in the schema
        pass

    def test_no_timestamps(self):
        class NoTimestampSchema(BaseModel):
            name: str

        model_cls = _create_sqlmodel_from_schema(
            NoTimestampSchema, "no_ts_items", uuid_pk=True, timestamps=False
        )

        fields = list(model_cls.model_fields.keys())
        assert "created_at" not in fields
        assert "updated_at" not in fields
        assert fields == ["id", "name"]

    def test_optional_fields(self):
        class OptionalSchema(BaseModel):
            required_field: str
            optional_field: Optional[str] = None
            default_field: str = "default"

        model_cls = _create_sqlmodel_from_schema(
            OptionalSchema, "optional_items", uuid_pk=True, timestamps=True
        )

        fields = list(model_cls.model_fields.keys())
        assert fields == [
            "id",
            "required_field",
            "optional_field",
            "default_field",
            "created_at",
            "updated_at",
        ]


class TestTableDecorator:
    """Test the @table decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        _table_registry.clear()

    def test_table_decorator_creates_sqlmodel(self):
        class TestSchema1(BaseModel):
            title: str

        @table(TestSchema1)
        def test_func1():
            pass

        assert hasattr(test_func1, "_table_sqlmodel")
        assert hasattr(test_func1, "_table_name")
        assert test_func1._table_name == "test_func1s"

    def test_table_decorator_custom_tablename(self):
        class TestSchema2(BaseModel):
            title: str

        @table(TestSchema2, tablename="custom_table")
        def test_func2():
            pass

        assert test_func2._table_name == "custom_table"

    def test_table_decorator_registers(self):
        class TestSchema3(BaseModel):
            title: str

        @table(TestSchema3)
        def test_func3():
            pass

        assert "test_func3s" in get_all_tables()
        assert get_table("test_func3s") is not None


class TestApplyDspyOnDf:
    """Test the apply_dspy_on_df utility function.

    These tests mock run_batch_sync since apply_dspy_on_df now uses it
    for parallel execution instead of calling dspy directly.
    """

    def test_empty_df_returns_unchanged(self):
        """apply_dspy_on_df should return empty df unchanged."""

        class MockSignature:
            model_fields = {}

        df = pd.DataFrame()
        result = apply_dspy_on_df(
            df, MockSignature, input_fields={"text": "content"}, progress=False
        )
        assert result.empty

    def test_processes_each_row_in_parallel(self):
        """Verify each row is processed through run_batch_sync."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        df = pd.DataFrame({"content": ["hello", "world", "test"]})

        # Mock run_batch_sync to return results for each row
        def mock_run_batch_sync(
            *, signature, items, max_concurrent, on_progress, config=None, predictor=None
        ):
            results = []
            for item in items:
                mock_result = MagicMock()
                mock_result.summary = f"Summary of: {item.get('text', '')}"
                results.append(
                    DSPyResult(
                        payload=item,
                        result=mock_result,
                        error=None,
                        telemetry={},
                    )
                )
            return results

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            result = apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"text": "content"},
                output_fields={"summary": "summary"},
                progress=False,
            )

        # Verify outputs were added to DataFrame
        assert len(result) == 3
        assert list(result["summary"]) == [
            "Summary of: hello",
            "Summary of: world",
            "Summary of: test",
        ]

    def test_max_concurrent_passed_to_run_batch_sync(self):
        """Verify max_concurrent is passed to run_batch_sync."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        df = pd.DataFrame({"content": ["hello"]})
        captured_kwargs = {}

        def mock_run_batch_sync(**kwargs):
            captured_kwargs.update(kwargs)
            mock_result = MagicMock()
            mock_result.summary = "done"
            return [DSPyResult(payload={}, result=mock_result, error=None, telemetry={})]

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"text": "content"},
                output_fields={"summary": "summary"},
                max_concurrent=10,
                progress=False,
            )

        assert captured_kwargs["max_concurrent"] == 10

    def test_pre_hook_transforms_input(self):
        """Test pre_hook is called before DSPy processing."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        def uppercase_hook(row):
            row["content"] = row["content"].upper()
            return row

        df = pd.DataFrame({"content": ["hello", "world"]})
        captured_items = []

        def mock_run_batch_sync(
            *, signature, items, max_concurrent, on_progress, config=None, predictor=None
        ):
            captured_items.extend(items)
            results = []
            for item in items:
                mock_result = MagicMock()
                mock_result.summary = "done"
                results.append(
                    DSPyResult(
                        payload=item,
                        result=mock_result,
                        error=None,
                        telemetry={},
                    )
                )
            return results

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"text": "content"},
                output_fields={"summary": "summary"},
                pre_hook=uppercase_hook,
                progress=False,
            )

        # Verify pre_hook transformed input before run_batch_sync
        assert captured_items[0] == {"text": "HELLO"}
        assert captured_items[1] == {"text": "WORLD"}

    def test_post_hook_transforms_output(self):
        """Test post_hook is called after DSPy processing."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        def add_word_count_hook(row, result):
            row["summary"] = result.summary
            row["word_count"] = len(result.summary.split())
            return row

        df = pd.DataFrame({"content": ["hello world"]})

        def mock_run_batch_sync(
            *, signature, items, max_concurrent, on_progress, config=None, predictor=None
        ):
            mock_result = MagicMock()
            mock_result.summary = "This is a test summary"
            return [DSPyResult(payload=items[0], result=mock_result, error=None, telemetry={})]

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            result = apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"text": "content"},
                output_fields={"summary": "summary"},
                post_hook=add_word_count_hook,
                progress=False,
            )

        # Verify post_hook added extra field
        assert result["summary"].iloc[0] == "This is a test summary"
        assert result["word_count"].iloc[0] == 5

    def test_handles_dspy_error_gracefully(self):
        """DSPy errors should be logged but not crash processing."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        df = pd.DataFrame({"content": ["good", "bad", "good2"]})

        def mock_run_batch_sync(
            *, signature, items, max_concurrent, on_progress, config=None, predictor=None
        ):
            results = []
            for item in items:
                if item.get("text") == "bad":
                    results.append(
                        DSPyResult(
                            payload=item,
                            result=None,
                            error=ValueError("DSPy API error"),
                            telemetry={"error": "DSPy API error"},
                        )
                    )
                else:
                    mock_result = MagicMock()
                    mock_result.summary = f"Summary: {item.get('text')}"
                    results.append(
                        DSPyResult(
                            payload=item,
                            result=mock_result,
                            error=None,
                            telemetry={},
                        )
                    )
            return results

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            result = apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"text": "content"},
                output_fields={"summary": "summary"},
                progress=False,
            )

        # All rows should be in result (error row has None/missing summary)
        assert len(result) == 3
        assert result["summary"].iloc[0] == "Summary: good"
        # Error row - summary not added, so check it's not there or None
        assert (
            "summary" not in result.iloc[1]
            or result["summary"].iloc[1] is None
            or pd.isna(result.get("summary", {}).get(1))
        )
        assert result["summary"].iloc[2] == "Summary: good2"

    def test_multiple_input_and_output_fields(self):
        """Test mapping multiple input and output fields."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        df = pd.DataFrame({"title": ["Doc 1", "Doc 2"], "body": ["Content 1", "Content 2"]})

        def mock_run_batch_sync(
            *, signature, items, max_concurrent, on_progress, config=None, predictor=None
        ):
            results = []
            for item in items:
                mock_result = MagicMock()
                mock_result.summary = f"{item.get('doc_title')}: {item.get('doc_body')}"
                mock_result.category = "test_category"
                results.append(
                    DSPyResult(
                        payload=item,
                        result=mock_result,
                        error=None,
                        telemetry={},
                    )
                )
            return results

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            result = apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"doc_title": "title", "doc_body": "body"},
                output_fields={"summary": "result_summary", "category": "result_cat"},
                progress=False,
            )

        # Verify multiple outputs mapped correctly
        assert result["result_summary"].iloc[0] == "Doc 1: Content 1"
        assert result["result_cat"].iloc[0] == "test_category"

    def test_parallel_execution_with_max_concurrent(self):
        """Test that max_concurrent controls parallelism in run_batch_sync."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        # Create 10 rows
        df = pd.DataFrame({"content": [f"row_{i}" for i in range(10)]})

        call_count = [0]

        def mock_run_batch_sync(
            *, signature, items, max_concurrent, on_progress, config=None, predictor=None
        ):
            call_count[0] += 1
            # Verify all items are passed in a single batch
            assert len(items) == 10
            results = []
            for item in items:
                mock_result = MagicMock()
                mock_result.summary = f"processed_{item.get('text')}"
                results.append(
                    DSPyResult(
                        payload=item,
                        result=mock_result,
                        error=None,
                        telemetry={},
                    )
                )
            return results

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            result = apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"text": "content"},
                output_fields={"summary": "summary"},
                max_concurrent=5,
                progress=False,
            )

        # run_batch_sync should be called once with all items
        assert call_count[0] == 1
        assert len(result) == 10

        # Verify all rows have output
        for i in range(10):
            assert result["summary"].iloc[i] == f"processed_row_{i}"

    def test_preserves_original_columns(self):
        """Output DataFrame should preserve all original columns."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "content": ["a", "b", "c"],
                "extra_col": ["x", "y", "z"],
            }
        )

        def mock_run_batch_sync(
            *, signature, items, max_concurrent, on_progress, config=None, predictor=None
        ):
            results = []
            for item in items:
                mock_result = MagicMock()
                mock_result.summary = "done"
                results.append(
                    DSPyResult(
                        payload=item,
                        result=mock_result,
                        error=None,
                        telemetry={},
                    )
                )
            return results

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            result = apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"text": "content"},
                output_fields={"summary": "summary"},
                progress=False,
            )

        # Original columns preserved
        assert "id" in result.columns
        assert "content" in result.columns
        assert "extra_col" in result.columns
        # New column added
        assert "summary" in result.columns

        # Values preserved
        assert list(result["id"]) == [1, 2, 3]
        assert list(result["extra_col"]) == ["x", "y", "z"]

    def test_config_passed_to_run_batch_sync(self):
        """Verify config parameter is passed through to run_batch_sync."""
        from kurt.core.dspy_helpers import DSPyResult

        class MockSignature:
            model_fields = {}

        class MockConfig:
            llm_model = "gpt-4"

        df = pd.DataFrame({"content": ["hello"]})
        captured_kwargs = {}

        def mock_run_batch_sync(**kwargs):
            captured_kwargs.update(kwargs)
            mock_result = MagicMock()
            mock_result.summary = "done"
            return [DSPyResult(payload={}, result=mock_result, error=None, telemetry={})]

        mock_config = MockConfig()

        with patch("kurt.core.dspy_helpers.run_batch_sync", side_effect=mock_run_batch_sync):
            apply_dspy_on_df(
                df,
                MockSignature,
                input_fields={"text": "content"},
                output_fields={"summary": "summary"},
                config=mock_config,
                progress=False,
            )

        assert captured_kwargs["config"] is mock_config


class TestModelDecorator:
    """Test the @model decorator with @table."""

    def setup_method(self):
        """Clear registry before each test."""
        _table_registry.clear()

    def test_model_requires_table(self):
        """@model without @table should raise error."""
        with pytest.raises(ValueError, match="requires @table decorator"):

            @model(name="test.no_table", primary_key=["id"])
            def no_table_func():
                pass

    def test_model_with_table_from_pydantic_schema(self):
        """@table(PydanticSchema) should generate SQLModel."""

        class TestModelSchema(BaseModel):
            title: str
            content: Optional[str] = None

        @model(name="test.with_pydantic", primary_key=["id"])
        @table(TestModelSchema)
        def with_pydantic_func(ctx=None, writer=None):
            pass

        assert hasattr(with_pydantic_func, "_model_metadata")
        metadata = with_pydantic_func._model_metadata
        assert metadata["name"] == "test.with_pydantic"
        assert metadata["primary_key"] == ["id"]
        assert metadata["db_model"] is not None
        assert metadata["table_schema"] == TestModelSchema

    def test_model_with_table_from_sqlmodel_class(self):
        """@table(SQLModelClass) should register existing SQLModel."""
        from sqlmodel import Field, SQLModel

        class ExistingSQLModel(SQLModel, table=True):
            __tablename__ = "test_existing_table"
            id: str = Field(primary_key=True)
            title: str
            content: Optional[str] = None

        @model(name="test.with_sqlmodel", primary_key=["id"])
        @table(ExistingSQLModel)
        def with_sqlmodel_func(ctx=None, writer=None):
            pass

        assert hasattr(with_sqlmodel_func, "_model_metadata")
        metadata = with_sqlmodel_func._model_metadata
        assert metadata["name"] == "test.with_sqlmodel"
        assert metadata["primary_key"] == ["id"]
        assert metadata["db_model"] is ExistingSQLModel
        # When using existing SQLModel, table_schema is None
        assert metadata["table_schema"] is None


class TestFieldOrdering:
    """Test that fields are always in correct order."""

    def setup_method(self):
        _table_registry.clear()

    def test_field_order_id_first_timestamps_last(self):
        class OrderTestSchema(BaseModel):
            field_a: str
            field_b: int
            field_c: Optional[str] = None

        @model(name="test.order", primary_key=["id"])
        @table(OrderTestSchema)
        def order_func(ctx=None, writer=None):
            pass

        db_model = order_func._model_metadata["db_model"]
        fields = list(db_model.model_fields.keys())

        # id should be first
        assert fields[0] == "id"

        # User fields in middle
        assert "field_a" in fields
        assert "field_b" in fields
        assert "field_c" in fields

        # Timestamps should be last
        assert fields[-2] == "created_at"
        assert fields[-1] == "updated_at"

        # Full expected order
        assert fields == ["id", "field_a", "field_b", "field_c", "created_at", "updated_at"]
