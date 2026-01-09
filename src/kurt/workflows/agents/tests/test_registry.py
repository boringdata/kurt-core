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
