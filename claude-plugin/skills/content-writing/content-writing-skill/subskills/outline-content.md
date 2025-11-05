# Outline Content Subskill

**Purpose:** Create detailed content outlines with comprehensive lineage tracking
**Parent Skill:** content-writing-skill
**Output:** Outline file with enhanced YAML frontmatter mapping sources to sections

---

## Context Received from Parent Skill

The parent skill provides:
- `$PROJECT_NAME` - Project name
- `$ASSET_NAME` - Asset/content name
- `$PROJECT_PATH` - Full path to project directory
- `$PROJECT_BRIEF` - Path to project brief/md file
- `$RULES_*` - Paths to rule directories and files
- `$ARGUMENTS` - Any additional arguments (--interactive, etc.)

---

## Step 1: Parse Subskill Arguments

Arguments received: $ARGUMENTS

**Expected:**
- Asset name (required) - already in `$ASSET_NAME`
- Optional flags:
  - `--interactive`: Enable guided outline development
  - `--template-override <name>`: Use specific structure template

**Extract from arguments:**
- Interactive mode flag
- Template override name (if specified)

---

## Step 2: Gather Content Requirements

### Load Project Context
Read project brief: `$PROJECT_BRIEF`

**Extract:**
- Project goals and objectives
- Content strategy and themes
- Target audiences
- Success metrics

### Load Task Information (if exists)
Check for: `$PROJECT_PATH/task-breakdown.md`

If exists, find outline task for this asset:
- Task ID
- Task description and requirements
- Dependencies
- Success criteria

### Determine Rule Files

**From Project or Task:**
- Which style guide to use?
- Which structure template to use?
- Which target persona?
- Publisher profile (default: rules/publisher/publisher-profile.md)

**If not specified in project/task:**
Ask user to select from available rules:
- List style guides in `rules/style/`
- List structure templates in `rules/structure/`
- List personas in `rules/personas/`

---

## Step 3: Load and Analyze Rule Files

### Read Structure Template
Path: Determined in Step 2 or from `--template-override`

**Extract:**
- Structural outline (sections and flow)
- Section purposes
- Typical length guidelines
- Required elements

**Adapt for this asset:**
- Customize section purposes for asset's objectives
- Adjust scope based on word count target
- Consider audience needs from persona

### Read Target Persona
Path: Determined in Step 2

**Extract:**
- Audience characteristics and needs
- Pain points to address
- Communication preferences
- Technical depth expectations

### Read Style Guide
Path: Determined in Step 2

**Extract:**
- Voice and tone characteristics
- Key messaging themes
- Writing patterns to follow

### Read Publisher Profile
Path: `$RULES_PUBLISHER` or rules/publisher/publisher-profile.md

**Extract:**
- Brand positioning
- Company values and messaging
- Voice characteristics

---

## Step 4: Gather Source Documents

### Identify Ground Truth Sources
**From project directory:**
Check: `$PROJECT_PATH/sources/` or `/sources/`

**From project brief/md:**
Look for listed source documents

