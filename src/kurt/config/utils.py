"""
Generic configuration utilities for Kurt integrations.

This module provides reusable utilities for managing integration configs
(CMS, Analytics, etc.) that are stored in the main kurt.config file with
prefixed keys (e.g., CMS_SANITY_PROD_PROJECT_ID, ANALYTICS_POSTHOG_API_KEY).

Pattern:
    - Configs stored in kurt.config with format: <PREFIX>_<LEVEL1>_<LEVEL2>_..._<KEY>
    - CMS example: CMS_SANITY_PROD_PROJECT_ID (prefix=CMS, levels=[sanity, prod], key=project_id)
    - Analytics example: ANALYTICS_POSTHOG_API_KEY (prefix=ANALYTICS, levels=[posthog], key=api_key)
"""

import json
from typing import Any, Dict, List, Optional

from kurt.config.base import get_config_or_default, update_config


def load_prefixed_config(prefix: str, levels: int = 2) -> Dict[str, Any]:
    """
    Load configuration for a specific prefix from kurt.config.

    This function extracts all fields starting with the given prefix and organizes
    them into a nested dictionary based on the number of levels.

    Args:
        prefix: The prefix to filter by (e.g., "CMS", "ANALYTICS")
        levels: Number of organizational levels after prefix (default: 2)
            - levels=1: PREFIX_PROVIDER_KEY -> {provider: {key: value}}
            - levels=2: PREFIX_PLATFORM_INSTANCE_KEY -> {platform: {instance: {key: value}}}

    Returns:
        Nested dictionary organized by the specified levels

    Example:
        >>> load_prefixed_config("CMS", levels=2)
        {
            "sanity": {
                "prod": {"project_id": "abc123", "token": "sk_..."},
                "staging": {"project_id": "xyz789"}
            }
        }

        >>> load_prefixed_config("ANALYTICS", levels=1)
        {
            "posthog": {"project_id": "phc_123", "api_key": "phx_456"},
            "ga4": {"property_id": "123456789"}
        }
    """
    config = get_config_or_default()

    # Extract fields with the given prefix from __pydantic_extra__
    extra_fields = getattr(config, "__pydantic_extra__", {})
    result: Dict[str, Any] = {}

    for key, value in extra_fields.items():
        if key.startswith(f"{prefix}_"):
            # Parse key: PREFIX_LEVEL1_LEVEL2_..._LEVELM_KEY
            # For levels=2: CMS_SANITY_PROD_PROJECT_ID -> [CMS, SANITY, PROD, PROJECT_ID]
            # For levels=1: ANALYTICS_POSTHOG_API_KEY -> [ANALYTICS, POSTHOG, API_KEY]

            # Split into: PREFIX + levels * LEVEL + KEY
            # Use maxsplit = levels + 1 to get: [PREFIX, LEVEL1, LEVEL2, ..., LEVELn, REST_AS_KEY]
            parts = key.split("_", levels + 1)

            # We expect: PREFIX (1) + levels (n) + KEY (1) = levels + 2 parts
            if len(parts) == levels + 2:
                # Extract levels: skip PREFIX (index 0), take next 'levels' parts
                parsed_levels = [parts[i].lower() for i in range(1, levels + 1)]
                # The rest is the key
                field_key = parts[-1].lower()

                # Build nested dictionary
                current = result
                for level in parsed_levels:
                    if level not in current:
                        current[level] = {}
                    current = current[level]

                # Handle JSON-encoded nested structures
                if isinstance(value, str) and (value.startswith("{") or value.startswith("[")):
                    try:
                        current[field_key] = json.loads(value)
                    except json.JSONDecodeError:
                        current[field_key] = value
                else:
                    current[field_key] = value

    return result


