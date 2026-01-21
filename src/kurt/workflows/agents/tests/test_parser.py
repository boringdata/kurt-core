"""Tests for agent workflow parser."""

from __future__ import annotations

from textwrap import dedent


# =============================================================================
# Markdown Format Tests (Backwards Compatibility)
# =============================================================================


class TestParseMarkdownWorkflow:
    """Tests for parse_workflow function with Markdown format."""

    def test_parse_minimal_workflow(self, tmp_path):
        """Test parsing a minimal valid workflow."""
        from kurt.workflows.agents.parser import parse_workflow

        workflow_file = tmp_path / "minimal.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: minimal-workflow
            title: Minimal Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            # Minimal Workflow

            Do something simple.
        """).strip()
        )

        result = parse_workflow(workflow_file)

        assert result.name == "minimal-workflow"
        assert result.title == "Minimal Workflow"
        assert result.agent.model == "claude-sonnet-4-20250514"
        assert "Do something simple" in result.body

    def test_parse_full_workflow(self, tmp_path):
        """Test parsing a fully-specified workflow."""
        from kurt.workflows.agents.parser import parse_workflow

        workflow_file = tmp_path / "full.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: full-workflow
            title: Full Workflow
            description: |
              A comprehensive workflow with all options.

            agent:
              model: claude-sonnet-4-20250514
              max_turns: 15
              allowed_tools:
                - Bash
                - Read
                - Write
                - Glob
              permission_mode: bypassPermissions

            guardrails:
              max_tokens: 200000
              max_tool_calls: 100
              max_time: 600

            schedule:
              cron: "0 9 * * 1-5"
              timezone: "Europe/Paris"
              enabled: true

            inputs:
              topic: "AI"
              depth: 3

            tags: [daily, research]
            ---

            # Full Workflow

            Research {{topic}} with depth {{depth}}.
        """).strip()
        )

        result = parse_workflow(workflow_file)

        assert result.name == "full-workflow"
        assert result.title == "Full Workflow"
        assert "comprehensive workflow" in result.description
        assert result.agent.model == "claude-sonnet-4-20250514"
        assert result.agent.max_turns == 15
        assert "Bash" in result.agent.allowed_tools
        assert result.agent.permission_mode == "bypassPermissions"
        assert result.guardrails.max_tokens == 200000
        assert result.guardrails.max_tool_calls == 100
        assert result.guardrails.max_time == 600
        assert result.schedule.cron == "0 9 * * 1-5"
        assert result.schedule.timezone == "Europe/Paris"
        assert result.schedule.enabled is True
        assert result.inputs["topic"] == "AI"
        assert result.inputs["depth"] == 3
        assert "daily" in result.tags
        assert "{{topic}}" in result.body

    def test_parse_uses_defaults(self, tmp_path):
        """Test that defaults are applied for missing fields."""
        from kurt.workflows.agents.parser import parse_workflow

        workflow_file = tmp_path / "defaults.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: default-workflow
            title: Default Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            Body content.
        """).strip()
        )

        result = parse_workflow(workflow_file)

        # Check defaults (based on actual implementation)
        assert result.agent.max_turns == 50  # Actual default
        assert result.agent.permission_mode == "bypassPermissions"
        assert result.guardrails.max_tokens == 500000
        assert result.guardrails.max_tool_calls == 200
        assert result.guardrails.max_time == 3600
        assert result.schedule is None
        assert result.inputs == {}
        assert result.tags == []


class TestValidateMarkdownWorkflow:
    """Tests for validate_workflow function with Markdown format."""

    def test_validate_valid_workflow(self, tmp_path):
        """Test validation passes for valid workflow."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "valid.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: valid-workflow
            title: Valid Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---

            Valid body content.
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert errors == []

    def test_validate_invalid_cron(self, tmp_path):
        """Test validation catches invalid cron expression."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "bad-cron.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: bad-cron-workflow
            title: Bad Cron Workflow
            agent:
              model: claude-sonnet-4-20250514
            schedule:
              cron: "invalid cron"
            ---

            Body content.
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("cron" in e.lower() for e in errors)

    def test_validate_empty_body(self, tmp_path):
        """Test validation catches empty body."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "empty-body.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: empty-body-workflow
            title: Empty Body Workflow
            agent:
              model: claude-sonnet-4-20250514
            ---
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("body" in e.lower() or "empty" in e.lower() for e in errors)

    def test_validate_nonexistent_file(self, tmp_path):
        """Test validation handles non-existent file."""
        from kurt.workflows.agents.parser import validate_workflow

        nonexistent = tmp_path / "nonexistent.md"

        errors = validate_workflow(nonexistent)
        assert len(errors) > 0
        # Should have a parse error
        assert any("error" in e.lower() for e in errors)

    def test_validate_invalid_max_turns(self, tmp_path):
        """Test validation catches invalid max_turns."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "bad-turns.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: bad-turns-workflow
            title: Bad Turns Workflow
            agent:
              model: claude-sonnet-4-20250514
              max_turns: 0
            ---

            Body content.
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("max_turns" in e for e in errors)

    def test_validate_invalid_permission_mode(self, tmp_path):
        """Test validation catches invalid permission_mode."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "bad-permission.md"
        workflow_file.write_text(
            dedent("""
            ---
            name: bad-permission-workflow
            title: Bad Permission Workflow
            agent:
              model: claude-sonnet-4-20250514
              permission_mode: invalid
            ---

            Body content.
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("permission_mode" in e for e in errors)


# =============================================================================
# TOML Format Tests
# =============================================================================


class TestParseTomlWorkflow:
    """Tests for parse_workflow function with TOML format."""

    def test_parse_minimal_toml_workflow(self, tmp_path):
        """Test parsing a minimal TOML workflow."""
        from kurt.workflows.agents.parser import parse_workflow

        workflow_file = tmp_path / "minimal.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "minimal-toml"
            title = "Minimal TOML Workflow"

            [agent]
            model = "claude-sonnet-4-20250514"
            prompt = "Do something simple."
        """).strip()
        )

        result = parse_workflow(workflow_file)

        assert result.name == "minimal-toml"
        assert result.title == "Minimal TOML Workflow"
        assert result.agent is not None
        assert result.agent.model == "claude-sonnet-4-20250514"
        assert result.agent.prompt == "Do something simple."
        assert result.effective_prompt == "Do something simple."
        assert result.is_agent_driven is True
        assert result.is_dbos_driven is False

    def test_parse_full_toml_workflow(self, tmp_path):
        """Test parsing a fully-specified TOML workflow."""
        from kurt.workflows.agents.parser import parse_workflow

        workflow_file = tmp_path / "full.toml"
        workflow_file.write_text(
            dedent('''
            # Root-level keys must come before sections in TOML
            tags = ["daily", "research"]

            [workflow]
            name = "full-toml"
            title = "Full TOML Workflow"
            description = "A comprehensive TOML workflow."

            [agent]
            model = "claude-sonnet-4-20250514"
            max_turns = 15
            prompt = """
            Research the topic thoroughly.
            Use available tools to gather data.
            """
            allowed_tools = ["Bash", "Read", "Write", "Glob"]
            permission_mode = "bypassPermissions"

            [guardrails]
            max_tokens = 200000
            max_tool_calls = 100
            max_time = 600

            [schedule]
            cron = "0 9 * * 1-5"
            timezone = "Europe/Paris"
            enabled = true

            [inputs]
            topic = "AI"
            depth = 3
        ''').strip()
        )

        result = parse_workflow(workflow_file)

        assert result.name == "full-toml"
        assert result.title == "Full TOML Workflow"
        assert result.description == "A comprehensive TOML workflow."
        assert result.workflow is not None
        assert result.workflow.name == "full-toml"
        assert result.agent.model == "claude-sonnet-4-20250514"
        assert result.agent.max_turns == 15
        assert "Research the topic" in result.agent.prompt
        assert result.agent.allowed_tools == ["Bash", "Read", "Write", "Glob"]
        assert result.agent.permission_mode == "bypassPermissions"
        assert result.guardrails.max_tokens == 200000
        assert result.guardrails.max_tool_calls == 100
        assert result.guardrails.max_time == 600
        assert result.schedule.cron == "0 9 * * 1-5"
        assert result.schedule.timezone == "Europe/Paris"
        assert result.schedule.enabled is True
        assert result.inputs["topic"] == "AI"
        assert result.inputs["depth"] == 3
        assert "daily" in result.tags
        assert "research" in result.tags

    def test_parse_dbos_driven_workflow(self, tmp_path):
        """Test parsing a DBOS-driven workflow with steps."""
        from kurt.workflows.agents.parser import parse_workflow

        workflow_file = tmp_path / "dag.toml"
        workflow_file.write_text(
            dedent('''
            [workflow]
            name = "dag-workflow"
            title = "DAG Workflow"

            [inputs]
            urls = ["https://example.com"]

            [steps.fetch]
            type = "function"
            function = "fetch_pages"

            [steps.analyze]
            type = "agent"
            depends_on = ["fetch"]
            model = "claude-sonnet-4-20250514"
            max_turns = 15
            prompt = "Analyze the fetched content."

            [steps.transform]
            type = "llm"
            depends_on = ["analyze"]
            prompt_template = "Transform: {input}"
            output_schema = "TransformResult"

            [steps.report]
            type = "function"
            depends_on = ["analyze", "transform"]
            function = "generate_report"
        ''').strip()
        )

        result = parse_workflow(workflow_file)

        assert result.name == "dag-workflow"
        assert result.is_dbos_driven is True
        assert result.is_agent_driven is False
        assert len(result.steps) == 4

        # Check fetch step
        assert result.steps["fetch"].type == "function"
        assert result.steps["fetch"].function == "fetch_pages"
        assert result.steps["fetch"].depends_on == []

        # Check analyze step
        assert result.steps["analyze"].type == "agent"
        assert result.steps["analyze"].depends_on == ["fetch"]
        assert result.steps["analyze"].model == "claude-sonnet-4-20250514"
        assert result.steps["analyze"].max_turns == 15
        assert result.steps["analyze"].prompt == "Analyze the fetched content."

        # Check transform step
        assert result.steps["transform"].type == "llm"
        assert result.steps["transform"].depends_on == ["analyze"]
        assert result.steps["transform"].prompt_template == "Transform: {input}"
        assert result.steps["transform"].output_schema == "TransformResult"

        # Check report step
        assert result.steps["report"].type == "function"
        assert result.steps["report"].depends_on == ["analyze", "transform"]
        assert result.steps["report"].function == "generate_report"

    def test_parse_toml_uses_defaults(self, tmp_path):
        """Test that defaults are applied for missing fields in TOML."""
        from kurt.workflows.agents.parser import parse_workflow

        workflow_file = tmp_path / "defaults.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "default-toml"
            title = "Default TOML"

            [agent]
            prompt = "Do something."
        """).strip()
        )

        result = parse_workflow(workflow_file)

        # Check defaults
        assert result.agent.model == "claude-sonnet-4-20250514"
        assert result.agent.max_turns == 50
        assert result.agent.permission_mode == "bypassPermissions"
        assert result.guardrails.max_tokens == 500000
        assert result.guardrails.max_tool_calls == 200
        assert result.guardrails.max_time == 3600
        assert result.schedule is None
        assert result.inputs == {}
        assert result.tags == []

    def test_parse_toml_missing_workflow_section(self, tmp_path):
        """Test that missing [workflow] section raises error."""
        from kurt.workflows.agents.parser import parse_workflow
        import pytest

        workflow_file = tmp_path / "missing-workflow.toml"
        workflow_file.write_text(
            dedent("""
            [agent]
            prompt = "Do something."
        """).strip()
        )

        with pytest.raises(ValueError, match="Missing required"):
            parse_workflow(workflow_file)


class TestValidateTomlWorkflow:
    """Tests for validate_workflow function with TOML format."""

    def test_validate_valid_toml_workflow(self, tmp_path):
        """Test validation passes for valid TOML workflow."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "valid.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "valid-toml"
            title = "Valid TOML"

            [agent]
            prompt = "Do something valid."
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert errors == []

    def test_validate_toml_empty_prompt(self, tmp_path):
        """Test validation catches empty prompt in TOML."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "empty-prompt.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "empty-prompt"
            title = "Empty Prompt"

            [agent]
            prompt = ""
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("empty" in e.lower() for e in errors)

    def test_validate_toml_invalid_cron(self, tmp_path):
        """Test validation catches invalid cron in TOML."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "bad-cron.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "bad-cron"
            title = "Bad Cron"

            [agent]
            prompt = "Do something."

            [schedule]
            cron = "not a valid cron"
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("cron" in e.lower() for e in errors)

    def test_validate_step_missing_function(self, tmp_path):
        """Test validation catches step missing function field."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "missing-function.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "missing-function"
            title = "Missing Function"

            [steps.fetch]
            type = "function"
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("function" in e.lower() for e in errors)

    def test_validate_step_missing_prompt(self, tmp_path):
        """Test validation catches agent step missing prompt field."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "missing-prompt.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "missing-prompt"
            title = "Missing Prompt"

            [steps.analyze]
            type = "agent"
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("prompt" in e.lower() for e in errors)

    def test_validate_step_missing_prompt_template(self, tmp_path):
        """Test validation catches llm step missing prompt_template field."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "missing-template.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "missing-template"
            title = "Missing Template"

            [steps.transform]
            type = "llm"
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("prompt_template" in e.lower() for e in errors)

    def test_validate_invalid_dependency(self, tmp_path):
        """Test validation catches non-existent dependency."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "bad-dep.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "bad-dep"
            title = "Bad Dependency"

            [steps.analyze]
            type = "function"
            function = "analyze"
            depends_on = ["nonexistent"]
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("nonexistent" in e.lower() for e in errors)

    def test_validate_circular_dependency(self, tmp_path):
        """Test validation catches circular dependencies."""
        from kurt.workflows.agents.parser import validate_workflow

        workflow_file = tmp_path / "circular.toml"
        workflow_file.write_text(
            dedent("""
            [workflow]
            name = "circular"
            title = "Circular Deps"

            [steps.a]
            type = "function"
            function = "step_a"
            depends_on = ["b"]

            [steps.b]
            type = "function"
            function = "step_b"
            depends_on = ["a"]
        """).strip()
        )

        errors = validate_workflow(workflow_file)
        assert len(errors) > 0
        assert any("circular" in e.lower() or "cycle" in e.lower() for e in errors)


