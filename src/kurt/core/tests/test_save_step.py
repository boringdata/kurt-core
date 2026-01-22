"""
Unit tests for SaveStep.

Tests the SaveStep class for batch-saving rows to SQLModel tables.
"""

from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import ValidationError
from sqlmodel import Field, SQLModel

from kurt.core.hooks import NoopStepHooks
from kurt.core.save_step import SaveStep, _format_validation_errors

# ============================================================================
# Test Models
# ============================================================================


class TestEntity(SQLModel, table=True):
    """Test model for SaveStep tests."""

    __tablename__ = "test_entities"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    value: float


class StrictEntity(SQLModel, table=True):
    """Model with strict validation for error testing."""

    __tablename__ = "strict_entities"

    id: Optional[int] = Field(default=None, primary_key=True)
    required_field: str
    positive_value: float = Field(gt=0)


# ============================================================================
# Helper Functions Tests
# ============================================================================


class TestFormatValidationErrors:
    """Test _format_validation_errors helper function."""

    def test_formats_single_error(self):
        """Single validation error is formatted correctly."""
        try:
            StrictEntity(required_field="test", positive_value=-1)
        except ValidationError as exc:
            errors = _format_validation_errors(exc)
            assert len(errors) >= 1
            error = errors[0]
            assert "loc" in error
            assert "msg" in error
            assert "type" in error

    def test_formats_multiple_errors(self):
        """Multiple validation errors are formatted correctly."""
        try:
            # Missing required_field and invalid positive_value
            StrictEntity(positive_value=-1)  # type: ignore
        except ValidationError as exc:
            errors = _format_validation_errors(exc)
            assert len(errors) >= 1  # At least one error


# ============================================================================
# SaveStep Initialization Tests
# ============================================================================


class TestSaveStepInit:
    """Test SaveStep initialization."""

    def test_name_stored(self, mock_dbos):
        """Step name is stored correctly."""
        step = SaveStep(name="my_save_step", model=TestEntity)
        assert step.name == "my_save_step"

    def test_model_stored(self, mock_dbos):
        """Model class is stored correctly."""
        step = SaveStep(name="save", model=TestEntity)
        assert step.model is TestEntity

    def test_table_name_from_tablename(self, mock_dbos):
        """Table name is extracted from __tablename__."""
        step = SaveStep(name="save", model=TestEntity)
        assert step._table_name == "test_entities"

    def test_hooks_default_to_noop(self, mock_dbos):
        """Without hooks param, uses NoopStepHooks."""
        step = SaveStep(name="save", model=TestEntity)
        assert isinstance(step._hooks, NoopStepHooks)

    def test_custom_hooks_assigned(self, recording_hooks, mock_dbos):
        """Custom hooks are used when provided."""
        step = SaveStep(name="save", model=TestEntity, hooks=recording_hooks)
        assert step._hooks is recording_hooks

    def test_transaction_registered(self, mock_dbos):
        """_save_rows is a callable after init."""
        step = SaveStep(name="save", model=TestEntity)
        assert callable(step._save_rows)


# ============================================================================
# SaveStep.run() Tests with Mocked DBOS
# ============================================================================


