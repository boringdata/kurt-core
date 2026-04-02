# Kurt Extensibility

## What This Is

Kurt is a content extraction and research tool for GTM teams and content creators. This milestone adds an extensible skill system where adding a new content source (Notion, Twitter, Airtable) requires only dropping a `SKILL.md` + `skill.py` folder — no Kurt source code changes needed.

## Core Value

Drop a folder with SKILL.md + skill.py → it works immediately. No code changes to Kurt needed.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. Inferred from existing codebase. -->

- ✓ CLI application with Click framework — existing
- ✓ Tool-based architecture (FetchTool, MapTool, etc.) — existing
- ✓ Multiple fetch engines (trafilatura, firecrawl, tavily, httpx, apify, twitterapi) — existing
- ✓ Multiple map engines (sitemap, rss, crawl, cms, folder, apify) — existing
- ✓ BaseFetcher and BaseMapper abstract classes — existing
- ✓ EngineRegistry class (currently unused) — existing
- ✓ Workflow execution engine — existing
- ✓ Dolt database for observability — existing

### Active

<!-- Current scope. Building toward these. -->

- [ ] Skill SDK with base class and standard interface
- [ ] SKILL.md manifest parser (YAML frontmatter like OpenClaw)
- [ ] Skill discovery from multiple paths (project, user, builtin)
- [ ] URL pattern matching for auto-selection of skills
- [ ] Migrate existing fetch engines to skill format
- [ ] Migrate existing map engines to skill format
- [ ] Replace hardcoded dispatchers with dynamic discovery
- [ ] CLI commands: `kurt skill list/info/check/install`

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- MCP server for Claude Desktop — future milestone
- OpenClaw bridge integration — future milestone
- Hot reload / file watching — nice to have, not v1
- Skill marketplace / remote registry — community infrastructure, later

## Context

Kurt already has the interfaces (BaseFetcher, BaseMapper, EngineRegistry) but they're not being used properly. The tool.py files have hardcoded dispatcher dicts and the CLI has hardcoded Literal types for engine choices.

The OpenClaw SKILL.md pattern is the model: YAML frontmatter manifest + implementation file. Kurt's Python equivalent: SKILL.md + skill.py.

Reference plan: `~/.claude/plans/nifty-cuddling-snail.md`

## Constraints

- **Backward compatibility**: Existing `--engine trafilatura` CLI usage must continue working
- **No breaking changes**: Existing workflows referencing engines by name must work
- **Python 3.10+**: Target runtime from pyproject.toml
- **Async-first**: Skill interface should be async like existing tools

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SKILL.md format matches OpenClaw | Familiarity for developers, ecosystem alignment | — Pending |
| skill.py as implementation file | Python convention, clear naming | — Pending |
| Function-based skills preferred | Simpler than class-based for most cases | — Pending |
| URL pattern auto-selection | User experience: `kurt fetch notion.so/...` just works | — Pending |

---
*Last updated: 2026-02-09 after initialization*
