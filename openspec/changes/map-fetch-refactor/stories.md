# Map/Fetch Refactor Implementation Stories (Updated)

Epic: kurt-core-1uhd
Total stories: 36

## kurt-core-1uhd.1: Define error handling patterns for engines
Priority: P1 | Type: task

Create EngineError class hierarchy and retry patterns before implementation begins.

## Acceptance Criteria
- EngineError base class with error_type, message, retryable fields
- Subclasses: RateLimitError, TimeoutError, AuthError, ContentError
- Exponential backoff helper with configurable base/max
- Unit tests for error classes

---

## kurt-core-1uhd.10: Create fetch/core/ module with shared logic
Priority: P2 | Type: task

Extract shared fetch logic into core module.

## Files
- fetch/core/__init__.py - exports
- fetch/core/base.py - BaseFetcher ABC
- fetch/core/storage.py - content persistence
- fetch/core/models.py - shared Pydantic models

---

## kurt-core-1uhd.11: Create fetch/engines/ module structure
Priority: P2 | Type: task

Organize fetch engines into dedicated module.

## Files
- fetch/engines/__init__.py - engine registry
- fetch/engines/trafilatura.py - existing
- fetch/engines/firecrawl.py - existing
- fetch/engines/tavily.py - existing
- fetch/engines/apify.py - Apify content fetcher

---

## kurt-core-1uhd.12: Create DocMetadata and DocContent models
Priority: P2 | Type: task

Define Pydantic models for document type.

## Models
- DocMetadata: url, title, description, language, discovered_from, depth
- DocContent: url, content_text, content_html, content_path, word_count, links

---

## kurt-core-1uhd.13: Create ProfileMetadata and ProfileContent models
Priority: P2 | Type: task

Define Pydantic models for profile type.

## Models
- ProfileMetadata: platform, username, display_name, bio, url
- ProfileContent: full profile data, followers, posts_count, verified, avatar

---

## kurt-core-1uhd.14: Create PostMetadata and PostContent models
Priority: P2 | Type: task

Define Pydantic models for posts type.

## Models
- PostMetadata: platform, post_id, profile_id, published_at, url
- PostContent: full text, media_urls, engagement metrics, replies

---

## kurt-core-1uhd.15: Implement kurt map doc subcommand
Priority: P2 | Type: task

Create doc subcommand preserving existing map behavior.

## CLI
kurt map doc <url> [--depth N] [--include PATTERN] [--exclude PATTERN]

## Behavior
- Sitemap detection and parsing
- Recursive crawl with depth limit
- Pattern filtering
- Output: DocMetadata records

---

## kurt-core-1uhd.16: Implement kurt map profile subcommand
Priority: P2 | Type: task

Create profile subcommand for discovering creator profiles.

## CLI
kurt map profile <query> --platform twitter|linkedin [--limit N]

## Behavior
- Search for profiles matching query
- Support multiple platforms via Apify
- Output: ProfileMetadata records with platform_id

---

## kurt-core-1uhd.17: Implement kurt map posts subcommand
Priority: P2 | Type: task

Create posts subcommand for enumerating posts from profiles.

## CLI
kurt map posts --from-profiles [--since DATE] [--limit N]
kurt map posts <profile_url> [--since DATE] [--limit N]

## Behavior
- Enumerate posts from discovered profiles
- Support date filtering
- Output: PostMetadata records linked to profile_id

---

## kurt-core-1uhd.18: Implement kurt fetch doc subcommand
Priority: P2 | Type: task

Create doc subcommand preserving existing fetch behavior.

## CLI
kurt fetch doc [--pending] [--engine trafilatura|firecrawl|tavily]

## Behavior
- Fetch pending doc URLs from map_documents
- Extract content using configured engine
- Save to content/ directory
- Update fetch_documents with status

---

## kurt-core-1uhd.19: Implement kurt fetch profile subcommand
Priority: P2 | Type: task

Create profile subcommand for fetching full profile details.

## CLI
kurt fetch profile [--pending] [--platform twitter|linkedin]

## Behavior
- Fetch pending profiles from map_documents where doc_type='profile'
- Use Apify to get full profile data
- Store in profiles table
- Output: ProfileContent records

---

## kurt-core-1uhd.2: Define rate limiting infrastructure
Priority: P1 | Type: task

Create RateLimiter class for managing API rate limits across engines.