**Record:**
- Path to each source file
- Purpose of each source (why it's relevant)

### Identify Existing Content
**From project brief/md:**
Look for existing content to analyze or update

**Record:**
- URLs or paths to existing content
- What to learn from it (structure, messaging, etc.)

### Load Update Patterns (Project-Specific)
**For projects like tutorial-refresh-fusion:**
Check project.md for defined update patterns (e.g., "Type 1: Add Choose Your Path Section")

**Record:**
- Pattern IDs
- Pattern descriptions
- Where each pattern should apply

---

## Step 5: Interactive Outline Development (if --interactive)

If `--interactive` flag used:

❓ **Content Focus Questions:**
```
Let's develop a focused outline for: $ASSET_NAME

**Content Angle:**
- What's the primary angle or unique perspective for this piece?
- What key insight or takeaway should readers have?
- How does this connect to your broader content themes?

**Audience Consideration:**
- What level of prior knowledge should we assume?
- What are the main objections or questions to address?
- What action do you want readers to take after reading?

**Content Scope:**
- What topics are essential vs. nice-to-have?
- Are there specific examples or case studies to include?
- What internal content should we reference or link to?
```

**Capture responses and integrate into outline planning.**

---

## Step 6: Map Sources to Sections

**For each section in the structure template:**

1. **Identify relevant sources:**
   - Which ground truth sources inform this section?
   - Which existing content provides inspiration?
   - Which update patterns apply?

2. **Document reasoning:**
   - Why these sources for this section?
   - What specific information/approach to extract?

3. **Create section-source mapping:**
```yaml
section_source_mapping:
  prerequisites:
    ground_truth:
      - /sources/docs.getdbt.com/docs/fusion/install-fusion.md
    existing_content:
      - docs.getdbt.com/guides/bigquery
    update_patterns:
      - type_2_fusion_installation
    reasoning: "Fusion has different prerequisites than Core; existing BigQuery guide needs updates"
    word_count: 150
```

---

## Step 7: Create Detailed Outline

### Load Outline Template
Read: `/skills/content-writing-skill/templates/outline-metadata-schema.yaml`

### Generate Enhanced YAML Frontmatter

**Required fields:**
```yaml
---
content_type: outline
project: $PROJECT_NAME
asset_name: $ASSET_NAME
created_date: [today's date]
status: outline_complete

# Project Context
project_brief: $PROJECT_BRIEF
task_id: [from task breakdown if exists]
next_task_id: [draft task ID if known]

# Rules Applied
style_guide: [path to style guide]
structure_template: [path to structure template]
target_persona: [path to persona]
publisher_profile: [path to publisher profile]

# Source Documents (Enhanced)
ground_truth_sources:
  - path: [source file path]
    purpose: "[why this source matters]"

existing_content_analyzed:
  - url: [existing content URL]
    purpose: "[what to learn from it]"

# Update Patterns (if applicable)
update_patterns:
  - pattern_id: [e.g., type_1_choose_path]
    description: "[what this pattern does]"
    applies_to_sections: [list of sections]

# Content Specifications
word_count_target: [X]
primary_objective: "[specific goal]"
success_metric: "[how to measure success]"
target_audience: "[persona description]"
content_depth: "[level of detail]"

# Section-Source Mapping
section_source_mapping:
  [section-1]:
    ground_truth: [list]
    existing_content: [list]
    update_patterns: [list]
    word_count: [X]
---
```

### Create Outline Body

Following the structure template, create detailed section breakdown:

**For each section:**
- Section title and purpose
- Word count target
- Key points to cover
- Supporting materials (research, examples, links)
- Content treatment approach
- Transition to next section

**Include:**
- Opening hook strategy
- Section-by-section breakdown
- Conclusion/CTA strategy
- Internal linking plan
- Research integration plan
- Quality assurance checklist

---

## Step 8: Validation & Quality Check

### Structure Quality
- [ ] Logical flow and progression
- [ ] All template requirements met
- [ ] Audience needs addressed
- [ ] Word count distribution reasonable

### Content Completeness
- [ ] All key messages covered
- [ ] Research findings integrated
- [ ] Internal linking strategy complete
- [ ] CTA placement strategic

### Lineage Completeness (NEW)
- [ ] All source documents listed in YAML
- [ ] Each section mapped to sources
- [ ] Update patterns identified and mapped
- [ ] Rule files referenced correctly

**If issues identified:**
❓ Present issues and options:
- Refine automatically
- Work through improvements interactively
- Proceed as-is
- Start over

---

## Step 9: Save Outline

**Output path:**
`$PROJECT_PATH/drafts/$ASSET_NAME-outline.md`

**File structure:**
1. Enhanced YAML frontmatter (from Step 7)
2. Outline body (from Step 7)
3. Metadata footer:
```markdown
---
*Generated: [timestamp]*
*Ready for: content-writing-skill draft $PROJECT_NAME $ASSET_NAME*
*Template: .claude/skills/content-writing-skill/subskills/outline-content.md*
```

### Update Task Breakdown (if exists)
If `$PROJECT_PATH/task-breakdown.md` exists:
- Mark outline task as complete
- Update next task (draft) status to "ready"
- Add reference to outline file

---

## Step 10: Completion Summary

Display summary:

```markdown
✅ **Outline Created Successfully**

**File:** $PROJECT_PATH/drafts/$ASSET_NAME-outline.md
**Word Count Planned:** [X] words across [Y] sections
**Sources Mapped:** [X] ground truth + [Y] existing content
**Update Patterns:** [list if applicable]

**Lineage Tracking:**
- ✅ Source documents catalogued
- ✅ Sections mapped to sources
- ✅ Update patterns identified
- ✅ Rule compliance planned

**Next Steps:**
1. Review outline structure and flow
2. Generate draft:
   `content-writing-skill draft $PROJECT_NAME $ASSET_NAME`

3. Check source mapping:
   `grep "section_source_mapping:" $PROJECT_PATH/drafts/$ASSET_NAME-outline.md`

**Writer Instructions:**
- Follow section structure and word count targets
- Integrate all planned research and references
- Maintain tone and style specified in outline
- Apply update patterns as mapped
- Include all planned CTAs and internal links
```

---

## Step 11: Feedback Collection (Optional - Every 5th Execution)

Check if we should prompt for feedback:

```bash
# Get execution count from feedback database
EXECUTION_COUNT=$(sqlite3 .kurt/kurt.sqlite "
    SELECT COUNT(*) + 1 FROM feedback_events
    WHERE operation = 'outline'
    AND skill_name = 'content-writing-skill'
" 2>/dev/null || echo "1")

# Get feedback frequency from config
FEEDBACK_FREQ=$(yq eval ".feedback.prompt_frequency" .kurt/feedback/feedback-config.yaml 2>/dev/null || echo "5")

# Check if feedback is enabled
FEEDBACK_ENABLED=$(yq eval ".feedback.enabled" .kurt/feedback/feedback-config.yaml 2>/dev/null || echo "true")

# Prompt for feedback if enabled and it's time
if [ "$FEEDBACK_ENABLED" = "true" ] && [ $((EXECUTION_COUNT % FEEDBACK_FREQ)) -eq 0 ]; then
    echo ""
    echo "───────────────────────────────────────────────────────"
    echo ""
    echo "Would you like to rate this outline? (Y/n): "
    read -r FEEDBACK_RESPONSE

    if [ "$FEEDBACK_RESPONSE" != "n" ] && [ "$FEEDBACK_RESPONSE" != "N" ]; then
        # Invoke feedback skill
        feedback-skill rate \
            --asset-path "$PROJECT_PATH/drafts/$ASSET_NAME-outline.md" \
            --asset-type "outline" \
            --project-id "$PROJECT_NAME" \
            --skill-name "content-writing-skill" \
            --operation "outline" \
            --execution-count "$EXECUTION_COUNT" \
            --prompted true
    fi
fi
```

**Notes:**
- Feedback prompts occur every 5th execution by default (configurable)
- Users can skip the prompt without affecting workflow
- Users can always rate explicitly later: `feedback-skill rate --asset-path <path>`
- Feedback data helps improve writing rules over time

---

## Error Handling

**If structure template not found:**
```
Error: Structure template not found: [path]

Available templates:
  [list files in rules/structure/]

Specify with: --template-override <name>
Or update project.md with template reference
```

**If source files not found:**
```
Warning: Some source files not found:
  - [missing file 1]
  - [missing file 2]

Continue anyway? Sources can be added to outline manually.
(Y/n)
```

**If no persona specified:**
```
Error: No target persona specified

Available personas:
  [list files in rules/personas/]

Update project.md with:
  target_persona: rules/personas/[filename].md
```

---

## Success Indicators

✅ **Complete outline created** with:
- Detailed section breakdown with word counts
- Clear purpose and key points for each section
- Research and supporting materials integrated
- Internal linking strategy planned
- Logical flow aligned with structure template

✅ **Enhanced lineage tracking** with:
- All source documents catalogued
- Section-to-source mapping complete
- Update patterns identified and assigned
- Rule files referenced
- Reasoning documented

---

## Integration Notes

**This subskill replaces:** `/outline-content` command

**Key enhancements over command:**
1. Comprehensive source tracking in YAML
2. Section-to-source mapping
3. Update pattern identification
4. Rule file validation
5. Structured metadata for queries

**Next in workflow:**
`content-writing-skill draft` will read this outline and its metadata to generate draft with inline lineage comments.

---

*This subskill creates outlines with comprehensive lineage tracking, enabling full traceability from plan to published content.*
