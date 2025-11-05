# Draft Content Subskill

**Purpose:** Generate content drafts with comprehensive inline lineage tracking
**Parent Skill:** content-writing-skill
**Output:** Draft file with enhanced YAML frontmatter + inline HTML comments attributing sources

---

## Context Received from Parent Skill

The parent skill provides:
- `$PROJECT_NAME` - Project name
- `$ASSET_NAME` - Asset/content name
- `$PROJECT_PATH` - Full path to project directory
- `$PROJECT_BRIEF` - Path to project brief/md file
- `$OUTLINE_PATH` - Path to outline file (if exists)
- `$RULES_*` - Paths to rule directories and files
- `$ARGUMENTS` - Any additional arguments

---

## Step 1: Parse Subskill Arguments

Arguments received: $ARGUMENTS

**Expected:**
- Asset name (required) - already in `$ASSET_NAME`
- Optional flags:
  - `--section "<name>"`: Write specific section only
  - `--style-override <name>`: Use different style guide temporarily

**Extract:**
- Section name (if --section flag)
- Style override (if specified)

---

## Step 2: Gather Writing Requirements

### Load Outline
**Primary source:** `$OUTLINE_PATH` or `$PROJECT_PATH/drafts/$ASSET_NAME-outline.md`

**If outline doesn't exist:**
❓ "No outline found for $ASSET_NAME. Would you like to:
1. Create outline first (recommended)
2. Write directly using structure template
3. Cancel and create outline manually

Choose (1/2/3):"

**Extract from outline:**
- Section structure and word count targets
- Key points for each section
- Supporting materials and research
- Internal links and CTAs
- Source-to-section mapping (from YAML)
- Update patterns to apply

### Load Rule Files
Read the rule files referenced in outline YAML:
- Style guide
- Structure template (fallback if no outline)
- Target persona
- Publisher profile

**Extract:**
- Voice and tone characteristics
- Sentence structure preferences
- Persona communication needs
- Brand messaging guidelines

### Load Source Documents
From outline YAML `ground_truth_sources` and `section_source_mapping`:
- Read each source file referenced
- Note key information from each source
- Prepare to integrate/adapt content

---

## Step 3: Calibrate Style & Voice

### Apply Style Guide
**Load:** Style guide file from outline YAML

**Extract and internalize:**
- Voice characteristics (professional, friendly, technical, etc.)
- Tone adjustments for audience
- Sentence structure patterns
- Word choice preferences
- Common phrases to use/avoid

### Apply Persona Requirements
**Load:** Persona file from outline YAML

**Adapt writing for:**
- Technical depth appropriate to audience
- Pain points to address
- Communication preferences
- Examples that resonate

### Apply Publisher Voice
**Load:** Publisher profile

**Ensure:**
- Brand personality reflected
- Company positioning maintained
- Key messaging themes integrated
- Value propositions clear

---

## Step 4: Load Inline Comment Patterns

Read: `/skills/content-writing-skill/templates/inline-comment-patterns.md`

**Prepare to use:**
- Pattern 1: Section Start Comments
- Pattern 2: Addition Comments
- Pattern 4: Inline Citation Comments
- Pattern 5: Update Pattern Application Comments

**Understand:**
- When to place comments
- How to format them
- What information to include
- Comment density guidelines

---

## Step 5: Generate Streamlined YAML Frontmatter

Load schema: `/skills/content-writing-skill/templates/draft-metadata-schema.yaml`

**Create frontmatter:**
```yaml
---
content_type: draft
project: $PROJECT_NAME
asset_name: $ASSET_NAME
created_date: [today's date YYYY-MM-DD]
status: draft_complete
based_on_outline: $OUTLINE_PATH

# Generation
generation:
  created_by: content-writing-skill/draft
  created_at: [ISO 8601 timestamp]
  session_id: [generate unique ID: draft-session-{random}]

# Rules Applied
rules:
  style: [from outline]
  structure: [from outline]
  persona: [from outline]
  publisher: [from outline]

# Section Sources (complete inventory)
# List ALL sections (changed and unchanged) for queryability
section_sources:
  [section-name]:
    ground_truth: [list of source paths, or [] if none]
    existing_content: [list of URLs, or [] if none]
    update_patterns: [list of pattern IDs, or [] if none]

  # Note: Sections with empty arrays are unchanged
  # Sections with sources/patterns will have inline comments
---
```

**What was removed:**
- ❌ rule_compliance section (subjective self-assessments)
- ❌ quality_metrics section (most redundant or calculable)
- ❌ completeness_check section (editorial commentary)

**What remains:**
- ✅ Basic identity (project, asset, dates)
- ✅ Generation metadata (who, when, session)
- ✅ Rules applied (which guidelines followed)
- ✅ Section sources (THE KEY VALUE - source-to-section mapping)

---

## Step 6: Write Content Section-by-Section

### For Each Section in Outline:

#### A. Section Setup

