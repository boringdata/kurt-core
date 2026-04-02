# Kurt Simplification Spec

**Version**: 0.1.0 (draft)
**Status**: Design phase
**Breaking changes**: Yes (removes DBOS, new Tool API)

## Goal

Transform Kurt from DBOS-based workflow system to simple tool-based CLI that:
- Provides tools for Claude Code (map, fetch, llm, embed, write, agent)
- Runs TOML-defined workflows
- Uses Git + Dolt for isolation/collaboration

## Core Concepts

### Tools (Layer 1)

User-facing primitives. 7 tools total:

| Tool | Purpose | input_data | Config | Output (list) |
|------|---------|------------|--------|---------------|
| `map` | Discover URLs/files | None | source, url, depth | [{url, source_type}] |
| `fetch` | Fetch content | [{url}] | engine, concurrency | [{url, content_path, status}] |
| `llm` | Batch LLM calls | [{row}] | prompt_template, output_schema, model | [{...row, ...llm_output}] |
| `embed` | Generate embeddings | [{text}] | model, text_field | [{text, embedding}] |
| `write` | Persist to DB | [{row}] | table, mode, key | [{row_id, status}] |
| `sql` | Query DB | None | query, params | [{...row}] |
| `agent` | Run sub-agent | [{row}]? | prompt, tools, max_turns, permission_mode | [{result, artifacts}] |

**All tools return `list[OutputModel]`** - even single-result tools wrap in list for consistency.

**input_data rules:**
- `None` = tool generates data (map, sql)
- `[{row}]` = tool transforms data (fetch, llm, embed, write)
- `[{row}]?` = optional (agent can work with or without input)
- If a step has no `depends_on`, `input_data = [{...inputs}]` (single row built from `[inputs]`)

**map config rules:**
- `source = "url"` requires `url`
- `source = "file"` requires `path`
- `source = "cms"` requires `base_url` (or provider-specific key)

### Substeps (Internal)

Each tool has internal substeps for observability:

```
map    → map_url | map_folder | map_cms
fetch  → fetch_urls → save_content → generate_embeddings
llm    → llm_batch
agent  → run_claude_agent
```

Users don't call substeps. They exist for debugging/progress tracking.

Substep progress is emitted as `SubstepEvent` entries and written to `step_events`.

### Workflows (Layer 2)

TOML files that compose tools:

```toml
[workflow]
name = "enrich_leads"

[inputs]
seed_url = "https://example.com/sitemap.xml"

[steps.discover]
type = "function"
function = "map"
config = { source = "url", url = "{{seed_url}}", depth = 2 }

[steps.fetch]
type = "function"
function = "fetch"
depends_on = ["discover"]
config = { engine = "trafilatura" }

[steps.extract]
type = "llm"
depends_on = ["fetch"]
prompt_template = "Extract: {content}"
output_schema = "CompanyInfo"
model = "gpt-4o-mini"

[steps.save]
type = "function"
function = "write"
depends_on = ["extract"]
config = { table = "leads", mode = "upsert", key = "url" }
```

**Step types:**
- `function`: calls a tool by name (`function = "map" | "fetch" | "write" | ...`).
- `llm`: runs the LLM tool with `prompt_template` and optional `output_schema`.
- `agent`: runs the agent tool with `prompt` and guardrails.

### Isolation (Layer 3)

Git + Dolt branching for environment isolation:

- **Git**: code, docs, TOML workflows (line-level merge)
- **Dolt**: metadata, embeddings, workflow state (cell-level merge)
- **Same branch names** in both systems
- **Git hooks** auto-sync Dolt on checkout/commit/push
- **`kurt merge`** required for merges (checks Dolt conflicts first)

## Architecture

