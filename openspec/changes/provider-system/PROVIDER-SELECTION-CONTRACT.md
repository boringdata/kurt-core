# Provider Selection Contract

**Status:** Final (for bd-26w epic)
**Created:** 2026-02-10
**Author:** BrightRiver (claude-opus-4-5)

## Overview

This document defines the authoritative contract for provider selection in Kurt's tool system. All components (executor, tools, CLI, config) must implement behavior consistent with this contract.

---

## 1. Terminology

| Term | Definition |
|------|------------|
| **tool** | Stable interface/category with defined input/output contract (fetch, map, publish, etc.) |
| **provider** | Implementation of a tool (trafilatura, notion, sitemap, httpx, etc.) |
| **engine** | **DEPRECATED** legacy synonym for provider. Treat as alias during migration. |
| **method** | Map-specific internal concept (sitemap, crawl, rss). Effectively a provider selector. |

---

## 2. User-Facing API Contract

### 2.1 Workflows (`workflows/*.toml`)

```toml
[[steps]]
type = "fetch"
config.provider = "notion"     # CANONICAL - use this
config.url = "https://notion.so/page"
```

- **Canonical**: `config.provider`
- **Deprecated**: `config.engine` (must emit `DeprecationWarning`, still works)

### 2.2 CLI

```bash
# Canonical (preferred)
kurt fetch --provider notion https://example.com

# Deprecated (works with warning)
kurt fetch --engine notion https://example.com
```

- **Canonical**: `--provider NAME`
- **Deprecated**: `--engine NAME` (emit warning, still works)
- **Future**: Consider removing `--engine` in v2.0

### 2.3 Tool Parameters

Tools accept `provider` (canonical) with `engine` as internal compat layer:

```python
class FetchToolConfig(BaseModel):
    provider: str | None = None  # Canonical
    engine: str | None = None    # Deprecated alias (internal only)
```

---

## 3. Provider Resolution Order

When executing a step/tool, select provider using this priority chain:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. EXPLICIT PROVIDER                                           │
│     config.provider from workflow TOML or --provider CLI flag   │
│     → If specified and found: USE IT                            │
│     → If specified but unknown: ProviderNotFoundError           │
├─────────────────────────────────────────────────────────────────┤
│  2. EXPLICIT ENGINE (deprecated)                                │
│     config.engine from workflow TOML or --engine CLI flag       │
│     → Emit DeprecationWarning                                   │
│     → Treat as provider name (alias)                            │
├─────────────────────────────────────────────────────────────────┤
│  3. URL PATTERN MATCHING (specific patterns only)               │
│     ProviderRegistry.match_provider(tool, url)                  │
│     → Check config.url, config.source, config.urls[0]           │
│     → If no URL in config: check upstream input_data URLs       │
│     → Match against provider url_patterns attributes            │
│     → ONLY non-wildcard patterns count as a "match"             │
│     → Wildcard patterns ("*") do NOT override tool default      │
├─────────────────────────────────────────────────────────────────┤
│  4. TOOL DEFAULT                                                │
│     Tool.default_provider attribute                             │
│     → Used when no specific URL pattern matches                 │
│     → Takes precedence over wildcard-only matches               │
├─────────────────────────────────────────────────────────────────┤
│  5. WILDCARD FALLBACK (last resort)                             │
│     Providers with url_patterns=["*"]                           │
│     → Only used when tool has NO default_provider               │
│     → Should be rare in practice                                │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 URL Sources Checked (in order)

1. `config.url` (primary)
2. `config.source` (secondary)
3. `config.urls[0]` (first element if list)
4. **Upstream `input_data` URLs** (from previous step output)

### 3.2 URL Pattern Matching Algorithm

Three-pass matching for specificity:

1. **Pass 1**: Match specific patterns (not `*`) - these are "real" matches
2. **Pass 2**: If no specific match AND tool has `default_provider` → use default
3. **Pass 3**: Match wildcard patterns (`*`) - only if no default exists

Within passes 1 and 3, first match wins (order of discovery).