## Acceptance Criteria
- RateLimiter with token bucket algorithm
- Per-engine configuration (requests/sec, burst)
- Thread-safe implementation
- Integration with async context managers
- Cost tracking hooks for paid APIs (Apify, Firecrawl)

---

## kurt-core-1uhd.20: Implement kurt fetch posts subcommand
Priority: P2 | Type: task

Create posts subcommand for fetching full post content.

## CLI
kurt fetch posts [--pending] [--platform twitter|linkedin]

## Behavior
- Fetch pending posts from map_documents where doc_type='posts'
- Use Apify to get full post content
- Store in posts table
- Output: PostContent records

---

## kurt-core-1uhd.21: Create ApifyEngine base class
Priority: P2 | Type: task

Create base class for Apify-powered engines.

## Features
- API key management
- Actor run management
- Result pagination
- Cost tracking
- Rate limiting integration

---

## kurt-core-1uhd.22: Implement Twitter profile/posts adapter
Priority: P2 | Type: task

Create Apify adapter for Twitter scraping.

## Actors
- Profile search: apify/twitter-scraper
- Profile details: apify/twitter-scraper
- Posts enumeration: apify/twitter-scraper

## Field Mapping
- Map Apify response to ProfileMetadata/PostMetadata models

---

## kurt-core-1uhd.23: Implement LinkedIn profile adapter
Priority: P2 | Type: task

Create Apify adapter for LinkedIn scraping.

## Actors
- Profile search: apify/linkedin-scraper
- Profile details: apify/linkedin-scraper

## Field Mapping
- Map Apify response to ProfileMetadata model
- Handle LinkedIn-specific fields (company, title, connections)

---

## kurt-core-1uhd.24: Implement RSS feed engine
Priority: P2 | Type: task

Create RSS/Atom feed discovery and parsing engine.

## Features
- Auto-discover RSS feeds from URLs
- Parse RSS/Atom formats
- Map entries to PostMetadata
- Support Substack, Medium, blog feeds

---

## kurt-core-1uhd.25: Add backward-compatible aliases
Priority: P2 | Type: task

Preserve backward compatibility with deprecation warnings.

## Aliases
- kurt content map -> kurt map doc (with deprecation warning)
- kurt content fetch -> kurt fetch doc (with deprecation warning)

## Timeline
- v1: aliases work with warning
- v2: remove aliases

---

## kurt-core-1uhd.26: Add --dry-run support for discovery commands
Priority: P2 | Type: task

Add dry-run mode for map commands to preview without persisting.

## Behavior
- kurt map profile 'AI' --platform twitter --dry-run
- Shows what would be discovered
- Displays cost estimate for Apify calls
- No database writes

---

## kurt-core-1uhd.27: Create map subcommand unit tests
Priority: P2 | Type: task

Comprehensive unit tests for all map subcommands.

## Coverage
- map doc: sitemap, crawl, patterns
- map profile: search, platform filtering
- map posts: enumeration, date filtering
- Error handling for each subcommand

---

## kurt-core-1uhd.28: Create fetch subcommand unit tests
Priority: P2 | Type: task

Comprehensive unit tests for all fetch subcommands.

## Coverage
- fetch doc: all engines
- fetch profile: Apify mocking
- fetch posts: Apify mocking
- Error handling and retries

---

## kurt-core-1uhd.29: Create E2E tests for full workflow
Priority: P2 | Type: task

End-to-end tests for complete map -> fetch workflows.

## Scenarios
- map doc -> fetch doc (existing behavior)
- map profile -> fetch profile -> map posts -> fetch posts
- Error recovery and partial completion
- Dry-run mode verification

---

## kurt-core-1uhd.3: Create unified API key management
Priority: P1 | Type: task

Standardize API key handling across all engines.

## Acceptance Criteria
- Single pattern: env var > kurt.config > error
- API key validation on engine init
- Helpful error messages with setup instructions
- Support for multiple keys per engine (rotation)

---

## kurt-core-1uhd.30: Create Apify integration tests
Priority: P3 | Type: task

Integration tests with Apify (requires API key).

## Coverage
- Twitter profile search (small query)
- LinkedIn profile fetch (single profile)
- Cost verification
- Rate limit handling

## Note
- Marked as slow tests
- Skipped in CI without APIFY_API_KEY

---

## kurt-core-1uhd.31: Update CLI documentation
Priority: P3 | Type: task

Update all CLI help text and README documentation.

