"""
Pytest configuration for indexing_new tests.

This conftest imports fixtures from the main test suite to make them available
to tests in this directory.
"""

# Import fixtures from main test conftest
# This allows tests here to use tmp_project fixture
pytest_plugins = ["tests.conftest"]
