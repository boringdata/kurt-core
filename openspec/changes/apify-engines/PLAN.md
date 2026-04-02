# Plan: Implement Apify Engines for Map/Fetch Tools + Substack Support

## Summary

Complete the stub implementations for Apify engines in Map/Fetch tools and add Substack support. This enables content discovery and extraction from social platforms (Twitter, LinkedIn, Threads, Substack) through the unified Map/Fetch pipeline.

## Current State

### Stubs to Implement

| File | Status | Priority |
|------|--------|----------|
| `src/kurt/tools/map/engines/apify.py` | Stub (TODO) | **High** |
| `src/kurt/tools/fetch/engines/apify.py` | Stub (TODO) | **High** |

### Working Reference Implementation

`src/kurt/integrations/research/monitoring/apify.py` has a fully working ApifyAdapter with:
- `ACTOR_REGISTRY` - Dict-based actor configuration
- `ActorConfig` - Dataclass with actor_id, source_name, build_input, field_mapping
- `FieldMapping` - Flexible field extraction (string, list, callable)
- Input builders per platform (_build_twitter_search_input, etc.)
- httpx-based API client with error handling

---

## Architecture Decision

**Create new top-level integration `integrations/apify/`** following the same pattern as `integrations/cms/`, `integrations/domains_analytics/`, etc. Both Map and Fetch engines will use this shared client. The existing `research/monitoring/apify.py` will be refactored to use the new shared client.

```
src/kurt/integrations/apify/          # NEW - top-level integration (like cms/, domains_analytics/)
├── __init__.py                       # Exports ApifyClient, ActorConfig, etc.
├── client.py                         # ApifyClient - raw API calls via httpx
├── registry.py                       # ACTOR_REGISTRY + Substack actors + input builders
├── parsers.py                        # FieldMapping, result parsing utilities
└── tests/
    ├── __init__.py
    └── test_client.py

src/kurt/tools/map/engines/apify.py   # UPDATE - use integrations/apify
src/kurt/tools/fetch/engines/apify.py # UPDATE - use integrations/apify
src/kurt/integrations/research/monitoring/apify.py  # REFACTOR - use integrations/apify
```

---

## Implementation Plan

### Phase 0: Cleanup & Verification

**0.1 Consolidate duplicate files**
- `map/engines/apify.py` + `map/engines/apify_engine.py` → single `apify.py`
- `fetch/engines/apify.py` + `fetch/engines/apify_engine.py` → single `apify.py`
- Preserve useful code from `apify_engine.py` (platform detection, doctype handling)

**0.2 Verify Substack actors on Apify Store** ⚠️ **BLOCKER - Must complete before Phase 1**
Before implementation, manually test each actor to verify:
- Input schema matches planned builders
- Output schema works with FieldMapping
- Pricing tier and rate limits
- Actor maintenance status (last update date)

Actors to verify:
- `epctex/substack-scraper` (primary - newsletter posts)
- `curious_coder/substack-scraper` (alternative)

**0.3 Update legacy CLI imports**
After deleting `apify_engine.py`, update imports in:
- `src/kurt/tools/cli.py` - imports `ApifyEngine` from `apify_engine`
- Any tests referencing the old module paths

---

### Phase 1: Shared Apify Integration Layer

**1.1 Create `src/kurt/integrations/apify/__init__.py`**
```python
from .client import ApifyClient
from .registry import ACTOR_REGISTRY, PLATFORM_DEFAULTS, ActorConfig
from .parsers import FieldMapping
```

**1.2 Create `src/kurt/integrations/apify/client.py`**
- `ApifyClient` class with:
  - `run_actor(actor_id, actor_input, timeout)` → `list[dict]`
    - Uses Apify's `run-sync-get-dataset-items` endpoint (returns items directly, no pagination needed)
    - `maxItems` in actor_input controls result size
  - `test_connection()` → `bool`
  - `get_user_info()` → `dict | None`
- API key resolution: **Use existing `kurt.tools.api_keys` system**
  ```python
  from kurt.tools.api_keys import get_api_key, configure_engines
  configure_engines()  # Registers apify with INTEGRATIONS.APIFY.API_KEY
  api_key = get_api_key("apify")  # Handles env var + config lookup
  ```
