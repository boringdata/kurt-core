# Architecture Research: Python Plugin Systems

**Domain:** Python CLI plugin/skill extensibility
**Researched:** 2026-02-09
**Confidence:** HIGH

## Standard Architecture

### System Overview

Plugin systems in Python follow a layered architecture with clear separation between host and plugins:

```
┌─────────────────────────────────────────────────────────────┐
│                   Host Application (CLI)                     │
│                  (Click commands, workflow orchestration)    │
├─────────────────────────────────────────────────────────────┤
│  Plugin Manager                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Discovery   │→ │ Registration │→ │  Lifecycle   │       │
│  │  (scan/load) │  │  (validate)  │  │  (init/run)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│  Extension Points (Hook System)                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ HookSpec │  │ HookSpec │  │ HookSpec │  │ HookSpec │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       ↓             ↓             ↓             ↓           │
│  [Plugin Implementations]                                    │
├─────────────────────────────────────────────────────────────┤
│  Plugin Interface Layer                                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Base Classes (Tool, Fetcher, Mapper)                 │   │
│  │  + Context (db, http, llm, settings)                  │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Plugin Storage                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │  ./skills │  │~/.kurt/   │  │ builtin/ │                   │
│  │          │  │ skills   │  │          │                   │
│  └──────────┘  └──────────┘  └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Kurt Implementation |
|-----------|----------------|---------------------|
| **Plugin Manager** | Discovery, validation, registration, lifecycle | `src/kurt/skills/manager.py` - SkillManager singleton |
| **Discovery Layer** | Find plugins from search paths, entry points | `src/kurt/skills/discovery.py` - scan paths, parse SKILL.md |
| **Registry** | Store plugin metadata, provide lookup | `src/kurt/tools/core/registry.py` - TOOLS dict, register_tool() |
| **Hook System** | Define extension points, invoke implementations | Pluggy-style: HookspecMarker/HookimplMarker OR simple ABC inheritance |
| **Base Classes** | Define plugin contracts (Tool, Fetcher, Mapper) | `src/kurt/tools/core/base.py` (Tool), `src/kurt/tools/fetch/core/base.py` |
| **Loader** | Import plugin code dynamically | importlib-based loader in discovery module |
| **Validator** | Check plugin structure, dependencies, compatibility | Validate SKILL.md schema, check Python version, verify base class |
| **Context** | Provide shared resources (db, http, config) | `ToolContext` dataclass with db, http, llm, settings |

## Recommended Project Structure

Kurt's existing structure naturally extends to skills:

```
src/kurt/
├── skills/                    # NEW - skill system core
│   ├── __init__.py
│   ├── manager.py             # SkillManager (singleton)
│   ├── discovery.py           # Path scanning, manifest parsing
│   ├── loader.py              # Dynamic import via importlib
│   ├── validator.py           # Validate SKILL.md + skill.py
│   ├── models.py              # SkillManifest Pydantic model
│   ├── errors.py              # SkillNotFoundError, SkillLoadError
│   ├── cli.py                 # `kurt skill` commands
│   └── tests/
│
├── tools/                     # Existing - becomes skill target
│   ├── core/
│   │   ├── base.py            # Tool ABC (skill implementations extend)
│   │   ├── registry.py        # TOOLS dict (skills register here)
│   │   └── errors.py
│   ├── fetch/
│   │   └── core/base.py       # BaseFetcher (skills can implement)
│   └── map/
│       └── core/base.py       # BaseMapper (skills can implement)
│
├── workflows/                 # Existing - workflow definitions
│   └── agents/
│       └── registry.py        # Similar pattern to skills registry
│
└── config/                    # Existing - config system
    └── base.py                # KurtConfig (add skill_paths field)

# Plugin search paths (in priority order):
./skills/                      # Project-local skills
~/.kurt/skills/                # User-global skills
<installed_package>/builtin/   # Built-in skills (future)
```

### Structure Rationale

- **`skills/` as top-level module**: Follows Kurt's pattern (tools/, workflows/, db/, etc.)
- **Separation from tools/**: Skills USE the Tool abstraction but aren't tools themselves
- **Reuse existing registry**: `tools/core/registry.py` already has TOOLS dict and register_tool()
- **Search path priority**: Project > User > Builtin (like git config: local > global > system)
- **Manifest-driven**: SKILL.md defines metadata, skill.py implements

## Architectural Patterns

### Pattern 1: Discovery via Filesystem Scanning

**What:** Scan designated directories for plugin manifests, similar to Kurt's workflow registry

**When to use:** Simple, no external dependencies, works for local/user plugins

**Trade-offs:**
- Pro: No packaging required, easy development workflow
- Pro: Matches Kurt's existing workflow pattern (workflows/agents/registry.py)
- Con: Doesn't discover installed packages (but Kurt is local-first anyway)

**Example:**
```python
# src/kurt/skills/discovery.py
from pathlib import Path