1. **Read section from outline:**
   - Section purpose
   - Key points to cover
   - Word count target
   - Supporting materials
   - Transition requirements

2. **Load section sources:**
   From outline `section_source_mapping`:
   - Ground truth sources for this section
   - Existing content to reference
   - Update patterns to apply

3. **Read relevant source content:**
   - Open each source file
   - Extract relevant information
   - Note specific passages to adapt/cite

#### B. Determine If Section Needs Inline Comment

**Check section characteristics:**
```python
needs_comment = (
    has_ground_truth_sources OR  # New content from sources
    has_update_patterns OR        # Patterns applied
    reasoning_contains("NEW SECTION") OR  # Completely new
    NOT reasoning_contains("Unchanged")   # Modified content
)
```

**✅ ADD comment if:**
- Section has ground_truth sources (new information)
- Section has update_patterns applied
- Section reasoning says "NEW SECTION"
- Section is modified from existing content

**❌ SKIP comment if:**
- Section reasoning contains "Unchanged"
- Section has empty ground_truth AND empty update_patterns
- Content is copied verbatim from existing_content

#### C. Write Section Start Comment (If Needed)

**Use simplified Pattern 1:**

```markdown
<!-- SECTION: [Section Name]
     Sources: [comma-separated source paths]
     Reasoning: [1-2 sentences explaining why this section changed or is new]
-->
```

**Example:**
```markdown
<!-- SECTION: Prerequisites
     Sources: /sources/docs.getdbt.com/guides/fusion-quickstart.md
     Reasoning: Added Fusion prerequisites (admin privileges, VS Code) to existing BigQuery requirements
-->
```

#### D. Write Section Content

**Following outline guidance:**
- Address section purpose
- Cover all key points
- Integrate research and supporting materials
- Maintain style guide voice/tone
- Apply persona-appropriate depth

**Apply update patterns (if applicable):**
- If pattern listed in section_source_mapping, apply it
- Use simplified Pattern 5 to document (sparingly)

**Example for tutorial-refresh-fusion:**
```markdown
<!-- PATTERN: type_1_choose_path
     Applied: Provides choice between Cloud and Fusion installation paths
-->
## Choose Your Installation Path

You can complete this quickstart using:
- **dbt Cloud**: Web-based IDE, no local installation
- **dbt Fusion**: Rust-based CLI with 30x faster performance

This guide uses **dbt Fusion**.
```

**Include inline citations for specific claims:**
Use Pattern 4:
```markdown
Fusion parses projects up to 30x faster <!-- Source: /sources/docs.getdbt.com/blog/dbt-fusion-engine.md, line 28 --> than dbt Core.
```

**Mark additions from sources:**
Use Pattern 2 when adding content not in original:
```markdown
<!-- ADDITION: type_2_fusion_installation
     Source: /sources/docs.getdbt.com/guides/fusion-quickstart.md
     Reasoning: Fusion installation differs from Core, needs new instructions
     Persona: Analytics Engineer comfortable with CLI tools
-->
Run the installation script:
```bash
curl -fsSL https://public.cdn.getdbt.com/fs/install/install.sh | sh -s -- --update
```
<!-- /ADDITION -->
```

#### D. Track Section Completion

**Update draft metadata (in memory):**
- Increment sections_completed
- Add section to sections_list
- Count internal links added
- Note research integrated

---

## Step 7: Integrate Internal Links

**From outline internal linking strategy:**
- Identify where links should be placed
- Ensure natural integration within content flow
- Use proper anchor text from style guide
- Track each link added

**Example:**
```markdown
As we covered in our [Fusion quickstart guide](link), the new engine provides significant performance improvements.
```

**Increment:** `internal_links_added` in metadata

---

## Step 8: Content Integration & Flow

### Verify Cohesion
- Smooth transitions between sections?
- Consistent voice throughout?
- Logical progression maintained?
- Key messages addressed?

### Finalize CTAs
- Place primary CTA per outline strategy
- Add secondary CTAs naturally
- Ensure contextual and compelling

---

## Step 9: Calculate Quality Metrics

**Update YAML frontmatter quality_metrics:**

```yaml
quality_metrics:
  word_count: [count actual words]
  target_word_count: [from outline]
  variance: "[calculate: (actual - target) / target * 100]%"

  readability_level: "[assess: Technical/Intermediate/Accessible for {persona}]"

  sections_completed: [X/Y - count vs. outline]
  sections_list: [list all section names written]

  internal_links_added: [count]
  internal_links_planned: [from outline]

  research_integration: "[X findings integrated, Y examples included]"
```

**Update rule_compliance:**
```yaml
rule_compliance:
  style_guide_adherence: [self-assess 0-100%]
  style_notes: "Applied {voice} tone, {sentence structure}, {key patterns}"

  persona_alignment: "{Persona name} - {key characteristics addressed}"
  persona_notes: "Served {needs}, addressed {pain points}, used {preferred communication}"

  structure_template_followed: true/false
  structure_notes: "[any deviations and why]"

  publisher_voice: "Maintained {brand personality}, integrated {key messaging}"
```