- httpx-based with proper error handling - **Map to existing `kurt.tools.errors` types:**
  - `httpx.TimeoutException` → `TimeoutError` (from `kurt.tools.errors`)
  - `httpx.HTTPStatusError(401/403)` → `AuthError` (from `kurt.tools.errors`)
  - `httpx.HTTPStatusError(429)` → `EngineError` with `error_type=ErrorType.RATE_LIMIT`
  - `httpx.HTTPStatusError(other)` → `EngineError`
  - `httpx.RequestError` → `EngineError` with `error_type=ErrorType.NETWORK_ERROR`

**Retry Policy (429 Rate Limiting):**
- **Client-level retries only** (avoid double-retry with tool layer)
- Max retries: 3
- Backoff: exponential with jitter (1s, 2s, 4s base)
- Respect `Retry-After` header if present (use as minimum wait)
- After max retries exhausted: raise `EngineError` with `error_type=ErrorType.RATE_LIMIT`
- CLI displays: "Rate limited by Apify, retrying in Xs..." on each retry (via logging)

**Result Behavior Contract:**

| Scenario | Map Engine | Fetch Engine |
|----------|------------|--------------|
| Empty results (0 items) | Return `MapperResult(urls=[], count=0)` | Return `FetchResult(content="", metadata={"empty": True})` |
| Partial results (some items failed parsing) | Return successfully parsed items, log warnings | Return first valid item, log warnings |
| Schema mismatch (unexpected fields) | Use `FieldMapping` fallbacks, skip unparseable items | Use `FieldMapping` fallbacks, return raw if all fail |
| Actor not found (404) | Raise `EngineError` with actor ID | Raise `EngineError` with actor ID |
| Invalid input rejected by actor | Raise `EngineError` with actor's error message | Raise `EngineError` with actor's error message |

**1.3 Create `src/kurt/integrations/apify/registry.py`**
- Copy `ACTOR_REGISTRY` pattern from research/monitoring/apify.py
- Add Substack actors:
  - `saswave/substack-leaderboard-scraper` - Find publishers by category
  - `red.cars/substack-newsletter-scraper` - Newsletter profile/metadata
  - `easyapi/substack-posts-scraper` - Posts by keyword
  - `easyapi/substack-notes-scraper` - Notes (social feed)
- Input builders for each Substack actor
- Update `PLATFORM_DEFAULTS` to include substack

**1.4 Create `src/kurt/integrations/apify/parsers.py`**
- Re-export `FieldMapping` from research/monitoring
- Add Substack-specific field mappings

---

### Phase 2: Map Apify Engine

**2.1 Update `src/kurt/tools/map/engines/apify.py`**

```python
class ApifyMapperConfig(MapperConfig):
    api_key: Optional[str] = None
    platform: Optional[str] = None  # twitter, linkedin, threads, substack
    apify_actor: Optional[str] = None  # Override default actor (e.g., "apidojo/tweet-scraper")

class ApifyEngine(BaseMapper):  # Keep name as ApifyEngine (matches existing pattern)
    """Mapper using Apify actors for social platform content discovery."""

    def map(self, source: str, doc_type: DocType) -> MapperResult:
        # 1. Detect platform from source or config
        # 2. Get appropriate actor from registry
        # 3. Build actor input using platform's builder
        # 4. Run actor via ApifyClient
        # 5. Parse results using FieldMapping
        # 6. Return MapperResult with discovered URLs
```

Key methods:
- `_map_profiles(query, platform)` - Discover profiles
- `_map_posts(source, platform)` - Discover posts from profile/search
- `_detect_platform(source)` - Simple URL pattern matching (twitter.com, x.com, linkedin.com, substack.com)
- `_get_actor_for_doctype(platform, doc_type)` - Actor resolution based on DocType

**DocType → Actor Mapping (configurable via registry):**

Note: Use existing `DocType` enum values: `DOC`, `PROFILE`, `POSTS` (not `POST`)

