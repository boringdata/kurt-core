"""Tests for TableWriter functionality."""

from unittest.mock import MagicMock

from sqlmodel import Field, SQLModel

from kurt.core.table_io import TableWriter


class DummyRow(SQLModel, table=True):
    """Simple SQLModel table for TableWriter tests."""

    __tablename__ = "test_dummy_rows"

    id: int = Field(primary_key=True)


def test_table_writer_write_strategy_parameter(monkeypatch):
    """TableWriter.write should pass through write_strategy parameter."""
    writer = TableWriter()
    writer._session = MagicMock()

    # Avoid actual DDL/DML calls
    monkeypatch.setattr(TableWriter, "_ensure_table_from_model", lambda self, model: None)

    captured = {}

    def fake_write(self, data, model, primary_keys, strategy):
        captured["strategy"] = strategy
        return len(data), 0

    monkeypatch.setattr(TableWriter, "_write_with_model", fake_write)

    rows = [DummyRow(id=1)]
    writer.write(rows, write_strategy="merge")

    assert captured["strategy"] == "merge"


def test_table_writer_default_strategy_with_pk(monkeypatch):
    """TableWriter.write converts 'append' to 'replace' when primary keys exist."""
    writer = TableWriter()
    writer._session = MagicMock()

    # Avoid actual DDL/DML calls
    monkeypatch.setattr(TableWriter, "_ensure_table_from_model", lambda self, model: None)

    captured = {}

    def fake_write(self, data, model, primary_keys, strategy):
        captured["strategy"] = strategy
        return len(data), 0

    monkeypatch.setattr(TableWriter, "_write_with_model", fake_write)

    # DummyRow has a primary key (id), so append gets converted to replace
    rows = [DummyRow(id=1)]
    writer.write(rows)  # No write_strategy specified

    assert captured["strategy"] == "replace"
