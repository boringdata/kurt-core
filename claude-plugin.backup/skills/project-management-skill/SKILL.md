---
name: project-management
description: Manage Kurt projects - add sources/targets, update project.md, detect missing content, track progress. (project)
---

# Project Management Skill

## Overview

This skill orchestrates Kurt project workflows by managing sources (ground truth), targets (content to update/create), and project progress. It delegates operational details to specialized subskills and domain skills.

**For usage examples and workflows, see `CLAUDE.md`.**

---

## Subskills

### Core Workflow Subskills

**create-project** - Create a new Kurt project
- Entry point: `/create-project` slash command or `project-management create-project`
- Workflow: intent → name → foundation → sources → targets → rules → structure
- See: `subskills/create-project.md`

**resume-project** - Resume work on existing project
- Entry point: `/resume-project` slash command or `project-management resume-project [name]`
- Workflow: load context → check foundation → check content → recommend → validate rules
- See: `subskills/resume-project.md`

**check-foundation** - Verify organizational foundation exists
- Entry point: Called by create-project and resume-project subskills
- Checks: content map (/sources/) + core rules (publisher, voice, personas)
- Delegates: ingest-content-skill (content map), extract-rules subskill (core rules)
- See: `subskills/check-foundation.md`

### Iterative Workflow Subskills

**gather-sources** - Orchestrate iterative source gathering
- Entry point: Called by create-project and resume-project subskills
- Routes to: research-skill, ingest-content-skill, cms-interaction-skill, local handling
- Pattern: Two-checkpoint validation (propose → execute → review → iterate)
- See: `subskills/gather-sources.md`

**extract-rules** - Orchestrate iterative rule extraction
- Entry point: Called by create-project, resume-project, and check-foundation subskills
- Routes to: writing-rules-skill with preview mode
- Pattern: Analyze → preview → approve → extract → review → iterate
- See: `subskills/extract-rules.md`

---

## Technical Details

### Project Structure

```
projects/<project-name>/
├── project.md           # Project manifest
├── sources/             # Project-specific sources only (PDFs, notes)
└── drafts/              # Work in progress
```

**Key principle**: Web content lives in `/sources/` (org KB), not project folders.

### Key Operations

**Add sources to project:**
- Web content: Ingest to `/sources/` first, then reference in project.md
- Local files: Copy to `projects/<name>/sources/`, reference in project.md
- Delegated to: gather-sources subskill for full workflow

**Add targets to project:**
- Existing content: Reference content in `/sources/` within project.md Targets section
- New content: Note planned location in project.md Targets section

**Update project.md:**
- Sources section: Track org KB references and project-specific files
- Targets section: Track content to update or create
- Progress section: Mark completed tasks with dates
- Rules section: List applicable rules for project

**Check project status:**
- Read project.md for context
- Count sources/targets (checked vs unchecked)
- Check Progress section
- Recommend next actions based on gaps

### project.md Format

See `KURT.md` for complete project.md specification.

**Key sections:**
- Goal and Intent Category
- Sources (From Organizational Knowledge Base + Project-Specific Sources)
- Targets (Existing Content to Update + New Content to Create)
- Rules Configuration (Style, Structure, Personas, Publisher, custom types)
- Progress
- Next Steps

---


**Delegates to:**
- **ingest-content-skill** - For fetching web content to `/sources/`
- **writing-rules-skill** - For extracting patterns from content (via extract-rules subskill)
- **content-writing-skill** - For creating/updating target content with lineage
- **research-skill** - For gathering research sources (via gather-sources subskill)
- **cms-interaction-skill** - For CMS content sources (via gather-sources subskill)

**Called by:**
- `/create-project` slash command → create-project subskill
- `/resume-project` slash command → resume-project subskill

---

## Key Principles

1. **Orchestration, not execution** - Subskills delegate operational details to domain skills
2. **Batch operations** - Always use `--url-prefix` for multiple URLs (never loop individual commands)
3. **Progressive disclosure** - Only required info (name/goal) upfront, rest is optional
4. **Foundation first** - Check organizational context before project-specific work
5. **Rule validation** - Check coverage before content work begins
6. **project.md as manifest** - Single source of truth for project state (for now)

---

For workflows and usage examples, see **`CLAUDE.md`**.
For project.md format specification, see **`KURT.md`**.
