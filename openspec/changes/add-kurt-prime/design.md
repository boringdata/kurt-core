# Design: Kurt Prime - Claude Code Integration

## Existing Infrastructure

Kurt already has Claude Code hooks configured in `src/kurt/agents/claude-settings.json`:
- **SessionStart**: Currently runs `kurt status --hook-cc`
- **PreToolUse/PostToolUse**: Approval service hooks for Edit/Write/Update

The `kurt prime` command will **replace** `kurt status --hook-cc` in SessionStart to provide
richer workflow context that survives compaction.

**Important**: Approval hooks (PreToolUse/PostToolUse) are **preserved** - they serve a different
purpose (security/approval) and coexist with context injection hooks.

## Hook Source of Truth

**CRITICAL**: There is ONE source of truth for SessionStart hooks: `claude-settings.json`.

The Claude plugin (`claude-plugin/plugin.json`) does NOT define hooks. Instead:
- Plugin provides slash commands, skills, and agents only
- All hooks remain in `claude-settings.json` (already used by Kurt projects)
- Migration updates `claude-settings.json` in-place (no duplication risk)

This avoids double-execution of `kurt prime` that would occur if both plugin.json
AND claude-settings.json defined SessionStart hooks.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code                                 │
├─────────────────────────────────────────────────────────────────┤
│  SessionStart Hook ──► kurt prime ──► Context Injection         │
│  PreCompact Hook   ──► kurt prime ──► Context Recovery          │
│                                                                  │
│  Slash Commands    ──► /kurt:workflow, /kurt:status, etc.       │
│  Skills            ──► Complex multi-step operations            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Kurt Core (CLI)                             │
├─────────────────────────────────────────────────────────────────┤
│  CLI Commands                                                   │
│  ├── kurt prime      (context injection)                        │
│  ├── kurt status     (current state)                            │
│  ├── kurt workflow   (workflow management)                      │
│  └── kurt tool       (tool execution)                           │
└─────────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Prime Command (`src/kurt/cli/prime.py`)

```python
@click.command()
@click.option('--export', is_flag=True, help='Output default (ignore override)')
def prime(export: bool):
    """Output AI-optimized workflow context."""
```

**Features:**
- Single output mode (~2-5k tokens)
- Dynamic project context (workflows, tools)
- Session close protocol with git workflow
- Override via `.kurt/PRIME.md`

**Project Root Detection:**
- Walk up directory tree to find nearest Kurt project marker
- Check for EITHER `.kurt/` directory OR `kurt.config` file (whichever found first)
- Use that directory as project root for all paths
- Enables running from any subdirectory within a project

**Silent Exit:**
- If neither `.kurt/` nor `kurt.config` found in current dir or any parent, exit 0 with no output
- Critical for hook compatibility in non-Kurt directories

### 2. Claude Plugin Structure

```
claude-plugin/
├── .claude-plugin/
│   └── plugin.json           # Metadata + hooks
├── commands/                  # Slash commands
│   ├── prime.md              # /kurt:prime
│   ├── status.md             # /kurt:status
│   ├── workflow.md           # /kurt:workflow
│   ├── map.md                # /kurt:map
│   └── fetch.md              # /kurt:fetch
├── skills/
│   └── kurt/
│       └── SKILL.md          # Main skill definition
└── agents/
    └── task-agent.md         # Autonomous task agent
```

**plugin.json:**
```json
{
  "name": "kurt",
  "description": "Document intelligence and workflow automation",
  "version": "1.0.0"
}
```

**Note**: Hooks are NOT defined in plugin.json - they remain in `claude-settings.json`
to avoid double-execution. The plugin only provides commands, skills, and agents.

### 3. Prime Output Template

```markdown
# Kurt Workflow Context

> Run `kurt prime` after compaction or new session

## Session Protocol
[ ] Check `kurt status` for running workflows
[ ] Commit code changes
[ ] Push to remote

## Essential Commands
- `kurt workflow list` - Available workflows
- `kurt workflow run <name>` - Execute workflow
- `kurt tool map <url>` - Map website
- `kurt tool fetch` - Fetch content
- `kurt status` - Check progress

## Available Workflows
{{dynamic: list from project workflows/ dir}}

## Project Configuration
{{dynamic: from kurt.config}}
```

### 4. Override Mechanism with Templating

Users can customize output by creating `.kurt/PRIME.md`:
- Supports template variables: `{{workflows}}`, `{{tools}}`, `{{project_name}}`, `{{project_root}}`
- Template variables are replaced with dynamic content
- If no template variables present, file content is used as-is
- `--export` flag outputs default template with RAW placeholders (unresolved)
  - Intended for users to copy to `.kurt/PRIME.md` and customize
  - Example: `{{workflows}}` appears literally in output, not expanded
- Allows project-specific customization while preserving dynamic context

**Token Limit Handling:**
- Default template is guaranteed under 5000 tokens
- Custom overrides may exceed this limit
- When override exceeds limit: emit warning to stderr, still output full content
- No truncation - user is responsible for override size

## Migration Path

1. **Phase 1**: Add `kurt prime` command
2. **Phase 2**: Create Claude plugin structure
3. **Phase 3**: Update hooks from `status --hook-cc` to `prime`
4. **Phase 4**: Document migration from static CLAUDE.md

## Testing Strategy

- Unit tests for prime output generation
- Unit tests for project detection
- Integration tests for hook execution
- Context size validation (<5k tokens)
