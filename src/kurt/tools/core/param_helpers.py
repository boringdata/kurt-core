"""
Parameter helpers for dual input/config patterns.

All Kurt tools support two input styles:
1. Executor style (flat): input_data + config fields at top level
2. Direct API style (nested): inputs + config=ConfigModel(...)

This module provides a mixin and helper to reduce boilerplate for this pattern.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

# Type variables for generic typing
InputT = TypeVar("InputT", bound=BaseModel)
ConfigT = TypeVar("ConfigT", bound=BaseModel)


class DualInputMixin:
    """
    Mixin for Pydantic models that support dual input/config patterns.

    Tool Params classes inherit from this to get `get_inputs_from_fields()` and
    `get_config_from_fields()` helper methods.

    Usage:
        class MyToolParams(DualInputMixin, BaseModel):
            # Executor style (flat)
            input_data: list[MyInput] = Field(default_factory=list)

            # Direct API style (nested)
            inputs: list[MyInput] = Field(default_factory=list)
            config: MyConfig | None = Field(default=None)

            # Flat config fields (for executor compatibility)
            concurrency: int = Field(default=5)
            timeout_ms: int = Field(default=30000)

            def get_inputs(self) -> list[MyInput]:
                return self.get_inputs_from_fields("input_data", "inputs")

            def get_config(self) -> MyConfig:
                return self.get_config_from_fields(
                    "config", MyConfig, ["concurrency", "timeout_ms"]
                )

    Note: Each tool must implement `get_inputs()` and `get_config()` since they
    have tool-specific logic (e.g., field names, validation, conversion).
    The mixin provides the common pattern implementation via helper methods.
    """

    def get_inputs_from_fields(
        self,
        primary_field: str = "input_data",
        fallback_field: str = "inputs",
    ) -> list[Any]:
        """
        Get inputs from either the primary or fallback field.

        Args:
            primary_field: Name of primary input field (executor style)
            fallback_field: Name of fallback field (API style)

        Returns:
            List of input items
        """
        primary = getattr(self, primary_field, None)
        if primary:
            return list(primary)
        fallback = getattr(self, fallback_field, None)
        return list(fallback) if fallback else []

    def get_config_from_fields(
        self,
        config_field: str,
        config_class: type[ConfigT],
        field_names: list[str],
    ) -> ConfigT:
        """
        Get config from nested config field or build from flat fields.

        Args:
            config_field: Name of nested config field
            config_class: Pydantic model class for config
            field_names: List of flat field names to extract

        Returns:
            Config instance

        Raises:
            ValueError: If config cannot be built (missing required fields)
        """
        # Try nested config first
        nested = getattr(self, config_field, None)
        if nested is not None:
            return nested

        # Build from flat fields
        return build_config_from_flat_fields(self, config_class, field_names)


def build_config_from_flat_fields(
    params: BaseModel,
    config_class: type[ConfigT],
    field_names: list[str],
) -> ConfigT:
    """
    Build a config instance from flat fields on a params model.

    Args:
        params: The params model instance with flat fields
        config_class: The config Pydantic model class
        field_names: List of field names to extract

    Returns:
        Config instance built from flat fields

    Example:
        config = build_config_from_flat_fields(
            params,
            FetchToolConfig,
            ["engine", "concurrency", "timeout_ms", "retries"]
        )
    """
    config_dict = {}
    for field_name in field_names:
        if hasattr(params, field_name):
            value = getattr(params, field_name)
            if value is not None:
                config_dict[field_name] = value

    return config_class(**config_dict)
