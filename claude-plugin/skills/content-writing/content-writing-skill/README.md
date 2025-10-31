# Content Writing Skill

**Unified content creation workflow with comprehensive lineage tracking**

## Overview

The content-writing-skill provides a complete workflow for creating outlines, drafts, and edited content with full traceability from sources to published output. Every piece of content tracks:

- **Sources used** (which documents informed which sections)
- **Reasoning** (why content was written this way)
- **Rule compliance** (style, structure, persona, publisher guidelines)
- **Edit history** (all changes, versions, and sessions)
- **Update patterns** (project-specific transformation patterns)

This enables comprehensible lineage that answers: "Why was this written this way? Which sources informed it? What changes were made and why?"

---

## Quick Start

### 1. Create an Outline
```bash
content-writing-skill outline tutorial-refresh-fusion bigquery-quickstart
```

**Output:** `/projects/tutorial-refresh-fusion/assets/bigquery-quickstart-outline.md`
- YAML frontmatter with source documents, update patterns, rule files
- Detailed section breakdown with source mapping
- Ready for draft generation

### 2. Generate a Draft
```bash
content-writing-skill draft tutorial-refresh-fusion bigquery-quickstart
```

**Output:** `/projects/tutorial-refresh-fusion/assets/bigquery-quickstart-draft.md`
- Enhanced YAML frontmatter with section-level source attribution
- Inline HTML comments at each section documenting sources and reasoning
- Update pattern application comments
- Ready for editing

### 3. Edit Content
```bash
content-writing-skill edit projects/tutorial-refresh-fusion/assets/bigquery-quickstart-draft.md --instructions "Add Fusion limitations callout per Type 5 pattern"
```

**Output:** Updated draft file with:
- Edit session added to YAML history
- Version incremented
- Inline edit comments at changed content
- Complete change traceability

---

## Skill Structure

```
.claude/skills/content-writing-skill/
├── skill.md                          # Main entry point (routes to subskills)
├── subskills/
│   ├── outline-content.md           # Create outlines with source mapping
│   ├── draft-content.md             # Generate drafts with inline lineage
│   └── edit-content.md              # Edit with session history tracking
├── templates/
│   ├── outline-metadata-schema.yaml # YAML schema for outlines
│   ├── draft-metadata-schema.yaml   # YAML schema for drafts
│   └── inline-comment-patterns.md   # HTML comment conventions
└── README.md                         # This file
```

---

## Lineage Tracking

### Two-Level Approach

**1. YAML Frontmatter (High-Level, Queryable)**
- Lists all source documents used
- Maps sources to sections
- Tracks rule compliance
- Records edit session history
- Maintains version history

**2. Inline HTML Comments (Granular, Contextual)**
- Section start comments with sources and reasoning
- Addition/modification comments for changes
- Citation comments for specific claims
- Edit comments marking revisions
- Update pattern application notes

### Example Lineage

**YAML in draft:**
```yaml
---
project: tutorial-refresh-fusion
asset_name: bigquery-quickstart

section_sources:
  prerequisites:
    ground_truth: [/sources/docs.getdbt.com/docs/fusion/install-fusion.md]
    existing_content: [docs.getdbt.com/guides/bigquery]
    update_patterns: [type_2_fusion_installation]

edit_sessions:
  - session_id: edit-session-xyz789
    edited_at: 2025-10-24T17:30:00Z
    instructions: "Add limitations callout"
    sections_modified: [running_models]
---
```

**Inline in draft:**
```markdown
<!-- SECTION: Prerequisites
     Sources: /sources/docs.getdbt.com/docs/fusion/install-fusion.md
     Update Pattern: type_2_fusion_installation
     Reasoning: Fusion has different prerequisites than Core - needs admin privileges for CLI install
     Rules Applied: analytics-engineer-persona (assumes CLI comfort), technical-documentation-style
     Generated: 2025-10-24T14:32:00Z by content-writing-skill/draft
-->

## Prerequisites

To complete this guide, you'll need:
- Understanding of dbt projects and BigQuery
- macOS, Linux, or Windows machine with admin privileges
...

<!-- EDIT: edit-session-xyz789
     Instructions: "Add Fusion limitations callout"
     Change: Added Python models limitation per Type 5 pattern
     Reasoning: Users need upfront knowledge of limitations
     Timestamp: 2025-10-24T17:30:00Z
-->
**Important:** Fusion does not currently support Python models.
<!-- /EDIT -->
```

---

## Querying Lineage

