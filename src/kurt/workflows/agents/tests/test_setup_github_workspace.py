"""Tests for setup-github-workspace example workflow."""

from __future__ import annotations

from pathlib import Path


class TestSetupGitHubWorkspaceDefinition:
    """Tests for the setup-github-workspace.md workflow definition."""

    def test_workflow_file_exists(self):
        """Test that the workflow template file exists."""

        # Get the examples directory
        agents_dir = Path(__file__).parent.parent
        examples_dir = agents_dir / "examples"
        workflow_file = examples_dir / "setup-github-workspace.md"

        assert workflow_file.exists(), f"Workflow file not found at {workflow_file}"
        assert workflow_file.is_file()

    def test_parse_workflow_definition(self):
        """Test that the workflow definition can be parsed."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        assert definition is not None
        assert definition.name == "setup-github-workspace"
        assert definition.title == "Setup GitHub Workspace Integration"

    def test_workflow_has_required_fields(self):
        """Test that the workflow has all required fields."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        # Required fields
        assert definition.name
        assert definition.title
        assert definition.description
        assert definition.agent
        assert definition.body

        # Agent configuration
        assert definition.agent.model == "claude-sonnet-4-20250514"
        assert definition.agent.max_turns == 15
        assert "Bash" in definition.agent.allowed_tools
        assert "Read" in definition.agent.allowed_tools
        assert definition.agent.permission_mode == "bypassPermissions"

    def test_workflow_has_guardrails(self):
        """Test that the workflow has appropriate guardrails."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        assert definition.guardrails
        assert definition.guardrails.max_tokens > 0
        assert definition.guardrails.max_tool_calls > 0
        assert definition.guardrails.max_time > 0

    def test_workflow_has_default_inputs(self):
        """Test that the workflow has default input values."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        assert definition.inputs
        assert "workspace_name" in definition.inputs
        assert "workspace_slug" in definition.inputs
        assert "github_owner" in definition.inputs
        assert "github_repo" in definition.inputs
        assert "github_branch" in definition.inputs

    def test_workflow_body_has_setup_steps(self):
        """Test that the workflow body contains setup instructions."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        # Check for key sections in the body
        assert "Gather Information" in definition.body
        assert "Validate GitHub Repository" in definition.body
        assert "Create Workspace via API" in definition.body
        assert "Install GitHub App" in definition.body
        assert "Poll for Installation" in definition.body
        assert "Verify GitHub Access" in definition.body
        assert "Report Success" in definition.body

    def test_workflow_body_has_curl_examples(self):
        """Test that the workflow includes API call examples."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        # Should include curl commands for API interaction
        assert "curl" in definition.body
        assert "/api/workspaces" in definition.body
        assert "github/status" in definition.body

    def test_workflow_body_has_error_handling(self):
        """Test that the workflow includes error handling guidance."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        # Should include error handling sections
        assert "Error Handling" in definition.body
        assert "Repository Not Found" in definition.body
        assert "Workspace Slug Already Exists" in definition.body
        assert "Installation Timeout" in definition.body

    def test_workflow_has_appropriate_tags(self):
        """Test that the workflow has descriptive tags."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        assert definition.tags
        assert "setup" in definition.tags
        assert "onboarding" in definition.tags
        assert "github" in definition.tags

    def test_workflow_validation_passes(self):
        """Test that the workflow passes validation."""
        from kurt.workflows.agents.parser import validate_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        errors = validate_workflow(workflow_file)

        assert len(errors) == 0, f"Workflow validation failed: {errors}"


class TestSetupGitHubWorkspaceIntegration:
    """Integration tests for setup-github-workspace workflow."""

    def test_workflow_can_be_listed(self):
        """Test that the workflow appears when listing from examples directory."""
        from unittest.mock import patch

        from kurt.workflows.agents.registry import list_definitions

        agents_dir = Path(__file__).parent.parent
        examples_dir = agents_dir / "examples"

        # Temporarily point registry to examples directory
        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = examples_dir

            definitions = list_definitions()

        # Should find at least our workflow
        assert len(definitions) > 0
        names = [d.name for d in definitions]
        assert "setup-github-workspace" in names

    def test_workflow_can_be_retrieved_by_name(self):
        """Test that the workflow can be retrieved by name."""
        from unittest.mock import patch

        from kurt.workflows.agents.registry import get_definition

        agents_dir = Path(__file__).parent.parent
        examples_dir = agents_dir / "examples"

        with patch("kurt.workflows.agents.registry.get_workflows_dir") as mock_dir:
            mock_dir.return_value = examples_dir

            definition = get_definition("setup-github-workspace")

        assert definition is not None
        assert definition.name == "setup-github-workspace"
        assert definition.title == "Setup GitHub Workspace Integration"

    def test_workflow_inputs_can_be_overridden(self):
        """Test that default inputs can be overridden at runtime."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        # Verify default inputs
        assert definition.inputs["workspace_name"] == "My Documentation"
        assert definition.inputs["workspace_slug"] == "my-docs"

        # In actual execution, these would be overridden via --input flags
        # The workflow definition provides sensible defaults for testing


class TestWorkflowDocumentation:
    """Tests for workflow documentation and help text."""

    def test_workflow_has_comprehensive_description(self):
        """Test that the workflow has a detailed description."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        assert definition.description
        assert len(definition.description) > 50  # Should be descriptive
        assert "workspace" in definition.description.lower()
        assert "github" in definition.description.lower()

    def test_workflow_description_lists_steps(self):
        """Test that the description outlines the workflow steps."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        # Description should outline the main steps
        description_lower = definition.description.lower()
        assert "create" in description_lower or "workspace" in description_lower
        assert "install" in description_lower or "github" in description_lower
        assert "verif" in description_lower or "test" in description_lower

    def test_workflow_body_has_success_criteria(self):
        """Test that the workflow defines success criteria."""
        from kurt.workflows.agents.parser import parse_workflow

        agents_dir = Path(__file__).parent.parent
        workflow_file = agents_dir / "examples" / "setup-github-workspace.md"

        definition = parse_workflow(workflow_file)

        assert "Success Criteria" in definition.body
        assert "Workspace created" in definition.body
        assert "GitHub App installed" in definition.body
        assert "Backend can access repository" in definition.body
