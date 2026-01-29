"""Tests for unified API key management."""

import os
import pytest

from kurt.tools.api_keys import (
    APIKeyError,
    APIKeyManager,
    configure_engines,
    get_api_key,
    get_key_manager,
    register_engine,
)


class TestAPIKeyManager:
    """Test APIKeyManager class."""

    def test_manager_creation(self):
        """Test creating an API key manager."""
        manager = APIKeyManager()
        assert manager._keys == {}
        assert manager._env_var_map == {}

    def test_register_engine(self):
        """Test registering an engine."""
        manager = APIKeyManager()
        manager.register_engine(
            engine="test_engine",
            env_var="TEST_API_KEY",
            config_key="TEST.API_KEY",
        )

        assert "test_engine" in manager._env_var_map
        assert manager._env_var_map["test_engine"] == "TEST_API_KEY"
        assert manager._config_key_map["test_engine"] == "TEST.API_KEY"

    def test_register_engine_with_instructions(self):
        """Test registering engine with setup instructions."""
        manager = APIKeyManager()
        instructions = "Go to https://example.com to get your key"
        manager.register_engine(
            engine="test",
            env_var="TEST_KEY",
            setup_instructions=instructions,
        )

        assert manager._setup_instructions["test"] == instructions

    def test_add_key(self):
        """Test adding an API key."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY")
        manager.add_key("test", "key123")

        assert "key123" in manager._keys["test"]

    def test_add_key_unregistered_engine(self):
        """Test adding key to unregistered engine raises."""
        manager = APIKeyManager()
        with pytest.raises(ValueError, match="not registered"):
            manager.add_key("unknown", "key123")

    def test_get_key_from_environment(self, monkeypatch):
        """Test getting key from environment variable."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_API_KEY")
        monkeypatch.setenv("TEST_API_KEY", "env_key")

        key = manager.get_key("test")
        assert key == "env_key"

    def test_get_key_from_loaded_keys(self):
        """Test getting key from previously loaded keys."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_API_KEY")
        manager.add_key("test", "loaded_key")

        key = manager.get_key("test", raise_on_missing=False)
        assert key == "loaded_key"

    def test_get_key_priority_env_over_loaded(self, monkeypatch):
        """Test that environment variable takes priority."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_API_KEY")
        manager.add_key("test", "loaded_key")
        monkeypatch.setenv("TEST_API_KEY", "env_key")

        key = manager.get_key("test")
        assert key == "env_key"

    def test_get_key_missing_raises(self):
        """Test that missing key raises APIKeyError."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_API_KEY")

        with pytest.raises(APIKeyError):
            manager.get_key("test", raise_on_missing=True)

    def test_get_key_missing_returns_none(self):
        """Test that missing key returns None when not raising."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_API_KEY")

        key = manager.get_key("test", raise_on_missing=False)
        assert key is None

    def test_get_key_unregistered_engine(self):
        """Test getting key from unregistered engine raises."""
        manager = APIKeyManager()
        with pytest.raises(ValueError, match="not registered"):
            manager.get_key("unknown")

    def test_get_all_keys(self, monkeypatch):
        """Test getting all keys with rotation."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_API_KEY")
        manager.add_key("test", "key1")
        manager.add_key("test", "key2")
        monkeypatch.setenv("TEST_API_KEY", "env_key")

        keys = manager.get_all_keys("test")
        assert keys[0] == "env_key"  # Env key first
        assert "key1" in keys
        assert "key2" in keys

    def test_load_from_config(self):
        """Test loading keys from config dictionary."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY", "INTEGRATIONS.TEST.KEY")

        config = {
            "INTEGRATIONS": {
                "TEST": {"KEY": "config_key"},
            },
        }
        manager.load_from_config(config)

        key = manager.get_key("test", raise_on_missing=False)
        assert key == "config_key"

    def test_load_from_config_nested(self):
        """Test loading from deeply nested config."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY", "INTEGRATIONS.TEST.API.TOKEN")

        config = {
            "INTEGRATIONS": {
                "TEST": {
                    "API": {"TOKEN": "nested_key"},
                },
            },
        }
        manager.load_from_config(config)

        key = manager.get_key("test", raise_on_missing=False)
        assert key == "nested_key"

    def test_load_from_config_missing_key(self):
        """Test loading from config with missing key doesn't error."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY", "MISSING.KEY")

        config = {"OTHER": "value"}
        # Should not raise
        manager.load_from_config(config)

        key = manager.get_key("test", raise_on_missing=False)
        assert key is None

    def test_validate_key(self):
        """Test API key validation."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY")

        assert manager.validate_key("test", "valid_key") is True
        assert manager.validate_key("test", "") is False
        assert manager.validate_key("test", None) is False

    def test_validate_key_custom_function(self):
        """Test API key validation with custom function."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY")

        def validate_length(key):
            return len(key) >= 10

        assert manager.validate_key("test", "short", validate_length) is False
        assert manager.validate_key("test", "long_enough_key", validate_length) is True

    def test_validate_key_custom_raises(self):
        """Test validation function that raises."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY")

        def bad_validator(key):
            raise ValueError("Validation failed")

        assert manager.validate_key("test", "key", bad_validator) is False

    def test_create_error_message(self):
        """Test error message includes setup instructions."""
        manager = APIKeyManager()
        manager.register_engine(
            "test",
            "TEST_KEY",
            "TEST.KEY",
            "Visit https://example.com for your key",
        )

        error = manager._create_api_key_error("test")
        assert "TEST_KEY" in str(error)
        assert "TEST.KEY" in str(error)
        assert "https://example.com" in str(error)

    def test_list_engines(self):
        """Test listing registered engines."""
        manager = APIKeyManager()
        manager.register_engine("engine1", "KEY1")
        manager.register_engine("engine2", "KEY2")

        engines = manager.list_engines()
        assert "engine1" in engines
        assert "engine2" in engines

    def test_is_configured(self, monkeypatch):
        """Test checking if engine is configured."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY")

        assert manager.is_configured("test") is False

        monkeypatch.setenv("TEST_KEY", "key_value")
        assert manager.is_configured("test") is True

    def test_is_configured_unregistered(self):
        """Test is_configured for unregistered engine."""
        manager = APIKeyManager()
        assert manager.is_configured("unknown") is False