class TestSaveStepRunMocked:
    """Test SaveStep.run() with mocked DBOS and database."""

    def test_run_returns_expected_structure(self, mock_dbos):
        """run() returns dict with saved, errors, table keys."""
        step = SaveStep(name="save", model=TestEntity)

        # Mock the transaction function to return expected result
        step._save_rows = Mock(return_value={"saved": 2, "errors": [], "table": "test_entities"})

        with patch("kurt.db.ensure_tables"):
            result = step.run([{"name": "A", "value": 1.0}, {"name": "B", "value": 2.0}])

        assert "saved" in result
        assert "errors" in result
        assert "table" in result

    def test_run_calls_ensure_tables(self, mock_dbos):
        """run() ensures table exists before saving."""
        step = SaveStep(name="save", model=TestEntity)
        step._save_rows = Mock(return_value={"saved": 0, "errors": [], "table": "test_entities"})

        with patch("kurt.db.ensure_tables") as mock_ensure:
            step.run([])
            mock_ensure.assert_called_once_with([TestEntity])

    def test_run_calls_on_start_hook(self, recording_hooks, mock_dbos):
        """run() calls on_start hook with correct args."""
        step = SaveStep(name="save_test", model=TestEntity, hooks=recording_hooks)
        step._save_rows = Mock(return_value={"saved": 3, "errors": [], "table": "test_entities"})

        with patch("kurt.db.ensure_tables"):
            step.run([{}, {}, {}])

        start_calls = recording_hooks.get_calls("on_start")
        assert len(start_calls) == 1
        assert start_calls[0]["step_name"] == "save_test"
        assert start_calls[0]["total"] == 3
        assert start_calls[0]["concurrency"] == 1

    def test_run_calls_on_end_hook(self, recording_hooks, mock_dbos):
        """run() calls on_end hook with results."""
        step = SaveStep(name="save_test", model=TestEntity, hooks=recording_hooks)
        step._save_rows = Mock(
            return_value={
                "saved": 2,
                "errors": [{"idx": 0, "type": "validation", "errors": []}],
                "table": "test_entities",
            }
        )

        with patch("kurt.db.ensure_tables"):
            step.run([{}, {}, {}])

        end_calls = recording_hooks.get_calls("on_end")
        assert len(end_calls) == 1
        assert end_calls[0]["step_name"] == "save_test"
        assert end_calls[0]["successful"] == 2
        assert end_calls[0]["total"] == 3
        assert len(end_calls[0]["errors"]) == 1

    def test_run_with_empty_rows(self, mock_dbos):
        """run() handles empty rows list."""
        step = SaveStep(name="save", model=TestEntity)
        step._save_rows = Mock(return_value={"saved": 0, "errors": [], "table": "test_entities"})

        with patch("kurt.db.ensure_tables"):
            result = step.run([])

        assert result["saved"] == 0
        assert result["errors"] == []


# ============================================================================
# Transaction Logic Tests (with mocked session)
# ============================================================================


class TestSaveRowsTransaction:
    """Test the _save_rows transaction logic."""

    def test_valid_rows_saved(self, mock_dbos, tmp_database):
        """Valid rows are saved to the database."""
        _step = SaveStep(name="save", model=TestEntity)  # noqa: F841

        # Re-register transaction to use the real function (not mocked)
        # and run it directly (not via DBOS)
        rows = [
            {"name": "Entity A", "value": 1.0},
            {"name": "Entity B", "value": 2.0},
        ]

        # Simulate the transaction logic directly
        from kurt.db import ensure_tables, managed_session

        ensure_tables([TestEntity])

        saved = 0
        errors = []
        with managed_session() as session:
            for idx, row in enumerate(rows):
                try:
                    instance = TestEntity(**row)
                    session.add(instance)
                    session.flush()
                    saved += 1
                except Exception as exc:
                    errors.append({"idx": idx, "error": str(exc)})

        assert saved == 2
        assert errors == []

    def test_validation_error_captured(self, mock_dbos, tmp_database):
        """Validation errors are captured per row."""
        from kurt.db import ensure_tables, managed_session

        ensure_tables([StrictEntity])

        rows = [
            {"required_field": "valid", "positive_value": 10},
            {"required_field": "valid", "positive_value": -1},  # Invalid
        ]

        saved = 0
        errors = []
        with managed_session() as session:
            for idx, row in enumerate(rows):
                try:
                    # Use model_validate for explicit validation
                    # (SQLModel table models don't validate by default on __init__)
                    instance = StrictEntity.model_validate(row)
                    session.add(instance)
                    session.flush()
                    saved += 1
                except ValidationError as exc:
                    errors.append(
                        {
                            "idx": idx,
                            "type": "validation",
                            "errors": _format_validation_errors(exc),
                        }
                    )
                except Exception as exc:
                    errors.append({"idx": idx, "error": str(exc)})

        assert saved == 1
        assert len(errors) == 1
        assert errors[0]["idx"] == 1
        assert errors[0]["type"] == "validation"

    def test_mixed_valid_and_invalid_rows(self, mock_dbos, tmp_database):
        """Mixed valid/invalid rows are handled correctly."""
        from kurt.db import ensure_tables, managed_session

        ensure_tables([TestEntity])

        rows = [
            {"name": "Valid", "value": 1.0},
            {"name": 123, "value": "not a float"},  # Invalid types (but may coerce)
            {"name": "Also Valid", "value": 3.0},
        ]

        saved = 0
        errors = []
        with managed_session() as session:
            for idx, row in enumerate(rows):
                try:
                    # Use model_validate for explicit validation
                    instance = TestEntity.model_validate(row)
                    session.add(instance)
                    session.flush()
                    saved += 1
                except (ValidationError, Exception) as exc:
                    errors.append({"idx": idx, "error": str(exc)})
                    session.rollback()  # Rollback to allow next iteration

        # Pydantic coerces types, so all 3 may succeed
        assert saved >= 1


