"""
Generic configuration support for workflows and steps.

This module provides a declarative way to expose configurable parameters
with type hints, defaults, and fallback resolution from kurt.config.

Supports two naming patterns:
1. Module-only: "map" -> MAP.MAX_PAGES, MAP.DRY_RUN (for workflow configs)
2. Module.Step: "map.discovery" -> MAP.DISCOVERY.MAX_DEPTH (for step configs)

Step configs can inherit from workflow configs with fallback chain:
    MAP.DISCOVERY.MAX_DEPTH -> MAP.MAX_DEPTH -> default

Example usage:

    # Workflow config (module-only)
    class MapConfig(StepConfig):
        max_pages: int = ConfigParam(default=1000, ge=1, le=10000)
        max_depth: int = ConfigParam(default=3, ge=1, le=10)
        dry_run: bool = ConfigParam(default=False)

    config = MapConfig.from_config("map")
    # Looks for MAP.MAX_PAGES, MAP.MAX_DEPTH, MAP.DRY_RUN

    # Step config with workflow fallback
    class DiscoveryStepConfig(StepConfig):
        # Inherits from workflow: MAP.DISCOVERY.MAX_DEPTH -> MAP.MAX_DEPTH
        max_depth: int = ConfigParam(default=3, workflow_fallback=True)
        # Step-specific param
        timeout: int = ConfigParam(default=30)
        # Global fallback
        llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

    config = DiscoveryStepConfig.from_config("map.discovery")
"""

from typing import Any, ClassVar, get_type_hints

from pydantic import BaseModel

from kurt_new.config.base import config_file_exists, load_config


class ConfigParam:
    """
    Metadata for a configuration parameter.

    Defines default value, fallback key, validation constraints, and description.
    Used with StepConfig to declare configurable parameters.

    Args:
        default: Default value if not set in config and no fallback
        fallback: Global config key to fall back to (e.g., "INDEXING_LLM_MODEL")
        workflow_fallback: If True, falls back to workflow-level param (e.g., MAP.MAX_DEPTH)
        description: Human-readable description of the parameter
        ge: Greater than or equal constraint (for numeric types)
        le: Less than or equal constraint (for numeric types)

    Fallback resolution order:
        1. Step-specific: MAP.DISCOVERY.MAX_DEPTH
        2. Workflow-level (if workflow_fallback=True): MAP.MAX_DEPTH
        3. Global fallback (if fallback set): INDEXING_LLM_MODEL
        4. Default value

    Example:
        # Simple default
        timeout: int = ConfigParam(default=30)

        # Falls back to workflow config
        max_depth: int = ConfigParam(default=3, workflow_fallback=True)

        # Falls back to global config
        llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        # Both workflow and global fallback
        fetch_engine: str = ConfigParam(workflow_fallback=True, fallback="INGESTION_FETCH_ENGINE")
    """

    def __init__(
        self,
        default: Any = None,
        fallback: str | None = None,
        workflow_fallback: bool = False,
        description: str = "",
        ge: float | None = None,
        le: float | None = None,
    ):
        self.default = default
        self.fallback = fallback
        self.workflow_fallback = workflow_fallback
        self.description = description
        self.ge = ge
        self.le = le

    def __repr__(self) -> str:
        parts = []
        if self.default is not None:
            parts.append(f"default={self.default!r}")
        if self.fallback:
            parts.append(f"fallback={self.fallback!r}")
        if self.workflow_fallback:
            parts.append("workflow_fallback=True")
        if self.ge is not None:
            parts.append(f"ge={self.ge}")
        if self.le is not None:
            parts.append(f"le={self.le}")
        return f"ConfigParam({', '.join(parts)})"


