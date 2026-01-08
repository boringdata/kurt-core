"""
Kurt configuration module.

This module manages all Kurt configuration including:
- Base configuration (paths, LLM settings, telemetry)
- Integration configs (CMS, Analytics, etc.) stored as prefixed extra fields
- Workflow configs (MAP.*, FETCH.*, etc.) via dot notation
"""

# Re-export base config API (backward compatibility)
from kurt_new.config.base import (
    KurtConfig,
    ModelSettings,
    config_exists,
    config_file_exists,
    create_config,
    get_config_file_path,
    get_config_or_default,
    get_step_config,
    load_config,
    resolve_model_settings,
    update_config,
    validate_config,
)

# Model configuration support for workflows and steps
from kurt_new.config.model_config import ConfigParam, ModelConfig, StepConfig

# Re-export config utilities for integrations
from kurt_new.config.utils import (
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
    "ModelSettings",
    "config_exists",  # deprecated, use config_file_exists
    "config_file_exists",
    "create_config",
    "get_config_file_path",
    "get_config_or_default",
    "get_step_config",
    "load_config",
    "resolve_model_settings",
    "update_config",
    "validate_config",
    # Model configuration
    "ConfigParam",
    "ModelConfig",  # Alias for StepConfig
    "StepConfig",
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
