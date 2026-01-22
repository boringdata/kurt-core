# Kurt CLI Simplification Plan

## Vision

**Kurt = Workflow orchestration layer for Claude Code**

Like beads lives behind Claude Code for issue tracking, Kurt lives behind Claude Code for data workflows.

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code                             │
│                                                              │
│    "Fetch example.com, extract company info, save to DB"    │
│                            │                                 │
│                            ▼                                 │
│    ┌────────────────────────────────────────────────────┐   │
│    │                      Kurt                           │   │
│    │                                                     │   │
│    │  1. Workflow orchestration (TOML → execution)      │   │
│    │  2. Tool definitions (fetch, llm, embed, write)    │   │
│    │  3. Isolation/collaboration (Git + Dolt branches)  │   │
│    │  4. Observability (progress, traces, costs)        │   │
│    │                                                     │   │
│    └────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Kurt doesn't replace Claude Code. Kurt gives Claude Code superpowers for data work.**

---

## What Kurt IS and IS NOT

### Kurt IS:
- **Tool provider** - fetch, map, llm_batch, embed, write
- **Workflow runner** - execute TOML-defined pipelines
- **Isolation manager** - Git + Dolt branches for safe experimentation
- **Observability layer** - track progress, costs, errors

### Kurt IS NOT:
- A replacement for Claude Code (Claude does the thinking)
- A complex orchestration system (no DBOS, no K8s)
- A database (uses Dolt)
- A file system (uses Git)

### Analogy:
```
beads   → Issue tracking for Claude Code
kurt    → Data workflows for Claude Code
```

---

## Current State (Problems)

| Issue | Impact |
|-------|--------|
| DBOS dependency | Complex, per-workspace schemas, cloud deployment bottleneck |
| Workflows = Python code | Hard for agents to create/modify |
| fetch/map are "workflows" | Should be tools/primitives |
| No isolation model | Can't safely run agent experiments |
| Coupled to specific DB | Hard to run locally vs hosted |

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Kurt CLI                                    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         Layer 1: Tools                              │ │
│  │                                                                      │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │ │
│  │  │   map   │ │  fetch  │ │   llm   │ │  embed  │ │  write  │      │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘      │ │
│  │                                                                      │ │
│  │  Pure async functions. No DBOS. Stateless.                          │ │
│  │  Can be called by: CLI, Agent, Workflow Engine, API                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Layer 2: Workflow Engine                        │ │
│  │                                                                      │ │
│  │  - Parses TOML workflow definitions                                 │ │
│  │  - Executes tools in DAG order                                      │ │
│  │  - Tracks progress (observability)                                  │ │
│  │  - Simple state: workflow_runs, step_logs tables                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Layer 3: Isolation                              │ │
│  │                                                                      │ │
│  │  Git (code + docs) ←──────────→ Dolt (metadata + embeddings)       │ │
│  │                                                                      │ │
│  │  Branch = full environment isolation                                │ │
│  │  Merge = smart conflict resolution (line-level + cell-level)        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Tools (Primitives)

### Tools vs Substeps

**User perspective**: Tools are high-level primitives. User calls `map`, `fetch`, `llm` - doesn't care about internals.

**Internal perspective**: Each tool may have substeps for observability/debugging.

```
┌─────────────────────────────────────────────────────────────────┐
│                     User-Facing Tools                            │
├─────────────────────────────────────────────────────────────────┤
│  map      │  fetch     │  llm       │  embed     │  write      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Internal Substeps (observability)               │
├─────────────────────────────────────────────────────────────────┤
│  map:                                                            │
│    └─ map_url | map_folder | map_cms                            │
│                                                                  │
│  fetch:                                                          │
│    ├─ fetch_urls (batch or single depending on engine)          │
│    ├─ save_content                                               │
│    └─ generate_embeddings (optional)                            │
│                                                                  │
│  llm:                                                            │
│    └─ llm_batch (parallel calls with semaphore)                 │
│                                                                  │
│  write:                                                          │
│    └─ persist (upsert to table)                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Substeps exist for:**
- Debugging → "which part failed?"
- Observability → "progress of each phase"
- Resumability → "retry from failed substep" (future)

**User never calls substeps directly.** They're internal implementation details.

### Tool Interface

```python
# kurt/tools/base.py

from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class SubstepEvent:
    """Emitted by tools for observability."""
    substep: str           # e.g., "map_url", "save_content"
    status: str            # running, completed, failed
    current: int | None    # progress counter
    total: int | None
    message: str | None
    metadata: dict | None

@dataclass
class ToolResult:
    success: bool
    data: list[BaseModel]
    errors: list[dict]
    metadata: dict         # timing, counts
    substeps: list[dict]   # substep execution log for observability

@dataclass
class ToolContext:
    db: Database
    http: HttpClient
    llm: LLMClient
    storage: StorageClient
    settings: Settings

