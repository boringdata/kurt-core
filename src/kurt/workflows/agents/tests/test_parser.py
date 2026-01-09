"""Tests for agent workflow parser."""

from __future__ import annotations

from textwrap import dedent


class TestParseWorkflow:
    """Tests for parse_workflow function."""

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


class TestValidateWorkflow:
    """Tests for validate_workflow function."""

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
