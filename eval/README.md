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

---

## Directory Structure

```
eval/
├── README.md                 # This file - comprehensive guide
├── scenarios/               # Test scenario definitions
│   ├── scenarios_kurt_setup.yaml
│   ├── scenarios_content_ingestion.yaml
│   └── scenarios_retrieval.yaml
│
├── mock/                    # Mock data for testing
│   ├── data/               # Raw source content
│   │   ├── documents/     # Website & documentation content
│   │   │   ├── acme-corp/      # Company website
│   │   │   ├── acme-docs/      # Technical documentation
│   │   │   └── competitor-co/  # Competitor site
│   │   ├── db/            # Database dumps (JSONL)
│   │   │   └── acme-docs/      # Pre-built knowledge graph
│   │   └── integrations/  # Integration data
│   │       ├── research/       # HackerNews, Reddit, Perplexity
│   │       ├── analytics/      # Domain/page analytics
│   │       └── cms/            # Sanity CMS exports
│   │
│   └── generators/         # Mock data generators & loaders
│
├── framework/              # Core evaluation framework
├── results/                # Test execution results
└── tests/                  # Framework unit tests
```

---

## Scenarios

Organized into three categories:

### Kurt Setup (`scenarios_kurt_setup.yaml`)
Tests for initialization and project configuration:
- `01_basic_init` - Basic Kurt initialization
- `02_project_no_sources` - Interactive project without sources
- `03_project_with_sources` - Interactive project with sources
- `04_preconfigured_project` - Handle existing configuration

### Content Ingestion (`scenarios_content_ingestion.yaml`)
Tests for fetching and indexing:
- `01_fetch_from_url` - Discover and fetch content
- `02_index_and_build_graph` - Build knowledge graph
- `03_fetch_with_include_filter` - Selective fetching
- `04_fetch_skip_index` - Fetch without indexing
- `05_multi_source_fetch` - Multiple sources integration

### Retrieval & Answer (`scenarios_retrieval.yaml`)
Tests for the answer command:
- `01_answer_multiple_questions` - Answer 4 questions with correctness metrics
- `02_answer_with_verbose` - Verbose retrieval statistics
- `03_answer_max_docs` - Document limit control
- `04_answer_full_workflow` - Complete end-to-end from scratch
- `05_answer_empty_graph` - Handle empty knowledge graph
- `06_answer_multi_source` - Cross-source synthesis

---

## Mock Data

### Quick Usage: Load Pre-Built Database (< 1 second)

```bash
# In your test directory
KURT_TELEMETRY_DISABLED=1 uv run kurt init
python3 eval/mock/generators/load_dump.py acme-docs
```

Now ready with 15+ entities and 4 documents!

### Using in Scenarios

```yaml
setup_commands:
  - KURT_TELEMETRY_DISABLED=1 uv run kurt init
  - python3 eval/mock/generators/load_dump.py acme-docs
```

### Available Mock Data

