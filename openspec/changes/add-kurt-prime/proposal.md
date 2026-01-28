# Proposal: Add Kurt Prime - Claude Code Integration

## Change ID
`add-kurt-prime`

## Summary
Add `kurt prime` command and Claude plugin architecture to enable seamless Claude Code integration, replacing static CLAUDE.md documentation with dynamic, context-aware workflow instructions.

## Problem Statement
Currently, Kurt projects require maintaining large static CLAUDE.md files (500+ lines) with:
- Instructions that get stale when Kurt updates
- Copy-pasted content across projects
- No adaptation to project-specific configuration
- Lost context after conversation compaction

The beads project demonstrates a superior pattern:
- `bd prime` command injects workflow context dynamically
- Claude plugin hooks run `bd prime` on SessionStart/PreCompact
- Context survives compaction automatically

## Proposed Solution

### 1. `kurt prime` Command
New CLI command that outputs AI-optimized workflow context:
- Single comprehensive output template (~2-5k tokens)
- Session close protocol (git workflow)
- Available workflows and tools
- Project-specific configuration
- Optional `.kurt/PRIME.md` override for customization

### 2. Claude Plugin Structure
Package Kurt as a Claude plugin (`claude-plugin/`):
- `plugin.json` with SessionStart/PreCompact hooks
- Slash commands as markdown files
- Skill definitions for complex operations
- Agent definitions for autonomous tasks

### 3. Migrate Existing Hooks
Kurt already has `claude-settings.json` with SessionStart hook running `kurt status --hook-cc`.
Migrate to `kurt prime` for richer context injection.

## Success Criteria
- [ ] `kurt prime` outputs context in <5k tokens
- [ ] SessionStart hook successfully injects context
- [ ] No more need for static CLAUDE.md in projects
- [ ] Context survives conversation compaction

## Scope
- **In scope**: prime command, plugin structure, hook migration
- **Out of scope**: MCP server (Kurt uses CLI hooks only)

## Dependencies
- Existing CLI infrastructure (`kurt.cli.main`)
- Existing hooks (`src/kurt/agents/claude-settings.json`)
- Kurt config system (`kurt.config`)

## Risks
- Plugin format may change with Claude Code updates
- Backward compatibility with existing projects

## Related Changes
- `kurt-simplification` - CLI reorganization
- `reorganize-cli` - Command structure
