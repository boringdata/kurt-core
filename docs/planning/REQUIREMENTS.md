# Requirements: Kurt Skill Extensibility

**Defined:** 2026-02-09
**Core Value:** Drop a folder with SKILL.md + skill.py -> it works immediately

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Skill SDK

- [ ] **SDK-01**: SKILL.md manifest parsing with YAML frontmatter
- [ ] **SDK-02**: Skill base interface with async fetch() and map() methods
- [ ] **SDK-03**: @skill decorator for function-based registration
- [ ] **SDK-04**: FetchResult and MapResult standard return types
- [ ] **SDK-05**: SkillConfig for input validation with Pydantic

### Discovery

- [ ] **DISC-01**: Filesystem scanning from ./skills/, ~/.kurt/skills/, builtin/
- [ ] **DISC-02**: Priority ordering (project > user > builtin)
- [ ] **DISC-03**: Lazy loading (parse manifest, defer code import until use)
- [ ] **DISC-04**: Hot reload via file watching during development
- [ ] **DISC-05**: SkillRegistry singleton for global skill access

### URL Matching

- [ ] **URL-01**: URL pattern declaration in SKILL.md manifest
- [ ] **URL-02**: Auto-selection of skill based on URL pattern match
- [ ] **URL-03**: Fallback to default engine (trafilatura) if no match

### Requirements Validation

- [ ] **VAL-01**: Environment variable requirement checks from manifest
- [ ] **VAL-02**: Python package requirement declaration
- [ ] **VAL-03**: Clear error messages for missing requirements
- [ ] **VAL-04**: Validation at discovery time (before execution)

### CLI Commands

- [ ] **CLI-01**: `kurt skill list` — show all available skills with status
- [ ] **CLI-02**: `kurt skill info <name>` — show skill details and requirements
- [ ] **CLI-03**: `kurt skill check <name>` — validate skill requirements are met
- [ ] **CLI-04**: `kurt skill install <path>` — install skill from git URL or local path

### Tool Integration

- [ ] **INTG-01**: Replace hardcoded _FETCH_ENGINES dict with SkillDiscovery
- [ ] **INTG-02**: Replace hardcoded _MAP_ENGINES dict with SkillDiscovery
- [ ] **INTG-03**: Dynamic CLI --engine choices from registered skills
- [ ] **INTG-04**: Backward compatibility: existing --engine trafilatura still works

### Engine Migration

- [ ] **MIG-01**: Convert trafilatura fetcher to skill format
- [ ] **MIG-02**: Convert tavily fetcher to skill format
- [ ] **MIG-03**: Convert firecrawl fetcher to skill format
- [ ] **MIG-04**: Convert apify fetcher to skill format
- [ ] **MIG-05**: Convert httpx fetcher to skill format
- [ ] **MIG-06**: Convert twitterapi fetcher to skill format
- [ ] **MIG-07**: Convert sitemap mapper to skill format
- [ ] **MIG-08**: Convert rss mapper to skill format
- [ ] **MIG-09**: Convert crawl mapper to skill format
- [ ] **MIG-10**: Convert cms mapper to skill format
- [ ] **MIG-11**: Convert folder mapper to skill format

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Distribution

- **DIST-01**: Entry point support for pip-installable skills
- **DIST-02**: Skill marketplace / registry integration
- **DIST-03**: Version pinning and compatibility checking

### Advanced Features

- **ADV-01**: Skill composition (skills that depend on other skills)
- **ADV-02**: Sandboxing for untrusted skills
- **ADV-03**: Observability integration (cost tracking per skill)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| MCP server | Future milestone — Phase 5 in original plan |
| OpenClaw bridge | Future milestone — Phase 6 in original plan |
| GUI skill manager | CLI-first approach |
| Skill versioning/updates | Adds complexity, defer to v2 |
| Remote skill execution | Security concerns, keep local |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SDK-01 | Phase 1 | Pending |
| SDK-02 | Phase 1 | Pending |
| SDK-03 | Phase 1 | Pending |
| SDK-04 | Phase 1 | Pending |
| SDK-05 | Phase 1 | Pending |
| DISC-01 | Phase 2 | Pending |
| DISC-02 | Phase 2 | Pending |
| DISC-03 | Phase 2 | Pending |
| DISC-04 | Phase 2 | Pending |
| DISC-05 | Phase 2 | Pending |
| URL-01 | Phase 2 | Pending |
| URL-02 | Phase 2 | Pending |
| URL-03 | Phase 2 | Pending |
| VAL-01 | Phase 3 | Pending |
| VAL-02 | Phase 3 | Pending |
| VAL-03 | Phase 3 | Pending |
| VAL-04 | Phase 3 | Pending |
| CLI-01 | Phase 4 | Pending |
| CLI-02 | Phase 4 | Pending |
| CLI-03 | Phase 4 | Pending |
| CLI-04 | Phase 4 | Pending |
| INTG-01 | Phase 5 | Pending |
| INTG-02 | Phase 5 | Pending |
| INTG-03 | Phase 5 | Pending |
| INTG-04 | Phase 5 | Pending |
| MIG-01 | Phase 6 | Pending |
| MIG-02 | Phase 6 | Pending |
| MIG-03 | Phase 6 | Pending |
| MIG-04 | Phase 6 | Pending |
| MIG-05 | Phase 6 | Pending |
| MIG-06 | Phase 6 | Pending |
| MIG-07 | Phase 6 | Pending |
| MIG-08 | Phase 6 | Pending |
| MIG-09 | Phase 6 | Pending |
| MIG-10 | Phase 6 | Pending |
| MIG-11 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 36 total
- Mapped to phases: 36
- Unmapped: 0

---
*Requirements defined: 2026-02-09*
*Last updated: 2026-02-09 after roadmap creation*