## Deliverables
- Updated kurt map --help with subcommands
- Updated kurt fetch --help with subcommands
- README section on content types
- Migration guide from old commands

---

## kurt-core-1uhd.32: Create extension guide for new platforms
Priority: P3 | Type: task

Document how to add support for new platforms.

## Guide Contents
- How to add a new Apify adapter
- How to create new Pydantic models
- How to add CLI subcommand
- Testing requirements
- Example: Adding YouTube support

---

## kurt-core-1uhd.33: Create Alembic migration and backfill script
Priority: P1 | Type: task

Create database migration for new columns and backfill existing data.

## Acceptance Criteria
- Alembic migration for doc_type and platform columns
- Backfill script sets doc_type='doc' for existing rows
- Rollback procedure documented
- Migration tested on copy of production data
- Zero-downtime migration strategy

## Per CLAUDE.md
Use Alembic exclusively - no manual SQL migrations.

---

## kurt-core-1uhd.34: Implement API cost tracking system
Priority: P1 | Type: task

Track and report API costs for paid services (Apify, Firecrawl).

## Acceptance Criteria
- Cost tracking model: api_costs table with provider, operation, cost_usd, created_at
- Integration with rate limiter (story 2)
- CLI command: kurt costs --since DATE
- Cost warnings when approaching limits
- Pre-execution cost estimates for dry-run mode

---

## kurt-core-1uhd.35: Add DBOS workflow integration to subcommands
Priority: P2 | Type: task

Ensure all new subcommands follow DBOS workflow patterns.

## Acceptance Criteria
- All map/fetch subcommands use @DBOS.workflow() decorator
- Progress tracking via DBOS events
- Workflow status visible in kurt workflows list
- Recovery from interrupted workflows
- Nested workflow support for parent tracking

## Per CLAUDE.md
Use @with_parent_workflow_id decorator for nested workflows.

---

## kurt-core-1uhd.36: Define engine registry pattern and interface
Priority: P2 | Type: task

Create consistent pattern for engine registration and discovery.

## Acceptance Criteria
- EngineRegistry ABC with register(), get(), list_available() methods
- Configuration-based engine selection
- Dynamic engine loading from plugins
- Engine capability declarations (supports_profiles, supports_posts)
- Unit tests for registry patterns

---

## kurt-core-1uhd.4: Add doc_type column to map_documents
Priority: P2 | Type: task

Add doc_type column to distinguish between doc, profile, and posts.

## Changes
- Add doc_type VARCHAR(20) DEFAULT 'doc' column
- Add platform VARCHAR(50) column for social platforms
- Create composite unique index on (source_url, doc_type)
- Backfill existing rows with doc_type='doc'

---

## kurt-core-1uhd.5: Add doc_type column to fetch_documents
Priority: P2 | Type: task

Add doc_type column to fetch_documents table.

## Changes
- Add doc_type VARCHAR(20) DEFAULT 'doc' column
- Add platform VARCHAR(50) column
- Update indexes for efficient queries by doc_type
- Backfill existing rows

---

## kurt-core-1uhd.6: Create profiles table schema
Priority: P2 | Type: task

Create dedicated table for profile metadata storage.

## Schema
- id, platform, platform_id, username, display_name
- bio, followers_count, following_count, posts_count
- profile_url, avatar_url, verified
- raw_metadata JSON, created_at, updated_at

---

## kurt-core-1uhd.7: Create posts table schema
Priority: P2 | Type: task

Create dedicated table for social posts metadata.

## Schema
- id, platform, platform_id, profile_id (FK)
- content_text, content_html, media_urls JSON
- likes_count, shares_count, comments_count
- published_at, raw_metadata JSON, created_at

---

## kurt-core-1uhd.8: Create map/core/ module with shared logic
Priority: P2 | Type: task

Extract shared map logic into core module.

## Files
- map/core/__init__.py - exports
- map/core/base.py - BaseMapper ABC
- map/core/storage.py - persistence helpers
- map/core/models.py - shared Pydantic models
- map/core/utils.py - URL normalization, etc.

---

## kurt-core-1uhd.9: Create map/engines/ module structure
Priority: P2 | Type: task

Organize map engines into dedicated module.

## Files
- map/engines/__init__.py - engine registry
- map/engines/sitemap.py - existing sitemap logic
- map/engines/crawl.py - existing crawl logic
- map/engines/rss.py - RSS feed discovery
- map/engines/apify.py - Apify adapter

---

