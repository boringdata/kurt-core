# Research Summary: Kurt Skill System

**Domain:** Python CLI plugin/skill extensibility for content extraction
**Researched:** 2026-02-09
**Overall confidence:** HIGH

## Executive Summary

Kurt should adopt a SKILL.md-based plugin system that balances simplicity (drop folders and go) with power (Python packaging via entry points). The ecosystem has converged around three proven patterns: filesystem scanning for development, entry points for distribution, and hook systems for extensibility.

The critical architectural decision is **async-first**: Kurt's existing async workflows require apluggy (async-capable hooks) instead of standard pluggy. This is non-negotiable given the codebase architecture.

Four table-stakes features emerged: declarative YAML/Markdown configuration (SKILL.md standard), URL pattern matching (core routing for content extraction), environment variable requirements (API keys for Notion/Twitter/Airtable), and input/output schema validation (type safety via Pydantic). Without these, the system is unusable.

The biggest pitfall is async/sync collision - synchronous blocking code in plugins will freeze Kurt's event loop. This must be prevented through interface design (enforce async def), not documentation alone.

## Key Findings

**Stack:** apluggy (async hooks) + importlib.metadata (discovery) + tomllib (manifest parsing) + Pydantic (validation). Avoid pluggy (no async), stevedore (too heavy), pluginbase (abandoned).

**Architecture:** Three-layer design: SkillManager (discovery/loading) → Registry (Tool/Fetcher/Mapper) → Plugin implementations. Filesystem scanning matches Kurt's workflow pattern. Progressive loading (metadata → instructions → execution) keeps startup fast.

**Critical pitfall:** Async/sync event loop collision. Sync plugins will block the entire CLI. Must enforce async-first interfaces and provide run_in_executor() helpers for legacy code.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Phase 1: Core Registry Enhancement** (Foundation)
   - Addresses: Lazy loading, decorator-based registration
   - Avoids: Hardcoded plugin imports (pitfall from architecture research)
   - Why first: All discovery/loading depends on registry interface

2. **Phase 2: Manifest and Discovery** (Discovery)
   - Addresses: SKILL.md parsing, URL pattern matching, env var requirements
   - Avoids: Import-time heavy dependencies (startup performance pitfall)
   - Why second: Needs registry interface from Phase 1

3. **Phase 3: Loading and Manager** (Integration)
   - Addresses: Dynamic importlib loading, SkillManager singleton, error handling
   - Avoids: Uncaught plugin exceptions, state leakage (critical pitfalls)
   - Why third: Needs discovery layer from Phase 2

4. **Phase 4: CLI and Testing** (User Interface)
   - Addresses: kurt skill list/info/validate, plugin testing framework
   - Avoids: Plugin testing without core integration (moderate pitfall)
   - Why fourth: Needs working SkillManager from Phase 3

5. **Phase 5: Advanced Features** (Post-MVP)
   - Addresses: Hot reload, skill composition, observability integration
   - Deferred: Skill marketplace, sandboxing (high complexity, low immediate value)

**Phase ordering rationale:**
- Registry before discovery: Discovery needs to know what pattern to target (Tool registration)
- Discovery before loading: Can't load until you know what exists
- Loading before CLI: CLI commands need working SkillManager to test
- Testing integrated throughout: Not a separate phase, but emphasis in Phase 4

**Research flags for phases:**
- Phase 1: Standard patterns, unlikely to need deeper research (Tool ABC already exists)
- Phase 2: May need research on URL routing libraries (urlmatch vs Routes vs custom regex)
- Phase 3: Likely needs research on importlib edge cases (namespace packages, reload semantics)
- Phase 4: Standard pytest patterns, unlikely to need research
- Phase 5: Skill composition needs dependency resolution research (topological sort, circular deps)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | apluggy verified on PyPI (Nov 2025 release), importlib.metadata is stdlib, tomllib is stdlib (Python 3.11+) |
| Features | HIGH | SKILL.md standard adopted by Anthropic, OpenAI, VS Code (verified via official docs) |
| Architecture | HIGH | Patterns verified in Kurt's existing codebase (workflows/agents/registry.py, tools/core/base.py) |
| Pitfalls | HIGH | Async/sync collision verified via Python asyncio docs and real-world reports from web search |

## Feature Priorities (MVP Focused)

### Must Have for Launch (P1)

From FEATURES.md research, these 7 features are MVP blockers:

1. **Declarative Configuration (SKILL.md)** - YAML frontmatter + Markdown body, parse with yaml.safe_load()
2. **URL Pattern Matching** - Regex or route-style patterns, route URLs to skills
3. **Environment Variable Requirements** - Declare NOTION_TOKEN, TWITTER_API_KEY, validate before execution
4. **Input/Output Schema Validation** - Pydantic models for type safety
5. **Plugin Discovery (Filesystem)** - Scan ~/.kurt/skills/ and ./skills/
6. **Error Handling & Validation** - Graceful failures, clear error messages
7. **Basic Documentation** - Extract from SKILL.md description, auto-list with kurt skill list