# =============================================================================
# Format Detection Tests
# =============================================================================


class TestDetectFileFormat:
    """Tests for detect_file_format function."""

    def test_detect_toml_by_extension(self, tmp_path):
        """Test detection of TOML by .toml extension."""
        from kurt.workflows.agents.parser import detect_file_format

        toml_file = tmp_path / "workflow.toml"
        toml_file.write_text("[workflow]\nname = 'test'")

        assert detect_file_format(toml_file) == "toml"

    def test_detect_markdown_by_extension(self, tmp_path):
        """Test detection of Markdown by .md extension."""
        from kurt.workflows.agents.parser import detect_file_format

        md_file = tmp_path / "workflow.md"
        md_file.write_text("---\nname: test\n---\n# Content")

        assert detect_file_format(md_file) == "markdown"

    def test_detect_toml_by_content(self, tmp_path):
        """Test detection of TOML by content when extension is unknown."""
        from kurt.workflows.agents.parser import detect_file_format

        file = tmp_path / "workflow.txt"
        file.write_text("[workflow]\nname = 'test'")

        assert detect_file_format(file) == "toml"

    def test_detect_markdown_by_content(self, tmp_path):
        """Test detection of Markdown by content when extension is unknown."""
        from kurt.workflows.agents.parser import detect_file_format

        file = tmp_path / "workflow.txt"
        file.write_text("---\nname: test\n---\n# Content")

        assert detect_file_format(file) == "markdown"

    def test_detect_unknown_defaults_to_markdown(self, tmp_path):
        """Test that unknown format defaults to markdown."""
        from kurt.workflows.agents.parser import detect_file_format

        file = tmp_path / "workflow.xyz"
        file.write_text("Some random content")

        assert detect_file_format(file) == "markdown"


