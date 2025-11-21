"""
Pytest configuration for fetch tests.

Imports shared fixtures from the main test suite (tests/conftest.py).
"""

# Import all fixtures from main conftest
import sys
from pathlib import Path

from tests.conftest import *  # noqa: F401, F403

# Add tests directory to path so we can import from tests.conftest
tests_dir = Path(__file__).parent.parent.parent.parent.parent / "tests"
sys.path.insert(0, str(tests_dir.parent))