**Rationale:** These enable the core loop: discover skills → match URLs → validate requirements → execute safely → handle errors. Remove any one and the system is broken.

### Should Have Post-MVP (P2)

Features to add based on user feedback, not speculation:

- **Package Dependency Declaration** - Trigger: Users need beautifulsoup4, playwright
- **Auto-generated CLI Commands** - Trigger: Users want kurt notion-sync instead of kurt fetch --skill notion
- **Progressive Skill Loading** - Trigger: CLI startup > 500ms with 20+ skills
- **Version Compatibility Checking** - Trigger: First breaking change, users report errors
- **Skill Health Checks** - Trigger: Users debug missing env vars repeatedly
- **Observability Integration** - Trigger: Users ask "How much did this cost?" or "Which skill is slow?"
- **Multi-source Plugin Loading** - Trigger: Users want to override bundled skills

### Defer to Future (P3)

Wait for ecosystem maturity before building:

- **Skill Composition/Chaining** - Defer: Complex dependency resolution, wait for patterns to emerge
- **Skill Testing Framework** - Defer: Low adoption until active developer community (3+ external contributors)
- **Hot Reload (Development)** - Defer: Developer convenience, restart is fast enough (< 1s)
- **Schema-Driven Documentation** - Defer: Documentation generation is polish, manual docs sufficient
- **Skill Marketplace/Registry** - Defer: Needs 50+ skills, moderation, security review

## Technology Decisions (from STACK.md)

### Core Dependencies

| Technology | Version | Why |
|------------|---------|-----|
| **apluggy** | 1.1.2+ | Only mature async hook system. Wraps pluggy with async/await support. Essential for Kurt's async architecture. |
| **importlib.metadata** | stdlib | Entry point discovery. Standard library since Python 3.8, zero dependencies. |
| **tomllib** | stdlib | TOML manifest parsing. Standard library since Python 3.11, zero dependencies. |
| **Pydantic** | 2.12.5+ | Already in Kurt's stack. Type-safe validation with excellent error messages. |

### Rejected Alternatives

| Avoid | Why Not | Use Instead |
|-------|---------|-------------|
| **pluggy** | No async support, would require complex event loop wrappers | apluggy (wraps pluggy, adds async) |
| **stevedore** | OpenStack-heavy, no async, more complex than needed | apluggy + importlib.metadata |
| **pkg_resources** | Deprecated by setuptools, slow imports | importlib.metadata |
| **click-plugins** | No longer maintained (2025), entry points only | Custom Click integration |
| **pluginbase** | Abandoned since 2018, no async, no Python 3.10+ | apluggy + filesystem scan |

## Critical Architectural Patterns (from ARCHITECTURE.md)

### Pattern 1: Filesystem Scanning (Local Development)

**Use for:** ~/.kurt/skills/, ./skills/ (project-local)

**Why:** Zero packaging overhead, matches Kurt's workflow pattern, enables rapid iteration.

**Structure:**
```
~/.kurt/skills/my-skill/
├── SKILL.md          # Manifest (YAML frontmatter + Markdown)
├── skill.py          # Python implementation
├── requirements.txt  # Optional dependencies
└── README.md         # Optional docs
```

### Pattern 2: Entry Points (Distribution)

**Use for:** pip-installable skills (kurt-skill-example)

**Why:** Standard Python packaging, works with virtual environments.

**Deferred to:** Post-MVP, only when distribution is needed.

### Pattern 3: Manifest-Based Configuration

**Use for:** All skills (required)

**Why:** Fast listing without importing Python, validates structure before execution, human-readable.

**Format:** SKILL.md with YAML frontmatter (name, description, patterns, requirements) + Markdown body (instructions, examples).

### Pattern 4: Lazy Loading

**Use for:** Startup performance

**Why:** Load metadata at discovery, import Python code only when skill is executed. Keeps kurt --help fast (< 300ms).

**Implementation:** Discovery scans paths → parse SKILL.md → store in registry → defer import skill.py until needed.

## Top Pitfalls to Mitigate (from PITFALLS.md)

### Critical (Must Address in Phase 1)

1. **Async/Sync Event Loop Collision** - Enforce async def interfaces, detect blocking calls in dev mode
2. **Import-Time Heavy Dependencies** - Lazy imports, startup time budget (< 300ms), separate discovery from loading
3. **Uncaught Plugin Exceptions** - Isolate execution in try/except, return Result types, graceful degradation

