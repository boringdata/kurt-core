"""Tests for agent workflow registry."""

from __future__ import annotations

from textwrap import dedent
from unittest.mock import patch


class TestListDefinitions:
    """Tests for list_definitions function."""

    def test_list_empty_directory(self, tmp_path):
        """Test listing definitions from empty directory."""
        from kurt.workflows.agents.registry import list_definitions

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = list_definitions()

        assert result == []

    def test_list_single_workflow(self, tmp_path):
        """Test listing a single workflow definition."""
        from kurt.workflows.agents.registry import list_definitions

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        workflow_file = workflows_dir / "test-workflow.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: test-workflow
            title: Test Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            Test body.
        """).strip()
        )

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = list_definitions()

        assert len(result) == 1
        assert result[0].name == "test-workflow"
        assert result[0].title == "Test Workflow"

    def test_list_multiple_workflows(self, tmp_path):
        """Test listing multiple workflow definitions."""
        from kurt.workflows.agents.registry import list_definitions

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        for i in range(3):
            workflow_file = workflows_dir / f"workflow-{i}.md"
            workflow_file.write_text(
                dedent(f"""
                ---
                name: workflow-{i}
                title: Workflow {i}
                agent:
                  model: claude-sonnet-4-20250514
                ---

                Body {i}.
            """).strip()
            )

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = list_definitions()

        assert len(result) == 3
        names = [w.name for w in result]
        assert "workflow-0" in names
        assert "workflow-1" in names
        assert "workflow-2" in names

    def test_list_ignores_invalid_files(self, tmp_path):
        """Test that invalid and non-markdown files are handled correctly."""
        from kurt.workflows.agents.registry import list_definitions

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Valid workflow with frontmatter
        valid_file = workflows_dir / "valid.md"
        valid_file.write_text(
            dedent("""
            ---
            name: valid-workflow
            title: Valid Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            Valid body.
        """).strip()
        )

        # Markdown file without frontmatter - still parses (uses filename as name)
        no_frontmatter = workflows_dir / "simple.md"
        no_frontmatter.write_text("Just some text without frontmatter")

        # Non-markdown file - should be ignored by glob("*.md")
        other_file = workflows_dir / "readme.txt"
        other_file.write_text("Not a workflow")

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = list_definitions()

        # Both .md files should parse (one with frontmatter, one without)
        assert len(result) == 2
        names = [w.name for w in result]
        assert "valid-workflow" in names
        assert "simple" in names  # Derived from filename


class TestGetDefinition:
    """Tests for get_definition function."""

    def test_get_existing_definition(self, tmp_path):
        """Test getting an existing workflow definition."""
        from kurt.workflows.agents.registry import get_definition

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        workflow_file = workflows_dir / "my-workflow.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: my-workflow
            title: My Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            My body.
        """).strip()
        )

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = get_definition("my-workflow")

        assert result is not None
        assert result.name == "my-workflow"
        assert result.title == "My Workflow"

    def test_get_nonexistent_definition(self, tmp_path):
        """Test getting a non-existent workflow definition."""
        from kurt.workflows.agents.registry import get_definition

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = get_definition("nonexistent")

        assert result is None

    def test_get_definition_by_filename(self, tmp_path):
        """Test getting a definition when name differs from filename."""
        from kurt.workflows.agents.registry import get_definition

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Filename is different from the 'name' field
        workflow_file = workflows_dir / "some-file.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: actual-name
            title: Actual Name Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            Body.
        """).strip()
        )

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = get_definition("actual-name")

        assert result is not None
        assert result.name == "actual-name"


class TestValidateAll:
    """Tests for validate_all function."""

    def test_validate_all_valid(self, tmp_path):
        """Test validating all valid workflows."""
        from kurt.workflows.agents.registry import validate_all

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        for i in range(2):
            workflow_file = workflows_dir / f"workflow-{i}.md"
            workflow_file.write_text(
                dedent(f"""
                ---
                name: workflow-{i}
                title: Workflow {i}
                agent:
                  model: claude-sonnet-4-20250514
                ---

                Body {i}.
            """).strip()
            )

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = validate_all()

        assert len(result["valid"]) == 2
        assert len(result["errors"]) == 0

    def test_validate_all_mixed(self, tmp_path):
        """Test validating mix of valid and invalid workflows."""
        from kurt.workflows.agents.registry import validate_all

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Valid workflow
        valid_file = workflows_dir / "valid.md"
        valid_file.write_text(
            dedent("""
            ---
            name: valid-workflow
            title: Valid Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            Valid body.
        """).strip()
        )

        # Invalid workflow (empty body)
        invalid_file = workflows_dir / "invalid.md"
        invalid_file.write_text(
            dedent("""
            ---
            name: invalid-workflow
            title: Invalid Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---
        """).strip()
        )

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = validate_all()

        assert len(result["valid"]) == 1
        assert "valid-workflow" in result["valid"]
        assert len(result["errors"]) == 1
        assert result["errors"][0]["file"] == "invalid.md"

    def test_validate_all_empty(self, tmp_path):
        """Test validating empty directory."""
        from kurt.workflows.agents.registry import validate_all

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = validate_all()

        assert result["valid"] == []
        assert result["errors"] == []


class TestEnsureWorkflowsDir:
    """Tests for ensure_workflows_dir function."""

    def test_creates_directory(self, tmp_path):
        """Test that ensure_workflows_dir creates the directory."""
        from kurt.workflows.agents.registry import ensure_workflows_dir

        workflows_dir = tmp_path / "workflows"

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = ensure_workflows_dir()

        assert result == workflows_dir
        assert workflows_dir.exists()
        assert workflows_dir.is_dir()

    def test_existing_directory(self, tmp_path):
        """Test ensure_workflows_dir with existing directory."""
        from kurt.workflows.agents.registry import ensure_workflows_dir

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Create a file inside
        test_file = workflows_dir / "test.md"
        test_file.write_text("test content")

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = ensure_workflows_dir()

        assert result == workflows_dir
        assert workflows_dir.exists()
        # Verify existing content wasn't deleted
        assert test_file.exists()


class TestDirectoryStructure:
    """Tests for workflows with directory structure (tools.py, schema.yaml)."""

    def test_list_includes_directory_workflows(self, tmp_path):
        """Test that list_definitions finds both flat and directory workflows."""
        from kurt.workflows.agents.registry import list_definitions

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Flat workflow
        flat_file = workflows_dir / "flat-workflow.md"
        flat_file.write_text(
            dedent("""
            ---
            name: flat-workflow
            title: Flat Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            Flat body.
        """).strip()
        )

        # Directory workflow
        dir_workflow = workflows_dir / "complex_workflow"
        dir_workflow.mkdir()
        (dir_workflow / "workflow.md").write_text(
            dedent("""
            ---
            name: complex-workflow
            title: Complex Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            Complex body.
        """).strip()
        )
        (dir_workflow / "tools.py").write_text('"""Tools for complex workflow."""')

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = list_definitions()

        assert len(result) == 2
        names = [w.name for w in result]
        assert "flat-workflow" in names
        assert "complex-workflow" in names

    def test_get_definition_from_directory(self, tmp_path):
        """Test getting a workflow from directory structure."""
        from kurt.workflows.agents.registry import get_definition

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Directory workflow
        dir_workflow = workflows_dir / "my_workflow"
        dir_workflow.mkdir()
        (dir_workflow / "workflow.md").write_text(
            dedent("""
            ---
            name: my-workflow
            title: My Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            My body.
        """).strip()
        )

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = get_definition("my-workflow")

        assert result is not None
        assert result.name == "my-workflow"
        assert result.title == "My Workflow"

    def test_get_workflow_dir(self, tmp_path):
        """Test get_workflow_dir returns path for directory workflows."""
        from kurt.workflows.agents.registry import get_workflow_dir

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Create directory workflow
        dir_workflow = workflows_dir / "my_workflow"
        dir_workflow.mkdir()
        (dir_workflow / "workflow.md").write_text("---\nname: my-workflow\n---\nBody")

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = get_workflow_dir("my-workflow")

        assert result == dir_workflow

    def test_get_workflow_dir_returns_none_for_flat(self, tmp_path):
        """Test get_workflow_dir returns None for flat file workflows."""
        from kurt.workflows.agents.registry import get_workflow_dir

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Flat workflow
        (workflows_dir / "flat.md").write_text("---\nname: flat\n---\nBody")

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = get_workflow_dir("flat")

        assert result is None

    def test_has_tools(self, tmp_path):
        """Test has_tools detects tools.py presence."""
        from kurt.workflows.agents.registry import has_tools

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Workflow with tools
        with_tools = workflows_dir / "with_tools"
        with_tools.mkdir()
        (with_tools / "workflow.md").write_text("---\nname: with-tools\n---\nBody")
        (with_tools / "tools.py").write_text("# tools")

        # Workflow without tools
        without_tools = workflows_dir / "without_tools"
        without_tools.mkdir()
        (without_tools / "workflow.md").write_text("---\nname: without-tools\n---\nBody")

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            assert has_tools("with-tools") is True
            assert has_tools("without-tools") is False
            assert has_tools("nonexistent") is False

    def test_has_schema(self, tmp_path):
        """Test has_schema detects schema.yaml presence."""
        from kurt.workflows.agents.registry import has_schema

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Workflow with schema
        with_schema = workflows_dir / "with_schema"
        with_schema.mkdir()
        (with_schema / "workflow.md").write_text("---\nname: with-schema\n---\nBody")
        (with_schema / "schema.yaml").write_text("tables: []")

        # Workflow without schema
        without_schema = workflows_dir / "without_schema"
        without_schema.mkdir()
        (without_schema / "workflow.md").write_text("---\nname: without-schema\n---\nBody")

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            assert has_schema("with-schema") is True
            assert has_schema("without-schema") is False

    def test_validate_all_includes_directory_workflows(self, tmp_path):
        """Test validate_all validates both flat and directory workflows."""
        from kurt.workflows.agents.registry import validate_all

        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()

        # Flat workflow
        (workflows_dir / "flat.md").write_text(
            dedent("""
            ---
            name: flat-workflow
            title: Flat
            agent:
              model: claude-sonnet-4-20250514
            ---

            Flat body.
        """).strip()
        )

        # Directory workflow
        dir_workflow = workflows_dir / "dir_workflow"
        dir_workflow.mkdir()
        (dir_workflow / "workflow.md").write_text(
            dedent("""
            ---
            name: dir-workflow
            title: Dir
            agent:
              model: claude-sonnet-4-20250514
            ---

            Dir body.
        """).strip()
        )

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = workflows_dir

            result = validate_all()

        assert len(result["valid"]) == 2
        assert "flat-workflow" in result["valid"]
        assert "dir-workflow" in result["valid"]
        assert len(result["errors"]) == 0
