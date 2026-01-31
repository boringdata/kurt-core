# Tasks: Add Kurt Prime

## Phase 1: Prime Command (Foundation)

### 1. Create prime command skeleton
- [ ] Create `src/kurt/cli/prime.py`
- [ ] Add basic Click command with `--export` flag
- [ ] Register in `main.py`
- [ ] Verify: `kurt prime --help` works

### 2. Implement project detection
- [ ] Walk up directory tree to find project root
- [ ] Check for EITHER `.kurt/` directory OR `kurt.config` file
- [ ] Use first match as project root
- [ ] Silent exit (code 0, no output) if neither found
- [ ] Verify: no output in non-Kurt directory

### 3. Create output template
- [ ] Define comprehensive template (~2-5k tokens)
- [ ] Include session close protocol checklist
- [ ] Include essential command reference
- [ ] Include workflow patterns section
- [ ] Verify: output under 5000 tokens

### 4. Add dynamic project context
- [ ] List available workflows from `workflows/` dir
- [ ] Show configured tools from `kurt.config`
- [ ] Include project name/path
- [ ] Verify: dynamic content appears correctly

### 5. Implement custom override support
- [ ] Check for `.kurt/PRIME.md`
- [ ] Output file content if exists
- [ ] Skip override with `--export` flag
- [ ] Verify: override takes precedence

### 6. Add git context detection
- [ ] Detect if in git repository
- [ ] Adapt session protocol for git vs non-git
- [ ] Include branch info if applicable
- [ ] Verify: git-aware output

### 7. Add unit tests for prime command
- [ ] Test project detection
- [ ] Test output generation
- [ ] Test override behavior
- [ ] Test flag combinations

## Phase 2: Claude Plugin Structure

### 8. Create plugin directory structure
- [ ] Create `claude-plugin/` directory
- [ ] Create `.claude-plugin/` subdirectory
- [ ] Create `commands/` subdirectory
- [ ] Create `skills/kurt/` subdirectory
- [ ] Create `agents/` subdirectory

### 9. Create plugin.json manifest
- [ ] Add name, description, version
- [ ] Add author and repository info
- [ ] NO hooks in plugin.json (hooks stay in claude-settings.json)
- [ ] Verify: valid JSON structure

### 10. Create slash command definitions
- [ ] Create `commands/prime.md`
- [ ] Create `commands/status.md`
- [ ] Create `commands/workflow.md`
- [ ] Create `commands/map.md`
- [ ] Create `commands/fetch.md`
- [ ] Each with frontmatter and instructions

### 11. Create main skill definition
- [ ] Create `skills/kurt/SKILL.md`
- [ ] Add frontmatter (name, description, allowed-tools)
- [ ] Document when to use Kurt vs other tools
- [ ] Include command reference table
- [ ] Include workflow patterns

### 12. Create task agent definition
- [ ] Create `agents/task-agent.md`
- [ ] Define autonomous workflow discovery
- [ ] Define task execution protocol
- [ ] Define progress reporting
- [ ] Define completion criteria

## Phase 3: Integration & Migration

### 13. Update hooks in claude-settings.json
- [ ] Update `claude-settings.json` SessionStart: `kurt status --hook-cc` → `kurt prime`
- [ ] Add PreCompact hook: `kurt prime` (new)
- [ ] Preserve PreToolUse/PostToolUse approval hooks unchanged
- [ ] Test hook execution
- [ ] Update documentation

### 14. Integration test: prime + hooks
- [ ] Test SessionStart hook execution
- [ ] Test PreCompact hook execution
- [ ] Verify context output in hook context
- [ ] Verify: end-to-end flow works

### 15. Documentation: migration guide
- [ ] Document removing static CLAUDE.md
- [ ] Document plugin installation
- [ ] Document `.kurt/PRIME.md` customization
- [ ] Add troubleshooting section

## Dependencies

```
1 ─► 2 ─► 3 ─► 4 ─► 5 ─► 6 ─► 7
                              │
8 ─► 9 ─► 10 ─► 11 ─► 12 ◄────┘
                              │
13 ─► 14 ─► 15 ◄──────────────┘
```

## Parallelizable Work

- Tasks 1-7 (Prime Command) must be sequential
- Tasks 8-12 (Plugin) can start after task 7
- Tasks 13-15 (Integration) require prior phases

## Validation Criteria

- [ ] `kurt prime` outputs workflow context
- [ ] Plugin installs and hooks trigger correctly
- [ ] All tests pass
- [ ] Documentation is complete
