"""
Model configuration support for step-specific settings.

This module provides a declarative way for pipeline models (steps) to expose
their configurable parameters with type hints, defaults, and fallback resolution.

Example usage:

    class EntityClusteringConfig(ModelConfig):
        eps: float = ConfigParam(default=0.25, ge=0.0, le=1.0, description="DBSCAN epsilon")
        min_samples: int = ConfigParam(default=2, ge=1, description="DBSCAN min_samples")
        llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL", description="LLM model")

    @model(name="indexing.entity_clustering", config_schema=EntityClusteringConfig)
    def entity_clustering(sources, writer, config: EntityClusteringConfig, **kwargs):
        clustering = DBSCAN(eps=config.eps, min_samples=config.min_samples)
        ...
"""

from typing import Any, ClassVar, get_type_hints

from pydantic import BaseModel

from kurt.config.base import get_step_config, load_config


class ConfigParam:
    """
    Metadata for a model configuration parameter.

    Defines default value, fallback key, validation constraints, and description.
    Used with ModelConfig to declare step-specific configurable parameters.

    Args:
        default: Default value if not set in config and no fallback
        fallback: Global config key to fall back to (e.g., "INDEXING_LLM_MODEL")
        description: Human-readable description of the parameter
        ge: Greater than or equal constraint (for numeric types)
        le: Less than or equal constraint (for numeric types)

    Example:
        eps: float = ConfigParam(default=0.25, ge=0.0, le=1.0, description="DBSCAN epsilon")
        llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")
    """

    def __init__(
        self,
        default: Any = None,
        fallback: str | None = None,
        description: str = "",
        ge: float | None = None,
        le: float | None = None,
    ):
        self.default = default
        self.fallback = fallback
        self.description = description
        self.ge = ge
        self.le = le

    def __repr__(self) -> str:
        parts = []
        if self.default is not None:
            parts.append(f"default={self.default!r}")
        if self.fallback:
            parts.append(f"fallback={self.fallback!r}")
        if self.ge is not None:
            parts.append(f"ge={self.ge}")
        if self.le is not None:
            parts.append(f"le={self.le}")
        return f"ConfigParam({', '.join(parts)})"


class ModelConfig(BaseModel):
    """
    Base class for model (step) configuration.

    Subclass this to declare configurable parameters for a pipeline step.
    Parameters are loaded from kurt.config using dot notation with fallback resolution.

    Resolution order for each parameter:
    1. Step-specific: MODULE.STEP.PARAM (e.g., INDEXING.ENTITY_CLUSTERING.EPS)
    2. Global fallback: specified via ConfigParam.fallback (e.g., INDEXING_LLM_MODEL)
    3. Default from ConfigParam

    Example:
        class SectionExtractionsConfig(ModelConfig):
            llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")
            batch_size: int = ConfigParam(default=50, ge=1, le=200)
            max_concurrent: int = ConfigParam(fallback="MAX_CONCURRENT_INDEXING")

        # Load config for a specific model
        config = SectionExtractionsConfig.load("indexing.section_extractions")
        print(config.batch_size)  # 50 (default) or value from config
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
                # This allows direct instantiation: CAGConfig(top_k=10) to work
                setattr(cls, name, value.default)

    @classmethod
    def load(cls, model_name: str) -> "ModelConfig":
        """
        Load configuration for this model from kurt.config.

        Converts model name to config key prefix and resolves each parameter
        using the fallback chain: step-specific -> global fallback -> default.

        Args:
            model_name: Full model name (e.g., "indexing.section_extractions")

        Returns:
            ModelConfig instance with resolved values

        Example:
            config = EntityClusteringConfig.load("indexing.entity_clustering")
            # Looks for INDEXING.ENTITY_CLUSTERING.EPS, etc.
        """
        kurt_config = load_config()

        # Convert model name to MODULE and STEP
        # "indexing.section_extractions" -> ("INDEXING", "SECTION_EXTRACTIONS")
        parts = model_name.upper().split(".")
        if len(parts) < 2:
            raise ValueError(f"Model name must be in format 'module.step', got: {model_name}")
        module = parts[0]
        step = "_".join(parts[1:])  # Handle multi-part step names

        # Get type hints for the config class
        type_hints = get_type_hints(cls)

        # Resolve each parameter
        values = {}
        for field_name, param in cls._param_metadata.items():
            # Get raw value from config with fallback resolution
            raw_value = get_step_config(
                kurt_config,
                module=module,
                step=step,
                param=field_name.upper(),
                fallback_key=param.fallback,
                default=param.default,
            )

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
    def get_config_keys(cls, model_name: str) -> dict[str, str]:
        """
        Get the config keys that would be used for this model.

        Useful for documentation and debugging.

        Args:
            model_name: Full model name (e.g., "indexing.section_extractions")

        Returns:
            Dict mapping parameter names to their full config keys

        Example:
            >>> EntityClusteringConfig.get_config_keys("indexing.entity_clustering")
            {'eps': 'INDEXING.ENTITY_CLUSTERING.EPS', 'llm_model': 'INDEXING.ENTITY_CLUSTERING.LLM_MODEL'}
        """
        parts = model_name.upper().split(".")
        if len(parts) < 2:
            raise ValueError(f"Model name must be in format 'module.step', got: {model_name}")
        module = parts[0]
        step = "_".join(parts[1:])

        return {
            field_name: f"{module}.{step}.{field_name.upper()}"
            for field_name in cls._param_metadata
        }

    @classmethod
    def get_param_info(cls) -> dict[str, dict[str, Any]]:
        """
        Get metadata about all configurable parameters.

        Returns:
            Dict mapping parameter names to their metadata (default, fallback, description, etc.)

        Example:
            >>> EntityClusteringConfig.get_param_info()
            {'eps': {'default': 0.25, 'fallback': None, 'description': 'DBSCAN epsilon', ...}}
        """
        return {
            name: {
                "default": param.default,
                "fallback": param.fallback,
                "description": param.description,
                "ge": param.ge,
                "le": param.le,
            }
            for name, param in cls._param_metadata.items()
        }