def save_prefixed_config(prefix: str, config_data: Dict[str, Any], levels: int = 2) -> None:
    """
    Save configuration for a specific prefix to kurt.config.

    This function converts a nested dictionary into prefixed keys and saves them
    to the main kurt.config file, preserving other integration configs.

    Args:
        prefix: The prefix to use (e.g., "CMS", "ANALYTICS")
        config_data: Nested dictionary to save
        levels: Number of organizational levels (must match load_prefixed_config)

    Example:
        >>> save_prefixed_config("CMS", {
        ...     "sanity": {
        ...         "prod": {"project_id": "abc123", "token": "sk_..."}
        ...     }
        ... }, levels=2)
        # Writes: CMS_SANITY_PROD_PROJECT_ID=abc123
        #         CMS_SANITY_PROD_TOKEN=sk_...

        >>> save_prefixed_config("ANALYTICS", {
        ...     "posthog": {"project_id": "phc_123"}
        ... }, levels=1)
        # Writes: ANALYTICS_POSTHOG_PROJECT_ID=phc_123
    """
    config = get_config_or_default()

    # Initialize __pydantic_extra__ if not present
    if not hasattr(config, "__pydantic_extra__"):
        config.__pydantic_extra__ = {}

    # Remove existing fields with this prefix (but preserve other prefixes)
    keys_to_remove = [k for k in config.__pydantic_extra__.keys() if k.startswith(f"{prefix}_")]
    for key in keys_to_remove:
        del config.__pydantic_extra__[key]

    # Add new fields with prefix
    def _flatten_and_add(data: Dict[str, Any], path: List[str]) -> None:
        """
        Recursively flatten nested dict and add to config.

        For levels=2: {"sanity": {"prod": {"project_id": "abc"}}}
        - path=[], key=sanity → path=['SANITY'], len=1 < 2 → recurse into sanity
        - path=['SANITY'], key=prod → path=['SANITY','PROD'], len=2 == 2 → at leaf level
          The value is a dict of config keys, so iterate and write each
        """
        for key, value in data.items():
            current_path = path + [key.upper()]

            # Check if we've reached the organizational leaf level
            if len(current_path) == levels:
                # At the final organizational level - value should be a dict of config keys
                if isinstance(value, dict):
                    for config_key, config_value in value.items():
                        field_name = "_".join([prefix] + current_path + [config_key.upper()])

                        # JSON-encode nested structures (like content_type_mappings)
                        if isinstance(config_value, (dict, list)):
                            config.__pydantic_extra__[field_name] = json.dumps(config_value)
                        else:
                            config.__pydantic_extra__[field_name] = config_value
                else:
                    # Edge case: value at organizational level isn't a dict
                    # Just write it directly
                    field_name = "_".join([prefix] + current_path)
                    config.__pydantic_extra__[field_name] = value
            elif len(current_path) < levels:
                # Still traversing organizational levels
                if isinstance(value, dict):
                    _flatten_and_add(value, current_path)
            # else: len > levels, skip (shouldn't happen with proper input)

    _flatten_and_add(config_data, [])
    update_config(config)


def get_nested_value(
    config_data: Dict[str, Any], path: List[str], default: Optional[Any] = None
) -> Optional[Any]:
    """
    Get a value from a nested dictionary using a path.

    Args:
        config_data: The nested dictionary
        path: List of keys to traverse (e.g., ["sanity", "prod", "project_id"])
        default: Default value if path not found

    Returns:
        The value at the path, or default if not found

    Example:
        >>> config = {"sanity": {"prod": {"project_id": "abc123"}}}
        >>> get_nested_value(config, ["sanity", "prod", "project_id"])
        'abc123'
        >>> get_nested_value(config, ["sanity", "staging"], default={})
        {}
    """
    current = config_data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def set_nested_value(config_data: Dict[str, Any], path: List[str], value: Any) -> None:
    """
    Set a value in a nested dictionary using a path.

    Creates intermediate dictionaries as needed.

    Args:
        config_data: The nested dictionary to modify
        path: List of keys to traverse (e.g., ["sanity", "prod", "project_id"])
        value: The value to set

    Example:
        >>> config = {}
        >>> set_nested_value(config, ["sanity", "prod", "project_id"], "abc123")
        >>> config
        {'sanity': {'prod': {'project_id': 'abc123'}}}
    """
    current = config_data
    for key in path[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[path[-1]] = value


def config_exists_for_prefix(prefix: str, levels: int = 2) -> bool:
    """
    Check if any configuration exists for the given prefix.

    Args:
        prefix: The prefix to check (e.g., "CMS", "ANALYTICS")
        levels: Number of organizational levels

    Returns:
        True if at least one config field exists for this prefix

    Example:
        >>> config_exists_for_prefix("CMS")
        True
        >>> config_exists_for_prefix("CUSTOM_INTEGRATION")
        False
    """
    try:
        config_data = load_prefixed_config(prefix, levels)
        return len(config_data) > 0
    except Exception:
        return False


# Backwards compatibility alias
def prefixed_config_exists(prefix: str, levels: int = 2) -> bool:
    """
    Deprecated: Use config_exists_for_prefix() instead.
    Check if any configuration exists for the given prefix.
    """
    return config_exists_for_prefix(prefix, levels)


def has_placeholder_values(config_dict: Dict[str, Any]) -> bool:
    """
    Check if a config dictionary contains placeholder values.

    Args:
        config_dict: Configuration dictionary to check

    Returns:
        True if any value contains "YOUR_" or "PLACEHOLDER"

    Example:
        >>> has_placeholder_values({"project_id": "YOUR_PROJECT_ID"})
        True
        >>> has_placeholder_values({"project_id": "abc123"})
        False
    """
    config_str = json.dumps(config_dict)
    return "YOUR_" in config_str or "PLACEHOLDER" in config_str


def get_available_keys(config_data: Dict[str, Any], level: int = 0) -> List[str]:
    """
    Get all keys at a specific level of the config hierarchy.

    Args:
        config_data: The nested configuration dictionary
        level: Which level to get keys from (0 = top level, 1 = second level, etc.)

    Returns:
        List of keys at the specified level

    Example:
        >>> config = {
        ...     "sanity": {"prod": {...}, "staging": {...}},
        ...     "contentful": {"default": {...}}
        ... }
        >>> get_available_keys(config, level=0)
        ['sanity', 'contentful']
        >>> get_available_keys(config["sanity"], level=0)
        ['prod', 'staging']
    """
    if level == 0:
        return list(config_data.keys())

    # For deeper levels, collect keys from all paths
    keys = set()
    for value in config_data.values():
        if isinstance(value, dict):
            keys.update(get_available_keys(value, level - 1))
    return sorted(keys)
