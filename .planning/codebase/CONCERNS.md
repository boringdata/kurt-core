# Codebase Concerns

**Analysis Date:** 2026-02-09

## Tech Debt

### Unimplemented CMS Adapters
- **Issue:** Placeholder adapters that raise `NotImplementedError`
- **Files:**
  - `src/kurt/integrations/cms/__init__.py:28,30` - Contentful and WordPress
  - `src/kurt/integrations/domains_analytics/__init__.py:32,34` - GA4 and Plausible
  - `src/kurt/integrations/domains_analytics/fetch.py:24,26` - GA4 and Plausible
- **Impact:** Users expect CMS support but get errors when attempting Contentful/WordPress integration
- **Fix approach:** Either implement adapters or remove from public API until ready

### Unimplemented Storage Interface
- **Issue:** Abstract `Storage` class with no default implementations in production
- **Files:** `src/kurt/web/api/storage.py:8-29` - All methods raise `NotImplementedError`
- **Impact:** Web API cannot function without S3 or LocalStorage configuration
- **Fix approach:** Document required storage implementation or provide sensible default

### Deprecated Functions Not Removed
- **Issue:** Deprecated code still referenced but flagged for removal
- **Files:**
  - `src/kurt/integrations/cms/sanity/adapter.py:806` - DEPRECATED extraction function
  - `src/kurt/workflows/agents/executor.py:1073` - DEPRECATED LLMStep requirement
- **Impact:** Code confusion, potential breaking changes if removed suddenly
- **Fix approach:** Create deprecation timeline and migrate callers before removal

### Bare Exception Handlers
- **Issue:** Multiple `except Exception:` blocks that silently swallow errors
- **Files:**
  - `src/kurt/conftest.py:184,187` - Silent failure in test fixtures
  - `src/kurt/status/cli.py:141,175` - Dolt init failures masked
  - `src/kurt/observability/status.py:452,475,537,590` - JSON parsing errors hidden
  - `src/kurt/db/connection.py:119-141` - Connection pool errors swallowed
- **Impact:** Debugging becomes difficult; subtle failures go unnoticed
- **Fix approach:** Log errors before catching, or be more specific about exception types

## Known Bugs

### CLI Commands Are Non-Functional Stubs
- **Symptoms:** `kurt tools map doc <url>` and similar commands only print parameter echoes without performing actual work
- **Files:** `src/kurt/tools/cli.py:62-67` and surrounding command handlers
- **Trigger:** Execute any `kurt tools map/fetch` CLI command
- **Issue Details:** Commands instantiate parameter messages but never invoke `MapDocSubcommand`, `FetchDocSubcommand`, or other subcommand implementations
- **Impact:** All CLI-based content discovery and extraction workflows are completely non-functional
- **Workaround:** None available; commands must be fixed to invoke subcommands
- **Status:** Identified in Codex review (CODEX_REVIEW_SUMMARY.md, P1 priority)

### Platform Parameter Ignored in Apify Profile Mapping
- **Symptoms:** `map profile "query" --platform linkedin` returns Twitter data instead of LinkedIn profiles
- **Files:** `src/kurt/tools/map/engines/apify.py:60-67` - `_map_profiles()` method
- **Trigger:** Call profile mapping with explicit platform parameter that differs from query keywords
- **Issue Details:** Method always infers platform from query keywords (`_detect_platform(query)`) and ignores the `platform` parameter
- **Example:** Query "data scientist" with `--platform linkedin` returns Twitter results (no "linkedin" keyword in query)
- **Impact:** Wrong data returned to users; platform mismatches in downstream fetch operations
- **Status:** Identified in Codex review (CODEX_REVIEW_SUMMARY.md, P2 priority)

### Bare `pass` Statements After Exception Handling
- **Issue:** Code catches exceptions then does nothing with them
- **Files:**
  - `src/kurt/db/connection.py:121-122,137-141` - Connection pool ignores connection failures
  - `src/kurt/workflows/agents/executor.py:118-120` - Tool call parsing suppresses errors
- **Impact:** Silent data loss or degraded service without operator awareness
- **Fix approach:** Either handle error properly or at minimum log it

## Security Considerations

### Environment Variable Loading Without Validation
- **Risk:** `.env` file loaded into `os.environ` without type validation or scope limitation
- **Files:** `src/kurt/workflows/agents/executor.py:502-510` - Subprocess environment setup
- **Current mitigation:** Only loads keys not already in `os.environ`; doesn't validate values
- **Recommendations:**
  - Whitelist allowed environment variables rather than loading all
  - Validate API key formats before passing to subprocess
  - Log which keys were injected (at debug level only)