| Platform | DocType.PROFILE | DocType.POSTS |
|----------|-----------------|---------------|
| twitter | `apidojo/twitter-user-scraper` | `apidojo/tweet-scraper` |
| linkedin | `anchor/linkedin-profile-scraper` | `curious_coder/linkedin-post-search-scraper` |
| substack | `epctex/substack-scraper` | `epctex/substack-scraper` |
| threads | `apidojo/threads-scraper` | `apidojo/threads-scraper` |

Users can override defaults via `--apify-actor` CLI option or config.

**2.2 Register in `src/kurt/tools/map/engines/__init__.py`**
```python
from .apify import ApifyEngine
EngineRegistry.register("apify", ApifyEngine)
```

---

### Phase 3: Fetch Apify Engine

**3.1 Update `src/kurt/tools/fetch/engines/apify.py`**

```python
class ApifyFetcherConfig(FetcherConfig):
    api_key: Optional[str] = None
    platform: Optional[str] = None  # twitter, linkedin, threads, substack
    apify_actor: Optional[str] = None  # Override default actor (e.g., "epctex/substack-scraper")

class ApifyFetcher(BaseFetcher):  # Keep name as ApifyFetcher (matches existing pattern)
    """Fetcher using Apify actors for social platform content extraction."""

    def fetch(self, url: str) -> FetchResult:
        # 1. Detect platform from URL pattern (twitter.com, x.com, linkedin.com, substack.com)
        # 2. Determine if profile or post URL
        # 3. Get appropriate actor (config.apify_actor or registry default)
        # 4. Run actor via ApifyClient
        # 5. Format content as markdown
        # 6. Return FetchResult
```

Key methods:
- `_fetch_profile(url, platform)` - Fetch full profile details
- `_fetch_post(url, platform)` - Fetch post content
- `_format_content(item, platform)` - Convert to markdown
- `_detect_platform(url)` - Simple URL pattern matching (no HTTP fetch needed)

**3.2 Integrate with FetchTool**
Update `src/kurt/tools/fetch/tool.py` `_FETCH_ENGINES` dict to include apify.

---

### Phase 4: CLI Integration

**4.1 Update `src/kurt/tools/map/cli.py`**
```python
@click.option("--engine", type=click.Choice(["auto", "sitemap", "crawl", "apify"]))
@click.option("--platform", type=click.Choice(["twitter", "linkedin", "threads", "substack"]),
              help="Social platform (uses default actor from registry)")
@click.option("--apify-actor", help="Specific Apify actor ID (e.g., 'apidojo/tweet-scraper')")
```

**4.2 Update `src/kurt/tools/fetch/cli.py`**
```python
@click.option("--engine", type=click.Choice(["trafilatura", "httpx", "tavily", "firecrawl", "apify"]))
@click.option("--apify-actor", help="Specific Apify actor ID for content extraction")
```

**CLI Usage Examples:**
```bash
# Easy mode: use platform shortcut (looks up default actor in registry)
kurt tool map --engine apify --platform twitter "AI agents"

# Power user mode: use specific Apify actor by ID
kurt tool map --engine apify --apify-actor apidojo/twitter-user-scraper "@username"

# List available actors (for discovery)
kurt tool map --engine apify --list-actors
```

**`--list-actors` Behavior:**
- Prints table of registered actors: `actor_id | platform | description`
- Exits with code 0 after printing (does not run map)
- Format: plain text table (compatible with grep/awk)

---

### Phase 5: Backward Compatibility Refactor

**5.1 Refactor `src/kurt/integrations/research/monitoring/apify.py`**
- Update `ApifyAdapter` to use shared `ApifyClient` from `integrations/apify/client.py`
- Keep `Signal` model output for backward compatibility with SignalsTool
- Run existing tests to verify no regressions

---

## Files to Create/Modify

### Delete Files (Phase 0 - Consolidation)
- `src/kurt/tools/map/engines/apify_engine.py` - Merge into apify.py
- `src/kurt/tools/fetch/engines/apify_engine.py` - Merge into apify.py

### New Files
- `src/kurt/integrations/apify/__init__.py`
- `src/kurt/integrations/apify/client.py`
- `src/kurt/integrations/apify/registry.py`
- `src/kurt/integrations/apify/parsers.py`
- `src/kurt/integrations/apify/tests/__init__.py`
- `src/kurt/integrations/apify/tests/test_client.py`
- `src/kurt/tools/map/tests/test_apify_engine.py`
- `src/kurt/tools/fetch/tests/test_apify_engine.py`

