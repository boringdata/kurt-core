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
    # Test top-level command modules
    top_level_commands = [
        "status",
    ]

    for cmd in top_level_commands:
        try:
            __import__(f"kurt.commands.{cmd}")
        except ImportError as e:
            pytest.fail(f"Failed to import kurt.commands.{cmd}: {e}")
        except NameError as e:
            pytest.fail(f"NameError in kurt.commands.{cmd}: {e}")

    # Test command groups
    command_groups = [
        "content",
        "integrations",
        "admin",
    ]

    for group in command_groups:
        try:
            __import__(f"kurt.commands.{group}")
        except ImportError as e:
            pytest.fail(f"Failed to import kurt.commands.{group}: {e}")
        except NameError as e:
            pytest.fail(f"NameError in kurt.commands.{group}: {e}")

    # Test subcommands within content group
    content_commands = [
        "cluster",
        "fetch",
        "map",
        "index",
        "list",
        "get",
        "delete",
        "stats",
        "list_clusters",
        "sync_metadata",
        "search",
    ]

    for cmd in content_commands:
        try:
            __import__(f"kurt.commands.content.{cmd}")
        except ImportError as e:
            pytest.fail(f"Failed to import kurt.commands.content.{cmd}: {e}")
        except NameError as e:
            pytest.fail(f"NameError in kurt.commands.content.{cmd}: {e}")

    # Test subcommands within integrations group
    integration_commands = [
        "analytics",
        "cms",
        "research",
    ]

    for cmd in integration_commands:
        try:
            __import__(f"kurt.commands.integrations.{cmd}")
        except ImportError as e:
            pytest.fail(f"Failed to import kurt.commands.integrations.{cmd}: {e}")
        except NameError as e:
            pytest.fail(f"NameError in kurt.commands.integrations.{cmd}: {e}")

    # Test subcommands within admin group
    admin_commands = [
        "feedback",
        "migrate",
        "telemetry",
        "project",
    ]

    for cmd in admin_commands:
        try:
            __import__(f"kurt.commands.admin.{cmd}")
        except ImportError as e:
            pytest.fail(f"Failed to import kurt.commands.admin.{cmd}: {e}")
        except NameError as e:
            pytest.fail(f"NameError in kurt.commands.admin.{cmd}: {e}")


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
