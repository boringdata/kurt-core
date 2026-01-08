"""
Unit tests for Database Abstraction.

Tests get_database_client factory, session management, and model mixins.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlmodel import SQLModel

from kurt_new.db import (
    ConfidenceMixin,
    EmbeddingMixin,
    LLMTrace,
    get_session,
    init_database,
    managed_session,
)
from kurt_new.db.base import DatabaseClient, get_database_client
from kurt_new.db.postgresql import PostgreSQLClient
from kurt_new.db.sqlite import SQLiteClient

# ============================================================================
# Database Client Factory Tests
# ============================================================================


class TestGetDatabaseClient:
    """Test get_database_client() factory."""

    def test_sqlite_by_default(self, monkeypatch):
        """Returns SQLiteClient when no DATABASE_URL."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        client = get_database_client()
        assert isinstance(client, SQLiteClient)

    def test_postgres_with_postgres_url(self, monkeypatch):
        """Returns PostgreSQLClient with postgres:// URL."""
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")
        client = get_database_client()
        assert isinstance(client, PostgreSQLClient)

    def test_postgres_with_postgresql_url(self, monkeypatch):
        """Returns PostgreSQLClient with postgresql:// URL."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
        client = get_database_client()
        assert isinstance(client, PostgreSQLClient)

    def test_sqlite_with_sqlite_url(self, monkeypatch):
        """Returns SQLiteClient with sqlite:// URL (or non-postgres URL)."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        client = get_database_client()
        # Note: Current implementation defaults to SQLite if not postgres
        assert isinstance(client, SQLiteClient)

    def test_database_client_is_abstract(self):
        """DatabaseClient is abstract base class."""
        assert hasattr(DatabaseClient, "get_database_url")
        assert hasattr(DatabaseClient, "init_database")
        assert hasattr(DatabaseClient, "get_session")

    def test_sqlite_client_mode_name(self, monkeypatch):
        """SQLiteClient returns 'sqlite' as mode name."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        client = get_database_client()
        assert client.get_mode_name() == "sqlite"

    def test_postgresql_client_mode_name(self, monkeypatch):
        """PostgreSQLClient returns 'postgresql' as mode name."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
        client = get_database_client()
        assert client.get_mode_name() == "postgresql"


# ============================================================================
# Session Management Tests
# ============================================================================


class TestSessionManagement:
    """Test session management functions."""

    def test_init_database_creates_tables(self, tmp_path, monkeypatch):
        """init_database() creates all SQLModel tables."""
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        try:
            init_database()

            # Check tables exist
            db_path = tmp_path / ".kurt" / "kurt.sqlite"
            assert db_path.exists()

            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            assert "llm_traces" in tables
        finally:
            os.chdir(original_cwd)

    def test_managed_session_commits_on_success(self, tmp_database):
        """managed_session commits on successful exit."""
        with managed_session() as session:
            trace = LLMTrace(
                workflow_id="w",
                step_name="s",
                model="m",
                prompt="p",
                response="r",
            )
            session.add(trace)

        # Verify committed
        with managed_session() as session:
            from sqlmodel import select

            result = session.exec(select(LLMTrace)).all()
        assert len(result) == 1

    def test_managed_session_rollbacks_on_error(self, tmp_database):
        """managed_session rollbacks on exception."""
        try:
            with managed_session() as session:
                trace = LLMTrace(
                    workflow_id="w",
                    step_name="s",
                    model="m",
                    prompt="p",
                    response="r",
                )
                session.add(trace)
                raise ValueError("test error")
        except ValueError:
            pass

        # Verify rolled back
        with managed_session() as session:
            from sqlmodel import select

            result = session.exec(select(LLMTrace)).all()
        assert len(result) == 0

    def test_get_session_returns_session(self, tmp_database):
        """get_session() returns a Session instance."""
        session = get_session()
        assert session is not None
        session.close()

    def test_managed_session_with_existing_session(self, tmp_database):
        """managed_session with existing session passes it through."""
        outer_session = get_session()
        try:
            with managed_session(outer_session) as inner_session:
                assert inner_session is outer_session
        finally:
            outer_session.close()


# ============================================================================
# Mixins Tests
# ============================================================================