# =============================================================================
# Model Tests
# =============================================================================


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_agent_config_defaults(self):
        """Test AgentConfig default values."""
        from kurt.workflows.agents.parser import AgentConfig

        config = AgentConfig(model="claude-sonnet-4-20250514")

        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_turns == 50  # Actual default
        assert len(config.allowed_tools) > 0  # Has default tools
        assert config.permission_mode == "bypassPermissions"

    def test_agent_config_custom(self):
        """Test AgentConfig with custom values."""
        from kurt.workflows.agents.parser import AgentConfig

        config = AgentConfig(
            model="claude-opus-4-20250514",
            max_turns=20,
            allowed_tools=["Bash", "Read", "Write"],
            permission_mode="auto",
        )

        assert config.model == "claude-opus-4-20250514"
        assert config.max_turns == 20
        assert len(config.allowed_tools) == 3
        assert config.permission_mode == "auto"

    def test_agent_config_with_prompt(self):
        """Test AgentConfig with prompt (TOML format)."""
        from kurt.workflows.agents.parser import AgentConfig

        config = AgentConfig(
            model="claude-sonnet-4-20250514",
            prompt="Do something useful.",
        )

        assert config.prompt == "Do something useful."


class TestStepConfig:
    """Tests for StepConfig model."""

    def test_function_step(self):
        """Test StepConfig for function type."""
        from kurt.workflows.agents.parser import StepConfig

        config = StepConfig(
            type="function",
            function="process_data",
            depends_on=["fetch"],
        )

        assert config.type == "function"
        assert config.function == "process_data"
        assert config.depends_on == ["fetch"]

    def test_agent_step(self):
        """Test StepConfig for agent type."""
        from kurt.workflows.agents.parser import StepConfig

        config = StepConfig(
            type="agent",
            model="claude-sonnet-4-20250514",
            max_turns=10,
            prompt="Analyze the data.",
        )

        assert config.type == "agent"
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_turns == 10
        assert config.prompt == "Analyze the data."

    def test_llm_step(self):
        """Test StepConfig for llm type."""
        from kurt.workflows.agents.parser import StepConfig

        config = StepConfig(
            type="llm",
            prompt_template="Extract: {input}",
            output_schema="ExtractResult",
        )

        assert config.type == "llm"
        assert config.prompt_template == "Extract: {input}"
        assert config.output_schema == "ExtractResult"


