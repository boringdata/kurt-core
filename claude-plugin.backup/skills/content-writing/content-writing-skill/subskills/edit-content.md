# Edit Content Subskill

**Purpose:** Interactive content editing with comprehensive session history and change tracking
**Parent Skill:** content-writing-skill
**Output:** Edited file with updated YAML (version history + edit sessions) and inline edit comments

---

## Context Received from Parent Skill

The parent skill provides:
- `$PROJECT_PATH` - Project directory (if derivable from file path)
- `$RULES_*` - Paths to rule directories
- `$ARGUMENTS` - File path and edit arguments

---

## Step 1: Parse Subskill Arguments

Arguments received: $ARGUMENTS

**Expected:**
- File path to edit (required)
- `--instructions "..."`: Edit instructions (required)
- Optional flags:
  - `--section "<name>"`: Edit specific section only
  - `--mode <interactive|batch|review>`: Edit mode
  - `--focus <style|flow|clarity|all>`: Focus area

**Extract:**
- File path
- Edit instructions
- Section name (if specified)
- Mode (default: interactive)
- Focus (default: all)

**Validate:**
- File exists
- File is readable/writable
- Has proper frontmatter (if not, warn)

---

## Step 2: Load Existing Content

### Read File
- Load complete file content
- Parse YAML frontmatter (if exists)
- Extract content body
- Note existing inline comments

### Load Metadata Context
**From YAML frontmatter (if exists):**
- Project name
- Asset name
- Rules applied (style, structure, persona, publisher)
- Previous edit sessions
- Current version number
- Section sources

**If no frontmatter:**
❓ "This file has no frontmatter. Would you like to:
1. Add basic frontmatter before editing
2. Edit without lineage tracking
3. Cancel and add frontmatter manually

Choose (1/2/3):"

### Load Rule Files
If frontmatter references rule files:
- Read style guide
- Read persona
- Read publisher profile

These inform edit quality assessment.

---

## Step 3: Generate Edit Session Metadata

**Create session ID:**
`edit-session-{random-8-char}`

**Record session start:**
```yaml
session_id: edit-session-abc12345
edited_by: content-writing-skill/edit
edited_at: [ISO 8601 timestamp]
instructions: "[the --instructions provided]"
mode: [interactive/batch/review]
focus: [style/flow/clarity/all]
sections_modified: [] # will populate
changes_summary: "" # will populate
```

---

## Step 4: Analyze Content & Detect Improvements

**Based on --focus flag:**

### If focus=style:
- Check against style guide (if available)
- Identify voice/tone inconsistencies
- Find word choice improvements
- Spot brand misalignment

### If focus=flow:
- Analyze transitions
- Check logical progression
- Identify structural issues
- Spot readability problems

### If focus=clarity:
- Find confusing sentences
- Identify jargon for target persona
- Spot unclear explanations
- Find opportunities to simplify

### If focus=all:
- Run all analyses above
- Prioritize by impact

**Apply edit instructions:**
Parse the `--instructions` to understand:
- What specific changes are requested
- Which sections to focus on (if --section specified)
- What success looks like

---

## Step 5: Group Changes

**Organize improvements into groups:**

**Group by:**
- Section/location proximity
- Change category (style/flow/clarity)
- Priority (high/medium/low)

**For each group, document:**
```yaml
group_id: [X]
category: [Style/Flow/Clarity/Content Quality]
priority: [High/Medium/Low]
location: [section name or line range]
issue: "[what needs improvement]"
estimated_impact: "[expected benefit]"
changes: [list of specific modifications]
```

---

## Step 6: Interactive Change Presentation (if mode=interactive)

**For each change group:**

❓ Present change:
```
**Group [X] of [Total]: [Category] ([Priority] Priority)**
**Location:** [Section name or lines]
**Issue:** [Specific problem]
**Impact:** [Expected improvement]

**Current Text:**
```
[Show original text with line numbers]
```

**Suggested Revision:**
```
[Show proposed text with changes highlighted]
```

**Changes Made:**
- [Change 1: specific modification]
- [Change 2: specific modification]
- [Change 3: specific modification]

**Why This Improves:**
- [Benefit 1: how it serves audience better]
- [Benefit 2: how it aligns with style/brand]
- [Benefit 3: how it improves clarity/engagement]

**Rule Alignment:**
- [Reference to style guide requirements]
- [Reference to persona needs]

**Actions:**
A) ACCEPT - Apply this change
B) MODIFY - Let me refine the suggestion
C) REJECT - Skip this change
D) EXPLAIN - Tell me more

Your choice (A/B/C/D):
```

