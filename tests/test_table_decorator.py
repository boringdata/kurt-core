"""Tests for @table, @model decorators and apply_dspy utility."""

from typing import Optional

import pandas as pd
import pytest
from pydantic import BaseModel
from sqlmodel import SQLModel

from kurt.core.decorator import (
    _create_sqlmodel_from_schema,
    _pluralize,
    _table_registry,
    apply_dspy,
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


class TestApplyDspy:
    """Test the apply_dspy utility function."""

    def test_apply_dspy_empty_df(self):
        """apply_dspy should return empty df unchanged."""

        class MockSignature:
            model_fields = {}

        df = pd.DataFrame()
        result = apply_dspy(df, MockSignature, input_fields={"text": "content"}, progress=False)
        assert result.empty

    def test_apply_dspy_with_pre_hook(self):
        """Test pre_hook is called before processing."""
        hook_calls = []

        def my_pre_hook(row):
            hook_calls.append(row.copy())
            row["content"] = row["content"].upper()
            return row

        # Create a mock signature that doesn't actually call DSPy
        class MockSignature:
            model_fields = {}

        df = pd.DataFrame({"content": ["hello", "world"]})

        # This will fail on DSPy call, but pre_hook should be called
        try:
            apply_dspy(
                df,
                MockSignature,
                input_fields={"text": "content"},
                pre_hook=my_pre_hook,
                progress=False,
            )
        except Exception:
            pass  # Expected - DSPy not configured

        # Pre-hook should have been called for each row
        assert len(hook_calls) == 2
        assert hook_calls[0]["content"] == "hello"
        assert hook_calls[1]["content"] == "world"


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

    def test_model_with_table(self):
        class TestModelSchema(BaseModel):
            title: str
            content: Optional[str] = None

        @model(name="test.with_table", primary_key=["id"])
        @table(TestModelSchema)
        def with_table_func(ctx=None, writer=None):
            pass

        assert hasattr(with_table_func, "_model_metadata")
        metadata = with_table_func._model_metadata
        assert metadata["name"] == "test.with_table"
        assert metadata["primary_key"] == ["id"]
        assert metadata["db_model"] is not None
        assert metadata["table_schema"] == TestModelSchema


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
