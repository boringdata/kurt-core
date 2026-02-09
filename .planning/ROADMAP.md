# Roadmap: Kurt Skill Extensibility

## Overview

This roadmap transforms Kurt from a tool with hardcoded engines into an extensible skill system. The journey starts with defining the core SDK interfaces, then builds discovery and validation layers, exposes CLI commands for skill management, integrates with existing tools, and finally migrates all 11 existing engines to the new skill format. Each phase delivers a coherent, testable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Skill SDK** - Core interfaces, decorators, and return types
- [ ] **Phase 2: Discovery & URL Matching** - Find skills from filesystem, route by URL patterns
- [ ] **Phase 3: Requirements Validation** - Check env vars, packages, validate before execution
- [ ] **Phase 4: CLI Commands** - User-facing skill management commands
- [ ] **Phase 5: Tool Integration** - Replace hardcoded dispatchers, dynamic --engine choices
- [ ] **Phase 6: Engine Migration** - Convert all existing engines to skill format

## Phase Details

### Phase 1: Skill SDK
**Goal**: Developers can define skills with a consistent interface that Kurt understands
**Depends on**: Nothing (first phase)
**Requirements**: SDK-01, SDK-02, SDK-03, SDK-04, SDK-05
**Success Criteria** (what must be TRUE):
  1. A SKILL.md file with YAML frontmatter parses into a SkillManifest object
  2. A Python function decorated with @skill registers in the SkillRegistry
  3. Skills return FetchResult or MapResult with consistent structure
  4. SkillConfig validates input using Pydantic before execution
  5. Async skill functions work correctly (no event loop blocking)
**Plans**: TBD

Plans:
- [ ] 01-01: TBD
- [ ] 01-02: TBD

### Phase 2: Discovery & URL Matching
**Goal**: Kurt automatically finds skills and routes URLs to the right skill
**Depends on**: Phase 1 (needs SDK interfaces to register against)
**Requirements**: DISC-01, DISC-02, DISC-03, DISC-04, DISC-05, URL-01, URL-02, URL-03
**Success Criteria** (what must be TRUE):
  1. Skills in ./skills/, ~/.kurt/skills/, and builtin/ are discovered at startup
  2. Project skills override user skills, which override builtin skills
  3. Skill code is not imported until the skill is actually invoked (lazy loading)
  4. URL patterns declared in SKILL.md correctly match incoming URLs
  5. `kurt fetch https://notion.so/page/...` auto-selects the notion skill (when present)
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Requirements Validation
**Goal**: Skills fail fast with clear errors when requirements are not met
**Depends on**: Phase 2 (needs discovery to have skills to validate)
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04
**Success Criteria** (what must be TRUE):
  1. Skills declaring `requires_env: [NOTION_TOKEN]` fail with clear message if env var is missing
  2. Skills declaring Python package requirements show what packages are needed
  3. Error messages include skill name, requirement type, and how to fix
  4. Validation runs at discovery time, not execution time (fail-fast)
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: CLI Commands
**Goal**: Users can discover, inspect, and manage skills from the command line
**Depends on**: Phase 3 (CLI shows validation status)
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04
**Success Criteria** (what must be TRUE):
  1. `kurt skill list` shows all discovered skills with their source (project/user/builtin)
  2. `kurt skill info notion` shows skill details, requirements, and URL patterns
  3. `kurt skill check notion` validates requirements and reports status
  4. `kurt skill install <path>` copies skill folder to ~/.kurt/skills/
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

### Phase 5: Tool Integration
**Goal**: Existing Kurt commands use the skill system instead of hardcoded dispatchers
**Depends on**: Phase 4 (needs complete skill system to integrate)
**Requirements**: INTG-01, INTG-02, INTG-03, INTG-04
**Success Criteria** (what must be TRUE):
  1. `kurt fetch --engine` dynamically lists available fetch skills
  2. `kurt map --engine` dynamically lists available map skills
  3. Adding a new skill folder immediately appears in --engine choices
  4. `kurt fetch --engine trafilatura` continues to work exactly as before
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Engine Migration
**Goal**: All existing engines are converted to skill format (proving the SDK works)
**Depends on**: Phase 5 (integration must work before migrating production code)
**Requirements**: MIG-01, MIG-02, MIG-03, MIG-04, MIG-05, MIG-06, MIG-07, MIG-08, MIG-09, MIG-10, MIG-11
**Success Criteria** (what must be TRUE):
  1. Each existing fetch engine (trafilatura, tavily, firecrawl, apify, httpx, twitterapi) works as a skill
  2. Each existing map engine (sitemap, rss, crawl, cms, folder) works as a skill
  3. Old _FETCH_ENGINES and _MAP_ENGINES dicts are deleted (no fallback to old code)
  4. All existing workflows using `--engine` names continue to work unchanged
  5. Each migrated skill has a SKILL.md with proper URL patterns and requirements
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Skill SDK | 0/2 | Not started | - |
| 2. Discovery & URL Matching | 0/2 | Not started | - |
| 3. Requirements Validation | 0/1 | Not started | - |
| 4. CLI Commands | 0/1 | Not started | - |
| 5. Tool Integration | 0/1 | Not started | - |
| 6. Engine Migration | 0/3 | Not started | - |

---
*Roadmap created: 2026-02-09*
*Last updated: 2026-02-09*