### 3.3 Wildcard Pattern Semantics (CRITICAL)

**Wildcard patterns (`url_patterns=["*"]`) do NOT count as matches when the tool has a `default_provider`.**

This is critical for usability and safety:
- A generic URL (e.g., `https://example.com/article`) should use the tool's default provider
- Wildcard providers often require credentials (e.g., `firecrawl`, `tavily`)
- Selecting a credentialed provider by default would cause hard failures

**Examples:**

```python
# Tool: fetch, default_provider="trafilatura"

# Specific match: notion URL matches notion provider
match_provider("fetch", "https://notion.so/page")  # → "notion"

# Generic URL: no specific match, use tool default
match_provider("fetch", "https://example.com/article")  # → "trafilatura" (default)
#   NOT "firecrawl" even though firecrawl has url_patterns=["*"]

# Twitter URL: specific match beats wildcard
match_provider("fetch", "https://twitter.com/user")  # → "twitterapi" (specific match)
```

**Rationale:**
- Providers that want to handle "all URLs" should be tool defaults, not wildcard matchers
- Wildcard patterns are for providers without better alternatives, not for hijacking selection
- Users explicitly select credentialed providers; they should never be auto-selected for generic URLs

---

## 4. Validation & Error Behavior

### 4.1 Unknown Provider

If an explicit `provider` or `engine` is specified but not discovered:

```python
raise ProviderNotFoundError(
    tool_name="fetch",
    provider_name="unknown-provider",
    available=["trafilatura", "httpx", "notion", "firecrawl", ...]
)
```

**Error message must include**:
- Tool name
- Requested provider name
- List of available providers for that tool

### 4.2 Missing Requirements

If provider requirements (`requires_env`) are not met:

```python
raise ProviderRequirementsError(
    provider_name="notion",
    missing_env=["NOTION_TOKEN"],
    message="Provider 'notion' requires NOTION_TOKEN environment variable"
)
```

**Validation timing**: BEFORE any network/expensive operations (fail fast).

### 4.3 Fail Fast Principle

- Validate provider existence at resolution time
- Validate requirements before execution starts
- Never silently ignore unknown providers
- Never silently skip missing requirements

---

## 5. Backwards Compatibility

### 5.1 Engine Alias Support

```python
# Executor behavior
if "engine" in config and "provider" not in config:
    warnings.warn(
        "config.engine is deprecated, use config.provider instead",
        DeprecationWarning
    )
    config["provider"] = config["engine"]
```

### 5.2 Map Tool Compatibility

Map tool maps `engine`/`provider` to internal `discovery_method`:

```python
# Map tool behavior
valid_methods = {"sitemap", "crawl", "rss", "folder", "cms", "apify"}
if params.provider and params.provider in valid_methods:
    params.discovery_method = params.provider
```

### 5.3 Timeline

| Version | engine Status |
|---------|---------------|
| Current | Deprecated with warning |
| v1.x | Still works, warning always emitted |
| v2.0 | Consider removal (assess adoption) |

---

## 6. Custom Provider Support

### 6.1 Requirement

Tools **MUST NOT** hardcode provider names in Pydantic `Literal` types.

### 6.2 Current Violation (to fix)

```python
# WRONG - blocks custom providers
engine: Literal["trafilatura", "httpx", "tavily", "firecrawl", "apify", "twitterapi"]
```

### 6.3 Correct Pattern

```python
# CORRECT - allows any provider, validates at runtime
provider: str | None = Field(default=None, description="Provider to use")

# Runtime validation
def validate_provider(self, provider_name: str, tool_name: str) -> None:
    registry = get_provider_registry()
    available = registry.list_providers(tool_name)
    if provider_name not in [p["name"] for p in available]:
        raise ProviderNotFoundError(tool_name, provider_name, available)
```

### 6.4 CLI Choices

Two acceptable approaches:

**Option A**: Dynamic choices (recommended)
```python
@click.option(
    "--provider",
    type=click.Choice(get_dynamic_provider_choices("fetch") + ["auto"]),
    default="auto"
)
```