class TestMixins:
    """Test database model mixins."""

    def test_timestamp_mixin_defaults(self, tmp_database):
        """TimestampMixin sets created_at and updated_at."""
        # LLMTrace uses TimestampMixin
        trace = LLMTrace(
            workflow_id="w",
            step_name="s",
            model="m",
            prompt="p",
            response="r",
        )
        assert trace.created_at is not None
        assert trace.updated_at is not None

    def test_tenant_mixin_fields(self, tmp_database):
        """TenantMixin has user_id and workspace_id."""
        # LLMTrace uses TenantMixin
        trace = LLMTrace(
            workflow_id="w",
            step_name="s",
            model="m",
            prompt="p",
            response="r",
            user_id="user-123",
            workspace_id="ws-456",
        )
        assert trace.user_id == "user-123"
        assert trace.workspace_id == "ws-456"

    def test_tenant_mixin_optional_fields(self, tmp_database):
        """TenantMixin fields are optional."""
        trace = LLMTrace(
            workflow_id="w",
            step_name="s",
            model="m",
            prompt="p",
            response="r",
        )
        assert trace.user_id is None
        assert trace.workspace_id is None

    def test_confidence_mixin_validation_valid(self):
        """ConfidenceMixin validates confidence 0-1."""

        class TestModel(ConfidenceMixin, SQLModel):
            pass

        model = TestModel(confidence=0.85)
        assert model.confidence == 0.85

        model_zero = TestModel(confidence=0.0)
        assert model_zero.confidence == 0.0

        model_one = TestModel(confidence=1.0)
        assert model_one.confidence == 1.0

    def test_confidence_mixin_validation_too_high(self):
        """ConfidenceMixin rejects confidence > 1."""

        class TestModel(ConfidenceMixin, SQLModel):
            pass

        with pytest.raises(ValidationError):
            TestModel(confidence=1.5)

    def test_confidence_mixin_validation_too_low(self):
        """ConfidenceMixin rejects confidence < 0."""

        class TestModel(ConfidenceMixin, SQLModel):
            pass

        with pytest.raises(ValidationError):
            TestModel(confidence=-0.1)

    def test_embedding_mixin_stores_bytes(self):
        """EmbeddingMixin stores embedding as bytes."""

        class TestModel(EmbeddingMixin, SQLModel):
            pass

        embedding = b"\x00\x01\x02\x03"
        model = TestModel(embedding=embedding)
        assert model.embedding == embedding

    def test_embedding_mixin_optional(self):
        """EmbeddingMixin embedding is optional."""

        class TestModel(EmbeddingMixin, SQLModel):
            pass

        model = TestModel()
        assert model.embedding is None


# ============================================================================
# SQLiteClient Tests
# ============================================================================


class TestSQLiteClient:
    """Test SQLiteClient specific behavior."""

    def test_get_database_path_default(self, tmp_path, monkeypatch):
        """Default path is .kurt/kurt.sqlite in cwd."""
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        monkeypatch.delenv("DATABASE_URL", raising=False)

        try:
            client = SQLiteClient()
            path = client.get_database_path()
            assert path == tmp_path / ".kurt" / "kurt.sqlite"
        finally:
            os.chdir(original_cwd)

    def test_get_database_path_custom(self):
        """Custom path is used when provided."""
        custom_path = Path("/tmp/custom/test.db")
        client = SQLiteClient(db_path=custom_path)
        assert client.get_database_path() == custom_path

    def test_get_database_url(self, tmp_path):
        """Returns sqlite:// URL."""
        db_path = tmp_path / "test.db"
        client = SQLiteClient(db_path=db_path)
        url = client.get_database_url()
        assert url.startswith("sqlite:///")
        assert str(db_path) in url

    def test_check_database_exists_false(self, tmp_path):
        """Returns False when database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"
        client = SQLiteClient(db_path=db_path)
        assert client.check_database_exists() is False

    def test_check_database_exists_true(self, tmp_path):
        """Returns True when database exists."""
        db_path = tmp_path / ".kurt" / "kurt.sqlite"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()

        client = SQLiteClient(db_path=db_path)
        assert client.check_database_exists() is True


# ============================================================================
# PostgreSQLClient Tests
# ============================================================================


class TestPostgreSQLClient:
    """Test PostgreSQLClient specific behavior."""

    def test_get_database_url(self):
        """Returns the provided database URL."""
        url = "postgresql://user:pass@host:5432/db"
        client = PostgreSQLClient(url)
        assert client.get_database_url() == url

    def test_async_url_conversion_postgresql(self):
        """Converts postgresql:// to postgresql+asyncpg://."""
        client = PostgreSQLClient("postgresql://user:pass@host/db")
        async_url = client._get_async_database_url()
        assert async_url.startswith("postgresql+asyncpg://")

    def test_async_url_conversion_postgres(self):
        """Converts postgres:// to postgresql+asyncpg://."""
        client = PostgreSQLClient("postgres://user:pass@host/db")
        async_url = client._get_async_database_url()
        assert async_url.startswith("postgresql+asyncpg://")

    def test_mode_name(self):
        """Returns 'postgresql' as mode name."""
        client = PostgreSQLClient("postgresql://user:pass@host/db")
        assert client.get_mode_name() == "postgresql"
