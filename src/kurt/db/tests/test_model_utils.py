"""
Tests for model_utils module.

Tests dynamic SQLModel discovery and table creation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlmodel import select

from kurt.db.model_utils import (
    ensure_all_workflow_tables,
    ensure_table_exists,
    find_models_in_workflow,
    get_model_by_table_name,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def workflow_dir(tmp_path: Path) -> Path:
    """Create a temporary workflow directory with models.py."""
    workflow = tmp_path / "my_workflow"
    workflow.mkdir()

    models_content = '''
"""Test workflow models."""
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import JSON, Column


class TestItem(SQLModel, table=True):
    """Test item model."""
    __tablename__ = "test_items"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    value: float = Field(default=0.0)


class TestCategory(SQLModel, table=True):
    """Test category model."""
    __tablename__ = "test_categories"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    category_name: str
    description: Optional[str] = Field(default=None)


class NotATable(SQLModel):
    """This is not a table - no table=True."""
    some_field: str = "default"
'''
    (workflow / "models.py").write_text(models_content)
    return workflow


@pytest.fixture
def workflow_dir_with_json(tmp_path: Path) -> Path:
    """Create a workflow directory with models that use JSON columns."""
    workflow = tmp_path / "json_workflow"
    workflow.mkdir()

    models_content = '''
"""Workflow models with JSON fields."""
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import JSON, Column


class CompetitorAnalysis(SQLModel, table=True):
    """Competitor analysis with JSON fields."""
    __tablename__ = "competitor_analysis"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)
    company: str
    products: list[str] = Field(sa_column=Column(JSON), default_factory=list)
    pricing: dict = Field(sa_column=Column(JSON), default_factory=dict)
'''
    (workflow / "models.py").write_text(models_content)
    return workflow


@pytest.fixture
def workflow_dir_with_duplicate(tmp_path: Path) -> Path:
    """Create a workflow directory with duplicate table names."""
    workflow = tmp_path / "dupe_workflow"
    workflow.mkdir()

    models_content = '''
"""Models with duplicate table names."""
from typing import Optional
from sqlmodel import Field, SQLModel


class ItemA(SQLModel, table=True):
    """First item with duplicate table name."""
    __tablename__ = "items"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class ItemB(SQLModel, table=True):
    """Second item with same table name."""
    __tablename__ = "items"
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    label: str
'''
    (workflow / "models.py").write_text(models_content)
    return workflow


@pytest.fixture
def workflow_dir_with_syntax_error(tmp_path: Path) -> Path:
    """Create a workflow directory with invalid models.py."""
    workflow = tmp_path / "bad_workflow"
    workflow.mkdir()

    models_content = '''
"""Broken models file."""
from sqlmodel import SQLModel

class Broken(SQLModel, table=True)  # Missing colon
    pass
'''
    (workflow / "models.py").write_text(models_content)
    return workflow


@pytest.fixture
def workflow_dir_empty(tmp_path: Path) -> Path:
    """Create an empty workflow directory (no models.py)."""
    workflow = tmp_path / "empty_workflow"
    workflow.mkdir()
    return workflow


# ============================================================================
# Tests for get_model_by_table_name
# ============================================================================


class TestGetModelByTableName:
    """Tests for get_model_by_table_name function."""

    def test_finds_model_by_table_name(self, workflow_dir: Path):
        """Should find SQLModel class by its __tablename__."""
        model = get_model_by_table_name("test_items", workflow_dir=workflow_dir)

        assert model is not None
        assert model.__name__ == "TestItem"
        assert model.__tablename__ == "test_items"

    def test_finds_different_model(self, workflow_dir: Path):
        """Should find different model by different table name."""
        model = get_model_by_table_name("test_categories", workflow_dir=workflow_dir)

        assert model is not None
        assert model.__name__ == "TestCategory"
        assert model.__tablename__ == "test_categories"

    def test_returns_none_for_nonexistent_table(self, workflow_dir: Path):
        """Should return None when table name not found."""
        model = get_model_by_table_name("nonexistent_table", workflow_dir=workflow_dir)

        assert model is None

    def test_returns_none_for_missing_models_file(self, workflow_dir_empty: Path):
        """Should return None when models.py doesn't exist."""
        model = get_model_by_table_name("any_table", workflow_dir=workflow_dir_empty)

        assert model is None

    def test_raises_on_syntax_error(self, workflow_dir_with_syntax_error: Path):
        """Should raise ImportError on syntax error in models.py."""
        with pytest.raises(ImportError):
            get_model_by_table_name(
                "any_table", workflow_dir=workflow_dir_with_syntax_error
            )

    def test_raises_on_duplicate_table_name(self, workflow_dir_with_duplicate: Path):
        """Should raise ValueError when multiple models have same table name."""
        with pytest.raises(ValueError, match="Multiple models found"):
            get_model_by_table_name("items", workflow_dir=workflow_dir_with_duplicate)

    def test_uses_cwd_when_no_workflow_dir(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Should use current working directory when workflow_dir not specified."""
        monkeypatch.chdir(workflow_dir)

        model = get_model_by_table_name("test_items")

        assert model is not None
        assert model.__name__ == "TestItem"

    def test_ignores_non_table_models(self, workflow_dir: Path):
        """Should not find SQLModel classes without table=True."""
        # NotATable exists but doesn't have __tablename__
        model = get_model_by_table_name("NotATable", workflow_dir=workflow_dir)

        assert model is None


# ============================================================================
# Tests for ensure_table_exists
# ============================================================================


class TestEnsureTableExists:
    """Tests for ensure_table_exists function."""

    def test_creates_table(self, tmp_database: Path, workflow_dir: Path):
        """Should create table for SQLModel class."""
        model = get_model_by_table_name("test_items", workflow_dir=workflow_dir)
        assert model is not None

        # Should not raise
        ensure_table_exists(model)

        # Verify table exists by inserting a row
        from kurt.db import managed_session

        with managed_session() as session:
            instance = model(name="Test", value=1.5)
            session.add(instance)
            session.commit()

            # Query back
            result = session.exec(select(model)).first()
            assert result is not None
            assert result.name == "Test"
            assert result.value == 1.5

    def test_idempotent(self, tmp_database: Path, workflow_dir: Path):
        """Should not error if table already exists."""
        model = get_model_by_table_name("test_items", workflow_dir=workflow_dir)
        assert model is not None

        # Call multiple times
        ensure_table_exists(model)
        ensure_table_exists(model)
        ensure_table_exists(model)

        # Should work fine
        from kurt.db import managed_session

        with managed_session() as session:
            instance = model(name="After Multiple Calls", value=2.0)
            session.add(instance)

    def test_creates_table_with_json_columns(
        self, tmp_database: Path, workflow_dir_with_json: Path
    ):
        """Should create table with JSON columns."""
        model = get_model_by_table_name(
            "competitor_analysis", workflow_dir=workflow_dir_with_json
        )
        assert model is not None

        ensure_table_exists(model)

        # Verify by inserting data with JSON
        from kurt.db import managed_session

        with managed_session() as session:
            instance = model(
                workflow_id="test-123",
                company="Acme",
                products=["Widget", "Gadget"],
                pricing={"basic": 9.99, "pro": 19.99},
            )
            session.add(instance)
            session.commit()

            result = session.exec(select(model)).first()
            assert result is not None
            assert result.company == "Acme"
            assert result.products == ["Widget", "Gadget"]
            assert result.pricing == {"basic": 9.99, "pro": 19.99}


# ============================================================================
# Tests for find_models_in_workflow
# ============================================================================


class TestFindModelsInWorkflow:
    """Tests for find_models_in_workflow function."""

    def test_finds_all_table_models(self, workflow_dir: Path):
        """Should find all SQLModel classes with table=True."""
        models = find_models_in_workflow(workflow_dir)

        assert len(models) == 2
        table_names = {m.__tablename__ for m in models}
        assert table_names == {"test_items", "test_categories"}

    def test_returns_empty_for_missing_models_file(self, workflow_dir_empty: Path):
        """Should return empty list when models.py doesn't exist."""
        models = find_models_in_workflow(workflow_dir_empty)

        assert models == []

    def test_uses_cwd_when_no_workflow_dir(
        self, workflow_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Should use current working directory when not specified."""
        monkeypatch.chdir(workflow_dir)

        models = find_models_in_workflow()

        assert len(models) == 2


# ============================================================================
# Tests for ensure_all_workflow_tables
# ============================================================================


class TestEnsureAllWorkflowTables:
    """Tests for ensure_all_workflow_tables function."""

    def test_creates_all_tables(self, tmp_database: Path, workflow_dir: Path):
        """Should create all tables defined in models.py."""
        count = ensure_all_workflow_tables(workflow_dir)

        assert count == 2

        # Verify tables exist
        from kurt.db import managed_session

        with managed_session() as session:
            # Should be able to query both tables
            item_model = get_model_by_table_name("test_items", workflow_dir=workflow_dir)
            category_model = get_model_by_table_name(
                "test_categories", workflow_dir=workflow_dir
            )

            session.add(item_model(name="Item1", value=1.0))
            session.add(category_model(category_name="Cat1"))

    def test_returns_zero_for_no_models(
        self, tmp_database: Path, workflow_dir_empty: Path
    ):
        """Should return 0 when no models.py exists."""
        count = ensure_all_workflow_tables(workflow_dir_empty)

        assert count == 0

    def test_idempotent(self, tmp_database: Path, workflow_dir: Path):
        """Should not error if called multiple times."""
        ensure_all_workflow_tables(workflow_dir)
        ensure_all_workflow_tables(workflow_dir)
        count = ensure_all_workflow_tables(workflow_dir)

        assert count == 2


# ============================================================================
# Integration Tests
# ============================================================================


class TestModelUtilsIntegration:
    """Integration tests combining multiple model_utils functions."""

    def test_full_workflow_table_lifecycle(
        self, tmp_database: Path, workflow_dir_with_json: Path
    ):
        """Test finding, creating, and using a workflow table."""
        # Find the model
        model = get_model_by_table_name(
            "competitor_analysis", workflow_dir=workflow_dir_with_json
        )
        assert model is not None

        # Create the table
        ensure_table_exists(model)

        # Use the table
        from kurt.db import managed_session

        with managed_session() as session:
            # Insert
            entry = model(
                workflow_id="wf-001",
                company="TechCorp",
                products=["SaaS Platform", "Mobile App"],
                pricing={"monthly": 99, "annual": 999},
            )
            session.add(entry)
            session.commit()

            # Query
            result = session.exec(
                select(model).where(model.company == "TechCorp")
            ).first()

            assert result is not None
            assert result.workflow_id == "wf-001"
            assert len(result.products) == 2
            assert result.pricing["annual"] == 999
