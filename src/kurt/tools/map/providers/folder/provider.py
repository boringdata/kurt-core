""" Folder map provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.map.engines.folder import FolderEngine

__all__ = ["FolderEngine"]