**Option B**: Free-form with validation
```python
@click.option("--provider", default="auto", help="Provider name or 'auto'")
def fetch(provider: str):
    if provider != "auto":
        validate_provider_exists("fetch", provider)
```

---

## 7. Provider Configuration Contract

### 7.1 Config Locations

| Location | Purpose | Priority |
|----------|---------|----------|
| CLI flags | Single invocation | Highest |
| Project `kurt.toml` | Team settings | High |
| User `~/.kurt/config.toml` | Personal defaults | Medium |
| Provider defaults | Code defaults | Lowest |

### 7.2 TOML Schema

```toml
# Tool-level defaults
[tool.fetch]
timeout = 30
batch_size = 10

# Provider-specific overrides
[tool.fetch.providers.notion]
timeout = 60
include_databases = true

[tool.fetch.providers.firecrawl]
formats = ["markdown"]
```

### 7.3 Resolution via ProviderConfigResolver

```python
# Get merged config for a provider
config = ProviderConfigResolver.resolve(
    tool="fetch",
    provider="notion",
    cli_overrides={"timeout": 120}
)
```

### 7.4 Legacy StepConfig Coexistence

- `StepConfig` (kurt.config KEY=VALUE format) continues to work
- `ProviderConfigResolver` (TOML) is authoritative for new development
- Gradual migration: new provider configs use TOML, old ones stay on StepConfig
- **No breaking changes**: both systems work simultaneously

---

## 8. Observability Requirements

### 8.1 Logging (at resolution time)

```python
logger.debug(
    "Provider selected",
    extra={
        "provider": provider_name,
        "tool": tool_name,
        "selection_reason": "explicit" | "url_match" | "default",
        "matched_url": url_used_for_matching,  # if url_match
        "pattern": matched_pattern,             # if url_match
    }
)
```

### 8.2 Error Logging

```python
logger.error(
    "Provider requirements not met",
    extra={
        "provider": provider_name,
        "tool": tool_name,
        "missing_env": ["NOTION_TOKEN"],
    }
)
```

### 8.3 Workflow Events

For workflow observability, emit events:

```python
DBOS.set_event("provider_selected", {
    "provider": provider_name,
    "tool": tool_name,
    "reason": selection_reason,
})
```

---

## 9. Implementation Checklist

### 9.1 Executor Changes

- [x] Read `config.provider` as canonical source
- [x] Fall back to `config.engine` with deprecation warning
- [x] Resolve via URL pattern matching
- [x] Check upstream `input_data` URLs
- [ ] Validate provider exists before execution
- [ ] Validate requirements before execution
- [ ] Add observability logging

### 9.2 Fetch Tool Changes

- [ ] Remove `Literal` type from `engine` field
- [ ] Add runtime provider validation
- [ ] Accept `provider` parameter (alongside `engine`)
- [ ] Wire ProviderConfigResolver for provider-specific config

### 9.3 Map Tool Changes

- [x] Map `engine`/`provider` to `discovery_method`
- [ ] Accept `provider` parameter explicitly
- [ ] Wire ProviderConfigResolver

### 9.4 CLI Changes

- [ ] Add `--provider` option alongside `--engine`
- [ ] Emit deprecation warning for `--engine`
- [ ] Support dynamic provider choices or free-form validation
- [ ] Update `kurt tool check` for provider validation

---

## 10. Test Requirements

### 10.1 Unit Tests

| Test Case | Expected Behavior |
|-----------|-------------------|
| Explicit provider specified | Uses that provider |
| Explicit engine specified | Uses that provider, emits warning |
| URL matches specific pattern | Auto-selects that provider |
| Generic URL, tool has default | Uses tool default (NOT wildcard provider) |
| Generic URL, tool has NO default | Uses wildcard provider |
| Unknown provider specified | Raises ProviderNotFoundError |
| Missing requirements | Raises ProviderRequirementsError |
| Custom provider in project dir | Discovered and usable |