class StepConfig(BaseModel):
    """
    Base class for workflow and step configuration.

    Subclass this to declare configurable parameters. Parameters can be loaded
    from kurt.config using dot notation with fallback resolution.

    Supports two naming patterns:
    - Module-only: "map" -> MAP.PARAM (for workflow configs)
    - Module.Step: "map.discovery" -> MAP.DISCOVERY.PARAM (for step configs)

    Resolution order for each parameter:
    1. Step-specific: MODULE.STEP.PARAM (e.g., MAP.DISCOVERY.MAX_DEPTH)
    2. Workflow-level (if workflow_fallback=True): MODULE.PARAM (e.g., MAP.MAX_DEPTH)
    3. Global fallback: specified via ConfigParam.fallback (e.g., INDEXING_LLM_MODEL)
    4. Default from ConfigParam

    Example:
        class MapConfig(StepConfig):
            max_pages: int = ConfigParam(default=1000)
            max_depth: int = ConfigParam(default=3)
            dry_run: bool = ConfigParam(default=False)

        class DiscoveryStepConfig(StepConfig):
            # Inherits from workflow
            max_depth: int = ConfigParam(default=3, workflow_fallback=True)
            # Step-specific
            timeout: int = ConfigParam(default=30)

        # Workflow config
        workflow_config = MapConfig.from_config("map")

        # Step config with workflow fallback
        step_config = DiscoveryStepConfig.from_config("map.discovery")
    """

    # Class variable to store ConfigParam metadata (not a Pydantic field)
    _param_metadata: ClassVar[dict[str, ConfigParam]] = {}

    model_config = {"extra": "forbid"}  # Pydantic v2: Don't allow extra fields

    def __init_subclass__(cls, **kwargs):
        """Collect ConfigParam metadata from class annotations."""
        super().__init_subclass__(**kwargs)

        # Collect ConfigParam instances from class attributes
        cls._param_metadata = {}
        for name, value in list(vars(cls).items()):
            if isinstance(value, ConfigParam):
                cls._param_metadata[name] = value
                # Replace ConfigParam with its default value so Pydantic uses it
                # This allows direct instantiation: MapConfig(max_pages=500) to work
                setattr(cls, name, value.default)

    @classmethod
    def from_config(cls, config_name: str, **overrides) -> "StepConfig":
        """
        Load configuration from kurt.config with optional overrides.

        Supports two naming patterns:
        - Module-only: "map" -> looks for MAP.PARAM
        - Module.Step: "map.discovery" -> looks for MAP.DISCOVERY.PARAM

        For step configs, parameters with workflow_fallback=True will fall back
        to the workflow-level config if not set at step level.

        Args:
            config_name: Config name - "map" or "map.discovery"
            **overrides: Override specific parameters

        Returns:
            StepConfig instance with resolved values

        Example:
            # Module-only (workflow config)
            config = MapConfig.from_config("map")
            # Looks for MAP.MAX_PAGES, MAP.DRY_RUN

            # Module.Step (step config)
            config = DiscoveryStepConfig.from_config("map.discovery")
            # Looks for MAP.DISCOVERY.MAX_DEPTH -> MAP.MAX_DEPTH (if workflow_fallback)

            # With overrides
            config = MapConfig.from_config("map", max_pages=500)
        """
        # If no config file exists, just use defaults + overrides
        if not config_file_exists():
            return cls(**overrides)

        kurt_config = load_config()
        extra = getattr(kurt_config, "__pydantic_extra__", {})

        # Parse config_name into module and optional step
        parts = config_name.upper().split(".")
        module = parts[0]
        step = "_".join(parts[1:]) if len(parts) > 1 else None

        # Get type hints for the config class
        type_hints = get_type_hints(cls)

        # Resolve each parameter
        values = {}
        for field_name, param in cls._param_metadata.items():
            # Check if override provided
            if field_name in overrides:
                values[field_name] = overrides[field_name]
                continue

            param_upper = field_name.upper()
            raw_value = None

            # 1. Try step-specific: MODULE.STEP.PARAM
            if step:
                step_key = f"{module}.{step}.{param_upper}"
                if step_key in extra:
                    raw_value = extra[step_key]

            # 2. Try workflow-level fallback: MODULE.PARAM (if workflow_fallback=True)
            if raw_value is None and param.workflow_fallback:
                workflow_key = f"{module}.{param_upper}"
                if workflow_key in extra:
                    raw_value = extra[workflow_key]

            # 3. Try module-level (for module-only configs): MODULE.PARAM
            if raw_value is None and step is None:
                module_key = f"{module}.{param_upper}"
                if module_key in extra:
                    raw_value = extra[module_key]

            # 4. Try global fallback
            if raw_value is None and param.fallback:
                if hasattr(kurt_config, param.fallback):
                    raw_value = getattr(kurt_config, param.fallback)
                elif param.fallback in extra:
                    raw_value = extra[param.fallback]

            # 5. Use default
            if raw_value is None:
                raw_value = param.default

            # Type coercion based on type hints
            if raw_value is not None and field_name in type_hints:
                target_type = type_hints[field_name]
                raw_value = cls._coerce_type(raw_value, target_type, field_name, param)

            values[field_name] = raw_value

        return cls(**values)

    @classmethod
    def _coerce_type(
        cls, value: Any, target_type: type, field_name: str, param: ConfigParam
    ) -> Any:
        """Coerce a value to the target type with validation."""
        # Handle None
        if value is None:
            return None

        # Handle Optional types
        origin = getattr(target_type, "__origin__", None)
        if origin is type(None):
            return None

        # For Union types (like Optional), get the first non-None type
        if origin is not None:
            args = getattr(target_type, "__args__", ())
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                target_type = non_none_args[0]

        # Already correct type
        if isinstance(value, target_type):
            return value

        # String to numeric conversion (config values are loaded as strings)
        if isinstance(value, str):
            try:
                if target_type is int:
                    value = int(value)
                elif target_type is float:
                    value = float(value)
                elif target_type is bool:
                    value = value.lower() in ("true", "1", "yes", "on")
            except (ValueError, TypeError):
                pass  # Keep original value, let Pydantic validate

        # Validate numeric constraints
        if isinstance(value, (int, float)):
            if param.ge is not None and value < param.ge:
                raise ValueError(f"{field_name} must be >= {param.ge}, got {value}")
            if param.le is not None and value > param.le:
                raise ValueError(f"{field_name} must be <= {param.le}, got {value}")

        return value

    @classmethod
    def get_config_keys(cls, config_name: str) -> dict[str, str]:
        """
        Get the config keys that would be used for this config.

        Useful for documentation and debugging.

        Args:
            config_name: Config name - "map" or "map.discovery"

        Returns:
            Dict mapping parameter names to their full config keys

        Example:
            >>> MapConfig.get_config_keys("map")
            {'max_pages': 'MAP.MAX_PAGES', 'dry_run': 'MAP.DRY_RUN'}

            >>> DiscoveryStepConfig.get_config_keys("map.discovery")
            {'max_depth': 'MAP.DISCOVERY.MAX_DEPTH (-> MAP.MAX_DEPTH)', 'timeout': 'MAP.DISCOVERY.TIMEOUT'}
        """
        parts = config_name.upper().split(".")
        module = parts[0]
        step = "_".join(parts[1:]) if len(parts) > 1 else None

        if step:
            prefix = f"{module}.{step}"
        else:
            prefix = module

        result = {}
        for field_name, param in cls._param_metadata.items():
            key = f"{prefix}.{field_name.upper()}"
            if step and param.workflow_fallback:
                key += f" (-> {module}.{field_name.upper()})"
            if param.fallback:
                key += f" (-> {param.fallback})"
            result[field_name] = key

        return result

    @classmethod
    def get_param_info(cls) -> dict[str, dict[str, Any]]:
        """
        Get metadata about all configurable parameters.

        Returns:
            Dict mapping parameter names to their metadata (default, fallback, description, etc.)

        Example:
            >>> MapConfig.get_param_info()
            {'max_pages': {'default': 1000, 'fallback': None, 'description': '...', ...}}
        """
        return {
            name: {
                "default": param.default,
                "fallback": param.fallback,
                "workflow_fallback": param.workflow_fallback,
                "description": param.description,
                "ge": param.ge,
                "le": param.le,
            }
            for name, param in cls._param_metadata.items()
        }


# Backwards compatibility alias
ModelConfig = StepConfig