class TestWorkflowConfig:
    """Tests for WorkflowConfig model."""

    def test_workflow_config_required_fields(self):
        """Test WorkflowConfig with required fields only."""
        from kurt.workflows.agents.parser import WorkflowConfig

        config = WorkflowConfig(
            name="test-workflow",
            title="Test Workflow",
        )

        assert config.name == "test-workflow"
        assert config.title == "Test Workflow"
        assert config.description is None

    def test_workflow_config_with_description(self):
        """Test WorkflowConfig with description."""
        from kurt.workflows.agents.parser import WorkflowConfig

        config = WorkflowConfig(
            name="test-workflow",
            title="Test Workflow",
            description="A test workflow for testing.",
        )

        assert config.description == "A test workflow for testing."


class TestGuardrailsConfig:
    """Tests for GuardrailsConfig model."""

    def test_guardrails_defaults(self):
        """Test GuardrailsConfig default values."""
        from kurt.workflows.agents.parser import GuardrailsConfig

        config = GuardrailsConfig()

        assert config.max_tokens == 500000
        assert config.max_tool_calls == 200
        assert config.max_time == 3600

    def test_guardrails_custom(self):
        """Test GuardrailsConfig with custom values."""
        from kurt.workflows.agents.parser import GuardrailsConfig

        config = GuardrailsConfig(
            max_tokens=100000,
            max_tool_calls=50,
            max_time=300,
        )

        assert config.max_tokens == 100000
        assert config.max_tool_calls == 50
        assert config.max_time == 300