class TestGlobalKeyManager:
    """Test global key manager functions."""

    def test_get_key_manager(self):
        """Test getting global key manager."""
        manager = get_key_manager()
        assert isinstance(manager, APIKeyManager)

    def test_register_engine_global(self):
        """Test registering engine globally."""
        manager = get_key_manager()
        initial_count = len(manager.list_engines())

        register_engine("global_test", "GLOBAL_TEST_KEY")

        updated_count = len(manager.list_engines())
        assert updated_count >= initial_count

    def test_get_api_key_global(self, monkeypatch):
        """Test getting API key from global manager."""
        register_engine("global_get_test", "GLOBAL_GET_TEST_KEY")
        monkeypatch.setenv("GLOBAL_GET_TEST_KEY", "global_value")

        key = get_api_key("global_get_test")
        assert key == "global_value"

    def test_configure_engines(self):
        """Test that configure_engines registers known engines."""
        manager = get_key_manager()
        configure_engines()

        assert "apify" in manager.list_engines()
        assert "firecrawl" in manager.list_engines()
        assert "tavily" in manager.list_engines()

    def test_apify_setup_instructions(self):
        """Test that Apify has setup instructions."""
        manager = get_key_manager()
        configure_engines()

        assert "apify" in manager._setup_instructions
        assert "https://console.apify.com" in manager._setup_instructions["apify"]


class TestAPIKeyError:
    """Test APIKeyError exception."""

    def test_error_creation(self):
        """Test creating an API key error."""
        error = APIKeyError("Test error message")
        assert str(error) == "Test error message"

    def test_error_is_exception(self):
        """Test that APIKeyError is an Exception."""
        error = APIKeyError("Test")
        assert isinstance(error, Exception)


class TestKeyRotation:
    """Test API key rotation strategies."""

    def test_multiple_keys_for_rotation(self, monkeypatch):
        """Test managing multiple keys for rotation."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY")
        manager.add_key("test", "key1")
        manager.add_key("test", "key2")
        manager.add_key("test", "key3")

        keys = manager.get_all_keys("test")
        assert len(keys) == 3
        assert all(k in keys for k in ["key1", "key2", "key3"])

    def test_env_key_included_in_rotation(self, monkeypatch):
        """Test that environment key is included in rotation."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY")
        manager.add_key("test", "key1")
        monkeypatch.setenv("TEST_KEY", "env_key")

        keys = manager.get_all_keys("test")
        assert "env_key" in keys
        assert "key1" in keys
        assert keys[0] == "env_key"  # Env key first

    def test_no_duplicate_keys_in_rotation(self):
        """Test that duplicate keys are not added twice."""
        manager = APIKeyManager()
        manager.register_engine("test", "TEST_KEY")
        manager.add_key("test", "key1")
        manager.add_key("test", "key1")  # Add same key twice

        keys = manager.get_all_keys("test")
        assert keys.count("key1") == 1
