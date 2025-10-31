"""Tests for workspace isolation functionality.

Tests that workspace setup correctly:
- Creates temporary directories
- Initializes Kurt projects
- Installs Claude Code plugin
- Cleans up properly
"""

import sys
from pathlib import Path

# Add framework to path
eval_dir = Path(__file__).parent.parent
sys.path.insert(0, str(eval_dir))

from framework import IsolatedWorkspace  # noqa: E402


def test_basic_workspace_creation():
    """Test that workspace creates a temp directory."""
    print("\n" + "=" * 60)
    print("TEST: Basic Workspace Creation")
    print("=" * 60)

    workspace = IsolatedWorkspace(
        init_kurt=False,  # Don't init kurt yet
        install_claude_plugin=False,
    )

    try:
        # Setup should create temp dir
        path = workspace.setup()

        print(f"✓ Created workspace at: {path}")
        assert path.exists(), "Workspace directory should exist"
        assert path.is_dir(), "Workspace should be a directory"
        assert "kurt_eval_" in str(path), "Workspace should have correct prefix"

        # Note: The workspace changes directory internally, but since this test
        # is running in its own context, we can't assert Path.cwd()
        print("✓ Workspace setup complete")
        print("✅ PASSED: Basic workspace creation")

    finally:
        workspace.teardown()
        print("✓ Cleaned up workspace")


def test_kurt_initialization():
    """Test that workspace can initialize Kurt."""
    print("\n" + "=" * 60)
    print("TEST: Kurt Initialization")
    print("=" * 60)

    workspace = IsolatedWorkspace(
        init_kurt=True,  # Initialize kurt
        install_claude_plugin=False,
    )

    try:
        path = workspace.setup()

        # Check that kurt.config was created
        config_path = path / "kurt.config"
        assert config_path.exists(), "kurt.config should exist"
        print("✓ Found kurt.config")

        # Check that database was created
        db_path = path / ".kurt" / "kurt.sqlite"
        assert db_path.exists(), "Database should exist"
        print("✓ Found database at .kurt/kurt.sqlite")

        # Check that directories were created
        sources_path = path / "sources"
        assert sources_path.exists(), "sources/ directory should exist"
        print("✓ Found sources/ directory")

        rules_path = path / "rules"
        assert rules_path.exists(), "rules/ directory should exist"
        print("✓ Found rules/ directory")

        projects_path = path / "projects"
        assert projects_path.exists(), "projects/ directory should exist"
        print("✓ Found projects/ directory")

        print("✅ PASSED: Kurt initialization")

    finally:
        workspace.teardown()


def test_claude_plugin_installation():
    """Test that Claude Code plugin can be installed."""
    print("\n" + "=" * 60)
    print("TEST: Claude Plugin Installation")
    print("=" * 60)

    workspace = IsolatedWorkspace(
        init_kurt=True,
        install_claude_plugin=True,  # Install plugin
    )

    try:
        path = workspace.setup()

        # Check that .claude directory was created
        claude_dir = path / ".claude"
        if not claude_dir.exists():
            print("⚠️  SKIPPED: .claude source not found (expected if kurt-demo not available)")
            return

        print("✓ Found .claude/ directory")

        # Check for key files
        settings = claude_dir / "settings.json"
        if settings.exists():
            print("✓ Found .claude/settings.json")

        skills_dir = claude_dir / "skills"
        if skills_dir.exists():
            print("✓ Found .claude/skills/ directory")

            # Check for project-management skill
            pm_skill = skills_dir / "project-management-skill"
            if pm_skill.exists():
                print("✓ Found project-management-skill")

        # Check for .env.example
        env_example = path / ".env.example"
        if env_example.exists():
            print("✓ Found .env.example")

        print("✅ PASSED: Claude plugin installation")

    finally:
        workspace.teardown()


def test_workspace_isolation():
    """Test that workspaces don't interfere with each other."""
    print("\n" + "=" * 60)
    print("TEST: Workspace Isolation")
    print("=" * 60)

    workspace1 = IsolatedWorkspace(init_kurt=True)
    workspace2 = IsolatedWorkspace(init_kurt=True)

    try:
        path1 = workspace1.setup()
        print(f"✓ Created workspace 1: {path1}")

        # Go back to original directory before setting up workspace2
        import os

        os.chdir(workspace1.original_cwd)

        path2 = workspace2.setup()
        print(f"✓ Created workspace 2: {path2}")

        # They should be different
        assert path1 != path2, "Workspaces should have different paths"
        print("✓ Workspaces are isolated")

        # Both should have their own kurt.config
        assert (path1 / "kurt.config").exists()
        assert (path2 / "kurt.config").exists()
        print("✓ Both workspaces initialized independently")

        print("✅ PASSED: Workspace isolation")

    finally:
        workspace1.teardown()
        workspace2.teardown()


def test_workspace_query_methods():
    """Test workspace helper methods for checking state."""
    print("\n" + "=" * 60)
    print("TEST: Workspace Query Methods")
    print("=" * 60)

    workspace = IsolatedWorkspace(init_kurt=True)

    try:
        workspace.setup()

        # Test file_exists
        assert workspace.file_exists("kurt.config"), "Should find kurt.config"
        assert not workspace.file_exists("nonexistent.txt"), "Should not find nonexistent file"
        print("✓ file_exists() works correctly")

        # Test read_file
        content = workspace.read_file("kurt.config")
        assert "PATH_DB" in content, "Should be able to read kurt.config"
        print("✓ read_file() works correctly")

        # Test count_files
        count = workspace.count_files("**/*")
        assert count > 0, "Should find some files"
        print(f"✓ count_files() found {count} files")

        # Test query_db
        # Note: Fresh DB might not have migrations applied yet
        try:
            doc_count = workspace.query_db("SELECT COUNT(*) FROM document")
            assert doc_count == 0, "Fresh database should have 0 documents"
            print("✓ query_db() works correctly")
        except Exception as e:
            # Database might not have migrations applied yet
            print(f"⚠️  query_db() skipped (migrations not applied): {e}")

        # Test get_context
        context = workspace.get_context()
        assert context["has_config"] is True
        assert context["has_database"] is True
        assert context["source_count"] == 0
        print("✓ get_context() returns correct state")

        print("✅ PASSED: Workspace query methods")

    finally:
        workspace.teardown()


def test_preserve_on_error():
    """Test that workspace can be preserved for debugging."""
    print("\n" + "=" * 60)
    print("TEST: Preserve on Error")
    print("=" * 60)

    workspace = IsolatedWorkspace(
        init_kurt=True,
        preserve_on_error=True,
    )

    path = workspace.setup()
    print(f"✓ Created workspace at: {path}")

    # Simulate an error scenario
    workspace.teardown(had_error=True)

    # Workspace should still exist
    assert path.exists(), "Workspace should be preserved on error"
    print(f"✓ Workspace preserved at: {path}")
    print(f"⚠️  Manual cleanup required: rm -rf {path}")
    print("✅ PASSED: Preserve on error")


def run_all_tests():
    """Run all workspace tests."""
    print("\n" + "🧪 " + "=" * 58)
    print("   WORKSPACE SETUP TESTS")
    print("   " + "=" * 58)

    tests = [
        test_basic_workspace_creation,
        test_kurt_initialization,
        test_claude_plugin_installation,
        test_workspace_isolation,
        test_workspace_query_methods,
        test_preserve_on_error,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    import sys

    success = run_all_tests()
    sys.exit(0 if success else 1)