def discover_skills(search_paths: list[Path]) -> list[SkillManifest]:
    """Scan paths for SKILL.md manifests."""
    manifests = []
    for base_path in search_paths:
        if not base_path.exists():
            continue

        # Structure 1: skills/my-skill/SKILL.md + skill.py
        for skill_dir in base_path.iterdir():
            if not skill_dir.is_dir():
                continue

            manifest_path = skill_dir / "SKILL.md"
            impl_path = skill_dir / "skill.py"

            if manifest_path.exists() and impl_path.exists():
                try:
                    manifest = parse_skill_manifest(manifest_path)
                    manifest.impl_path = impl_path
                    manifests.append(manifest)
                except Exception as e:
                    # Log and skip invalid skills
                    continue

    return manifests
```

**Confidence:** HIGH - Verified pattern from workflows/agents/registry.py (lines 22-59)

### Pattern 2: Entry Points for Installed Packages

**What:** Use setuptools entry points for pip-installable skill packages

**When to use:** For distribution via PyPI, sharing skills across projects

**Trade-offs:**
- Pro: Standard Python packaging mechanism
- Pro: Automatic discovery via importlib.metadata
- Con: Requires packaging setup (pyproject.toml)
- Con: Overkill for local development

**Example:**
```python
# In skill package's pyproject.toml:
[project.entry-points."kurt.skills"]
my_skill = "my_skill_package:register"

# In my_skill_package/__init__.py:
from kurt.tools import register_tool
from .tool import MySkillTool

def register():
    """Called by Kurt during plugin discovery."""
    register_tool(MySkillTool)
```

**Confidence:** HIGH - Official Python packaging standard (https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)

### Pattern 3: Hook System (Pluggy-style)

**What:** Define explicit extension points (hookspecs) that plugins implement (hookimpls)

**When to use:** When host needs control over execution order, result handling, or complex plugin interactions

**Trade-offs:**
- Pro: Explicit contracts, loose coupling
- Pro: Advanced features (call order, wrappers, result collection)
- Con: More complex than simple ABC inheritance
- Con: Additional dependency (pluggy library)

**Example:**
```python
# Host defines hookspecs
from pluggy import HookspecMarker, HookimplMarker

hookspec = HookspecMarker("kurt")
hookimpl = HookimplMarker("kurt")

class SkillHooks:
    @hookspec
    def skill_register(self, manager):
        """Called when skill is loaded."""
        pass

    @hookspec
    def skill_cleanup(self):
        """Called on shutdown."""
        pass

# Plugin implements hooks
class MySkill:
    @hookimpl
    def skill_register(self, manager):
        from kurt.tools import register_tool
        register_tool(MyTool)

    @hookimpl
    def skill_cleanup(self):
        # Release resources
        pass
```

**Confidence:** MEDIUM - Pluggy is production-ready (pytest uses it) but may be overkill for Kurt's needs

**Recommendation for Kurt:** Start with Pattern 1 (filesystem scanning) + simple ABC inheritance (existing Tool base class). Add Pattern 2 (entry points) later if distribution is needed. Skip Pattern 3 unless complex hook orchestration becomes necessary.

### Pattern 4: Manifest-Based Configuration

**What:** Plugin metadata in declarative file (YAML/TOML/Markdown), separate from code

**When to use:** Always - enables validation before loading, supports metadata queries without importing code

**Trade-offs:**
- Pro: Fast listing without importing Python
- Pro: Validates structure before execution
- Pro: Human-readable, easy to edit
- Con: Two files to maintain (manifest + implementation)

**Example:**
```markdown
<!-- SKILL.md -->
---
name: web-archiver
version: 0.1.0
author: Example <user@example.com>
description: Archive web pages to Internet Archive
tags: [web, archival, automation]
requires_python: ">=3.10"
requires_api: [wayback]
implements:
  - type: tool
    class: WebArchiverTool
    name: archive
---

# Web Archiver Skill

Archives web pages to the Internet Archive's Wayback Machine.

## Usage

```bash
kurt workflow run --tool archive --url https://example.com
```
```

**Confidence:** HIGH - Matches Kurt's workflow pattern (workflows/agents/parser.py parses Markdown frontmatter)

## Data Flow

### Plugin Discovery Flow

```
CLI Startup
    ↓