#### `mock/data/documents/` - Website & Documentation Content
- **acme-corp/**: Company website (home, about, blog posts, pricing)
- **acme-docs/**: Technical documentation (6 markdown files: getting-started, authentication guide, advanced guide, API reference, etc.)
- **competitor-co/**: Competitor website (case studies, feature comparisons, tutorials)

#### `mock/data/db/` - Fast Database Dumps

**ACME Docs Knowledge Graph** (`acme-docs/`)
- 4 documents (Getting Started, Auth Guide, Advanced, API Ref)
- 15 entities (ACME, Node.js, Python, JWT, OAuth, etc.)
- 19 document-entity links
- 11 entity relationships

**Loading time**: < 1 second (vs 30-60s for fetch+index) - **50-60x faster!**

**Format**: JSONL (one JSON object per line)
- Human-readable
- Git-friendly (line-based diffs)
- Streamable (process line-by-line)

#### `mock/data/integrations/` - Integration Data
- **research/**: HackerNews posts, Reddit threads, Perplexity queries (5 JSON files)
- **analytics/**: Domain summaries, page analytics, trending/declining pages (5 JSON files)
- **cms/**: Sanity CMS exports

#### `mock/generators/` - Data Tools
- `load_dump.py` - Import JSONL dumps into Kurt projects
- `create_dump.py` - Export Kurt projects to JSONL dumps
- `generate_mock_data.py` - Generate mock content

```bash
# Create new dump from your project
python3 eval/mock/generators/create_dump.py ~/my-kurt-project my-dump-name
```

---

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

---

## Creating New Scenarios

### Basic Scenario

```yaml
- name: my_test
  description: What this tests

  initial_prompt: |
    Do something interesting

  assertions:
    - type: FileExists
      path: output.txt
```

### With Pre-Setup (Fast)

```yaml
- name: my_test
  description: Test with pre-built fixtures

  setup_commands:
    - KURT_TELEMETRY_DISABLED=1 uv run kurt init
    - python3 eval/mock/fixtures/databases/load_dump.py acme_docs

  initial_prompt: |
    Answer: "What is ACME?"
```

### From Scratch (Full Workflow)

```yaml
- name: my_test
  description: Test complete workflow

  # No setup_commands - agent does everything

  initial_prompt: |
    1. Initialize Kurt
    2. Fetch from http://docs.acme-corp.com
    3. Index content
    4. Answer: "What is ACME?"
```

---

## Assertion Types

```yaml
assertions:
  # File checks
  - type: FileExists
    path: kurt.config

  # Database checks
  - type: SQLQueryAssertion
    query: SELECT COUNT(*) >= 5 FROM entities

  # Content checks
  - type: ConversationContains
    text: "Success"
    case_sensitive: false

  # Tool usage
  - type: ToolWasUsed
    tool_name: Bash

  # Metrics
  - type: MetricEquals
    metric_path: conversation.completed
    expected_value: true

  - type: MetricGreaterThan
    metric_path: conversation.turns
    expected_value: 3
```

---

## Best Practices

### 1. Use Database Dumps for Speed
✅ **Do**: Pre-load with JSONL dumps (< 1s)
```yaml
setup_commands:
  - python3 eval/mock/generators/load_dump.py acme-docs
```

❌ **Don't**: Fetch + index in every test (30-60s)
```yaml
setup_commands:
  - kurt content fetch && kurt content index
```

### 2. Organize Scenarios by Purpose
- **Setup tests** → `scenarios_kurt_setup.yaml`
- **Ingestion tests** → `scenarios_content_ingestion.yaml`
- **Retrieval tests** → `scenarios_retrieval.yaml`

### 3. Add Correctness Metrics
Check that answers contain expected keywords:
```yaml
assertions:
  - type: ConversationContains
    text: "API key"
    case_sensitive: false
```

### 4. Use Pre-Setup for Fast Iteration
- **Development**: Use fixtures (fast, consistent)
- **CI/CD**: Mix of both (validate full workflow)

---

## Performance Tips

**Database Dumps**: 50-60x faster than fetch+index
- Setup: < 1 second
- Consistent: Same data every time
- Portable: JSONL files are git-friendly

**Parallel Scenarios**: Run multiple scenarios in parallel
```bash
uv run kurt-eval run 1 2 3 --parallel
```

---

## Troubleshooting

### Scenario Fails Immediately
- Check `setup_commands` run successfully
- Verify database fixture exists
- Check API key is configured

### Agent Gets Stuck
- Review conversation in `eval/results/*.md`
- Check if initial_prompt is clear
- Verify assertions are achievable

### Database Dump Load Fails
```bash
# Verify dump exists
ls eval/mock/fixtures/databases/acme_docs/

# Check database is initialized
ls .kurt/kurt.sqlite

# Load manually to see errors
python3 eval/mock/fixtures/databases/load_dump.py acme_docs
```

---

## Additional Documentation

- **[CONVERSATION_COMPLETION.md](CONVERSATION_COMPLETION.md)** - Multi-turn conversation completion detection
- **Test results** in `eval/results/` - JSON + markdown transcripts

---

## Contributing

When adding new scenarios or mock data:

1. **New scenario** → Add to appropriate `scenarios_*.yaml` file
2. **New mock data** → Add to `mock/data/`
3. **New fixture** → Export with `create_dump.py`, add to `mock/fixtures/databases/`
4. **Test it** → Run the scenario to verify it works

Keep mock data realistic but minimal for fast tests.
