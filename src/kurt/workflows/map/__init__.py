"""Map workflow - discover URLs/files/CMS sources.

For lightweight imports (models only), use:
    from kurt.workflows.map.models import MapDocument, MapStatus

For workflow execution (requires [workflows] extras):
    from kurt.workflows.map.workflow import map_workflow, run_map
"""

from .config import MapConfig
from .models import MapDocument, MapStatus

# NOTE: workflow and steps not imported here to avoid heavy dependencies
# Import directly when needed: from kurt.workflows.map.workflow import map_workflow

__all__ = [
    "MapConfig",
    "MapDocument",
    "MapStatus",
]