### Subprocess Command Building with User Input
- **Risk:** User prompts and parameters passed directly to `claude` CLI subprocess
- **Files:** `src/kurt/workflows/agents/executor.py:535-560` - Command building
- **Current mitigation:** Using `subprocess.run()` with list (not string), so no shell injection
- **Recommendations:**
  - Document that prompt should not contain shell metacharacters
  - Consider escaping or validating prompt content
  - Log the actual command executed (masked if contains secrets)

### SQL Parameterization
- **Status:** ✅ Good - Code uses parameterized queries throughout
- **Files:** `src/kurt/tools/sql/__init__.py:4` documents SQL injection prevention
- **Note:** Queries use `?` placeholders with separate parameter lists

### API Key Storage in Vault
- **Risk:** Vault permissions must be strict; token expiration not monitored
- **Files:** `src/kurt/workflows/agents/executor.py` and Vault configuration
- **Current mitigation:** Vault uses `http://100.77.36.113:8200` (local network only)
- **Recommendations:**
  - Monitor vault token expiration
  - Implement rotation strategy
  - Audit vault access logs regularly

## Performance Bottlenecks

### `.all()` Queries Without Pagination
- **Problem:** Multiple `session.exec(select(...)).all()` calls load entire tables into memory
- **Files:**
  - `src/kurt/status/queries.py:34,73` - Loads all runs/events
  - `src/kurt/observability/traces.py:262,371` - Loads all traces for analysis
  - `src/kurt/documents/registry.py:57,99` - Loads all documents
  - `src/kurt/integrations/domains_analytics/cli.py:205,401` - Loads all domains/pages
- **Impact:** Queries become O(n) in table size; memory usage scales with data volume
- **Improvement path:**
  - Add LIMIT/OFFSET to queries or use pagination
  - Implement cursor-based streaming for large result sets
  - Add database indexes on commonly queried fields

### N+1 Query Pattern in Step Log Processing
- **Problem:** Fetching step logs then querying events separately for each step
- **Files:** `src/kurt/observability/status.py:143-195` - Step log and event queries
- **Impact:** For a workflow with 10 steps, makes 11 database queries instead of 1-2
- **Improvement path:** Use JOIN queries or batch event loading

### Session Creation Per Operation
- **Problem:** Some code creates new database sessions repeatedly instead of reusing
- **Files:** `src/kurt/status/queries.py` - Multiple `managed_session()` calls
- **Impact:** Connection pool churn; slower operations
- **Improvement path:** Use connection pooling more aggressively

### Large File Streaming Not Implemented
- **Problem:** `LocalStorage.read_file()` loads entire files into memory
- **Files:** `src/kurt/web/api/storage.py:58-61`
- **Impact:** Cannot handle files larger than available RAM
- **Improvement path:** Implement streaming reader for large files

## Fragile Areas

### WebSocket Stream Bridge Session Management
- **Files:** `src/kurt/web/api/stream_bridge.py:37-38` - Global session registry
- **Why fragile:**
  - Global dictionary without cleanup guarantees
  - Sessions stored by ID but no TTL enforcement visible
  - Max session limit (`MAX_SESSIONS=20`) could cause connection drop
  - Permission persistence happens out-of-band (lines 41-163)
- **Safe modification:**
  - Test concurrent connection scenarios
  - Verify session cleanup on disconnect
  - Monitor MAX_SESSIONS enforcement

### Observability Lifecycle State Transitions
- **Files:** `src/kurt/observability/lifecycle.py:61-77` - Status transition tables
- **Why fragile:**
  - Multiple code paths can trigger status updates (CLI, API, agent)
  - No lock prevents race conditions on concurrent updates
  - Invalid transitions raise exceptions but don't prevent partial updates
- **Safe modification:**
  - Add transaction-level locks around status updates
  - Test concurrent workflow updates
  - Verify atomicity of metadata updates alongside status

### Database Connection Pool Fallback Logic
- **Files:** `src/kurt/db/connection.py:111-131` - `ConnectionPool.get_connection()`
- **Why fragile:**
  - If pool exhausted, blocks indefinitely waiting for connection
  - No timeout on `_pool.get()` call (line 131)
  - If mysql.connector and pymysql both missing, error message only tells about mysql-connector
- **Safe modification:**
  - Add timeout to pool.get() with fallback error
  - Test behavior when pool size exceeded
  - Improve error message to mention both possible packages

### Agent Execution Subprocess Environment
- **Files:** `src/kurt/workflows/agents/executor.py:498-532` - Subprocess env setup
- **Why fragile:**
  - `.env` parsing could fail silently (only logged at line 503)
  - PYTHONPATH modification could create circular imports if not careful
  - Tool tracking via temp files has race condition if cleanup fails
- **Safe modification:**
  - Add explicit validation of `.env` structure
  - Test PYTHONPATH with actual workflow imports
  - Implement file locking on tool log file

## Scaling Limits

### WebSocket Server Session Limit
- **Current capacity:** 20 concurrent sessions (hardcoded in `stream_bridge.py:27`)
- **Limit:** Adding 21st connection will exhaust capacity
- **Scaling path:** Make configurable, implement session eviction policy
- **Files:** `src/kurt/web/api/stream_bridge.py`