class Tool(ABC):
    name: str
    description: str
    InputModel: type[BaseModel]
    OutputModel: type[BaseModel]

    @abstractmethod
    async def run(
        self,
        *,
        params: BaseModel,
        context: ToolContext,
        on_progress: Callable[[SubstepEvent], None] | None = None,
    ) -> ToolResult:
        pass
```

Each tool defines Pydantic `InputModel` and `OutputModel`. This drives validation and schema generation for the CLI/agents.

### Core Tools

| Tool | Purpose | Config | Output |
|------|---------|--------|--------|
| `map` | Discover URLs/files | `{source: url\|folder\|cms, url?, folder?, depth?}` | `[{url, source_type}]` |
| `fetch` | Fetch content | `{engine, concurrency, embed?}` | `[{url, content, status}]` |
| `llm` | Batch LLM processing | `{prompt_template, output_schema, model}` | `[{row + llm_output}]` |
| `embed` | Generate embeddings | `{model, text_field}` | `[{text, embedding}]` |
| `write` | Persist to database | `{table, mode, key}` | `{rows_written}` |
| `sql` | Query database | `{query, params}` | `[{row}]` |
| `agent` | Run sub-agent (Claude) | `{prompt, tools?, max_turns?}` | `{result, artifacts}` |

**Data flow**: Tools receive `input_data` (list of rows from previous step) + `config` dict.

### Agent Tool

The `agent` tool spawns a sub-agent (Claude Code) that can use other tools:

```python
# kurt/tools/agent/__init__.py

class AgentTool(Tool):
    name = "agent"
    description = "Run a sub-agent with access to kurt tools"

    class InputModel(BaseModel):
        input_data: list[dict] | None = None
        config: AgentConfig

    class AgentConfig(BaseModel):
        prompt: str                          # Task for the agent
        tools: list[str] | None = None       # Subset of tools (default: all)
        max_turns: int = 10                  # Max agent iterations
        model: str = "claude-sonnet-4-20250514"

    class OutputModel(BaseModel):
        success: bool
        result: str                          # Agent's final response
        artifacts: list[dict]                # Files created, data written, etc.
        tool_calls: list[dict]               # Tools the agent called

    async def run(self, *, params, context, on_progress) -> ToolResult:
        # 1. Prepare tool schemas for agent
        available_tools = self._filter_tools(params.config.tools, context.tools)

        # 2. Run Claude Code sub-agent
        agent_result = await run_claude_agent(
            prompt=params.config.prompt,
            input_data=params.input_data,
            tools=available_tools,
            max_turns=params.config.max_turns,
            model=params.config.model,
            on_progress=on_progress,
        )

        return ToolResult(
            success=agent_result.success,
            data=[self.OutputModel(
                success=agent_result.success,
                result=agent_result.response,
                artifacts=agent_result.artifacts,
                tool_calls=agent_result.tool_calls,
            )],
            errors=agent_result.errors,
            metadata={"turns": agent_result.turns_used},
            substeps=agent_result.substeps,
        )
```

**Use in workflow:**
```toml
[steps.review]
tool = "agent"
depends_on = ["extract"]
config = {
    prompt = "Review the extracted data. Fix any inconsistencies. Flag uncertain entries.",
    tools = ["sql", "write"],    # Only allow sql and write
    max_turns = 5
}
```

**Agent can:**
- Read `input_data` from previous step
- Call other kurt tools (map, fetch, llm, write, sql)
- Create/modify files in the workspace
- Return structured result + artifacts

### Tool Implementation (with Substeps)

```python
# kurt/tools/fetch.py

