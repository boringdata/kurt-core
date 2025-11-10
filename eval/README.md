# Kurt Evaluation Framework

Test Kurt agent behavior using Claude agent sessions via Anthropic SDK.

## Quick Start

### 1. Install

```bash
uv sync --extra eval
```

### 2. Configure API Key

```bash
cp eval/.env.example eval/.env
# Edit eval/.env and add your ANTHROPIC_API_KEY
```

Get your API key from: https://console.anthropic.com/settings/keys

### 3. List Available Scenarios

```bash
uv run kurt-eval list
```

### 4. Run a Scenario

```bash
# Run by number
uv run kurt-eval run 1

# Run by name
uv run kurt-eval run 01_basic_init

# View results
cat eval/results/01_basic_init_*.json
cat eval/results/01_basic_init_*.md
```

## How It Works

1. **Isolated Workspace**: Each test runs in `/tmp/kurt_eval_<uuid>/`
2. **Auto-setup**: Runs `kurt init`, creates directories, installs `.claude/` plugin
3. **Real Agent**: Uses Anthropic SDK to create actual Claude agent sessions
4. **Tool Execution**: Agent can use Bash, Read, Write, Edit, Glob, Grep
5. **Validation**: Assertions check files, database, tool usage
6. **Results**: JSON metrics + markdown transcript saved to `eval/results/`

## Available Scenarios

See [scenarios/](scenarios/) directory for all scenario definitions.

## Documentation

- **[CONVERSATION_COMPLETION.md](CONVERSATION_COMPLETION.md)** - Two-tier conversation completion detection system
  - How it detects when multi-turn conversations should end
  - Heuristics + LLM fallback approach
  - Configuration, testing, and troubleshooting

## Multi-Turn Conversations

The framework supports intelligent multi-turn conversations with automatic completion detection:

```yaml
- name: my_scenario
  initial_prompt: run /create-project

  user_agent_prompt: |
    You are creating a blog project.
    When asked for project name: respond "tech-blog"
    When asked for goal: respond "Write technical articles"
```

The system automatically:
- Detects when the agent is asking questions (continues conversation)
- Detects when the task is complete (ends conversation)
- Uses fast heuristics for obvious cases
- Falls back to LLM for nuanced cases

See [CONVERSATION_COMPLETION.md](CONVERSATION_COMPLETION.md) for details.