### Modify Files
- `src/kurt/tools/map/engines/apify.py` - Full implementation (merge from apify_engine.py)
- `src/kurt/tools/fetch/engines/apify.py` - Full implementation (merge from apify_engine.py)
- `src/kurt/tools/map/engines/__init__.py` - Register ApifyEngine
- `src/kurt/tools/fetch/engines/__init__.py` - Register ApifyFetcher
- `src/kurt/tools/cli.py` - **Update imports** from `apify_engine` → `apify` (legacy CLI)
- `src/kurt/tools/map/cli.py` - Add --platform, --apify-actor options
- `src/kurt/tools/fetch/cli.py` - Add --apify-actor option
- `src/kurt/integrations/research/monitoring/apify.py` - Refactor to use integrations/apify (Phase 5)

---

## Substack Actor Details

| Actor | Use Case | Input Builder |
|-------|----------|---------------|
| `saswave/substack-leaderboard-scraper` | Find publishers by category | `{"category": "technology", "limit": 50}` |
| `red.cars/substack-newsletter-scraper` | Newsletter metadata | `{"urls": ["https://newsletter.substack.com"]}` |
| `easyapi/substack-posts-scraper` | Search posts | `{"keywords": "AI", "maxPosts": 50}` |
| `easyapi/substack-notes-scraper` | Notes feed | `{"topic": "AI", "maxNotes": 50}` |

---

## Testing Strategy

### Unit Tests
- Mock `ApifyClient.run_actor` to return fixture data
- Test platform detection with edge cases:
  - `x.com` vs `twitter.com`
  - `newsletter.substack.com` vs `newsletter.customdomain.com`
  - Malformed URLs
- Test field mapping extraction for each platform
- Test markdown formatting
- Test error paths:
  - Invalid API key → AuthError
  - Empty results → appropriate handling
  - Actor timeout → TimeoutError
  - Unexpected schema → graceful degradation

### Integration Tests
- E2E: Map discovers URLs → stored in `map_documents`
- E2E: Fetch retrieves content → stored in `fetch_documents`
- Pipeline: map → fetch works end-to-end
- Dry-run mode works correctly
- Skip integration tests when `APIFY_API_KEY` not set (`@pytest.mark.skipif`)

### Test Fixtures
Create JSON fixtures in `tests/fixtures/`:
- `twitter_profile_search.json`
- `linkedin_post_search.json`
- `substack_leaderboard.json`
- `substack_newsletter.json`
- `substack_posts.json`
- `error_responses.json` (401, 429, 500)

---

## Verification

1. **Unit tests pass:**
   ```bash
   pytest src/kurt/integrations/apify/tests/ -v
   pytest src/kurt/tools/map/tests/test_apify_engine.py -v
   pytest src/kurt/tools/fetch/tests/test_apify_engine.py -v
   ```

2. **CLI works:**
   ```bash
   # Map Twitter profiles (using platform shortcut)
   kurt tool map --engine apify --platform twitter "AI research" --dry-run

   # Map Twitter with specific actor
   kurt tool map --engine apify --apify-actor apidojo/twitter-user-scraper "@elonmusk" --dry-run

   # Map Substack posts
   kurt tool map --engine apify --platform substack "machine learning" --dry-run

   # Fetch Twitter profile
   kurt tool fetch --engine apify https://twitter.com/elonmusk --dry-run

   # Fetch Substack newsletter
   kurt tool fetch --engine apify https://newsletter.substack.com --dry-run

   # List available actors
   kurt tool map --engine apify --list-actors
   ```

---

## Implementation Order

1. **Phase 0** - Cleanup duplicate files + verify Substack actors
2. **Phase 1** - Shared Apify layer (client, registry, parsers)
3. **Phase 2** - Map Apify engine
4. **Phase 3** - Fetch Apify engine
5. **Phase 4** - CLI integration + tests
6. **Phase 5** - Backward compat refactor of research/monitoring/apify.py