### 10.1.1 Wildcard vs Default Precedence Tests (CRITICAL)

These tests verify the core wildcard semantics:

```python
# fetch default_provider="trafilatura"
assert resolve("fetch", "https://example.com") == "trafilatura"  # NOT "firecrawl"
assert resolve("fetch", "https://notion.so/page") == "notion"    # specific match

# map default_provider="sitemap" (or similar)
assert resolve("map", "https://example.com") == "sitemap"        # NOT "crawl"
assert resolve("map", "https://example.com/sitemap.xml") == "sitemap"  # specific match
```

### 10.2 Integration Tests

| Scenario | Validation |
|----------|------------|
| map → fetch pipeline | Provider resolved from map output URLs |
| Explicit provider with missing env | Fails fast with clear error |
| Custom provider end-to-end | Project provider works without code changes |

---

## 11. Decision Summary

| Decision Point | Resolution |
|----------------|------------|
| Canonical API name | `provider` |
| Deprecated alias | `engine` (with warning) |
| Map semantics | `provider` maps to `discovery_method` |
| Custom providers | MUST be supported (no Literals) |
| Config authority | ProviderConfigResolver (TOML) |
| Validation timing | At resolution, before execution |
| **Wildcard vs default** | **Tool default takes precedence over wildcard patterns** |
| **Wildcard usage** | **Avoid wildcards for credentialed providers** |

---

## 12. Provider Pattern Guidelines

### 12.1 When to Use Specific Patterns

Providers SHOULD use specific patterns when they:
- Handle a particular domain (e.g., `*.notion.so/*`, `*twitter.com/*`)
- Handle a particular file type (e.g., `*/sitemap.xml`, `*/feed*`)
- Require specific credentials tied to that service

**Examples:**
```python
# Good: specific patterns
url_patterns = ["*.notion.so/*", "*.notion.site/*"]  # notion provider
url_patterns = ["*/sitemap.xml", "*/sitemap_*.xml"]  # sitemap provider
url_patterns = ["*twitter.com/*", "*x.com/*"]        # twitterapi provider
```

### 12.2 When to Use Wildcard Patterns

Providers SHOULD use wildcard patterns (`["*"]`) ONLY when:
- They are the designated fallback for a tool that has NO `default_provider`
- They handle a broad category but are NOT credentialed (rare)

**Generally, wildcard patterns should be AVOIDED.** If a provider wants to handle "any URL", it should be the tool's `default_provider` instead.

### 12.3 Recommended Builtin Provider Patterns

| Tool | Provider | Recommended url_patterns | Notes |
|------|----------|-------------------------|-------|
| fetch | trafilatura | `[]` (empty or none) | Is default_provider |
| fetch | httpx | `[]` | Generic HTTP, use only when requested |
| fetch | notion | `["*.notion.so/*", "*.notion.site/*"]` | Specific domain |
| fetch | firecrawl | `[]` | Credentialed, explicit use only |
| fetch | twitterapi | `["*twitter.com/*", "*x.com/*"]` | Specific domain |
| map | sitemap | `["*/sitemap.xml", "*/sitemap*.xml"]` | Specific file pattern |
| map | rss | `["*/feed*", "*/rss*", "*atom*"]` | Specific file pattern |
| map | crawl | `[]` | Credentialed (often), explicit use only |

### 12.4 Migration: Removing Unsafe Wildcards

Providers with `url_patterns=["*"]` that also require credentials MUST have their wildcards removed:

```python
# BEFORE (unsafe - can hijack generic URLs)
class FirecrawlProvider:
    url_patterns = ["*"]
    requires_env = ["FIRECRAWL_API_KEY"]

# AFTER (safe - explicit use only)
class FirecrawlProvider:
    url_patterns = []  # No auto-selection
    requires_env = ["FIRECRAWL_API_KEY"]
```

---

*Contract finalized: 2026-02-10*
*Updated: 2026-02-10 (wildcard semantics clarification per bd-21im.1.1)*
*Implements: bd-26w.1, bd-21im.1.1*