```
┌────────────────────────────────────────────┐
│                   CLI                       │
│  kurt map | fetch | llm | run | merge      │
└─────────────────────┬──────────────────────┘
                      │
┌─────────────────────▼──────────────────────┐
│              Tool Registry                  │
│  map | fetch | llm | embed | write | agent │
└─────────────────────┬──────────────────────┘
                      │
┌─────────────────────▼──────────────────────┐
│            Workflow Engine                  │
│  TOML parser → DAG → async executor        │
└─────────────────────┬──────────────────────┘
                      │
┌─────────────────────▼──────────────────────┐
│              Observability                  │
│  workflow_runs | step_logs | step_events   │
└─────────────────────┬──────────────────────┘
                      │
┌─────────────────────▼──────────────────────┐
│            Storage (Git + Dolt)            │
│  .git/ (code) | .dolt/ (data)              │
└────────────────────────────────────────────┘
```

## Tool Interface

```python
@dataclass
class ToolContext:
    db: DoltDB                    # Database connection
    http: HttpClient              # HTTP client for fetching
    llm: LLMClient                # LLM provider (OpenAI, Anthropic, etc.)
    settings: Settings            # Config (API keys, paths, etc.)
    tools: dict[str, Tool]        # Registry for agent tool calls

class Tool(ABC):
    name: str
    description: str
    InputModel: type[BaseModel]
    OutputModel: type[BaseModel]

    async def run(
        self,
        params: BaseModel,
        context: ToolContext,
        on_progress: Callable[[SubstepEvent], None] | None,
    ) -> ToolResult
```

```python
@dataclass
class ToolResult:
    success: bool
    data: list[BaseModel]
    errors: list[dict]           # [{step_id, error, row_idx?}]
    metadata: dict
    substeps: list[dict]         # Optional summary; detailed events go to step_events

@dataclass
class SubstepEvent:
    substep: str                  # e.g., "fetch_urls", "save_content"
    status: str                   # running | completed | failed
    current: int | None           # Progress counter
    total: int | None
    message: str | None
```

## Error Handling

**Tool failure**: Returns `ToolResult(success=False, errors=[...])`

**Workflow behavior**:
- Step fails → workflow stops (default)
- `continue_on_error = true` in step config → log error, continue
- Partial results available in `step_logs`
- `step_logs.error_count = len(ToolResult.errors)`

```toml
[steps.fetch]
type = "function"
function = "fetch"
continue_on_error = true    # Don't fail workflow if some URLs fail
```

## Agent Tool Config

```python
class AgentConfig(BaseModel):
    prompt: str                              # Required: task for agent
    tools: list[str] | None = None           # Allowed tools (default: all except agent)
    max_turns: int = 10                      # Max agent iterations
    model: str = "claude-sonnet-4-20250514"  # LLM model
    permission_mode: str = "bypassPermissions"
    max_tokens: int = 200000
    timeout_seconds: int = 300               # Hard timeout

class AgentOutput(BaseModel):
    result: str                              # Agent's final response
    artifacts: list[dict]                    # Files/data created
    tool_calls: list[dict]                   # Tools called with results
    turns_used: int                          # Actual turns taken
```

**Constraints:**
- Agent cannot call `agent` tool (no recursion)
- `tools = ["sql", "write"]` restricts to only those tools
- `tools = null` allows all tools except agent
- Exceeding `max_turns` returns partial result with `turns_used = max_turns`

**CLI usage:**
```bash
# Run agent directly (outside workflow)
kurt agent "Review the data and fix inconsistencies" --tools=sql,write --max-turns=5
```

## File Structure

```
kurt-core/src/kurt/
├── tools/
│   ├── base.py           # Tool, ToolResult, SubstepEvent
│   ├── registry.py       # TOOLS dict, execute_tool()
│   ├── map/              # MapTool + substeps
│   ├── fetch/            # FetchTool + substeps
│   ├── llm/              # LLMTool
│   ├── embed/            # EmbedTool
│   ├── write/            # WriteTool
│   └── agent/            # AgentTool
├── engine/
│   ├── parser.py         # TOML → Workflow
│   ├── dag.py            # Build execution graph
│   └── runner.py         # Async executor
├── isolation/
│   ├── branch.py         # Git + Dolt branching
│   ├── merge.py          # Conflict detection
│   └── hooks.py          # Git hook scripts
├── db/
│   └── dolt.py           # Dolt client (embedded + server)
└── cli/
    ├── tools.py          # kurt map, fetch, llm
    ├── workflow.py       # kurt run, status
    └── branch.py         # kurt branch, merge, pull
```

