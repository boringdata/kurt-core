"""
Kurt configuration module.

This module manages all Kurt configuration including:
- Base configuration (paths, LLM settings, telemetry)
- Integration configs (CMS, Analytics, etc.) stored as prefixed extra fields
"""

# Re-export base config API (backward compatibility)
from kurt.config.base import (
    KurtConfig,
    config_exists,
    config_file_exists,
    create_config,
    get_config_file_path,
    get_config_or_default,
    load_config,
    update_config,
    validate_config,
)

# Re-export config utilities for integrations
from kurt.config.utils import (
    config_exists_for_prefix,
    get_available_keys,
    get_nested_value,
    has_placeholder_values,
    load_prefixed_config,
    prefixed_config_exists,
    save_prefixed_config,
    set_nested_value,
)

__all__ = [
    # Base config
    "KurtConfig",
    "config_exists",  # deprecated, use config_file_exists
    "config_file_exists",
    "create_config",
    "get_config_file_path",
    "get_config_or_default",
    "load_config",
    "update_config",
    "validate_config",
    # Config utilities
    "config_exists_for_prefix",
    "get_available_keys",
    "get_nested_value",
    "has_placeholder_values",
    "load_prefixed_config",
    "prefixed_config_exists",  # deprecated, use config_exists_for_prefix
    "save_prefixed_config",
    "set_nested_value",
]
