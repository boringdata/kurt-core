""" CMS map provider.

Delegates to the canonical implementation in engines/.
"""

from kurt.tools.map.engines.cms import CmsEngine

__all__ = ["CmsEngine"]
