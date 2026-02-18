# Phase 1: Skill SDK - Context

**Gathered:** 2026-02-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Define core SDK interfaces, decorators, and return types for the skill system. Developers can create skills with a consistent interface that Kurt understands. Discovery, validation, CLI, and migration are separate phases.

</domain>

<decisions>
## Implementation Decisions

### SKILL.md Format
- Follow OpenClaw-style YAML frontmatter + optional Markdown body
- Required fields: `name`, `type` (fetch/map), `description`
- Version field: required, semver format (e.g., `version: 1.0.0`)
- Markdown body: optional, for extended documentation

### @skill Decorator
- Convention-based linking: skill.py in same folder as SKILL.md (no explicit name argument)
- No required arguments on decorator — type comes from SKILL.md
- Multiple functions per folder: Claude's discretion based on codebase patterns

### Skill Contract
- Interface-only (duck typing) — no inheritance required
- Type (fetch/map) determined by SKILL.md, not decorator
- Skills just need to return correct result type

### Result Types
- Use existing `FetchResult` and `MapperResult` (no new types)
- Error handling: both return values (success=False) and exceptions allowed — SDK normalizes
- Built-in timing metrics: SDK adds duration_ms, retry_count automatically
- `content_html` remains optional in FetchResult

### Function Signature
- Explicit typed arguments: `fetch(url: str, config: FetcherConfig) -> FetchResult`
- Config passed as second argument (not via context object or closure)
- SDK inspects type hints to instantiate correct config class
- Matches Python conventions: explicit is better than implicit

### OpenClaw Alignment
- Kurt skill manifest format aligns with OpenClaw SKILL.md where applicable
- Same precedence pattern: project > user > builtin
- Enables future OpenClaw bridge integration (Phase 6+)

### Claude's Discretion
- Whether to allow multiple @skill functions per folder
- Exact helper utilities to extract from base classes
- Config merging strategy (SKILL.md defaults + runtime overrides)

</decisions>

<specifics>
## Specific Ideas

- "Drop a folder with SKILL.md + skill.py → it works immediately" is the north star
- Function-based skills preferred over class-based for simplicity
- Existing FetcherConfig/MapperConfig patterns should inform SkillConfig design
- SDK should handle async/sync collision gracefully (research flagged as critical pitfall)

</specifics>

<deferred>
## Deferred Ideas

- Migration approach for existing engines (trafilatura, etc.) — Phase 6
- Hot reload / file watching — research says defer to post-MVP
- Skill composition (skills calling other skills) — v2 feature
- OpenClaw bridge integration — future milestone

</deferred>

---

*Phase: 01-skill-sdk*
*Context gathered: 2026-02-09*
