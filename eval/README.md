# Kurt Evaluation Framework

An evaluation framework for testing Kurt agent behavior using the Claude Code SDK.

## Overview

This evaluation framework allows you to:
- **Test agent behavior**: Use Anthropic SDK to test real agent interactions with Kurt CLI
- **Workspace isolation**: Each test runs in a clean temporary directory
- **SDK Integration**: Real agent sessions via Anthropic SDK (with graceful fallback)
- **Real-time Output**: See agent interactions as they happen in the console
- **Collect metrics**: Track tool usage, file operations, database state, timing
- **Validate outcomes**: Assert on files, database content, and tool usage
- **Detailed Results**: JSON metrics + markdown transcripts for each test run

## Quick Start

### 1. Install Dependencies

```bash
uv pip install -r requirements.txt
```

### 2. Configure API Key (Required)

The runner requires an Anthropic API key to test agent behavior. It will automatically check for the key in this order:
1. `ANTHROPIC_API_KEY` environment variable
2. `../kurt-demo/.env` file
3. Local `.env` file (copy from `.env.example`)

If no API key is found, the test will fail with an error message.

```bash
# Option 1: Environment variable
export ANTHROPIC_API_KEY="sk-ant-..."

# Option 2: Create local .env
cp .env.example .env
# Edit .env and add your API key
```

### 3. Run a Scenario

```bash
# Run a specific scenario (requires API key)
uv run python run_scenario.py 01_basic_init

# Or set API key inline
ANTHROPIC_API_KEY="sk-ant-..." uv run python run_scenario.py 01_basic_init
```

### 4. View Results

Each test run generates two files in `results/`:
- **JSON file**: Complete metrics and metadata
- **Markdown file**: Raw transcript of the test run

```bash
cat results/01_basic_init_20251031_100119.json
cat results/01_basic_init_20251031_100119.md
```

## Architecture

```
eval/
├── framework/              # Core framework code
│   ├── workspace.py       # Isolated temp directories
│   ├── conversation.py    # Conversation structures
│   ├── runner.py          # Scenario execution
│   ├── metrics.py         # Metrics collection
│   └── evaluator.py       # Assertions
│
├── scenarios/             # Test scenarios (agent behavior)
│   ├── 01_basic_init.py
│   ├── 02_add_url.py
│   ├── 03_interactive_project.py
│   └── 04_with_claude_plugin.py
│
├── tests/                 # Framework tests (not agent tests)
│   ├── test_workspace.py # Test workspace isolation
│   └── README.md
│
├── results/               # Test outputs (gitignored)
└── run_scenario.py        # CLI entry point
```

## Key Concepts

### Workspace Isolation

Each scenario runs in a temporary directory (`/tmp/kurt_eval_<uuid>/`) to ensure:
- No contamination between tests
- No impact on your actual Kurt projects
- Clean slate for every run
- Safe inspection after failures

**Workspace automatically:**
1. Creates temp directory
2. Runs `kurt init` to initialize project
3. Creates `sources/`, `rules/`, `projects/` directories
4. **Installs `.claude/` plugin from kurt-demo** (by default)
5. Changes to workspace directory
6. Cleans up after (or preserves on error)

```python
workspace = IsolatedWorkspace(
    init_kurt=True,                   # Run kurt init (default: True)
    install_claude_plugin=True,       # Install .claude/ from kurt-demo (default: True)
)
workspace.setup()  # Does all the setup
# ... scenario runs ...
workspace.teardown()  # Cleans up
```

**Note**: Claude plugin is installed by default since it's essential for Kurt agent behavior. You can disable it per-scenario if needed:

```python
scenario = Scenario(
    name="simple_test",
    needs_claude_plugin=False,  # Disable for simple tests
    # ...
)
```

### Scenarios

A scenario defines:
- **Name and description**: What's being tested
- **Initial prompt or conversation**: How to interact with agent
- **User agent**: Automated responses to agent questions
- **Assertions**: What to validate
- **Expected metrics**: What outcomes to expect

```python
from framework import Scenario, FileExists, ToolWasUsed

scenario = Scenario(
    name="my_test",
    description="Test something",
    initial_prompt="Initialize Kurt project",
    assertions=[
        FileExists("kurt.config"),
        ToolWasUsed("bash", min_count=1),
    ]
)
```

### User Agent

Simulates user responses in multi-turn conversations:

```python
from framework import UserAgent

user_agent = UserAgent(
    responses={
        "project name": "test-blog",
        "goal": "Write a blog post",
    },
    default_response="yes"
)

# When agent asks "What's your project name?"
# User agent automatically responds: "test-blog"
```

### Assertions

Validate scenario outcomes:

```python
from framework import (
    FileExists,
    FileContains,
    DatabaseHasDocuments,
    ToolWasUsed,
    MetricEquals,
)

assertions = [
    FileExists("kurt.config"),
    FileContains("project.md", "# my-project"),
    DatabaseHasDocuments(min_count=1, status="FETCHED"),
    ToolWasUsed("bash", min_count=2, max_count=5),
    MetricEquals("files.config_exists", True),
]
```

### Metrics

Automatically collected:

**Tool Usage**:
```json
{
  "tool_usage": {
    "bash": 3,
    "read": 1,
    "write": 2
  }
}
```

**File State**:
```json
{
  "files": {
    "config_exists": true,
    "db_exists": true,
    "sources_count": 5,
    "projects_count": 1
  }
}
```

**Database State**:
```json
{
  "database": {
    "total_documents": 10,
    "fetched_documents": 8,
    "not_fetched_documents": 2
  }
}
```

**Timing**:
```json
{
  "timing": {
    "start": "2025-10-30T14:30:22",
    "end": "2025-10-30T14:30:45",
    "duration_seconds": 23.5
  }
}
```

