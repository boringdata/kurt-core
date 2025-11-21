"""Conftest for indexing tests - imports fixtures from root conftest."""

import sys
from pathlib import Path

# Add project root to path to import root conftest fixtures
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import fixtures from root conftest
pytest_plugins = ["tests.conftest"]