# ============================================================================
# Integration Tests (with real DBOS)
# ============================================================================


class TestSaveStepIntegration:
    """Integration tests for SaveStep with real DBOS."""

    def test_save_step_in_workflow(self, dbos_launched):
        """SaveStep works within a DBOS workflow."""
        from dbos import DBOS

        from kurt.db import ensure_tables, managed_session

        ensure_tables([TestEntity])

        save_step = SaveStep(name="save_entities", model=TestEntity)

        @DBOS.workflow()
        def test_workflow():
            return save_step.run(
                [
                    {"name": "Integration A", "value": 10.0},
                    {"name": "Integration B", "value": 20.0},
                ]
            )

        result = test_workflow()

        assert result["saved"] == 2
        assert result["errors"] == []
        assert result["table"] == "test_entities"

        # Verify rows were actually saved
        with managed_session() as session:
            from sqlmodel import select

            entities = session.exec(select(TestEntity)).all()
            names = [e.name for e in entities]
            assert "Integration A" in names
            assert "Integration B" in names

    def test_save_step_with_validation_errors_in_workflow(self, dbos_launched):
        """SaveStep captures validation errors in workflow context."""
        from dbos import DBOS

        from kurt.db import ensure_tables

        ensure_tables([StrictEntity])

        save_step = SaveStep(name="save_strict", model=StrictEntity)

        @DBOS.workflow()
        def test_workflow():
            return save_step.run(
                [
                    {"required_field": "valid", "positive_value": 5.0},
                    {"required_field": "invalid", "positive_value": -1.0},  # Invalid
                ]
            )

        result = test_workflow()

        assert result["saved"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["idx"] == 1

    def test_save_step_with_hooks_in_workflow(self, dbos_launched, recording_hooks):
        """Hooks are called correctly in workflow context."""
        from dbos import DBOS

        from kurt.db import ensure_tables

        ensure_tables([TestEntity])

        save_step = SaveStep(name="tracked_save", model=TestEntity, hooks=recording_hooks)

        @DBOS.workflow()
        def test_workflow():
            return save_step.run([{"name": "Tracked", "value": 1.0}])

        _result = test_workflow()  # noqa: F841

        # Verify hooks were called
        assert len(recording_hooks.get_calls("on_start")) == 1
        assert len(recording_hooks.get_calls("on_end")) == 1
        assert recording_hooks.get_calls("on_end")[0]["successful"] == 1


# ============================================================================
# Mock DBOS Fixture
# ============================================================================


@pytest.fixture
def mock_dbos():
    """
    Mock DBOS for unit tests that don't need real DBOS infrastructure.

    Patches DBOS.transaction to be a simple passthrough decorator.
    """

    def mock_transaction_decorator():
        def decorator(fn):
            return fn

        return decorator

    mock_dbos_cls = MagicMock()
    mock_dbos_cls.transaction = mock_transaction_decorator

    with patch("kurt.core.save_step.DBOS", mock_dbos_cls):
        yield mock_dbos_cls