### Dolt Server Not Horizontally Scalable
- **Current capacity:** Single Dolt instance per project
- **Limit:** Cannot distribute database across multiple servers (Dolt is single-instance)
- **Scaling path:** Implement sharding by project/workspace or switch to cloud-hosted option
- **Files:** `src/kurt/db/dolt.py`, `src/kurt/db/connection.py`

### In-Memory Session Registry
- **Current capacity:** Limited by available RAM for session dictionaries
- **Limit:** No persistent session storage; all sessions lost on restart
- **Scaling path:** Implement Redis or similar for session persistence
- **Files:** `src/kurt/web/api/stream_bridge.py:37-38`

### Rate Limiter Token Bucket Per Process
- **Current capacity:** Each process has independent token bucket
- **Limit:** Multi-process deployments get N× the rate limit
- **Scaling path:** Implement distributed rate limiting (Redis-backed)
- **Files:** `src/kurt/tools/rate_limit.py`

## Dependencies at Risk

### Dolt Database Stability
- **Risk:** Dolt is relatively new database; production stability not yet proven at scale
- **Impact:** Data loss, corruption, or unexpected behavior in unfamiliar scenarios
- **Current mitigation:** Git-like versioning allows rollback
- **Recommendations:**
  - Regular backups of `.dolt` directory
  - Test disaster recovery procedures
  - Monitor Dolt repository integrity with `dolt status`

### Apify API Dependency
- **Risk:** Apify API rate limits and pricing could change; service could be discontinued
- **Impact:** Content discovery features fail; users must find alternative
- **Current mitigation:** Multiple engines (crawl, sitemap, RSS) provide fallbacks
- **Recommendations:**
  - Keep Apify optional; document fallback engines
  - Monitor Apify API status
  - Maintain alternative web scraping approach

### Claude Code CLI Availability
- **Risk:** Claude Code CLI availability depends on Anthropic infrastructure
- **Impact:** Agent workflows cannot execute without `claude` command
- **Current mitigation:** Subprocess checks `shutil.which("claude")` before running
- **Recommendations:**
  - Document installation process clearly
  - Provide fallback for when `claude` is unavailable
  - Consider timeout for very long-running agents

## Missing Critical Features

### No Database Migration Strategy
- **Problem:** Schema changes require manual `ensure_tables()` calls; no migration framework
- **Files:** `src/kurt/db/schema.py`, `src/kurt/db/migrations.py`
- **Blocks:** Multi-tenant deployments; version upgrades with schema changes
- **Fix approach:** Implement Dolt-native migration system or adopt Alembic

### No Built-in Monitoring/Alerting
- **Problem:** No health checks for Dolt, Apify, or other critical services
- **Blocks:** Operational visibility; alerting on service degradation
- **Fix approach:** Add Prometheus metrics and alert rules

### No Backup/Restore Procedures
- **Problem:** No documented or automated backup strategy for Dolt repositories
- **Blocks:** Disaster recovery planning
- **Fix approach:** Implement daily incremental backups with restore testing

### No Audit Logging for Sensitive Operations
- **Problem:** API key access, admin operations not logged
- **Blocks:** Compliance requirements (SOC2, etc.)
- **Fix approach:** Implement audit trail table with immutable logging

## Test Coverage Gaps

### Untested Workflow Cancellation
- **What's not tested:** Canceling a running workflow mid-execution
- **Files:** `src/kurt/observability/lifecycle.py:65-66` - `canceling → canceled` transition
- **Risk:** Concurrent cancellation could leave data in inconsistent state
- **Priority:** High

### Untested Concurrent Database Writes
- **What's not tested:** Multiple processes writing to same Dolt repository simultaneously
- **Files:** `src/kurt/db/connection.py` - Connection pool
- **Risk:** Dolt transaction semantics unclear under write contention
- **Priority:** High (if multi-process deployment is expected)

### Untested Large File Streaming
- **What's not tested:** Reading files larger than 1GB via LocalStorage
- **Files:** `src/kurt/web/api/storage.py:58-61` - `read_file()` method
- **Risk:** OOM crashes on large files
- **Priority:** Medium

### Untested API Key Rotation
- **What's not tested:** Changing API keys while workflows are running
- **Files:** `src/kurt/integrations/apify/client.py` - API key loading
- **Risk:** In-flight operations fail with stale keys
- **Priority:** Medium

### Untested Network Failures During Agent Execution
- **What's not tested:** Network timeouts, reconnects during `claude` subprocess execution
- **Files:** `src/kurt/workflows/agents/executor.py:566-573` - Subprocess invocation
- **Risk:** Partial agent execution or zombie processes
- **Priority:** Medium

---

*Concerns audit: 2026-02-09*
