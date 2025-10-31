# Inline Comment Patterns

This document defines standard HTML comment patterns for embedding lineage metadata directly in content files.

**Purpose:** Provide section-level and change-level attribution that stays with the content, making lineage comprehensible when reading the raw markdown.

**Key Principle:** Only comment what changed. Inline comments signal "this section is new or modified" - their absence signals "unchanged from existing content."

---

## When to Add Inline Comments

### ✅ ADD comments for:
1. **New sections** that didn't exist in original content
2. **Modified sections** where existing content was changed
3. **Sections with update patterns applied** (project-specific transformations)
4. **Sections drawing from new ground truth sources**

### ❌ SKIP comments for:
1. **Unchanged sections** copied verbatim from existing content
2. **Sections with no modifications** (even if referenced in YAML)

**Why:** Inline comments are a visual signal that something changed. Their presence = modified, their absence = unchanged. This makes scanning for changes trivial.

**Note:** YAML frontmatter still documents ALL sections (changed and unchanged) for complete source inventory.

---

## Comment Placement Guidelines

### 1. **Section Start Comments**
Place at the beginning of new or modified major sections to document sources and reasoning.

### 2. **Addition/Change Comments**
Place around new content blocks or significant modifications to document what changed and why.

### 3. **Citation Comments**
Place inline after specific claims, data, or quotes to attribute sources.

---

## Pattern 1: Section Start Comment

**When to use:** At the start of new or modified major sections (skip for unchanged sections)

**Template:**
```markdown
<!-- SECTION: [Section Name]
     Sources: [comma-separated list of source file paths]
     Reasoning: [1-2 sentences explaining WHY this section changed or is new]
-->

## [Section Name]

[Section content...]
```

**Example:**
```markdown
<!-- SECTION: Prerequisites
     Sources: /sources/docs.getdbt.com/docs/fusion/install-fusion.md, /sources/docs.getdbt.com/guides/bigquery
     Reasoning: Added Fusion-specific prerequisites (admin privileges, VS Code) while preserving BigQuery setup requirements
-->

## Prerequisites

To complete this guide, you'll need:

- Understanding of dbt projects and BigQuery
- macOS, Linux, or Windows machine with admin privileges
- BigQuery project with appropriate permissions
```

**Removed fields (now in YAML):**
- ~~Update Pattern~~ (in YAML section_sources)
- ~~Rules Applied~~ (in YAML rules section)
- ~~Generated~~ (in YAML generation_metadata)

---

## Pattern 2: Addition Comment

**When to use:** Around new content that wasn't in the original/outline

**Template:**
```markdown
<!-- ADDITION: [update pattern IDs or "new content"]
     Source: [source file path]
     Reasoning: [why this was added]
     [Optional] Persona: [how this serves the target audience]
-->
[New content here]
<!-- /ADDITION -->
```

**Example:**
```markdown
### For BigQuery (using Fusion):

<!-- ADDITION: type_1_choose_path, type_2_fusion_installation
     Source: /sources/docs.getdbt.com/guides/fusion-quickstart.md
     Reasoning: Type 1 pattern - provide path choice for Cloud vs Fusion to serve both audiences
     Persona: Analytics Engineer comfortable with CLI installation
-->
You can use either dbt Cloud or dbt Fusion for this quickstart:

- **dbt Cloud**: Web-based IDE, no local installation required
- **dbt Fusion**: Rust-based CLI with 30x faster performance

This guide focuses on the **dbt Fusion** path.
<!-- /ADDITION -->
```

---

## Pattern 3: Modification Comment

**When to use:** When existing content was changed during draft/edit

**Template:**
```markdown
<!-- MODIFIED: [what changed]
     Original: [brief description of original content]
     Source: [source that informed the change]
     Reasoning: [why the change was made]
     Modified by: [content-writing-skill/draft or content-writing-skill/edit]
     Session: [session-id if from edit]
-->
[Modified content here]
<!-- /MODIFIED -->
```

**Example:**
```markdown
<!-- MODIFIED: Simplified command sequence
     Original: Multi-step installation with separate profile setup
     Source: /sources/docs.getdbt.com/guides/fusion-quickstart.md (lines 36-42)
     Reasoning: Fusion installation is simpler than Core, reduced from 4 steps to 2
     Modified by: content-writing-skill/draft
-->
## Installation Steps

### For macOS & Linux:
```bash
curl -fsSL https://public.cdn.getdbt.com/fs/install/install.sh | sh -s -- --update
exec $SHELL
```
<!-- /MODIFIED -->
```

---

## Pattern 4: Inline Citation Comment

**When to use:** After specific claims, statistics, or direct quotes

**Template:**
```markdown
[Content with claim/statistic] <!-- Source: [file path], [line numbers or section] -->
```

**Example:**
```markdown
The Fusion engine parses projects up to 30x faster than dbt Core <!-- Source: /sources/docs.getdbt.com/blog/dbt-fusion-engine.md, line 28 -->, enabling rapid iteration during development.
```

