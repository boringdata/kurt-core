"""Tests for TableWriter write strategy handling."""

from unittest.mock import MagicMock

from sqlmodel import Field, SQLModel

from kurt.core.table_io import TableWriter


class DummyRow(SQLModel, table=True):
    """Simple SQLModel table for TableWriter tests."""

    __tablename__ = "test_dummy_rows"

    id: int = Field(primary_key=True)


def test_table_writer_uses_default_strategy(monkeypatch):
    """TableWriter.write should honor the configured default strategy."""
    writer = TableWriter(default_write_strategy="merge")
    writer._session = MagicMock()

    # Avoid actual DDL/DML calls
    monkeypatch.setattr(TableWriter, "_ensure_table_from_model", lambda self, model: None)

    captured = {}

    def fake_write(self, data, model, primary_keys, strategy):
        captured["strategy"] = strategy
        return len(data), 0

    monkeypatch.setattr(TableWriter, "_write_with_model", fake_write)

    rows = [DummyRow(id=1)]
    writer.write(rows)

    assert captured["strategy"] == "merge"