SkillManager.__init__()
    ↓
Discovery.scan_paths(["./skills", "~/.kurt/skills", "builtin/"])
    ↓
For each skill directory:
    ↓
Parse SKILL.md → SkillManifest
    ↓
Validate manifest (schema, version, dependencies)
    ↓
Store in registry (SKILLS dict)
    ↓
Return to host (deferred loading - don't import yet)
```

### Plugin Loading and Registration

```
Tool Execution Request (e.g., "archive" tool)
    ↓
get_tool("archive") called
    ↓
Check TOOLS registry → Not found
    ↓
SkillManager.load_skill("web-archiver")
    ↓
Loader.import_module(skill.impl_path)
    ↓
skill.py executes:
    - @register_tool decorator
    - Adds WebArchiverTool to TOOLS
    ↓
get_tool("archive") → Return WebArchiverTool class
    ↓
Instantiate and execute tool
```

### Plugin Context Flow

```
Tool Execution
    ↓
ToolContext created:
    ↓
    ├── db: DoltDB connection (from get_database_client())
    ├── http: AsyncClient (shared session)
    ├── llm: LLM config (from kurt.toml)
    └── settings: tool-specific config
    ↓
Tool.run(params, context, on_progress)
    ↓
Tool accesses context.db, context.http, etc.
    ↓
ToolResult returned
```

### Key Data Flows

1. **Discovery to Registry:** SKILL.md → SkillManifest → SKILLS dict (metadata only, no code import)
2. **Registry to Execution:** TOOLS dict lookup → import skill.py → register_tool() → Tool class
3. **Host to Plugin:** ToolContext passed to Tool.run() → plugin accesses shared resources
4. **Plugin to Host:** ToolResult returned with success/data/errors/metadata

## Integration Points

### Extension Points in Kurt

| Extension Point | Current Pattern | Skill Integration |
|----------------|-----------------|-------------------|
| **Tools** | register_tool() decorator | Skills call register_tool() on import |
| **Fetchers** | EngineRegistry.register() | Skills call EngineRegistry.register() |
| **Mappers** | EngineRegistry.register() | Skills call EngineRegistry.register() |
| **CLI Commands** | @click.command() | Future: Skills can register subcommands via click-plugins |
| **Workflows** | File-based (workflow.md) | Future: Skills can provide workflow templates |

### Current Registry Patterns in Kurt

Kurt already has THREE registry patterns (inconsistent):

1. **Tools**: Decorator-based (`@register_tool`) with lazy loading
2. **Fetchers/Mappers**: Class method (`EngineRegistry.register()`) with hardcoded calls
3. **Workflows**: File-based discovery (no code registration)

**Recommendation:** Unify on decorator pattern for skills:
- Use `@register_tool` for Tool implementations (already exists)
- Add `@register_fetcher` and `@register_mapper` decorators (new)
- Skills import and decorate their classes, host auto-discovers via filesystem

### External Service Integration

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Dolt DB | Via ToolContext.db | Skills access pre-configured client |
| HTTP | Via ToolContext.http | Shared AsyncClient with retry/timeout |
| LLM APIs | Via ToolContext.llm | Config from kurt.toml |
| External APIs | Skill manages own client | Store API keys in kurt.toml SKILL section |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI ↔ SkillManager | Direct function calls | SkillManager is singleton |
| SkillManager ↔ Registry | Dictionary lookup | SKILLS dict (metadata), TOOLS dict (loaded) |
| Tool ↔ Context | Dataclass attribute access | ToolContext passed on every run() call |
| Skill ↔ Skill | Via registry only | Skills don't import each other directly |

## Anti-Patterns

### Anti-Pattern 1: Hardcoded Plugin Registration

**What people do:** Import and register all plugins in `__init__.py`:
```python
# BAD - forces eager loading, tight coupling
from .plugin1 import Plugin1Tool
from .plugin2 import Plugin2Tool

TOOLS = {
    "plugin1": Plugin1Tool,
    "plugin2": Plugin2Tool,
}
```

**Why it's wrong:**
- All plugins loaded on import (slow startup)
- New plugins require modifying core code
- Breaks with missing dependencies (crashes if plugin1's deps missing)

**Do this instead:** Lazy discovery with filesystem scanning:
```python
# GOOD - lazy loading, loose coupling
def get_tool(name: str) -> type[Tool]:
    _ensure_tools_loaded()  # Only loads when needed
    if name not in TOOLS:
        # Try loading from skills
        skill = SkillManager.find_skill_for_tool(name)
        if skill:
            SkillManager.load_skill(skill.name)
    return TOOLS[name]
```

**Confidence:** HIGH - Kurt already has this pattern in tools/core/registry.py (lines 34-86)

### Anti-Pattern 2: Plugins Modifying Core State

**What people do:** Plugin directly modifies host application state:
```python
# BAD - plugin reaches into host internals
class BadSkill:
    def setup(self):
        import kurt.config
        kurt.config.GLOBAL_SETTING = "modified"  # Mutation!
```

**Why it's wrong:**
- Hidden dependencies between plugins
- Order-dependent behavior (breaks if plugin load order changes)
- Hard to debug (who changed this?)

**Do this instead:** Pass context, return values:
```python
# GOOD - explicit data flow
class GoodSkillTool(Tool):
    async def run(self, params, context, on_progress):
        # Read from context (immutable)
        db = context.db
        config = context.settings

        # Return results (explicit)
        return ToolResult(
            success=True,
            data=[{"key": "value"}],
        )
```

**Confidence:** HIGH - Matches Kurt's existing ToolContext pattern

### Anti-Pattern 3: Complex Hook Hierarchies

**What people do:** Create elaborate inheritance trees for plugins:
```python
# BAD - over-engineered
class BasePlugin(ABC):
    pass

class AdvancedPlugin(BasePlugin):
    pass

class WebPlugin(AdvancedPlugin):
    pass

class MyPlugin(WebPlugin):
    pass  # 4 levels deep!
```

**Why it's wrong:**
- Hard to understand which methods to override
- Fragile base class problem
- Forces plugins to know about abstract concepts they don't use

**Do this instead:** Flat inheritance with composition:
```python
# GOOD - shallow hierarchy, clear contracts
class MySkillTool(Tool[MyInput, MyOutput]):
    """Single inheritance from Tool ABC."""
    name = "my-skill"
    InputModel = MyInput
    OutputModel = MyOutput

    async def run(self, params, context, on_progress):
        # Composition for shared logic
        fetcher = TrafilaturaFetcher(context.http)
        result = fetcher.fetch(params.url)
        return ToolResult(success=True, data=[result])
```

**Confidence:** HIGH - Kurt's Tool base class is already flat (tools/core/base.py)

### Anti-Pattern 4: Entry Points Without Fallback

**What people do:** Only support entry point discovery:
```python
# BAD - fails for local development
def discover_plugins():
    from importlib.metadata import entry_points
    return entry_points(group="myapp.plugins")
```

**Why it's wrong:**
- Requires packaging for every change (slow iteration)
- Can't prototype without setup.py/pyproject.toml
- Doesn't support project-local plugins

**Do this instead:** Filesystem first, entry points optional:
```python
# GOOD - supports multiple discovery methods
def discover_all():
    skills = []

    # 1. Filesystem scanning (fast iteration)
    skills.extend(discover_from_paths([
        Path("./skills"),
        Path.home() / ".kurt/skills",
    ]))

    # 2. Entry points (optional, for distribution)
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="kurt.skills")
        skills.extend(discover_from_entry_points(eps))
    except ImportError:
        pass  # Not required

    return skills