### Find Sources Used
```bash
# High-level: check YAML
head -100 bigquery-quickstart-draft.md | grep "ground_truth:"

# Section-level: check inline comments
grep "<!-- SECTION:" bigquery-quickstart-draft.md

# Specific source mentions
grep -r "/sources/docs.getdbt.com/guides/fusion-quickstart.md" projects/
```

### Find Update Patterns Applied
```bash
# In YAML
grep "update_patterns:" bigquery-quickstart-draft.md

# In inline comments
grep "UPDATE PATTERN: type_1" bigquery-quickstart-draft.md
```

### Check Edit History
```bash
# All edit sessions
head -100 bigquery-quickstart-draft.md | grep -A 10 "edit_sessions:"

# Specific session changes
grep "EDIT: edit-session-xyz789" bigquery-quickstart-draft.md

# Version history
grep -A 5 "version:" bigquery-quickstart-draft.md
```

### Verify Rule Compliance
```bash
# Check which rules were applied
head -100 bigquery-quickstart-draft.md | grep "style_guide:"

# See compliance scores
head -100 bigquery-quickstart-draft.md | grep "rule_compliance:" -A 10
```

---

## Usage Examples

### Tutorial Refresh Project (tutorial-refresh-fusion)

**Scenario:** Updating 23 existing tutorials to include dbt Fusion instructions

**Workflow:**

1. **Create outline for BigQuery quickstart:**
```bash
content-writing-skill outline tutorial-refresh-fusion bigquery-quickstart
```

This creates an outline that:
- Maps ground truth sources (Fusion docs)
- References existing BigQuery tutorial
- Identifies which of the 7 update patterns to apply
- Plans section structure

2. **Generate draft:**
```bash
content-writing-skill draft tutorial-refresh-fusion bigquery-quickstart
```

This creates a draft that:
- Includes inline comments at each section citing sources
- Documents which update pattern was applied where
- Tracks rule compliance (style guide, persona)
- Ready for review

3. **Edit to add missing content:**
```bash
content-writing-skill edit projects/tutorial-refresh-fusion/assets/bigquery-quickstart-draft.md --instructions "Add Type 5 pattern - Fusion limitations callout in running models section"
```

This creates an edit that:
- Adds session to edit history
- Increments version (1.0 → 1.1)
- Adds inline edit comment explaining the change
- Documents which section was modified

4. **Query lineage:**
```bash
# See which update patterns were applied
grep "update_patterns:" projects/tutorial-refresh-fusion/assets/*-draft.md

# Find all tutorials using Type 1 pattern
grep -r "type_1_choose_path" projects/tutorial-refresh-fusion/assets/
```

### Blog Post Creation

**Scenario:** Writing a new blog post about analytics engineering

1. **Create outline (interactive mode):**
```bash
content-writing-skill outline content-hub analytics-engineering-intro --interactive
```

Answer questions about:
- Content angle and unique perspective
- Audience knowledge level
- Key topics to cover

2. **Generate draft:**
```bash
content-writing-skill draft content-hub analytics-engineering-intro
```

Draft includes:
- Section citations from research sources
- Internal link integration
- Brand voice applied per style guide

3. **Edit for clarity:**
```bash
content-writing-skill edit projects/content-hub/assets/analytics-engineering-intro-draft.md --instructions "Simplify technical jargon for beginner audience" --focus clarity
```

---

## Use Cases

### 1. Tutorial Updates (Documented Patterns)
**Example:** tutorial-refresh-fusion project

**Benefits:**
- Track which update pattern applied where
- Ensure consistency across 23 tutorials
- Validate that all patterns were applied
- Trace back to source Fusion docs

### 2. New Content Creation (Source Attribution)
**Example:** Blog posts, guides, case studies

**Benefits:**
- Document research sources
- Cite claims and statistics
- Track internal linking strategy
- Maintain brand voice consistency

### 3. Content Refresh (Edit History)
**Example:** Updating outdated tutorials

**Benefits:**
- See what changed and why
- Track versions over time
- Understand edit rationale
- Rollback if needed

### 4. Multi-Author Collaboration (Accountability)
**Example:** Team content creation

**Benefits:**
- See who made what changes
- Understand reasoning for decisions
- Review edit instructions and outcomes
- Maintain quality standards

---

## Metadata Schemas

### Outline Metadata

**Location:** `templates/outline-metadata-schema.yaml`

**Key fields:**
- `project`, `asset_name`: Identity
- `ground_truth_sources`: Source documents with purposes
- `existing_content_analyzed`: Existing content references
- `update_patterns`: Project-specific transformation patterns
- `section_source_mapping`: Maps each section to its sources