## Git-Dolt Sync

| Git operation | Dolt sync | Method |
|---------------|-----------|--------|
| checkout | auto | post-checkout hook |
| commit | auto | post-commit hook |
| push | auto | pre-push hook |
| merge | manual | `kurt merge` command |
| pull | manual | `kurt pull` command |

**Hook enforcement:**
- `prepare-commit-msg` hook blocks merge commits with error message
- User must use `kurt merge` instead of `git merge`

**Known bypass scenarios (hooks can't prevent):**
- `git merge --no-verify` skips hooks
- Fast-forward merges (no commit, no hook)
- Direct branch manipulation (`git reset`, `git rebase`)
- Hooks not installed (fresh clone)

**Detection & repair:**
```bash
# Check sync status
kurt doctor

# Output:
# ✓ Git hooks installed
# ✓ Dolt initialized
# ✗ Git/Dolt branch mismatch: git=main, dolt=feature/old
# ✗ Uncommitted Dolt changes
#
# Run 'kurt repair' to fix issues

# Auto-repair
kurt repair

# Actions:
# - Sync Dolt branch to match Git
# - Commit pending Dolt changes
# - Reinstall hooks if missing
```

## CLI Commands

### Tool commands (direct invocation)
```bash
# Map URLs
kurt map https://example.com/sitemap.xml --depth=2

# Fetch content
kurt fetch urls.txt --engine=trafilatura --concurrency=5

# Batch LLM
kurt llm data.jsonl --prompt-template="Extract: {content}" --model=gpt-4o-mini

# Embed
kurt embed data.jsonl --text-field=content --model=text-embedding-3-small

# Write to DB
kurt write data.jsonl --table=leads --mode=upsert --key=url

# Query
kurt sql "SELECT * FROM leads WHERE status='new'"
```

### Workflow commands
```bash
kurt run workflow.toml --seed-url="..."     # Run workflow
kurt status <run_id>                         # Check status
kurt status <run_id> --follow                # Stream progress
kurt logs <run_id> --step=fetch              # View step logs
kurt cancel <run_id>                         # Cancel running workflow
```

### Branch commands
```bash
kurt branch create feature/experiment        # Create Git + Dolt branch
kurt branch list                             # List branches
kurt branch switch main                      # Switch (uses git checkout)
kurt merge feature/experiment                # Merge (Dolt first, then Git)
kurt pull                                    # Pull Git + Dolt
kurt push                                    # Push Git + Dolt
```

## Config Validation

Tool configs are validated against `InputModel`:

```python
class FetchTool(Tool):
    class InputModel(BaseModel):
        input_data: list[dict] | None = None
        config: FetchConfig

    class FetchConfig(BaseModel):
        engine: Literal["trafilatura", "tavily", "firecrawl", "httpx"] = "trafilatura"
        concurrency: int = Field(default=5, ge=1, le=20)
        embed: bool = False
```

**Validation happens:**
1. CLI parses args → validates against InputModel
2. Workflow engine parses step config → validates against InputModel
3. Invalid config → clear error message with schema

## Data Flow Semantics

### Input Interpolation

Config values can reference workflow inputs using `{{var}}` syntax:

```toml
[inputs]
seed_url = { type = "string", required = true }
max_depth = { type = "int", default = 2 }

[steps.discover]
type = "function"
function = "map"
config = { source = "url", url = "{{seed_url}}", depth = "{{max_depth}}" }
```

**Rules:**
- `{{var}}` replaced with input value before validation
- Type coercion: string input → target type (int, bool, etc.)
- Missing required input → error before workflow starts
- Unknown `{{var}}` → error (typo protection)
- Escaping: `\{\{literal\}\}` for literal braces
- Only applies to config values, not input_data

### Fan-in Behavior (Multiple Dependencies)

When a step has multiple `depends_on`, input_data is **concatenated**:

```toml
[steps.merge]
type = "function"
function = "write"
depends_on = ["fetch_a", "fetch_b"]  # input_data = fetch_a.output + fetch_b.output
```

**Concat rules:**
- Order matches `depends_on` order
- Duplicates preserved (no dedup)
- Empty outputs skipped

**For join semantics**, use explicit SQL step:
```toml
[steps.join]
type = "function"
function = "sql"
depends_on = ["users", "orders"]
config = { query = "SELECT * FROM {{users}} u JOIN {{orders}} o ON u.id = o.user_id" }
```

### Step Output Persistence

Step outputs are:
1. Stored in memory during workflow execution
2. Available to dependent steps via `depends_on`
3. Logged to `step_logs.output_count` (count only, not data)
4. **Not** persisted to Dolt automatically

**Default input_data behavior:**
- No `depends_on` → `input_data = [{...inputs}]` (single row after interpolation)
- One dependency → `input_data = outputs[dep].data`
- Multiple dependencies → concat in `depends_on` order
- Failed dependency:
  - `continue_on_error = false` → workflow stops
  - `continue_on_error = true` → dependency contributes empty list, errors logged

To persist, use explicit `write` step:
```toml
[steps.save]
type = "function"
function = "write"
depends_on = ["extract"]
config = { table = "results" }
```

## DAG Execution

Steps with independent `depends_on` run in parallel:

```toml
[steps.fetch_a]
type = "function"
function = "fetch"
depends_on = ["discover"]

[steps.fetch_b]
type = "function"
function = "fetch"
depends_on = ["discover"]

[steps.merge]
type = "function"
function = "write"
depends_on = ["fetch_a", "fetch_b"]  # Waits for both
```

Execution:
```
discover ─┬─► fetch_a ─┬─► merge
          └─► fetch_b ─┘
```

## Output Schema Reference

`output_schema` references Pydantic models in `models.py`:

```toml
[steps.extract]
type = "llm"
output_schema = "CompanyInfo"
```

```python
# workflows/enrich/models.py
class CompanyInfo(BaseModel):
    name: str
    industry: str | None
    size: str | None
    confidence: float
```

**Resolution order:**
1. `workflows/<name>/models.py` (workflow-local)
2. `kurt/tools/llm/models.py` (built-in)
3. Error if not found

## Branch Naming

```
main                     # Default branch
feature/<name>           # Feature work
agent/<task_id>          # Agent-created branches
user/<username>/<name>   # User experiments
```

**Rules:**
- Alphanumeric + `.` `_` `-` `/`
- Max 100 chars
- Same name in Git and Dolt
- Auto-sanitized: `"my feature!"` → `"my-feature"`

## Migration from DBOS

| Before (DBOS) | After (Simple) |
|---------------|----------------|
| @DBOS.workflow() | TOML workflow |
| @DBOS.step() | Tool.run() |
| DBOS.Queue | asyncio.Semaphore |
| DBOS.set_event() | DB insert |
| per-workspace schema | Git + Dolt branches |

## Dolt Schema

```sql
-- Workflow execution tracking
CREATE TABLE workflow_runs (
    id VARCHAR(36) PRIMARY KEY,
    workflow VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,      -- pending | running | completed | failed
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error TEXT,
    inputs JSON,
    metadata JSON
);

-- Step-level tracking (summary per step)
CREATE TABLE step_logs (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) REFERENCES workflow_runs(id),
    step_id VARCHAR(255) NOT NULL,
    tool VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    input_count INT,
    output_count INT,
    error_count INT,
    errors JSON,
    metadata JSON
);

-- Append-only event stream (step + substep progress)
CREATE TABLE step_events (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36) REFERENCES workflow_runs(id),
    step_id VARCHAR(255) NOT NULL,
    substep VARCHAR(255),
    status VARCHAR(20) NOT NULL,      -- running | progress | completed | failed
    created_at TIMESTAMP,
    current INT,
    total INT,
    message TEXT,
    metadata JSON
);

-- Document metadata (from map/fetch)
CREATE TABLE documents (
    id VARCHAR(36) PRIMARY KEY,
    url TEXT NOT NULL,
    source_type VARCHAR(20),          -- url | file | cms
    content_path TEXT,                -- Path to content file
    content_hash VARCHAR(64),
    embedding BLOB,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Index for streaming queries
CREATE INDEX idx_step_events_run ON step_events(run_id, created_at);

-- LLM call traces
CREATE TABLE llm_traces (
    id VARCHAR(36) PRIMARY KEY,
    run_id VARCHAR(36),
    step_id VARCHAR(255),
    model VARCHAR(100),
    prompt TEXT,
    response TEXT,
    tokens_in INT,
    tokens_out INT,
    cost DECIMAL(10,6),
    latency_ms INT,
    created_at TIMESTAMP
);
```

## Workflow Inputs

First step gets data from `[inputs]` section:

```toml
[workflow]
name = "enrich"

[inputs]
seed_url = { type = "string", required = true }
max_pages = { type = "int", default = 100 }

[steps.discover]
type = "function"
function = "map"
config = { source = "url", url = "{{seed_url}}", depth = 2 }
```

**CLI usage:**
```bash
kurt run workflow.toml --seed-url="https://example.com" --max-pages=50
```

**Input resolution:**
1. CLI args (`--seed-url`)
2. Environment vars (`KURT_SEED_URL`)
3. Default values from spec
4. Error if required input missing
See **Data Flow Semantics → Input Interpolation** for templating rules.

## Secrets & Configuration

```bash
# ~/.kurt/config.toml
[llm]
openai_api_key = "sk-..."
anthropic_api_key = "sk-ant-..."
default_model = "gpt-4o-mini"

[fetch]
tavily_api_key = "tvly-..."
firecrawl_api_key = "fc-..."

[storage]
content_dir = "./content"        # Where to save fetched content
```

**Environment variables override config:**
```bash
OPENAI_API_KEY=sk-... kurt llm data.jsonl
```

**Per-project config**: `kurt.toml` in project root overrides global.

## Config Module Alignment

The existing `kurt.config` module remains the **single source of truth** for settings.

**Precedence (highest → lowest):**
1. Environment variables
2. Project config (`kurt.toml`)
3. User config (`~/.kurt/config.toml`)

**Key mappings (examples):**
- `LLM.default_model` → `settings.llm.default_model`
- `LLM.openai_api_key` → `settings.llm.openai_api_key`
- `LLM.anthropic_api_key` → `settings.llm.anthropic_api_key`
- `Fetch.default_engine` → `settings.fetch.default_engine`
- `Fetch.content_dir` → `settings.storage.content_dir`

**ToolContext construction** must use `kurt.config.load_config()` (no ad hoc loaders).

## Testing

### Tool tests
```python
# tests/tools/test_fetch.py
async def test_fetch_single_url():
    tool = FetchTool()
    result = await tool.run(
        params=FetchTool.InputModel(
            input_data=[{"url": "https://example.com"}],
            config={"engine": "httpx"},
        ),
        context=mock_context(),
    )
    assert result.success
    assert len(result.data) == 1
```

### Workflow tests
```bash
# Dry run (no side effects)
kurt run workflow.toml --dry-run --seed-url="..."

# Test with fixtures
kurt test workflow.toml --fixtures=tests/fixtures/
```

### Integration tests
```bash
# Uses test Dolt DB
KURT_TEST=1 pytest tests/integration/
```

## Observability API

Query workflow/step status programmatically:

```python
from kurt.db import DoltDB

db = DoltDB(".dolt")

# Get workflow status (single row)
run = db.query_one("SELECT * FROM workflow_runs WHERE id = ?", [run_id])

# Get step summary (one row per step)
steps = db.query("SELECT * FROM step_logs WHERE run_id = ?", [run_id])

# Stream progress events (append-only table)
for event in db.subscribe("step_events", run_id=run_id):
    print(f"{event.step_id}/{event.substep}: {event.status} [{event.current}/{event.total}]")
```

**Streaming model:**
- `step_events` is append-only (new row per progress update)
- `step_logs` is updated in place (final summary per step)
- `db.subscribe()` polls `step_events` with `created_at > last_seen`

## Observability Compatibility (DBOS → Kurt Events)

Replace DBOS tracking with a thin tracking module:

```python
from kurt.observability import track_event, write_event

track_event(run_id, key="status", value="running")      # replaces DBOS.set_event
write_event(run_id, key="progress", payload={...})      # replaces DBOS.write_stream
```

**Event payload schema (step_events):**
- `run_id`, `step_id`, `substep` (optional)
- `status`: `running | progress | completed | failed`
- `current`, `total` for progress counters
- `message` for human-readable context
- `metadata` for tool-specific data

**CLI mapping:**
- `kurt workflows list/status` → `workflow_runs`
- `kurt logs` → `step_events` (filtered by `step_id` and `substep`)

**CLI status polling:**
```bash
# JSON output for scripting
kurt status <run_id> --json

# Stream progress events
kurt status <run_id> --follow

# Output:
# [12:00:01] fetch/fetch_urls: running [0/100]
# [12:00:02] fetch/fetch_urls: progress [10/100]
# [12:00:03] fetch/fetch_urls: progress [20/100]
# ...
# [12:00:10] fetch/fetch_urls: completed [100/100]
# [12:00:10] fetch/save_content: running
```

## Complete Example

**Project structure:**
```
my-project/
├── .git/
├── .dolt/
├── kurt.toml
├── workflows/
│   └── enrich.toml
├── content/                 # Fetched content (gitignored)
└── models.py
```

**kurt.toml:**
```toml
[project]
name = "my-project"

[llm]
default_model = "gpt-4o-mini"

[fetch]
default_engine = "trafilatura"
content_dir = "./content"
```

**workflows/enrich.toml:**
```toml
[workflow]
name = "enrich_companies"
description = "Discover and enrich company data"

[inputs]
seed_url = { type = "string", required = true }

[steps.discover]
type = "function"
function = "map"
config = { source = "url", depth = 2 }

[steps.fetch]
type = "function"
function = "fetch"
depends_on = ["discover"]
config = { engine = "trafilatura", concurrency = 5, embed = true }

[steps.extract]
type = "llm"
depends_on = ["fetch"]
prompt_template = """
Extract company information from this content:
{content}

Return JSON with: name, industry, size, website
"""
output_schema = "CompanyInfo"
model = "gpt-4o-mini"

[steps.save]
type = "function"
function = "write"
depends_on = ["extract"]
config = { table = "companies", mode = "upsert", key = "url" }
```

**models.py:**
```python
from pydantic import BaseModel

class CompanyInfo(BaseModel):
    name: str
    industry: str | None = None
    size: str | None = None
    website: str | None = None
```

**Run:**
```bash
# Create isolated branch
kurt branch create feature/enrich-test

# Run workflow
kurt run workflows/enrich.toml --seed-url="https://example.com/sitemap.xml"

# Check results
kurt sql "SELECT name, industry FROM companies LIMIT 10"

# If good, merge to main
kurt merge feature/enrich-test
```

## Design Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Tool config validation | Strict Pydantic, reject unknown keys | Catch typos early, explicit > implicit |
| Workflow resumability | Not in v1, add later | Complexity; step outputs not persisted |
| Agent CLI access | Yes, `kurt agent "prompt"` | Useful for ad-hoc tasks |
| Dolt hosting | Local files (v1), bucket remote (v2) | Start simple, add sharing later |
| Content storage | Files on disk (gitignored) | CC can grep, Dolt for metadata only |

## Open Questions

1. **Real-time collab**: Yjs layer or just branch-per-user?
2. **Embeddings**: Store in Dolt or treat as rebuild-able cache?
3. **Streaming transport**: WebSocket vs SSE vs polling for `--follow`?
4. **Workflow resumability (v2)**: Checkpoint to Dolt or external storage?
