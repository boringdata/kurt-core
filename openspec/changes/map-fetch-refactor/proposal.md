# Proposal: Map/Fetch Refactor with Subcommands and Schema-Driven Models

**Change ID:** `map-fetch-refactor`
**Status:** Draft
**Breaking Changes:** Yes (CLI structure)

## Summary

Refactor `map` and `fetch` tools to support multiple content types (doc, profile, posts) via subcommands, with schema-driven Pydantic models for metadata extraction. Add Apify as a new engine for social media platforms.

## Motivation

**Current limitations:**
1. `map` and `fetch` only support web pages (doc) - no profiles or social posts
2. No integration with social platforms (Twitter, LinkedIn, Substack)
3. Metadata extraction is ad-hoc, not schema-driven
4. CLI options become unwieldy when adding new content types

**Target state:**
- `kurt map doc`, `kurt map profile`, `kurt map posts` - clear intent via subcommands
- `kurt fetch doc`, `kurt fetch profile`, `kurt fetch posts` - matching subcommands
- Apify integration for Twitter, LinkedIn profile/post scraping
- Pydantic models define metadata schema per content type
- Engines are shared, content-type modules are isolated

## Scope

### In Scope

1. **CLI Refactor** - Subcommand structure:
   - `kurt map doc` - existing behavior (sitemap, crawl, folder, cms)
   - `kurt map profile` - discover creator/company profiles
   - `kurt map posts` - enumerate posts from profiles
   - `kurt fetch doc` - existing behavior (trafilatura, firecrawl, tavily)
   - `kurt fetch profile` - fetch full profile details
   - `kurt fetch posts` - fetch full post content

2. **Module Structure** - Separation of concerns:
   - `map/core/` - shared logic, base classes, storage
   - `map/engines/` - sitemap, crawl, apify, rss
   - `map/doc/`, `map/profile/`, `map/posts/` - CLI + Pydantic model per type
   - Same pattern for `fetch/`

3. **Pydantic Models** - Schema-driven metadata:
   - `DocMetadata`, `ProfileMetadata`, `PostMetadata` for map
   - `DocContent`, `ProfileContent`, `PostContent` for fetch

4. **Apify Integration** - New engine:
   - Profile search (Twitter, LinkedIn)
   - Profile scraping (full details)
   - Post enumeration and fetching

5. **Database Changes**:
   - Add `doc_type` column to `map_documents`
   - Add `doc_type` column to `fetch_documents`
   - Add `platform` column to both tables

### Out of Scope (v1)

- Custom user-defined schemas (future enhancement)
- YouTube, TikTok support (add later)
- Real-time streaming of social posts
- Webhook notifications

## Migration Impact

| Component | Before | After |
|-----------|--------|-------|
| CLI | `kurt content map` | `kurt map doc`, `kurt map profile`, `kurt map posts` |
| CLI | `kurt content fetch` | `kurt fetch doc`, `kurt fetch profile`, `kurt fetch posts` |
| Models | Single MapDocument | MapDocument with doc_type field |
| Engines | Web-only | Web + Apify + RSS |
| Metadata | Ad-hoc JSON | Pydantic schema per type |

**Breaking changes:**
- CLI command structure changes (aliases can preserve backward compat)
- Database schema adds columns (non-breaking, nullable)

## Dependencies

- **Apify** - Social media scraping API (existing integration in PR #89)
- **Pydantic** - Schema definitions (already present)
- **httpx** - HTTP client for RSS/Substack (already present)

## Risks

| Risk | Mitigation |
|------|------------|
| Apify API costs | Document pricing, add --dry-run for discovery |
| Platform rate limits | Built-in delays, respect rate limits |
| Schema evolution | Version field in metadata, migration scripts |
| CLI breaking change | Provide aliases for backward compatibility |

## Success Criteria

1. `kurt map profile "AI" --platform twitter` discovers profiles
2. `kurt fetch profile --pending` fetches full profile details
3. `kurt map posts --from-profiles` enumerates posts
4. `kurt fetch posts --pending` fetches post content
5. All data stored with proper `doc_type` and Pydantic-validated metadata
6. Existing `kurt map doc` and `kurt fetch doc` work unchanged
7. Tests pass for all new functionality

## Codex Review Summary (3 Iterations)

### Iteration 1: Architecture
- Over-engineering concerns with deep directory structure
- Consider simpler `--type` option vs subcommands (rejected - subcommands clearer)
- Tool class implementation pattern needs clarification

### Iteration 2: Implementation Feasibility
| Severity | Issue | Resolution |
|----------|-------|------------|
| CRITICAL | Tool input model hierarchy unclear | Use single Tool with doc_type discriminator |
| CRITICAL | ApifyAdapter returns Signal, not ProfileMetadata | Create adapter wrapper with field conversion |
| HIGH | Database uniqueness constraint missing | Add composite unique on (source_url, doc_type) |
| HIGH | Backward compatibility not addressed | Add deprecation phase + migration docs |
| HIGH | Data migration strategy missing | Create backfill script for existing rows |
| MEDIUM | Timeline underestimated | Adjust to 15-17 days (was 11 days) |

### Iteration 3: Security, Errors, Extensibility
| Category | Score | Notes |
|----------|-------|-------|
| Security | ⚠️ | API key handling inconsistent, no cost tracking |
| Error Handling | ⚠️ | No retry logic, partial failure handling missing |
| Rate Limiting | ❌ | Missing completely - must add before implementation |
| Extensibility | 7/10 | Good foundation, needs plugin documentation |
| Developer Experience | 6/10 | Missing examples and wizard |

### Pre-Implementation Requirements

Before coding begins, create addendum addressing:

1. **API Key Management** - Unified pattern across engines
2. **Error Handling & Retry** - EngineError classes, exponential backoff
3. **Rate Limiting & Costs** - RateLimiter class, cost estimation, quota tracking
4. **Extension Guide** - Step-by-step: how to add YouTube/TikTok later

**Estimated addendum work: 2-3 days**

### Revised Timeline

| Phase | Description | Original | Revised |
|-------|-------------|----------|---------|
| 0 | Pre-implementation addendum | - | 2-3 days |
| 1 | Database changes | 1 day | 1 day |
| 2-3 | Directory structure, move existing | 1 day | 1 day |
| 4 | Core modules + error handling | 2 days | 3 days |
| 5 | Engines (apify, rss) | 2 days | 3-4 days |
| 6 | Type modules (profile, posts) | 2 days | 2 days |
| 7 | CLI integration | 1 day | 1 day |
| 8 | Tests + documentation | 2 days | 3 days |
| **Total** | | **11 days** | **16-18 days** |

## Related Specs

- `kurt-simplification` - Tool-based architecture (this builds on it)
- `apify-integration` - Apify adapter (PR #89, merged)