---

## Pattern 5: Update Pattern Application Comment

**When to use:** When applying a specific update pattern from project documentation (use sparingly - usually covered by section comment)

**Template:**
```markdown
<!-- PATTERN: [pattern ID]
     Applied: [brief description of how pattern manifests here]
-->
[Pattern-affected content]
```

**Example:**
```markdown
<!-- PATTERN: type_4_command_variants
     Applied: Shows both Cloud IDE button and Fusion CLI command for running models
-->
Run your models:

**dbt Cloud:** Click the **Run** button in the IDE

**Fusion CLI:**
```bash
dbtf run --select models/bigquery/*
```
```

**Note:** Often the section start comment already documents patterns (in YAML section_sources). Use this only for additional clarity within a section.

---

## Pattern 6: Edit Session Comment

**When to use:** During edit sessions to mark changes made

**Template:**
```markdown
<!-- EDIT: [session-id]
     Instructions: "[the edit instructions given]"
     Change: [what was changed]
     Reasoning: [why this edit improves the content]
     Rules checked: [any rules validated during edit]
     Timestamp: [YYYY-MM-DDTHH:MM:SSZ]
-->
[Edited content]
<!-- /EDIT -->
```

**Example:**
```markdown
<!-- EDIT: edit-session-xyz789
     Instructions: "Add missing Fusion limitations callout"
     Change: Added Type 5 pattern - Fusion limitations note for Python models
     Reasoning: Users need to know Python models aren't supported before attempting
     Rules checked: technical-documentation-style (clear warnings), analytics-engineer-persona (technical depth)
     Timestamp: 2025-10-24T17:30:00Z
-->

**Important:** Fusion does not currently support Python models. If your project uses Python models, you'll need to use dbt Core or dbt Cloud until Python support is added to Fusion.

<!-- /EDIT -->
```

---

## Pattern 7: Removal Comment

**When to use:** To document content that was removed and why

**Template:**
```markdown
<!-- REMOVED: [what was removed]
     Original content: "[brief excerpt or description]"
     Reasoning: [why it was removed]
     Removed by: [content-writing-skill/draft or edit]
     Session: [session-id if from edit]
-->
```

**Example:**
```markdown
<!-- REMOVED: Legacy dbt Core installation section
     Original content: "pip install dbt-bigquery" instructions and virtual environment setup
     Reasoning: Fusion uses different installation method (curl script), Core instructions no longer relevant for this Fusion-focused tutorial
     Removed by: content-writing-skill/draft
-->
```

---

## Best Practices

### DO:
✅ **Be concise:** Keep comments brief (1-2 sentences for reasoning)
✅ **Be specific:** Reference exact file paths when possible
✅ **Be selective:** Only comment what changed or is new
✅ **Signal changes:** Comment presence = modified, absence = unchanged
✅ **Use short form:** Simplified templates (removed redundant fields)

### DON'T:
❌ **Over-comment:** Skip comments for unchanged sections
❌ **Duplicate YAML:** Don't repeat info already in frontmatter (rules, timestamps, patterns)
❌ **Break markdown:** Ensure comments don't interfere with markdown rendering
❌ **Use ambiguous references:** "See above" or "from docs" - be explicit
❌ **Comment everything:** Let absence of comments signal "unchanged content"

---

## Comment Density Guidelines

**Appropriate comment density:**
- **Section starts:** Only for new or modified major sections (skip unchanged)
- **Additions:** New blocks of significant content (2+ paragraphs)
- **Modifications:** Significant changes to existing content (not minor tweaks)
- **Citations:** Facts, statistics, claims that need attribution
- **Edit sessions:** Each distinct change group from editing

**Expected density:**
- For content updates: 30-50% of sections commented (modified sections only)
- For new content: 70-90% of sections commented (most sections are new)
- Unchanged sections: 0% commented (absence signals no changes)

**Visual scanning:** `grep "<!-- SECTION:"` should show only what changed.

---

## Querying Comments

These patterns enable easy searching:

```bash
# Find all sections
grep "<!-- SECTION:" file.md

# Find all additions from a specific pattern
grep -A 5 "UPDATE PATTERN: type_1" file.md

# Find all edit sessions
grep "<!-- EDIT:" file.md

# See inline citations
grep "<!-- Source:" file.md

# Find content from specific source
grep -r "/sources/docs.getdbt.com/guides/fusion-quickstart.md" projects/
```

---

## Integration with YAML Frontmatter

**Inline comments** provide granular, contextual lineage.
**YAML frontmatter** provides high-level, queryable metadata.

**Use both:**
- YAML: Overall source list, rule compliance summary, edit session history
- Comments: Specific attribution, reasoning at point of change

**Example workflow:**
1. Check YAML to see "What sources were used?"
2. Check section comments to see "Which source for this specific section?"
3. Check inline citations to see "What specific fact came from where?"

---

*Use these patterns consistently to maintain comprehensive, comprehensible lineage throughout the content creation and editing process.*
