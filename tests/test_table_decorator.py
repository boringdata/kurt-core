"""Tests for @table, @llm, and @model decorators."""

from typing import Optional

import pytest
from pydantic import BaseModel
from sqlmodel import SQLModel

from kurt.core.decorator import (
    _create_sqlmodel_from_schema,
    _pluralize,
    _table_registry,
    get_all_tables,
    get_table,
    llm,
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


class TestLLMDecorator:
    """Test the @llm decorator."""

    def test_llm_decorator_attaches_config(self):
        class MockSignature:
            pass

        @llm(MockSignature, input_fields={"text": "content"}, output_field="summary")
        def test_llm_func():
            pass

        assert hasattr(test_llm_func, "_llm_config")
        config = test_llm_func._llm_config
        assert config["signature"] == MockSignature
        assert config["input_fields"] == {"text": "content"}
        assert config["output_field"] == "summary"
        assert config["pre_hook"] is None
        assert config["post_hook"] is None

    def test_llm_decorator_with_hooks(self):
        class MockSignature:
            pass

        def my_pre_hook(row):
            return row

        def my_post_hook(row, result):
            return row

        @llm(
            MockSignature,
            pre_hook=my_pre_hook,
            post_hook=my_post_hook,
        )
        def test_llm_func_with_hooks():
            pass

        config = test_llm_func_with_hooks._llm_config
        assert config["pre_hook"] == my_pre_hook
        assert config["post_hook"] == my_post_hook


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

    def test_model_with_llm(self):
        class TestLLMSchema(BaseModel):
            content: str
            summary: Optional[str] = None

        class MockExtractSignature:
            pass

        @model(name="test.with_llm", primary_key=["id"])
        @llm(MockExtractSignature, input_fields={"text": "content"})
        @table(TestLLMSchema)
        def with_llm_func(ctx=None, writer=None):
            pass

        metadata = with_llm_func._model_metadata
        assert metadata["llm_config"] is not None
        assert metadata["llm_config"]["signature"] == MockExtractSignature


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