**Update completeness_check:**
```yaml
completeness_check:
  outline_adherence: "[X% of outline followed, note any deviations]"
  key_messages_covered: [list messages from outline addressed]
  success_criteria_met: [list criteria from outline satisfied]
  gaps_or_issues: [note anything incomplete or needing attention]
```

---

## Step 10: Save Draft

**Output path:**
`$PROJECT_PATH/drafts/$ASSET_NAME-draft.md`

**File structure:**
1. Enhanced YAML frontmatter (from Steps 5 & 9)
2. Draft content with inline comments (from Step 6)
3. Metadata footer:
```markdown
---

## Draft Metadata

**Generated:** [timestamp]
**Word count:** [X] words (target: [Y])
**Outline adherence:** [X%]
**Ready for:** Review and editing

**Lineage:**
- Sources catalogued in frontmatter
- Section attribution in HTML comments
- Update patterns documented inline
- Rule compliance tracked

**Next steps:**
1. Review draft for accuracy
2. Edit: `content-writing-skill edit $PROJECT_PATH/drafts/$ASSET_NAME-draft.md --instructions "..."`
3. Check lineage: `grep "<!-- SECTION:" $PROJECT_PATH/drafts/$ASSET_NAME-draft.md`

---
*Template: .claude/skills/content-writing-skill/subskills/draft-content.md*
*Session: [session-id]*
```

### Update Task Breakdown (if exists)
If task breakdown exists:
- Mark draft task as complete
- Update next task (review/edit) to ready

---

## Step 11: Completion Summary

Display:

```markdown
✅ **Draft Created Successfully**

**File:** $PROJECT_PATH/drafts/$ASSET_NAME-draft.md

**Content Metrics:**
- **Word Count:** [X] words (target: [Y], variance: [+/-]Z%)
- **Sections:** [X/Y] completed
- **Internal Links:** [X] added ([Y] planned)
- **Research:** [X] findings integrated

**Lineage Tracking:**
- ✅ YAML frontmatter: Complete source attribution by section
- ✅ Inline comments: Section-level reasoning and citations
- ✅ Update patterns: [X] patterns applied and documented
- ✅ Rule compliance: [X%] style guide adherence

**Quality Assessment:**
- **Readability:** [assessment for persona]
- **Brand Alignment:** [publisher voice maintained]
- **Outline Adherence:** [X%]
- **Persona Fit:** [how it serves target audience]

**Lineage Queries:**
```bash
# View section sources
grep "<!-- SECTION:" $ASSET_NAME-draft.md

# Find specific pattern applications
grep "UPDATE PATTERN: type_1" $ASSET_NAME-draft.md

# See all citations
grep "<!-- Source:" $ASSET_NAME-draft.md

# Check YAML metadata
head -100 $ASSET_NAME-draft.md
```

**Next Steps:**
1. Review draft content
2. Edit as needed:
   `content-writing-skill edit $PROJECT_PATH/drafts/$ASSET_NAME-draft.md --instructions "improve clarity in prerequisites section"`

3. Validate lineage completeness
4. Proceed to review/publishing workflow
```

---

## Error Handling

**If outline not found and user chose to write without:**
- Use structure template as guide
- Create section_source_mapping on the fly
- Warn about limited lineage tracking

**If source files referenced but not found:**
```
Warning: Some source files not accessible:
  - [missing file 1]

Continue writing? Citations may be incomplete.
(Y/n)
```

**If rule files not found:**
```
Error: Required rule file missing: [path]

Cannot generate draft without:
  - Style guide (for voice/tone)
  - Persona (for audience targeting)

Update outline or project.md with correct paths.
```

---

## Success Indicators

✅ **Complete draft** with:
- All outline sections written
- Appropriate depth for persona
- Style guide voice applied
- Internal links integrated
- CTAs placed strategically

✅ **Comprehensive lineage** with:
- YAML section_sources populated
- Inline section comments at every major section
- Update pattern applications documented
- Specific citations for claims/facts
- Rule compliance tracked

✅ **Quality metrics** calculated:
- Word count vs. target
- Readability assessment
- Outline adherence percentage
- Rule compliance scores

---

## Integration Notes

**This subskill replaces:** `/write-content` command

**Key enhancements:**
1. Inline HTML comments for section-level attribution
2. Update pattern application tracking
3. Specific citation comments for facts/claims
4. Enhanced quality metrics calculation
5. Comprehensive rule compliance documentation

**Lineage enabled:**
- Future editors can see WHY content was written this way
- Source documents are traceable to specific sections
- Update patterns are documented at point of application
- Rule compliance is explicit and measurable

**Next in workflow:**
`content-writing-skill edit` will read this draft, its metadata, and inline comments to make informed improvements while tracking edit lineage.

---

*This subskill generates drafts with comprehensive inline lineage, making every section's sources, reasoning, and rule compliance transparent and traceable.*
