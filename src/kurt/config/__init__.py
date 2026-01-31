"""
Kurt configuration module.

This module manages all Kurt configuration including:
- Base configuration (paths, LLM settings, telemetry)
- Workflow / step configuration (ConfigParam, StepConfig)
- Integration configs (CMS, Analytics, etc.) stored as prefixed extra fields
- Workflow configs (MAP.*, FETCH.*, etc.) via dot notation
"""

# Re-export base config API (includes ConfigParam, StepConfig, ModelConfig)
from kurt.config.base import (
    ConfigParam,
    KurtConfig,
    ModelConfig,
    ModelSettings,
    StepConfig,
    config_file_exists,
    create_config,
    get_config_file_path,
    get_config_or_default,
    get_project_root,
    load_config,
    resolve_model_settings,
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
    save_prefixed_config,
    set_nested_value,
)

__all__ = [
    # Base config
    "KurtConfig",
    "ModelSettings",
    "config_file_exists",
    "create_config",
    "get_config_file_path",
    "get_config_or_default",
    "get_project_root",
    "load_config",
    "resolve_model_settings",
    "update_config",
    "validate_config",
    # Workflow / step configuration
    "ConfigParam",
    "ModelConfig",  # Backwards-compatibility alias for StepConfig
    "StepConfig",
    # Config utilities
    "config_exists_for_prefix",
    "get_available_keys",
    "get_nested_value",
    "has_placeholder_values",
    "load_prefixed_config",
    "save_prefixed_config",
    "set_nested_value",
]