```

**Confidence:** HIGH - Matches Python packaging best practices

## Build Order and Dependencies

### Phase Structure Recommendations

Based on component dependencies:

**Phase 1: Core Registry Enhancement** (Foundation)
- Enhance `tools/core/registry.py` to support lazy loading from skills
- Add `@register_fetcher` and `@register_mapper` decorators
- **Depends on:** Nothing (pure refactoring)
- **Enables:** Phases 2-4

**Phase 2: Manifest and Discovery** (Discovery)
- Create `skills/models.py` (SkillManifest Pydantic model)
- Create `skills/discovery.py` (scan paths, parse SKILL.md)
- Create `skills/validator.py` (validate manifests)
- **Depends on:** Phase 1 (needs registry interface)
- **Enables:** Phase 3

**Phase 3: Loading and Manager** (Integration)
- Create `skills/loader.py` (importlib-based dynamic loading)
- Create `skills/manager.py` (SkillManager singleton)
- Create `skills/errors.py` (error types)
- **Depends on:** Phases 1-2
- **Enables:** Phase 4

**Phase 4: CLI and Testing** (User Interface)
- Create `skills/cli.py` (kurt skill list/info/validate)
- Add skill_paths to `config/base.py`
- Comprehensive test coverage
- **Depends on:** Phases 1-3
- **Completes:** Core functionality

**Phase 5: Documentation and Examples** (Optional)
- Example skills in `examples/skills/`
- Documentation in `docs/skills.md`
- Migration guide for existing custom tools
- **Depends on:** Phase 4
- **Completes:** Production-ready

### Critical Dependencies

```
Registry Refactor (Phase 1)
    ↓