class TestScheduleConfig:
    """Tests for ScheduleConfig model."""

    def test_schedule_config_basic(self):
        """Test ScheduleConfig basic creation."""
        from kurt.workflows.agents.parser import ScheduleConfig

        config = ScheduleConfig(cron="0 9 * * *")

        assert config.cron == "0 9 * * *"
        assert config.timezone == "UTC"  # Default
        assert config.enabled is True  # Default

    def test_schedule_config_full(self):
        """Test ScheduleConfig with all options."""
        from kurt.workflows.agents.parser import ScheduleConfig

        config = ScheduleConfig(
            cron="0 9 * * 1-5",
            timezone="America/New_York",
            enabled=False,
        )

        assert config.cron == "0 9 * * 1-5"
        assert config.timezone == "America/New_York"
        assert config.enabled is False


class TestParsedWorkflow:
    """Tests for ParsedWorkflow model properties."""

    def test_is_agent_driven(self):
        """Test is_agent_driven property."""
        from kurt.workflows.agents.parser import ParsedWorkflow, AgentConfig

        workflow = ParsedWorkflow(
            name="test",
            title="Test",
            agent=AgentConfig(prompt="Do something."),
            steps={},
        )

        assert workflow.is_agent_driven is True
        assert workflow.is_dbos_driven is False

    def test_is_dbos_driven(self):
        """Test is_dbos_driven property."""
        from kurt.workflows.agents.parser import ParsedWorkflow, StepConfig

        workflow = ParsedWorkflow(
            name="test",
            title="Test",
            steps={"step1": StepConfig(type="function", function="test")},
        )

        assert workflow.is_agent_driven is False
        assert workflow.is_dbos_driven is True

    def test_effective_prompt_from_agent(self):
        """Test effective_prompt returns agent.prompt for TOML."""
        from kurt.workflows.agents.parser import ParsedWorkflow, AgentConfig

        workflow = ParsedWorkflow(
            name="test",
            title="Test",
            agent=AgentConfig(prompt="Agent prompt."),
            body="Body content.",
        )

        assert workflow.effective_prompt == "Agent prompt."

    def test_effective_prompt_from_body(self):
        """Test effective_prompt returns body for Markdown."""
        from kurt.workflows.agents.parser import ParsedWorkflow, AgentConfig

        workflow = ParsedWorkflow(
            name="test",
            title="Test",
            agent=AgentConfig(),  # No prompt
            body="Body content.",
        )

        assert workflow.effective_prompt == "Body content."
