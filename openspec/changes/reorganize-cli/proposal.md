# Proposal: Reorganize CLI Command Structure

## Problem

The current CLI has 32 top-level commands, creating confusion:

1. **Duplicates**: `map`/`fetch` exist both top-level AND under `tool` AND partially under `content`
2. **Confusing names**: `agents` vs `agent` - different things, similar names
3. **Too flat**: 32 commands at root level is overwhelming
4. **Inconsistent grouping**: `research`/`signals` are top-level but `analytics` is under `integrations`

### Current Structure (32 top-level commands)
```
kurt
├── init, status, doctor, repair, update    # Project
├── map, fetch, llm, embed, sql, write      # Tools (duplicated)
├── run, test, logs, cancel                 # Workflow execution
├── content (list, get, delete)             # Documents
├── tool (map, fetch, llm, embed, sql, write)  # Tools (duplicate)
├── workflow (run, test, logs, cancel, status)  # Duplicate
├── agents (list, show, run, validate, ...)    # Agent workflows
├── agent (tool save-to-db, ...)               # Agent tools
├── branch, pull, push, merge               # Git+Dolt
├── integrations (cms, analytics, research) # External
├── research, signals                       # Also external (inconsistent)
├── admin (migrate, telemetry, feedback)    # Admin
├── db (status, export, import)             # Database
├── cloud (login, status, invite, ...)      # Cloud
├── show (format-templates, ...)            # Documentation
└── serve                                   # Web UI
```

## Proposed Structure

**Guiding principles:**
1. Most-used commands stay top-level (init, status, run, map, fetch)
2. Group related commands logically
3. Remove duplicates
4. Rename confusing commands

### New Structure (~12 top-level)
```
kurt
├── init                    # Initialize project
├── status                  # Project status
├── doctor                  # Health check
├── serve                   # Web UI (stays top-level for dev convenience)
│
├── workflow                # ALL workflow operations (merged agent + workflow)
│   ├── run <file.toml>     # Run TOML workflow
│   ├── test                # Test workflow
│   ├── logs                # View logs
│   ├── cancel              # Cancel workflow
│   ├── list                # List all workflows (.toml + .md)
│   ├── show                # Show workflow details
│   ├── validate            # Validate workflow file
│   ├── create              # Create new workflow
│   └── history             # Run history
│
├── tool                    # ALL data tools
│   ├── map                 # Discover URLs
│   ├── fetch               # Fetch content
│   ├── llm                 # LLM processing
│   ├── embed               # Generate embeddings
│   ├── sql                 # Query database
│   ├── save                # Save to DB table (was: write)
│   ├── research            # Research queries (uses API keys from env)
│   └── signals             # Signal monitoring (uses API keys from env)
│
├── docs                    # Document management (was: content)
│   ├── list
│   ├── get
│   └── delete
│
├── sync                    # Git+Dolt operations
│   ├── pull
│   ├── push
│   ├── branch
│   └── merge
│
├── connect                 # External service setup ONLY
│   ├── cms                 # CMS connection (Sanity, etc.)
│   └── analytics           # Analytics connection (PostHog, etc.)
│
├── cloud                   # Kurt Cloud
│   ├── login
│   ├── status
│   └── invite
│
├── admin                   # Administrative
│   ├── migrate
│   ├── db                  # Database operations
│   ├── telemetry
│   └── update
│
└── help                    # Documentation (was: show)
    ├── workflow-create
    ├── format-templates
    └── ...
```

## Key Changes

| Current | Proposed | Reason |
|---------|----------|--------|
| `agents` + `workflow` | `workflow` | Merge into single group (TOML + MD workflows) |
| `agent` (tools) | Remove | Merge into `tool` |
| `content` | `docs` | Shorter, clearer |
| `integrations` | `connect` | Shorter, only CMS/analytics setup |
| `research`, `signals` | `tool research`, `tool signals` | They're tools, not connections |
| `write` | `save` | Clearer - saves to DB table |
| `show` | `help` | More intuitive |
| `branch`, `pull`, `push`, `merge` | `sync *` | Group version control |
| `db` | `admin db` | Admin task |
| `serve` | Keep top-level | Dev convenience |
| `update` | `admin update` | Rarely used |

## Migration Strategy

1. **Phase 1**: Add new command groups, keep old as aliases
2. **Phase 2**: Deprecation warnings on old commands
3. **Phase 3**: Remove old commands (major version)

## Resolved Questions

1. ~~Should `map`/`fetch`/`sql` stay top-level as shortcuts?~~ → No, all under `tool`
2. ~~Should `run` stay top-level?~~ → No, use `workflow run`
3. ~~Should `serve` stay top-level?~~ → Yes, for dev convenience
4. ~~Where do research/signals go?~~ → `tool research`, `tool signals` (not connect)
5. ~~Merge agent and workflow?~~ → Yes, single `workflow` group

## Open Questions

1. Backwards compatibility: How long to keep aliases? (Proposed: 1 minor version with warnings)

## Success Criteria

- `kurt --help` shows ~15 commands instead of 32
- No duplicate commands
- Logical grouping is intuitive
- Common operations (init, status, run, map, fetch) are quick to access