## Creating New Scenarios

### 1. Create a Scenario File

Create `eval/scenarios/04_my_scenario.py`:

```python
"""Scenario 04: My Custom Test

Description of what this tests.
"""

from framework import (
    Scenario,
    FileExists,
    DatabaseHasDocuments,
    ToolWasUsed,
)


def create() -> Scenario:
    """Create the scenario.

    Returns:
        Configured Scenario instance
    """
    return Scenario(
        name="04_my_scenario",
        description="Test something specific",
        initial_prompt="Do something with Kurt",
        assertions=[
            FileExists("kurt.config"),
            DatabaseHasDocuments(min_count=1),
            ToolWasUsed("bash", min_count=1),
        ],
    )
```

### 2. Run It

```bash
python eval/run_scenario.py 04_my_scenario
```

## Example Scenarios

### Scenario 01: Basic Init

Tests the most basic functionality - initializing a Kurt project.

**What it does**:
- Sends message: "Initialize a new Kurt project"
- Agent runs: `kurt init`

**Validates**:
- `kurt.config` exists
- `.kurt/kurt.sqlite` exists
- At least one bash command was used

### Scenario 02: Add URL

Tests content ingestion from a URL.

**What it does**:
- Initialize Kurt
- Add content from https://docs.anthropic.com

**Validates**:
- Database has at least 1 document
- Multiple bash commands used
- Project properly initialized

### Scenario 03: Interactive Project

Tests multi-turn conversation (aspirational).

**What it does**:
- User asks to create project
- Agent asks for details
- User agent responds automatically
- Agent creates project structure

**Note**: This scenario demonstrates the framework structure for multi-turn conversations, but full implementation requires Claude Code SDK integration.

## How It Works

The runner uses the **Anthropic SDK** to create real agent sessions:

1. **Workspace Setup**: Creates temporary directory, runs `kurt init`, installs Claude plugin
2. **SDK Session**: Creates Anthropic agent session with appropriate context
3. **Execution**: Sends user prompts to agent, captures responses
4. **Validation**: Runs assertions against workspace state and metrics
5. **Cleanup**: Saves results (JSON + MD) and removes temporary workspace

### Current SDK Integration

The current implementation uses the **full Claude Code Agent SDK**:
- ✅ Uses `claude-agent-sdk>=0.1.6` for real agent sessions
- ✅ Creates async agent sessions with proper tool integration
- ✅ Provides workspace context and working directory to agent
- ✅ Captures agent text responses, thinking, and tool calls
- ✅ **Full tool support**: Bash, Read, Write, Edit, Glob, Grep
- ✅ Real-time tool execution tracking
- ✅ Automatic permission acceptance for unattended testing

### Available Tools

The agent has access to these tools in the workspace:

- **Bash**: Execute shell commands (including `kurt` CLI commands)
- **Read**: Read file contents
- **Write**: Create or overwrite files
- **Edit**: Modify existing files with string replacement
- **Glob**: Find files by pattern
- **Grep**: Search file contents

All tool calls are automatically tracked and recorded in metrics

## Extending the Framework

### Custom Assertions

Create custom assertions in `framework/evaluator.py`:

```python
class ProjectManifestValid(Assertion):
    """Assert that project.md follows expected format."""

    def evaluate(self, workspace, metrics) -> bool:
        content = workspace.read_file("projects/test/project.md")

        # Check for required sections
        if "## Goal" not in content:
            raise AssertionError("Missing Goal section")

        if "## Sources" not in content:
            raise AssertionError("Missing Sources section")

        return True
```

### Custom Metrics

Add custom metrics in `framework/metrics.py`:

```python
def collect_metrics(workspace):
    metrics = {...}  # existing metrics

    # Add custom metric
    metrics["custom"] = {
        "rule_files": workspace.count_files("rules/**/*.md"),
        "draft_files": workspace.count_files("projects/*/drafts/*.md"),
    }

    return metrics
```

### Conversation Patterns

For complex multi-turn scenarios:

```python
from framework import ConversationTurn, UserAgent

conversation = [
    ConversationTurn(speaker="user", message="Start task"),
    # Agent responds and may ask questions
    # User agent provides answers based on keywords
]

user_agent = UserAgent(
    responses={
        "project name": "my-project",
        "goal": "My goal",
    },
    # Or use custom logic:
    custom_responder=lambda msg, ctx: (
        "yes" if "confirm" in msg.lower() else None
    )
)
```

## Troubleshooting

### Scenario Fails but Want to Inspect

Set `preserve_on_error=True` in runner:

```python
runner = ScenarioRunner(preserve_on_error=True)
```

Workspace will be preserved at `/tmp/kurt_eval_<uuid>/`.

### Check What Happened

View detailed results:

```bash
cat eval/results/01_basic_init_<timestamp>.json | jq .
```

### Debug a Scenario

Add verbose output:

```python
runner = ScenarioRunner(verbose=True)
```

### Manual Workspace Testing

Create a workspace manually:

```python
from framework import IsolatedWorkspace

workspace = IsolatedWorkspace()
workspace.setup()
print(f"Workspace: {workspace.path}")
# Don't call teardown() - inspect manually
```

## Future Enhancements

- [ ] Full Claude Code SDK integration
- [ ] Parallel scenario execution
- [ ] Benchmark tracking over time
- [ ] HTML report generation
- [ ] Scenario recording/replay
- [ ] Network mocking for reproducible tests
- [ ] Integration with CI/CD

## Contributing

To add new scenarios:

1. Create scenario file in `scenarios/`
2. Follow the pattern: `def create() -> Scenario`
3. Document expected behavior and assertions
4. Test it: `python eval/run_scenario.py <name>`
5. Update this README

## License

Same as kurt-core project.