**Process response:**
- **Accept:** Apply changes, add inline comment, continue
- **Modify:** Ask for refinement, regenerate, re-present
- **Reject:** Log rejection reason, continue
- **Explain:** Provide detailed rationale, return to choice

---

## Step 7: Apply Approved Changes

**For each accepted change:**

### A. Make the edit
- Apply text modifications
- Maintain markdown formatting
- Preserve existing inline comments (don't delete)

### B. Add inline edit comment
**Use Pattern 6 from inline-comment-patterns.md:**

```markdown
<!-- EDIT: [session-id]
     Instructions: "[the edit instructions]"
     Change: [what was changed in this specific spot]
     Reasoning: [why this edit improves content]
     Rules checked: [style guide, persona alignment checked]
     Timestamp: [ISO 8601]
-->
[Edited content]
<!-- /EDIT -->
```

**Example:**
```markdown
<!-- EDIT: edit-session-xyz789
     Instructions: "Add missing Fusion limitations callout"
     Change: Added Type 5 pattern - Fusion limitations note for Python models
     Reasoning: Analytics engineers need to know Python models aren't supported before attempting to use them
     Rules checked: technical-documentation-style (clear warnings), analytics-engineer-persona (technical depth)
     Timestamp: 2025-10-24T17:30:00Z
-->

**Important:** Fusion does not currently support Python models. If your project uses Python models, you'll need to use dbt Core or dbt Cloud until Python support is added to Fusion.

<!-- /EDIT -->
```

### C. Track section modified
- Add section name to `sections_modified` list (if not already there)
- Note change in changes_summary

---

## Step 8: Update YAML Frontmatter

### A. Increment version
**If version exists:**
- Parse current version (e.g., "1.2")
- Increment minor version (1.2 → 1.3)

**If no version:**
- Start at 1.0 (was base draft)
- This edit makes it 1.1

### B. Add edit session to history
**Update or add edit_sessions array:**
```yaml
edit_sessions:
  - session_id: [current session ID]
    edited_by: content-writing-skill/edit
    edited_at: [timestamp]
    instructions: "[instructions provided]"
    sections_modified: [list of section names changed]
    changes_summary: "[brief summary of what was improved]"
    changes_applied: [X]
    changes_rejected: [Y]

  - session_id: [previous session]
    # ... previous edits
```

### C. Update version history
**Update or add previous_versions array:**
```yaml
version: [new version number]
previous_versions:
  - version: [previous version]
    timestamp: [when that version was created]
    session_id: [session that created it]
  - version: [even earlier version]
    # ...
```

### D. Update quality metrics (if exists)
```yaml
quality_metrics:
  word_count: [recalculate]
  # ... other metrics updated as appropriate
```

---

## Step 9: Track Progress & Summary

**During editing, display progress:**
```
✅ **Group [X] Applied**
**Changes:** [Brief summary]
**Lines Updated:** [range]
**Content Status:** [X] of [Y] groups reviewed

**Session Progress:**
- Groups Complete: [X]
- Groups Remaining: [Y]
- Changes Applied: [X]
- Changes Rejected: [Y]
- Sections Modified: [list]
```

---

## Step 10: Save Edited Content

**Write file back:**
1. Updated YAML frontmatter (with edit history, version)
2. Content body with inline edit comments
3. Preserve all existing metadata footer

**File structure after edit:**
```markdown
---
# ... existing metadata
version: [new version]
previous_versions:
  - version: [old version]
    timestamp: [timestamp]
    session_id: [previous session if any]

edit_sessions:
  - session_id: [this session]
    edited_by: content-writing-skill/edit
    edited_at: [timestamp]
    instructions: "[instructions]"
    sections_modified: [list]
    changes_summary: "[summary]"
  # ... previous sessions
---

# Content Title

<!-- SECTION: Introduction
     ... original section comment ...
-->

## Introduction

[Original content...]

<!-- EDIT: edit-session-xyz789
     Instructions: "..."
     Change: "..."
     ...
-->
[Edited content]
<!-- /EDIT -->

[More content...]
```

---

## Step 11: Completion Summary

Display:

```markdown
✅ **Edit Session Complete**

**File:** [file path]
**Session ID:** [session-id]
**Version:** [old] → [new]
**Timestamp:** [ISO 8601]

**Changes Applied:**
- **Groups Reviewed:** [X]
- **Changes Applied:** [X]
- **Changes Rejected:** [Y]
- **Sections Modified:** [list of section names]

**Edit Summary:**
[Changes summary from session metadata]

**Quality Impact:**
- **Word Count:** [original] → [new] ([+/-X] words)
- **Estimated Improvement:** [assessment based on changes]

**Lineage Tracking:**
- ✅ Edit session added to YAML history
- ✅ Version incremented and tracked
- ✅ Inline edit comments added at change points
- ✅ Section modifications documented

**View Changes:**
```bash
# See this edit session's changes
grep -A 5 "EDIT: [session-id]" [file]

# View edit history
head -100 [file] | grep -A 10 "edit_sessions:"

# See all sections modified
grep "sections_modified:" [file]

# Check version history
grep -A 5 "version:" [file]
```

**Next Steps:**
1. Review changes in file
2. Further edits if needed:
   `content-writing-skill edit [file] --instructions "..."`

3. Check complete edit lineage:
   `head -200 [file]` to see YAML with full history

**Rollback (if needed):**
- Previous version info available in YAML frontmatter
- Can restore from backup or version control
```

---

## Error Handling

**If file not found:**
```
Error: File not found: [path]

Check path and try again.
```

**If file not writable:**
```
Error: Cannot write to file: [path]

Check permissions and try again.
```

**If no frontmatter and user chose not to add:**
```
Warning: Editing without lineage tracking

Changes will be made but not tracked in metadata.
Consider adding frontmatter for full traceability.

Continue? (Y/n)
```

**If instructions unclear:**
```
Error: Edit instructions unclear or too vague

Please provide specific instructions like:
- "Simplify the prerequisites section for beginners"
- "Add Fusion limitations callout to installation section"
- "Improve transitions between sections 2 and 3"

Not: "Make it better" or "Fix it"
```

---

## Batch Mode (if mode=batch)

**Instead of interactive approval:**
1. Analyze all changes
2. Present complete summary:
   - All groups with proposed changes
   - Estimated overall impact
   - Total changes count

3. Ask for approval once:
   - Apply all
   - Apply by category
   - Return to interactive
   - Cancel

4. Apply all approved changes with single session ID
5. Add inline comments for each change
6. Update YAML once with complete session

---

## Review Mode (if mode=review)

**Analysis only, no changes:**
1. Detect all improvements
2. Generate report:
   - Issues found by category
   - Suggested improvements
   - Priority ranking
   - Estimated impact

3. Save report:
   `[file]-review-[session-id].md`

4. No edits made to original file
5. User can review report and decide to edit

---

## Success Indicators

✅ **Edit session complete** with:
- Changes applied successfully
- File saved with updates
- No markdown formatting broken
- Inline comments added appropriately

✅ **Lineage tracked** with:
- Edit session in YAML history
- Version incremented
- Section modifications documented
- Inline edit comments at changes
- Changes summary clear

✅ **Quality maintained** with:
- Rule compliance checked
- Style consistency preserved
- Content improvements measured
- No regressions introduced

---

## Integration Notes

**This subskill replaces:** `/edit-content` command

**Key enhancements:**
1. **Session history tracking** in YAML
2. **Version management** with increment and history
3. **Inline edit comments** at each change point
4. **Change attribution** with reasoning
5. **Rule validation** during editing

**Lineage enabled:**
- **Version history:** See all versions and when created
- **Edit sessions:** See all edit sessions with instructions
- **Change reasoning:** Inline comments explain why changes made
- **Rule compliance:** Track what rules were checked

**Full traceability:**
```
Project Plan → Outline (sources mapped) →
Draft (inline section attribution) →
Edit v1.1 (session 1 changes) →
Edit v1.2 (session 2 changes) →
Published
```

Every step documented, every source traceable, every change explained.

---

*This subskill provides interactive editing with comprehensive session tracking, enabling complete lineage from initial draft through all revisions to published content.*
