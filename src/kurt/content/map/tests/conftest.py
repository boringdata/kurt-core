"""
Test configuration for map module tests.

Imports shared fixtures from root tests/conftest.py.
"""

# Import shared fixtures from root conftest
import sys
from pathlib import Path

# Add tests directory to path so we can import from tests.conftest
tests_dir = Path(__file__).parents[5] / "tests"
sys.path.insert(0, str(tests_dir))

from conftest import *  # noqa: F401, F403, E402

# Map-specific fixtures can be added here if needed
