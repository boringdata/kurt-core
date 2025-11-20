"""Tests for PostgreSQL configuration and .env loading."""

import os
from unittest.mock import patch

import pytest

from kurt.config.base import KurtConfig, get_config_or_default, load_config


@pytest.fixture
def temp_project_dir(tmp_path, monkeypatch):
    """Create a temporary project directory and change to it."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    monkeypatch.chdir(project_dir)
    return project_dir


@pytest.fixture
def kurt_config_file(temp_project_dir):
    """Create a basic kurt.config file."""
    config_file = temp_project_dir / "kurt.config"
    config_file.write_text(
        """# Kurt Project Configuration
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
PATH_PROJECTS="projects"
PATH_RULES="rules"
INDEXING_LLM_MODEL="openai/gpt-4o-mini"
EMBEDDING_MODEL="openai/text-embedding-3-small"
INGESTION_FETCH_ENGINE="trafilatura"
MAX_CONCURRENT_INDEXING=50
TELEMETRY_ENABLED=True
"""
    )
    return config_file


def test_config_with_database_url_field():
    """Test KurtConfig supports DATABASE_URL field."""
    config = KurtConfig(
        DATABASE_URL="postgresql://user:pass@host:5432/db",
        WORKSPACE_ID="workspace-123",
    )

    assert config.DATABASE_URL == "postgresql://user:pass@host:5432/db"
    assert config.WORKSPACE_ID == "workspace-123"


def test_config_with_optional_fields():
    """Test DATABASE_URL and WORKSPACE_ID are optional."""
    config = KurtConfig()

    assert config.DATABASE_URL is None
    assert config.WORKSPACE_ID is None


def test_load_config_from_env(temp_project_dir, kurt_config_file):
    """Test loading DATABASE_URL from .env file."""
    # Create .env file
    env_file = temp_project_dir / ".env"
    env_file.write_text(
        """DATABASE_URL="postgresql://user:pass@host:5432/db"
WORKSPACE_ID="test-workspace"
"""
    )

    # Load config (should read .env)
    config = load_config()

    assert config.DATABASE_URL == "postgresql://user:pass@host:5432/db"
    assert config.WORKSPACE_ID == "test-workspace"


def test_env_overrides_kurt_config(temp_project_dir):
    """Test .env overrides kurt.config for DATABASE_URL."""
    # Create kurt.config with DATABASE_URL
    config_file = temp_project_dir / "kurt.config"
    config_file.write_text(
        """DATABASE_URL="postgresql://old:pass@old.host:5432/db"
WORKSPACE_ID="old-workspace"
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
"""
    )

    # Create .env with different DATABASE_URL
    env_file = temp_project_dir / ".env"
    env_file.write_text(
        """DATABASE_URL="postgresql://new:pass@new.host:5432/db"
WORKSPACE_ID="new-workspace"
"""
    )

    # Load config
    config = load_config()

    # .env should override kurt.config
    assert config.DATABASE_URL == "postgresql://new:pass@new.host:5432/db"
    assert config.WORKSPACE_ID == "new-workspace"


def test_get_config_or_default_with_env(temp_project_dir):
    """Test get_config_or_default reads from .env even without kurt.config."""
    # Create .env file (no kurt.config)
    env_file = temp_project_dir / ".env"
    env_file.write_text(
        """DATABASE_URL="postgresql://user:pass@host:5432/db"
WORKSPACE_ID="test-workspace"
"""
    )

    # Load config
    config = get_config_or_default()

    assert config.DATABASE_URL == "postgresql://user:pass@host:5432/db"
    assert config.WORKSPACE_ID == "test-workspace"


def test_get_config_or_default_without_env(temp_project_dir):
    """Test get_config_or_default returns default when no config or env."""
    # No kurt.config, no .env
    config = get_config_or_default()

    assert config.DATABASE_URL is None
    assert config.WORKSPACE_ID is None
    assert config.PATH_DB == ".kurt/kurt.sqlite"  # Default


@patch.dict(os.environ, {"DATABASE_URL": "postgresql://env:pass@host:5432/db"})
def test_env_vars_from_shell(temp_project_dir, kurt_config_file):
    """Test loading DATABASE_URL from shell environment variables."""
    # Load config (should read from os.environ)
    config = load_config()

    assert config.DATABASE_URL == "postgresql://env:pass@host:5432/db"


def test_config_priority(temp_project_dir):
    """Test configuration priority: shell env > .env > kurt.config."""
    # Create kurt.config
    config_file = temp_project_dir / "kurt.config"
    config_file.write_text(
        """DATABASE_URL="postgresql://config:pass@config.host:5432/db"
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
"""
    )

    # Create .env (should override kurt.config)
    env_file = temp_project_dir / ".env"
    env_file.write_text(
        """DATABASE_URL="postgresql://dotenv:pass@dotenv.host:5432/db"
"""
    )

    # Load config
    config = load_config()

    # .env should win
    assert config.DATABASE_URL == "postgresql://dotenv:pass@dotenv.host:5432/db"


def test_database_url_in_config_file(temp_project_dir):
    """Test DATABASE_URL can be stored in kurt.config (though not recommended)."""
    config_file = temp_project_dir / "kurt.config"
    config_file.write_text(
        """DATABASE_URL="postgresql://user:pass@host:5432/db"
WORKSPACE_ID="workspace-abc"
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
"""
    )

    config = load_config()

    assert config.DATABASE_URL == "postgresql://user:pass@host:5432/db"
    assert config.WORKSPACE_ID == "workspace-abc"


def test_database_url_with_quotes(temp_project_dir):
    """Test DATABASE_URL with different quote styles."""
    # Test with double quotes
    config_file = temp_project_dir / "kurt.config"
    config_file.write_text(
        """DATABASE_URL="postgresql://user:pass@host:5432/db"
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
"""
    )

    config = load_config()
    assert config.DATABASE_URL == "postgresql://user:pass@host:5432/db"

    # Test with single quotes
    config_file.write_text(
        """DATABASE_URL='postgresql://user:pass@host:5432/db'
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
"""
    )

    config = load_config()
    assert config.DATABASE_URL == "postgresql://user:pass@host:5432/db"

    # Test without quotes
    config_file.write_text(
        """DATABASE_URL=postgresql://user:pass@host:5432/db
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
"""
    )

    config = load_config()
    assert config.DATABASE_URL == "postgresql://user:pass@host:5432/db"


def test_config_write_includes_database_url(temp_project_dir):
    """Test update_config writes DATABASE_URL and WORKSPACE_ID."""
    from kurt.config.base import create_config, update_config

    # Create initial config
    config = create_config()

    # Add PostgreSQL settings
    config.DATABASE_URL = "postgresql://user:pass@host:5432/db"
    config.WORKSPACE_ID = "workspace-123"

    # Update config file
    update_config(config)

    # Read file and verify
    config_file = temp_project_dir / "kurt.config"
    content = config_file.read_text()

    assert 'DATABASE_URL="postgresql://user:pass@host:5432/db"' in content
    assert 'WORKSPACE_ID="workspace-123"' in content


def test_config_write_without_database_url(temp_project_dir):
    """Test update_config doesn't write DATABASE_URL if None."""
    from kurt.config.base import create_config, update_config

    # Create config without PostgreSQL
    config = create_config()
    config.DATABASE_URL = None
    config.WORKSPACE_ID = None

    # Update config file
    update_config(config)

    # Read file and verify
    config_file = temp_project_dir / "kurt.config"
    content = config_file.read_text()

    assert "DATABASE_URL" not in content
    assert "WORKSPACE_ID" not in content