class FetchTool(Tool):
    name = "fetch"
    description = "Fetch content from URLs"

    class InputModel(BaseModel):
        input_data: list[dict]
        config: FetchConfig

    class OutputModel(BaseModel):
        document_id: str
        url: str
        content_path: str | None
        status: str
        error: str | None = None

    async def run(
        self,
        *,
        params: InputModel,
        context: ToolContext,
        on_progress: Callable[[SubstepEvent], None] | None = None,
    ) -> ToolResult:
        rows = params.input_data
        config = params.config
        substeps = []

        # ─────────────────────────────────────────────────────────
        # SUBSTEP 1: fetch_urls
        # ─────────────────────────────────────────────────────────
        if on_progress:
            on_progress(SubstepEvent(
                substep="fetch_urls", status="running",
                current=0, total=len(rows), message=f"Fetching {len(rows)} URLs"
            ))

        fetched_rows = await self._fetch_urls(rows, config, on_progress)

        substeps.append({
            "substep": "fetch_urls",
            "status": "completed",
            "fetched": len([r for r in fetched_rows if r["status"] == "success"]),
            "failed": len([r for r in fetched_rows if r["status"] == "error"]),
        })

        # ─────────────────────────────────────────────────────────
        # SUBSTEP 2: save_content
        # ─────────────────────────────────────────────────────────
        if on_progress:
            on_progress(SubstepEvent(
                substep="save_content", status="running",
                total=len(fetched_rows), message="Saving content to files"
            ))

        rows_with_paths = await self._save_content(fetched_rows, config)

        substeps.append({
            "substep": "save_content",
            "status": "completed",
            "saved": len([r for r in rows_with_paths if r.get("content_path")]),
        })

        # ─────────────────────────────────────────────────────────
        # SUBSTEP 3: generate_embeddings (optional)
        # ─────────────────────────────────────────────────────────
        if config.embed:
            if on_progress:
                on_progress(SubstepEvent(
                    substep="generate_embeddings", status="running",
                    message="Generating embeddings"
                ))

            rows_with_embeddings = await self._generate_embeddings(rows_with_paths, config)

            substeps.append({
                "substep": "generate_embeddings",
                "status": "completed",
                "embedded": len([r for r in rows_with_embeddings if r.get("embedding")]),
            })
            final_rows = rows_with_embeddings
        else:
            final_rows = rows_with_paths

        # ─────────────────────────────────────────────────────────
        # Return result with substep log
        # ─────────────────────────────────────────────────────────
        return ToolResult(
            success=all(r["status"] == "success" for r in final_rows),
            data=[self.OutputModel.model_validate(r) for r in final_rows],
            errors=[r for r in final_rows if r["status"] == "error"],
            metadata={"total": len(rows)},
            substeps=substeps,  # For observability
        )

    async def _fetch_urls(self, rows, config, on_progress):
        """Internal: fetch URLs with concurrency control."""
        sem = asyncio.Semaphore(config.concurrency)
        # ... implementation using fetch_from_web(), fetch_from_file(), etc.

    async def _save_content(self, rows, config):
        """Internal: save content to files."""
        # ... implementation

    async def _generate_embeddings(self, rows, config):
        """Internal: generate embeddings."""
        # ... implementation
```

**Key points:**
- User calls `fetch` tool - one tool, simple interface
- Internally, tool runs substeps: `fetch_urls` → `save_content` → `generate_embeddings`
- Each substep emits progress events for observability
- `substeps` list in result shows what happened (for debugging/logging)

### Tools as Agent Tools

```python
# kurt/tools/registry.py

TOOLS = build_tools(build_tool_context(load_settings()))