### Draft Metadata

**Location:** `templates/draft-metadata-schema.yaml`

**Key fields:**
- `generation_metadata`: Session ID, timestamp, creator
- `section_sources`: Per-section source attribution with citations
- `rule_compliance`: Style, persona, structure adherence
- `quality_metrics`: Word count, readability, completeness
- `completeness_check`: Outline adherence, gaps, issues

### Inline Comment Patterns

**Location:** `templates/inline-comment-patterns.md`

**Seven patterns:**
1. **Section Start**: Sources, reasoning, rules applied
2. **Addition**: New content with source and rationale
3. **Modification**: Changed content with before/after
4. **Inline Citation**: Specific claim attribution
5. **Update Pattern**: Pattern application with compliance
6. **Edit Session**: Change with session ID and reasoning
7. **Removal**: Deleted content with explanation

---

## Integration with Existing Workflow

### Replaces Slash Commands

| Old Command | New Skill Invocation |
|-------------|---------------------|
| `/outline-content @projects/X/task-breakdown.md task-01` | `content-writing-skill outline X asset-name` |
| `/write-content @projects/X/task-breakdown.md task-02` | `content-writing-skill draft X asset-name` |
| `/edit-content @projects/X/assets/file.md "instructions"` | `content-writing-skill edit projects/X/assets/file.md --instructions "..."` |

### Advantages Over Commands

1. **Unified entry point** with consistent context loading
2. **Enhanced lineage** built into every step
3. **Reusable templates** for metadata consistency
4. **Better validation** of rule files and sources
5. **Skill can invoke skill** for complex workflows

### Backwards Compatibility

Old files created by commands can be edited by this skill:
- Skill will add frontmatter if missing (with user permission)
- Existing inline comments are preserved
- Edit history starts tracking from first skill edit

---

## Best Practices

### For Outlines

✅ **DO:**
- List ALL source documents, even "for inspiration"
- Document WHY each source matters (purpose field)
- Map sources to specific sections
- Identify applicable update patterns

❌ **DON'T:**
- Skip source attribution
- Use vague source purposes ("reference material")
- Leave section_source_mapping empty

### For Drafts

✅ **DO:**
- Add section comments at every major heading
- Use inline citations for specific claims
- Document update pattern applications
- Track word count vs. target

❌ **DON'T:**
- Over-comment (not every paragraph needs attribution)
- Forget to close multi-line comments
- Skip rule compliance assessment

### For Edits

✅ **DO:**
- Provide specific edit instructions
- Review changes before accepting
- Check that inline comments were added
- Verify version incremented

❌ **DON'T:**
- Use vague instructions ("make it better")
- Accept all changes without review
- Edit without understanding original rationale

---

## Troubleshooting

### "Project not found"
**Cause:** Project directory doesn't exist
**Fix:** Check project name spelling, or create project first

### "Outline not found" (when drafting)
**Cause:** No outline file exists
**Fix:** Create outline first with `content-writing-skill outline`, or choose to write without outline (less lineage)

### "Rule file not found"
**Cause:** Referenced rule file doesn't exist
**Fix:** Check paths in project.md, ensure rule files exist, or update references

### "No frontmatter" (when editing)
**Cause:** File created outside this workflow
**Fix:** Choose to add frontmatter, or edit without lineage tracking

### Changes not showing in file
**Cause:** File write failed or wrong file path
**Fix:** Check file permissions, verify path is correct

---

## Future Enhancements

**Potential additions:**
- Automated lineage validation (check all sources exist)
- Lineage visualization (graph of sources → sections)
- Diff view for edits (before/after comparison)
- Bulk operations (edit multiple files with same pattern)
- Export lineage reports (markdown summary of all sources)

---

## Support & Documentation

**Skill files:**
- Main: `.claude/skills/content-writing-skill/skill.md`
- Subskills: `.claude/skills/content-writing-skill/subskills/`
- Templates: `.claude/skills/content-writing-skill/templates/`

**Examples:**
- Tutorial refresh: `/projects/tutorial-refresh-fusion/`
- See project.md for usage in context

**Questions:**
- Check inline comment patterns: `templates/inline-comment-patterns.md`
- Check metadata schemas: `templates/*-metadata-schema.yaml`
- Review subskill documentation in `subskills/*.md`

---

*This skill enables comprehensive, traceable content creation from outline to published content with full lineage at every step.*
