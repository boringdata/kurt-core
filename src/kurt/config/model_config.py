"""Backwards-compatibility shim.

All classes have been consolidated into ``kurt.config.base``.
Import from ``kurt.config`` (the package) instead of this module.
"""

from kurt.config.base import ConfigParam, ModelConfig, StepConfig

__all__ = ["ConfigParam", "ModelConfig", "StepConfig"]