def get_tool_schemas() -> list[dict]:
    """Return tool schemas for Claude."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.InputModel.model_json_schema(),
            "output_schema": tool.OutputModel.model_json_schema(),
        }
        for tool in TOOLS.values()
    ]

async def execute_tool(name: str, params: dict, context: ToolContext) -> ToolResult:
    """Execute a tool by name."""
    tool = TOOLS[name]
    validated = tool.InputModel.model_validate(params)
    return await tool.run(params=validated, context=context)
```

### Tool Construction (Config Module)

The config module builds dependencies and provides the `ToolContext` used everywhere (local/team/hosted).

```python
# kurt/config.py

def build_tool_context(settings: Settings) -> ToolContext:
    return ToolContext(
        db=Database(settings.database_url),
        http=HttpClient(settings.http),
        llm=LLMClient(settings.llm),
        storage=StorageClient(settings.storage),
        settings=settings,
    )

def build_tools(context: ToolContext) -> dict[str, Tool]:
    return {
        "map": MapTool(),
        "fetch": FetchTool(),
        "llm": LLMTool(),
        "embed": EmbedTool(),
        "write": WriteTool(),
        "sql": SQLTool(),
    }
```

### Workflow-Local Tools and Models (Breaking Change)

Keep the `workflows/<name>/tools.py` and `workflows/<name>/models.py` layout, but require the new Tool API:

- `tools.py` must expose Tool classes or a `TOOLS` dict of Tool instances. Legacy context-only functions are not supported.
- `steps.<name>.function` references a tool name from the registry (global or workflow-local namespace).
- `models.py` holds Pydantic models referenced by `steps.<name>.output_schema`.

---

## Layer 2: Workflow Engine

### Workflow Definition (TOML)

```toml
# workflows/enrich_leads.toml

[workflow]
name = "enrich_leads"
description = "Discover, fetch, and enrich company data"

[inputs]
seed_url = { type = "string", description = "Starting URL for discovery" }

# ─────────────────────────────────────────────────────────────
# Steps use TOOLS (map, fetch, llm, embed, write)
# ─────────────────────────────────────────────────────────────

[steps.discover]
tool = "map"                              # Tool name
config = { source = "url", depth = 2 }    # Tool config
# input_data comes from [inputs] for first step

[steps.fetch]
tool = "fetch"
depends_on = ["discover"]                 # DAG dependency
config = { engine = "trafilatura", concurrency = 5, embed = true }

[steps.extract]
tool = "llm"
depends_on = ["fetch"]
config = {
    prompt_template = "Extract company info from: {content}",
    output_schema = "CompanyInfo",        # Reference to models.py
    model = "gpt-4o-mini"
}

[steps.save]
tool = "write"
depends_on = ["extract"]
config = { table = "enriched_leads", mode = "upsert", key = "url" }
```

**Step types:**
- All steps use `tool = "<tool_name>"` - unified syntax
- `llm` is a tool like any other, not a special type
- Config is tool-specific (validated against tool's InputModel)

**Data flow:**
- First step gets data from `[inputs]`
- Subsequent steps get `input_data` from `depends_on` step's output
- Multiple `depends_on` = data merged from all dependencies

### Workflow Engine (Simple)

```python
# kurt/engine/runner.py

class WorkflowRunner:
    def __init__(self, context: ToolContext):
        self.context = context
        self.db = context.db
        self.tools = context.tools  # Tool registry

    async def run(
        self,
        workflow_path: str,
        inputs: dict | None = None,
    ) -> WorkflowResult:
        workflow = parse_workflow(workflow_path)
        run_id = str(uuid4())

        # Track workflow start
        await self.db.insert("workflow_runs", {
            "id": run_id,
            "workflow": workflow.name,
            "status": "running",
            "started_at": datetime.utcnow(),
        })

        # Build DAG and execute in topological order
        dag = build_dag(workflow.steps)
        results: dict[str, ToolResult] = {}

        try:
            for step_id in dag.topological_order():
                step = workflow.steps[step_id]

                # Resolve input_data from dependencies
                input_data = self._resolve_input(step, results, inputs)

                # Log step start
                step_log_id = str(uuid4())
                await self.db.insert("step_logs", {
                    "id": step_log_id,
                    "run_id": run_id,
                    "step_id": step_id,
                    "tool": step.tool,
                    "status": "running",
                    "started_at": datetime.utcnow(),
                    "input_count": len(input_data or []),
                })

                # Execute tool (unified - all steps use tool = "<name>")
                tool = self.tools[step.tool]
                params = tool.InputModel.model_validate({
                    "input_data": input_data,
                    "config": step.config or {},
                })
                result = await tool.run(
                    params=params,
                    context=self.context,
                    on_progress=lambda e: self._emit_progress(run_id, step_id, e),
                )

                results[step_id] = result

                # Log step completion + substeps
                await self.db.update("step_logs", step_log_id, {
                    "status": "completed" if result.success else "failed",
                    "completed_at": datetime.utcnow(),
                    "output_count": len(result.data or []),
                    "substeps": result.substeps,  # For observability
                    "metadata": result.metadata,
                })

                if not result.success:
                    raise ToolError(f"Step {step_id} failed", errors=result.errors)

            await self.db.update("workflow_runs", run_id, {"status": "completed"})
            return WorkflowResult(success=True, results=results)

        except Exception as e:
            await self.db.update("workflow_runs", run_id, {
                "status": "failed",
                "error": str(e),
            })
            raise

    def _resolve_input(self, step, results, workflow_inputs):
        """Get input_data from dependencies or workflow inputs."""
        if not step.depends_on:
            # First step - use workflow inputs
            return workflow_inputs

        # Merge outputs from all dependencies
        input_data = []
        for dep_id in step.depends_on:
            dep_result = results.get(dep_id)
            if dep_result and dep_result.data:
                input_data.extend(dep_result.data)
        return input_data
```

**Simplified:**
- All steps use `tool = "<name>"` - no special cases for `llm` or `agent`
- `llm` is just a tool like `fetch` or `map`
- Substeps logged in `step_logs.substeps` for observability

---

## Layer 3: Isolation Model

### Environment = Git + Dolt

```
workspace/
├── .git/                    # Git versioning (code + docs)
├── .dolt/                   # Local Dolt database (default)
├── src/                     # Code
├── content/                 # Markdown docs (agent can grep/edit)
│   └── *.md
├── workflows/               # Workflow definitions
│   └── *.toml
├── kurt.toml                # Project config
└── .dolt-ref                # Optional pointer to remote Dolt branch/commit

Dolt (local file store, optional remote):
├── documents                # Metadata, file references
├── embeddings               # Vectors
├── workflow_runs            # Execution state
└── step_logs                # Step-level observability
```

### Sandbox Profiles (Same DB Engine Everywhere)

- **Solo local**: `.dolt/` file store only, no remote required.
- **Local team**: Shared GitHub repo + shared bucket as Dolt remote.
- **Hosted**: Shared GitHub repo + bucket-backed Dolt remote, same branches and tools.

### Branching = Full Isolation

```python
# kurt/isolation/branch.py

import re

def sanitize_branch(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._/-]+", "-", name).strip("-")

async def create_branch(name: str):
    """Create isolated environment."""
    safe_name = sanitize_branch(name)
    # Git branch (code + docs)
    await run(f"git checkout -b {safe_name}")
    try:
        # Dolt branch (data)
        await dolt(f"CALL DOLT_CHECKOUT('-b', '{safe_name}')")
    except Exception:
        # Roll back git branch to avoid drift
        await run("git checkout main")
        await run(f"git branch -D {safe_name}")
        raise

async def merge_branch(name: str):
    """Merge isolated work back."""
    safe_name = sanitize_branch(name)
    # Git merge (line-level)
    await run(f"git checkout main && git merge {safe_name}")

    # Dolt merge (cell-level, smart)
    await dolt(f"CALL DOLT_CHECKOUT('main')")
    await dolt(f"CALL DOLT_MERGE('{safe_name}')")
```

### Agent Workflow

```python
# kurt/agent/executor.py

async def run_agent_task(task_id: str, prompt: str):
    branch = f"agent/{sanitize_branch(task_id)}"

    # 1. Create isolated environment
    await create_branch(branch)

    # 2. Agent works (uses tools, edits files)
    result = await run_claude_code(prompt, tools=TOOLS)

    # 3. Commit work
    await run("git add -A && git commit -m 'Agent work'")
    await dolt("CALL DOLT_COMMIT('-am', 'Agent work')")

    # 4. Return for human review (or auto-merge)
    return AgentResult(branch=branch, result=result)
```

---

## Observability

### Tables (Simple, No DBOS)

```sql
-- Workflow execution tracking
CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY,
    workspace_id UUID,
    workflow TEXT NOT NULL,
    status TEXT NOT NULL,  -- pending, running, completed, failed
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    metadata JSONB
);

-- Step-level tracking
CREATE TABLE step_logs (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES workflow_runs(id),
    step_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    input_count INT,
    output_count INT,
    error_count INT,
    metadata JSONB  -- timing, custom metrics
);

-- Progress/event stream (append-only)
CREATE TABLE step_events (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES workflow_runs(id),
    step_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- running, progress, completed, failed
    created_at TIMESTAMPTZ,
    message TEXT,
    metadata JSONB
);

-- LLM call tracing (existing, keep)
CREATE TABLE llm_traces (
    id UUID PRIMARY KEY,
    run_id UUID,
    step_id TEXT,
    model TEXT,
    prompt TEXT,
    response TEXT,
    tokens_in INT,
    tokens_out INT,
    cost DECIMAL(10,6),
    latency_ms INT,
    error TEXT,
    created_at TIMESTAMPTZ
);
```

### Progress Streaming

```python
# kurt/observability/progress.py

@dataclass
class ProgressEvent:
    run_id: str
    step_id: str
    status: str  # running, progress, completed, failed
    current: int | None = None
    total: int | None = None
    message: str | None = None
    metadata: dict | None = None

class ProgressTracker:
    def __init__(self, db: Database, run_id: str):
        self.db = db
        self.run_id = run_id

    async def emit(self, event: ProgressEvent):
        # Store in DB (append-only)
        await self.db.insert("step_events", {...})

        # Emit to subscribers (WebSocket, CLI display)
        await self._notify_subscribers(event)
```

### CLI Status

```bash
# Watch workflow progress
kurt status <run_id> --follow

# Output:
# Workflow: enrich_leads (run_id: abc123)
# Status: running
#
# Steps:
# ✓ discover    completed  (found 150 URLs)
# ◐ fetch       running    [45/150] 30%
# ○ extract     pending
# ○ embed       pending
# ○ save        pending
```

---

## CLI Commands (Simplified)

```bash
# Tools (direct use)
kurt map https://example.com/sitemap.xml
kurt fetch urls.txt --concurrency 5
kurt llm data.jsonl --prompt-template "Extract..." --model gpt-4o-mini

# Workflows
kurt run workflows/enrich.toml
kurt status <run_id>
kurt logs <run_id> --step fetch

# Isolation
kurt branch create feature/experiment
kurt branch list
kurt branch merge feature/experiment

# Sync
kurt push    # git push + dolt push
kurt pull    # git pull + dolt pull
```

---

## Migration Path

### Phase 1: Tool API + Registry (Breaking Change)

```
1. Define Tool API (Pydantic Input/Output) + ToolContext
2. Replace workflow tools.py functions with Tool classes or TOOLS dict
3. Update steps.<name>.function to reference tool names
```

### Phase 2: Workflow Engine (Reuse Existing DSL)

```
1. Reuse current steps schema (function/llm/agent)
2. Implement async DAG executor (no DBOS)
3. Add workflow_runs/step_logs/step_events
4. Update kurt workflows CLI to read new tables
```

### Phase 3: Remove DBOS

```
1. Remove DBOS dependency + DBOS tables
2. Replace DBOS step helpers (llm_step/embedding_step/save_step)
3. Replace background worker + scheduler with async runner
4. Remove DBOS-specific status/logs APIs
```

### Phase 4: Add Isolation (Dolt)

```
1. Add Dolt integration for metadata
2. Implement branch commands
3. Implement merge with conflict resolution
4. Update agent executor to use branches
```

---

## File Structure (Target)

```
kurt-core/
├── src/kurt/
│   ├── tools/                    # Layer 1: User-facing tools
│   │   ├── __init__.py
│   │   ├── base.py               # Tool interface, SubstepEvent, ToolResult
│   │   ├── registry.py           # Tool registry + execute_tool()
│   │   │
│   │   ├── map/                  # MapTool
│   │   │   ├── __init__.py       # MapTool class (user-facing)
│   │   │   ├── url.py            # substep: discover_from_url()
│   │   │   ├── folder.py         # substep: discover_from_folder()
│   │   │   ├── cms.py            # substep: discover_from_cms()
│   │   │   └── models.py         # MapConfig, MapDocument
│   │   │
│   │   ├── fetch/                # FetchTool
│   │   │   ├── __init__.py       # FetchTool class (user-facing)
│   │   │   ├── web.py            # substep: fetch_from_web()
│   │   │   ├── file.py           # substep: fetch_from_file()
│   │   │   ├── engines/          # trafilatura, tavily, firecrawl, httpx
│   │   │   └── models.py         # FetchConfig, FetchDocument
│   │   │
│   │   ├── llm/                  # LLMTool
│   │   │   ├── __init__.py       # LLMTool class (user-facing)
│   │   │   └── batch.py          # substep: llm_batch()
│   │   │
│   │   ├── embed/                # EmbedTool
│   │   │   ├── __init__.py       # EmbedTool class (user-facing)
│   │   │   └── batch.py          # substep: embed_batch()
│   │   │
│   │   └── write/                # WriteTool
│   │       ├── __init__.py       # WriteTool class (user-facing)
│   │       └── persist.py        # substep: persist_rows()
│   │
│   ├── engine/                   # Layer 2: Workflow Engine
│   │   ├── __init__.py
│   │   ├── parser.py             # TOML parsing
│   │   ├── dag.py                # DAG building/sorting
│   │   └── runner.py             # Async execution
│   │
│   ├── isolation/                # Layer 3: Git + Dolt
│   │   ├── __init__.py
│   │   ├── branch.py             # create/switch/delete branches
│   │   ├── merge.py              # merge with conflict detection
│   │   ├── sync.py               # push/pull coordination
│   │   └── hooks.py              # Git hook scripts
│   │
│   ├── db/                       # Database (Dolt)
│   │   ├── __init__.py
│   │   ├── dolt.py               # DoltDB client (embedded + server)
│   │   └── models.py             # workflow_runs, step_logs, etc.
│   │
│   ├── observability/            # Tracking
│   │   ├── __init__.py
│   │   ├── progress.py           # SubstepEvent handling
│   │   └── display.py            # CLI progress display
│   │
│   └── cli/                      # CLI
│       ├── __init__.py
│       ├── main.py               # Entry point
│       ├── tools.py              # kurt map, kurt fetch, etc.
│       ├── workflow.py           # kurt run, kurt status
│       └── branch.py             # kurt branch, kurt merge, kurt pull
│
├── workflows/                    # Example TOML workflows
│   └── *.toml
│
└── pyproject.toml
```

**Structure rationale:**
- Each tool is a **folder** containing the tool class + internal substeps
- Substeps (`url.py`, `web.py`, etc.) are internal - not exposed to users
- User imports `from kurt.tools import MapTool, FetchTool` - doesn't see substeps
- Substeps share models/config within their tool folder

---

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| Orchestration | DBOS | Simple async + DAG |
| Parallelism | DBOS.Queue | asyncio.Semaphore |
| State tracking | DBOS.set_event | DB inserts |
| Workflows | Python code | TOML definitions |
| fetch/map | Workflows | Tools (primitives) |
| Isolation | Per-workspace schema | Git + Dolt branches |
| Observability | DBOS events/streams | Simple tables |
| Complexity | High | **Low** |

---

## How Claude Code Uses Kurt

### Direct Tool Calls

```bash
# Claude Code runs tools directly
claude> "Fetch the pricing pages from example.com"

# Claude executes:
kurt fetch https://example.com/pricing https://example.com/plans

# Claude reads result:
cat content/example.com/pricing.md
```

### Workflow Execution

```bash
# Claude creates a workflow
claude> "Create a workflow to enrich leads"

# Claude writes:
# workflows/enrich.toml

# Claude runs it:
kurt run workflows/enrich.toml

# Claude monitors:
kurt status <run_id> --follow
```

### Isolated Experimentation

```bash
# Claude creates a branch for risky work
claude> "Try a new approach for extraction"

# Claude executes:
kurt branch create experiment/new-extraction

# Claude works (all changes isolated)
kurt fetch ...
kurt llm ...

# If it works:
kurt branch merge experiment/new-extraction

# If it fails:
kurt branch delete experiment/new-extraction
```

### Example Session

```
User: "Build me a lead enrichment pipeline for SaaS companies"

Claude: I'll create a workflow for this. Let me:

1. First, create an isolated branch:
   $ kurt branch create feature/saas-enrichment

2. Create the workflow definition:
   $ cat > workflows/saas_enrich.toml << 'EOF'
   [workflow]
   name = "saas_enrichment"
   description = "Enrich SaaS company data"

   [inputs]
   seed_url = { type = "string" }

   [steps.discover]
   tool = "map"
   config = { source = "url", depth = 2 }

   [steps.fetch]
   tool = "fetch"
   depends_on = ["discover"]
   config = { engine = "trafilatura", embed = true }

   [steps.extract]
   tool = "llm"
   depends_on = ["fetch"]
   config = {
       prompt_template = "Extract: company_name, pricing_model, target_market",
       model = "gpt-4o-mini"
   }

   [steps.save]
   tool = "write"
   depends_on = ["extract"]
   config = { table = "saas_leads", mode = "upsert", key = "url" }
   EOF

3. Test the workflow:
   $ kurt run workflows/saas_enrich.toml --input-url="https://example.com/sitemap.xml"

4. Check results:
   $ kurt sql "SELECT * FROM saas_leads LIMIT 5"

5. If good, merge to main:
   $ kurt branch merge feature/saas-enrichment
```

---

## Open Questions

### Collaboration

1. **Real-time collab**: Add Yjs layer for live editing?
   - Yjs for real-time → periodic commits to Git/Dolt
   - Or skip Yjs, just use branch-per-user model?

2. **Conflict resolution UX**: How to surface Git vs Dolt conflicts?
   - Git: edit files manually (familiar)
   - Dolt: SQL or --ours/--theirs (less familiar)
   - Need good CLI guidance

### Architecture

3. **Cloud vs Local execution**:
   - Local: Git + Dolt files on disk
   - Cloud: GitHub + Dolt remote bucket + hosted compute
   - How to make transition seamless?

### Data Model

4. **What goes in Git vs Dolt?**
   ```
   Git (text, line-merge):     Dolt (data, cell-merge):
   ├── Code                    ├── Document metadata
   ├── Markdown docs           ├── Embeddings
   ├── TOML configs            ├── Workflow runs
   └── ???                     └── LLM traces
   ```
   - Where does workflow state belong?
   - Where do large outputs go?

5. **Embeddings**: Git or Dolt?
   - Dolt: Queryable, but large binary blobs
   - Git: Would need LFS
   - Or: Treat as cache, rebuild from content?

---

## Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Remove DBOS | ✓ Yes | Simplify, cloud-friendly |
| Git for code/docs | ✓ Yes | Line-level merge, CC can grep |
| Dolt everywhere | ✓ Yes | Same engine local/team/hosted |
| Local bootstrap | ✓ .dolt file store | Zero setup, works offline |
| Sharing model | ✓ Shared bucket + GitHub | Simple collaboration model |
| .dolt-ref | Optional | Track remote branch/commit when sharing |
| Same branch names | ✓ Yes | Simple mental model |
| Breaking change | ✓ Yes | Remove DBOS + require Tool API |
| Tools as primitives | ✓ Yes | fetch, map, llm are tools not workflows |
| TOML workflows | ✓ Yes | Agent-friendly, declarative |

## Key Decisions Pending

| Decision | Options | Notes |
|----------|---------|-------|
| Bucket provider | S3 / GCS / R2 | Cost vs latency |
| Real-time collab | Yjs / Branch-per-user | Complexity vs UX |
| Embeddings storage | Dolt / Cache (rebuild) | Size vs simplicity |

---

## Git-Dolt Sync Strategy

**Problem**: Git has no `pre-merge` hook. Can't safely check Dolt conflicts before Git merge.

**Solution**: Hooks for safe ops, `kurt merge` command for merges.

```
┌─────────────────────────────────────────────────────────────┐
│                     Sync Strategy                            │
├─────────────────────────────────────────────────────────────┤
│  Operation      │  Method       │  Why                      │
├─────────────────────────────────────────────────────────────┤
│  checkout       │  hook         │  Safe, post-op sync       │
│  commit         │  hook         │  Safe, post-op sync       │
│  push           │  hook         │  Safe, pre-op check       │
│  merge          │  kurt cmd     │  No pre-merge hook in Git │
│  pull           │  kurt cmd     │  Includes merge           │
├─────────────────────────────────────────────────────────────┤
│  git checkout ✓    git commit ✓    git push ✓               │
│  git merge ✗ → use kurt merge                               │
│  git pull ✗  → use kurt pull                                │
└─────────────────────────────────────────────────────────────┘
```

### Hooks (auto-sync for safe ops)

**post-checkout** - Switch Dolt branch when Git switches
```bash
#!/bin/bash
# .git/hooks/post-checkout
[ "$3" != "1" ] && exit 0  # only branch checkout
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null) || exit 0
[ ! -d ".dolt" ] && exit 0

if dolt sql -q "SELECT 1 FROM dolt_branches WHERE name='$BRANCH'" | grep -q 1; then
    dolt sql -q "CALL DOLT_CHECKOUT('$BRANCH')"
else
    dolt sql -q "CALL DOLT_CHECKOUT('-b', '$BRANCH')"
fi
echo "[kurt] Dolt → $BRANCH"
```

**post-commit** - Commit Dolt when Git commits
```bash
#!/bin/bash
# .git/hooks/post-commit
[ ! -d ".dolt" ] && exit 0
MSG=$(git log -1 --format=%s)
dolt sql -q "CALL DOLT_ADD('.')"
dolt sql -q "CALL DOLT_COMMIT('-m', '$MSG')" 2>/dev/null || true
echo "[kurt] Dolt committed"
```

**pre-push** - Push Dolt when Git pushes
```bash
#!/bin/bash
# .git/hooks/pre-push
[ ! -d ".dolt" ] && exit 0
REMOTE=$1
BRANCH=$(git symbolic-ref --short HEAD)
if dolt remote | grep -q "$REMOTE"; then
    dolt push "$REMOTE" "$BRANCH" || exit 1
    echo "[kurt] Dolt pushed"
fi
```

**pre-merge (blocker)** - Block `git merge`, require `kurt merge`
```bash
#!/bin/bash
# .git/hooks/prepare-commit-msg
[ "$2" != "merge" ] && exit 0
[ ! -d ".dolt" ] && exit 0

echo ""
echo "❌ Use 'kurt merge' instead of 'git merge'"
echo ""
echo "   kurt merge checks Dolt conflicts first."
echo "   Direct git merge could desync Git/Dolt."
echo ""
exit 1
```

### Commands (for merge/pull)

**kurt merge** - Dolt first, then Git
```bash
#!/bin/bash
# kurt merge <branch>
BRANCH=$1
[ -z "$BRANCH" ] && echo "Usage: kurt merge <branch>" && exit 1

# 1. Try Dolt merge first
echo "[kurt] Checking Dolt merge..."
dolt sql -q "CALL DOLT_MERGE('$BRANCH')"
if [ $? -ne 0 ]; then
    CONFLICTS=$(dolt sql -q "SELECT count(*) FROM dolt_conflicts" -r csv | tail -1)
    if [ "$CONFLICTS" != "0" ]; then
        echo ""
        echo "❌ Dolt has $CONFLICTS conflict(s)"
        echo ""
        echo "Resolve with:"
        echo "  dolt conflicts cat <table>"
        echo "  dolt conflicts resolve --ours   # or --theirs"
        echo "  kurt merge $BRANCH              # retry"
        exit 1
    fi
    exit 1
fi
echo "[kurt] Dolt merged ✓"

# 2. Dolt succeeded, now Git merge (skip hook via env var)
echo "[kurt] Git merge..."
KURT_SKIP_MERGE_HOOK=1 git merge "$BRANCH"
echo "[kurt] Done ✓"
```

**kurt pull** - Pull both, merge if needed
```bash
#!/bin/bash
# kurt pull [remote]
REMOTE=${1:-origin}
BRANCH=$(git symbolic-ref --short HEAD)

# 1. Fetch both
git fetch "$REMOTE"
dolt fetch "$REMOTE" 2>/dev/null || true

# 2. Check if merge needed
LOCAL=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse "$REMOTE/$BRANCH")
[ "$LOCAL" = "$REMOTE_HEAD" ] && echo "[kurt] Already up to date" && exit 0

# 3. Use kurt merge
kurt merge "$REMOTE/$BRANCH"
```

### Summary

| Command | What happens |
|---------|--------------|
| `git checkout -b feature` | ✓ Hook creates Dolt branch |
| `git checkout main` | ✓ Hook switches Dolt branch |
| `git commit -m "msg"` | ✓ Hook commits Dolt |
| `git push origin` | ✓ Hook pushes Dolt |
| `git merge feature` | ✗ Blocked → use `kurt merge` |
| `git pull origin` | ✗ Use `kurt pull` |

**90% of Git works normally. Only merge/pull need `kurt` commands.**

---

## Next Steps

1. [ ] Create `kurt/tools/` with simple async implementations
2. [ ] Create `kurt/engine/` with TOML parser + DAG runner
3. [ ] Add observability tables (workflow_runs, step_logs)
4. [ ] Integrate Dolt for data storage
5. [ ] Add Git hooks for Dolt sync
6. [ ] Remove DBOS dependency
7. [ ] Update CLI commands
8. [ ] Test agent workflow (branch → work → merge)