Manifest System (Phase 2)
    ↓
Dynamic Loading (Phase 3)
    ↓
CLI Interface (Phase 4)
```

**Do NOT start Phase 2 before Phase 1** - Discovery needs to know what registry pattern to target.

**Do NOT start Phase 4 before Phase 3** - CLI needs working SkillManager to test against.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **1-10 skills** | Current design is sufficient. Single SKILLS dict, linear scan acceptable. |
| **10-100 skills** | Add caching layer (cache manifest parsing), index by type/tag for faster filtering. |
| **100+ skills** | Consider: (1) Lazy manifest parsing (only parse when accessed), (2) SQLite index for metadata queries, (3) Namespace isolation (skills in separate directories don't see each other). |

### Scaling Priorities

1. **First bottleneck:** Manifest parsing on every CLI invocation
   - **Fix:** Cache parsed manifests in `~/.kurt/cache/skills.json` with mtime validation

2. **Second bottleneck:** Tool lookup across many skills
   - **Fix:** Build index `{tool_name: skill_name}` during discovery, O(1) lookup instead of linear scan

3. **Third bottleneck:** Dependency resolution with circular deps
   - **Fix:** Topological sort during load, defer plugins with unmet deps (pluggy pattern)

**For Kurt's use case:** 1-10 skills expected, first bottleneck optimization is sufficient.

## Comparison with Kurt's Existing Patterns

| Pattern | Workflows (agents/) | Tools (tools/) | Skills (proposed) |
|---------|---------------------|----------------|-------------------|
| **Discovery** | Filesystem scan | Hardcoded imports | Filesystem scan |
| **Metadata** | Markdown frontmatter | Class attributes | SKILL.md frontmatter |
| **Registration** | File-based | @register_tool | Import + decorator |
| **Loading** | Parse on list | Lazy load | Lazy load |
| **Validation** | validate_workflow() | Pydantic models | validate_skill() |
| **CLI** | workflow list/run | N/A (internal) | skill list/info |

**Consistency recommendation:** Skills should match workflows pattern (filesystem scan + manifest) but register via tools pattern (decorator).

## Sources

### HIGH Confidence (Official Docs)

- [Python Packaging: Creating and Discovering Plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) - Official Python packaging authority on entry points, namespace packages, naming conventions
- [Setuptools Entry Points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) - Official setuptools documentation on entry_points metadata
- [Pluggy Documentation](https://pluggy.readthedocs.io/en/latest/) - Official pluggy framework docs (hook system architecture)

### MEDIUM Confidence (Framework Docs)

- [click-plugins GitHub](https://github.com/click-contrib/click-plugins) - Official click-contrib plugin integration pattern (no longer maintained but reference implementation)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) - Context manager pattern for plugin lifecycle

### MEDIUM Confidence (Technical Articles)

- [How to Design and Implement a Plugin Architecture in Python](https://mathieularose.com/plugin-architecture-in-python) - Component architecture patterns
- [Building a plugin architecture with Python | Medium](https://mwax911.medium.com/building-a-plugin-architecture-with-python-7b4ab39ad4fc) - Dependency resolution and load order
- [Developing Plugin Architecture with Pluggy | Medium](https://medium.com/@garzia.luke/developing-plugin-architecture-with-pluggy-8eb7bdba3303) - Hook specification patterns
- [How to Build Plugin Systems in Python](https://oneuptime.com/blog/post/2026-01-30-python-plugin-systems/view) - Recent (2026) overview of plugin patterns
- [Implementing a Plugin Architecture in a Python Application](https://alysivji.com/simple-plugin-system.html) - Practical implementation guide

### Kurt Codebase (Verified Patterns)

- `src/kurt/tools/core/registry.py` - Existing Tool registry with lazy loading
- `src/kurt/tools/core/base.py` - Tool ABC with ToolContext pattern
- `src/kurt/workflows/agents/registry.py` - Filesystem-based workflow discovery
- `src/kurt/workflows/agents/parser.py` - Markdown frontmatter parsing
- `src/kurt/tools/fetch/engines/__init__.py` - EngineRegistry pattern (lines 37-97)
- `src/kurt/tools/map/engines/__init__.py` - EngineRegistry pattern (lines 56-116)

---
*Architecture research for: Python plugin/skill extensibility in async CLI*
*Researched: 2026-02-09*