### Critical (Must Address in Phase 2)

4. **Plugin Security - Arbitrary Code Execution** - Warn on untrusted plugins, audit imports at registration, defer sandboxing to Phase 5
5. **Entry Point Discovery Namespace Pollution** - Conflict detection, naming conventions (author.skill_name)

### Critical (Must Address Throughout)

6. **Plugin API Versioning Chaos** - Version plugin API separately from Kurt version, check compatibility at load, maintain backwards compat
7. **Plugin State Leakage** - Stateless interface design, thread-local storage for context, test concurrent execution

### Moderate (Address Post-MVP)

8. **Plugin Dependency Conflicts** - Document version ranges, fail early with clear errors, consider vendoring later
9. **Plugin Testing Without Core Integration** - Ship test harness, example plugins with tests, pytest fixtures

## Feature Landscape Insights (from My Research)

### What pytest Does Well (Learn From)

- Entry point discovery (pytest11) - Standard, works with packaging tools
- Hook-based architecture - Minimal core, extensible via plugins
- Fixture system - Reusable setup, dependency injection
- Auto-discovery (conftest.py) - Zero config, works out of the box

**Apply to Kurt:** Use entry points for packaged skills, keep core minimal with hooks for edge cases, provide fixtures for testing, scan ~/.kurt/skills/ automatically.

### What OpenClaw Does Well (Skill System Pioneer)

- SKILL.md format - Declarative, version-controllable, human-readable
- Progressive loading - Metadata → instructions → execution
- Skill precedence - workspace > user > bundled (clear override rules)
- XML system prompt injection - Compact skill list in LLM context

**Apply to Kurt:** Adopt SKILL.md standard, load name/description upfront (full content on-demand), use same precedence hierarchy, consider agent integration later.

### What Pydantic Does Well (Schema Validation)

- Type hints = schema - No separate schema language
- JSON Schema generation - Auto-docs, API contracts
- Validation error messages - Clear, actionable errors

**Apply to Kurt:** Use Pydantic models for skill input/output, export schemas for documentation, surface Pydantic errors in CLI output.

## Gaps to Address

### Known Gaps (Require Further Research)

1. **URL Routing Library Selection** - Need to compare urlmatch vs Routes vs custom regex for performance and expressiveness. Research in Phase 2.

2. **Dependency Installation Strategy** - How should skills install their requirements.txt? Auto-install (risky), manual prompt (friction), or validation-only (safe but UX cost)? Research in Phase 2.

3. **Skill Composition Dependency Resolution** - If skills call other skills, need topological sort for load order and circular dependency detection. Research in Phase 5 (post-MVP).

4. **Sandboxing for Untrusted Skills** - Research RestrictedPython vs subprocess isolation vs Docker for security. Phase 5 (post-MVP).

### Verification Needed (Low Confidence Areas)

1. **Hot Reload Reliability** - importlib.reload() has known issues with decorators, metaclasses, global state. Need to test with Kurt's codebase patterns before committing to support.

2. **Cross-Platform Path Handling** - Verify ~/.kurt/skills/ works on Windows, handle path separators correctly in skill loading.

3. **Concurrent Plugin Execution** - Test race conditions with multiple workflows calling same skill simultaneously. Thread-local storage may not be sufficient if using asyncio tasks instead of threads.

## Recommended First Steps

Based on all research:

1. **Start with Phase 1 (Registry Enhancement)** - Foundation layer, low risk, unblocks everything else.

2. **Prototype SKILL.md parser early** - Validate frontmatter format with real examples before full implementation.

3. **Build async/sync test harness** - Create deliberate test case with blocking code to verify enforcement works.

4. **Document plugin API contract** - Define public API surface (kurt.plugin.*) before first skill is written.

5. **Create one example skill** - Build "notion-export" as reference implementation, find rough edges.

## Success Criteria

MVP is successful when:

- Users drop a SKILL.md + skill.py folder into ~/.kurt/skills/ and it "just works"
- kurt skill list shows discovered skills with descriptions
- URL patterns route correctly (notion.so URLs → notion-export skill)
- Missing env vars fail fast with clear error (not cryptic AttributeError)
- Pydantic validation catches type errors before execution
- Startup remains fast (kurt --help < 300ms with 10 skills)
- Plugin exceptions don't crash the CLI (graceful degradation)

---

**Next Actions for Roadmap Creation:**

1. Use Phase 1-5 structure above as backbone
2. Break each phase into concrete tasks (ARCHITECTURE.md has component breakdown)
3. Flag Phase 2 for URL routing research, Phase 5 for composition research
4. Prioritize P1 features across all phases
5. Add async/sync enforcement as acceptance criteria for Phase 1
6. Include startup time budget (< 300ms) in Phase 2 acceptance criteria
