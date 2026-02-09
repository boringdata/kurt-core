# Feature Landscape

**Domain:** Python CLI Plugin/Skill System
**Researched:** 2026-02-09

## Table Stakes

Features users expect in a plugin system. Missing these = system feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **File-based plugin loading** | Users expect to drop folders and have them work. Standard pattern in VSCode, Sublime Text, etc. | Low | `~/.kurt/skills/my-skill/` with SKILL.toml + skill.py |
| **Installed package plugins** | Power users want `pip install kurt-skill-web` to auto-discover. Standard Python packaging. | Low | Use importlib.metadata entry points (`kurt.skills`) |
| **Plugin manifest validation** | Must fail fast with clear errors. "Missing required field 'name'" not cryptic tracebacks. | Low | Pydantic handles this well (already in stack) |
| **Async hook support** | Kurt's existing code is async. Plugins must integrate cleanly without sync/async bridging hacks. | Medium | apluggy provides this natively |
| **Plugin listing** | `kurt skills list` to see what's loaded. Basic discoverability. | Low | Query plugin manager, format table |
| **Plugin enable/disable** | Users need to turn plugins off without deleting them. Debugging, conflicts, experimentation. | Low | Config flag per plugin, skip during discovery |
| **Clear error messages** | "Plugin 'web-scraper' failed to load: missing dependency 'beautifulsoup4'" not "AttributeError". | Medium | Wrap discovery/loading in try/except, log details |

## Differentiators

Features that set Kurt's plugin system apart. Not expected, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Per-project skills** | Project-specific plugins in `.kurt/skills/` override global. Enables project-specific extractors. | Low | Check project dir before ~/.kurt/ during discovery |
| **Plugin priorities** | Let users control execution order. "Run my-auth before my-scraper". | Low | apluggy supports hook priorities natively via wrappers |
| **Hot reload in dev mode** | `--watch` flag reloads plugins on file change. Massive DX improvement during development. | Medium | Use watchdog library, re-run discovery on change |
| **Plugin sandboxing** | Limit plugin filesystem access, network calls. Security for untrusted plugins. | High | Out of scope for MVP. Would need separate process boundaries. |
| **Plugin marketplace** | `kurt skills search web` finds community plugins. Central registry. | High | MVP: Document pattern. Phase 2: Build registry. |
| **Skill composition** | Skills can call other skills. "pdf-extractor" uses "text-cleaner" skill. | Medium | Plugin manager needs skill dependency resolution |

## Anti-Features

Features to explicitly NOT build (at least initially).

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Custom manifest format** | Don't invent KURT-TOML dialect. Users know TOML already. | Use standard TOML. Document conventions in examples. |
| **Plugin GUI/TUI** | Adding Textual UI for plugin management is scope creep. CLI is sufficient. | Stick to `kurt skills list/enable/disable`. Document workflow. |
| **Plugin versioning system** | Solving dependency conflicts between plugins is pip's job, not ours. | Rely on Python packaging. Document version conflicts if they arise. |
| **Built-in plugin repo** | Hosting/maintaining plugin registry is operational burden. | MVP: Link to GitHub topic/tag. Later: Maybe static site generator. |
| **Plugin code signing** | Crypto + PKI infrastructure is massive undertaking. Not needed for MVP. | Document security practices. Warn about untrusted plugins. |
| **Multi-language plugins** | Supporting Node.js/Rust/etc. plugins via subprocess is complexity nightmare. | Python-only for MVP. Document workaround (Python wrapper around CLI tools). |

## Feature Dependencies

```
Plugin Discovery (file + entry points)
  → Plugin Manifest Validation (Pydantic)
    → Plugin Loading (importlib.util + entry_points)
      → Plugin Registration (apluggy)
        → Hook Execution (async hooks)

Plugin Listing
  → Plugin Discovery

Plugin Enable/Disable
  → Plugin Discovery
  → Config Management (kurt.toml)

Per-Project Skills
  → Plugin Discovery (search project dir first)

Hot Reload
  → Plugin Discovery
  → Plugin Unloading (tricky - need cleanup hooks)

Skill Composition
  → Plugin Registration
  → Plugin Context (pass plugin manager to skills)
```

## MVP Recommendation

**Phase 1 (Core):**
1. File-based plugin discovery (`~/.kurt/skills/`)
2. SKILL.toml manifest with Pydantic validation
3. Async hook registration via apluggy
4. Basic error handling (catch and log failures)

**Phase 2 (Usability):**
5. Entry point discovery (pip-installed plugins)
6. `kurt skills list` command
7. Plugin enable/disable via config

**Phase 3 (Polish):**
8. Per-project skills (`.kurt/skills/` override)
9. Better error messages (missing deps, syntax errors)
10. Hook priorities

**Defer to Future:**
- Hot reload (requires plugin cleanup hooks - complex)
- Skill composition (needs dependency resolution)
- Plugin sandboxing (requires process isolation)
- Marketplace (operational burden)

## Example Skill Structure

Based on research, recommended pattern:

```
~/.kurt/skills/
└── my-web-scraper/
    ├── SKILL.toml          # Manifest (required)
    ├── skill.py            # Hook implementations (required)
    ├── requirements.txt    # Optional dependencies
    └── README.md           # Optional documentation

# SKILL.toml
name = "my-web-scraper"
version = "0.1.0"
description = "Custom web scraper for my use case"
author = "Your Name"
license = "MIT"

[hooks]
# Declare which hooks this skill implements
extract_content = true
validate_url = true

[config]
# Skill-specific config (optional)
max_retries = 3
timeout = 30

# skill.py
import apluggy

hookimpl = apluggy.HookimplMarker('kurt')

@hookimpl
async def extract_content(url: str, config: dict) -> dict:
    """Extract content from URL."""
    # Your implementation
    return {
        "title": "...",
        "content": "...",
        "metadata": {...}
    }

@hookimpl
def validate_url(url: str) -> bool:
    """Check if this skill can handle the URL."""
    return url.startswith('https://example.com')
```

## Real-World Patterns from Research

**From Python Packaging Guide:**
- Use entry points for installed plugins
- Use file scanning for development plugins
- Validate early, fail fast

**From pytest plugin system (uses pluggy):**
- Hook specifications define contracts
- Multiple implementations can coexist
- Priority/ordering for execution control

**From Click documentation:**
- Commands as plugins via `@group.command()`
- Context for shared state
- Lazy loading for performance

**From 2026 plugin system guide:**
- Abstract base classes for type safety
- Error isolation (try/except per plugin)
- Plugin lifecycle states (discovered/loading/active/error/disabled)

## Sources

- [How to Build Plugin Systems in Python](https://oneuptime.com/blog/post/2026-01-30-python-plugin-systems/view)
- [Creating and discovering plugins — Python Packaging Guide](https://packaging.python.org/guides/creating-and-discovering-plugins/)
- [pluggy documentation](https://pluggy.readthedocs.io/)
- [Click documentation](https://click.palletsprojects.com/)
- Kurt's existing workflow patterns (CLAUDE.md)

---
*Feature research for: Kurt Plugin/Skill System*
*Researched: 2026-02-09*
