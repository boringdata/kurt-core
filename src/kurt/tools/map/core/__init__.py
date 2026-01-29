"""Map core module - shared mapping logic and utilities."""

from kurt.tools.map.core.base import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.core.storage import MapDocumentStorage
from kurt.tools.map.core.utils import (
    extract_domain,
    get_url_depth,
    is_internal_url,
    normalize_url,
    relative_to_absolute_url,
    should_include_url,
)

__all__ = [
    "BaseMapper",
    "MapperConfig",
    "MapperResult",
    "MapDocumentStorage",
    "normalize_url",
    "is_internal_url",
    "extract_domain",
    "should_include_url",
    "relative_to_absolute_url",
    "get_url_depth",
]
