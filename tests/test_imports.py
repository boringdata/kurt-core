"""Test that all modules can be imported without errors."""

import pytest


def test_cli_imports():
    """Test that the main CLI module can be imported."""
    try:
        from kurt.cli import main

        assert main is not None
    except ImportError as e:
        pytest.fail(f"Failed to import kurt.cli: {e}")
    except NameError as e:
        pytest.fail(f"NameError in kurt.cli imports: {e}")


def test_command_imports():
    """Test that all command modules can be imported."""
    commands = [
        "cluster_urls",
        "cms",
        "content",
        "fetch",
        "map",
        "migrate",
        "project",
        "research",
        "status",
    ]

    for cmd in commands:
        try:
            __import__(f"kurt.commands.{cmd}")
        except ImportError as e:
            pytest.fail(f"Failed to import kurt.commands.{cmd}: {e}")
        except NameError as e:
            pytest.fail(f"NameError in kurt.commands.{cmd}: {e}")


def test_utils_imports():
    """Test that utils modules can be imported."""
    try:
        from kurt.utils import calculate_content_hash, extract_section

        assert calculate_content_hash is not None
        assert extract_section is not None
    except ImportError as e:
        pytest.fail(f"Failed to import kurt.utils: {e}")
    except NameError as e:
        pytest.fail(f"NameError in kurt.utils: {e}")
