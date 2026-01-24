"""Map workflow - discover URLs/files/CMS sources.

For lightweight imports (models only), use:
    from kurt.tools.map.models import MapDocument, MapStatus

For CLI commands, use:
    from kurt.tools.map.cli import map_cmd

Note: config, models, and CLI have moved to kurt.tools.map.
This module re-exports for backward compatibility.
"""

# Re-export from tools/ for backward compatibility
from kurt.tools.map.config import MapConfig
from kurt.tools.map.models import MapDocument, MapStatus

__all__ = [
    "MapConfig",
    "MapDocument",
    "MapStatus",
]
