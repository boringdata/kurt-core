"""Utility package for Kurt."""

# Re-export functions from parent-level utils.py module
# This allows both imports to work:
#   from kurt.utils import calculate_content_hash  (package)
#   from kurt import utils; utils.calculate_content_hash()  (module)

import importlib.util
from pathlib import Path

from kurt.utils.project_utils import extract_section

# Load the sibling utils.py module directly
utils_module_path = Path(__file__).parent.parent / "utils.py"
spec = importlib.util.spec_from_file_location("_kurt_utils_module", utils_module_path)
_utils_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_utils_module)

# Re-export functions from parent utils.py
calculate_content_hash = _utils_module.calculate_content_hash
get_git_commit_hash = _utils_module.get_git_commit_hash
get_file_content_hash = _utils_module.get_file_content_hash
should_force = _utils_module.should_force

__all__ = [
    "calculate_content_hash",
    "get_git_commit_hash",
    "get_file_content_hash",
    "should_force",
    "extract_section",
]
