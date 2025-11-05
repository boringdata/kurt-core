# Feedback Content Subskill

**Purpose:** Generate persona-based feedback on draft content to identify issues from target audience perspective
**Parent Skill:** content-writing-skill
**Output:** Feedback document with persona-specific analysis and recommendations

---

## Context Received from Parent Skill

The parent skill provides:
- `$PROJECT_NAME` - Project name
- `$ASSET_NAME` - Asset/content name
- `$PROJECT_PATH` - Full path to project directory
- `$PROJECT_BRIEF` - Path to project brief/md file
- `$DRAFT_PATH` - Path to draft file
- `$RULES_*` - Paths to rule directories and files
- `$ARGUMENTS` - Any additional arguments

---

## Step 1: Parse Subskill Arguments

Arguments received: $ARGUMENTS

**Expected:**
- Asset name (required) - already in `$ASSET_NAME`
- Optional flags:
  - `--persona "<name>"`: Limit feedback to specific persona
  - `--focus "<area>"`: Focus on specific aspect (comprehension, depth, length, tone)
  - `--section "<name>"`: Review specific section only

**Extract:**
- Persona filter (if specified)
- Focus area (if specified)
- Section filter (if specified)

---

## Step 2: Load Draft and Extract Context

**Read draft file:** `$DRAFT_PATH` or `$PROJECT_PATH/drafts/$ASSET_NAME-draft.md`

**If draft doesn't exist:**
```
❌ No draft found for $ASSET_NAME

Cannot generate feedback without a draft.

Options:
1. Create draft first: content-writing-skill draft $PROJECT_NAME $ASSET_NAME
2. Specify different asset name
3. Cancel

Choose (1/2/3):
```

**Extract from draft YAML frontmatter:**
- `target_personas` - List of persona files to review from
- `rule_compliance.persona` - Persona files already applied
- `section_structure` - Sections with line numbers
- `ground_truth_sources` - Sources used
- `section_source_mapping` - Which sources informed which sections
- `word_count` - Total and per-section

**Parse draft content:**
- Extract each section with line numbers
- Note inline source citations (HTML comments)
- Identify code examples, warnings, notes
- Track headings and structure

**Display draft summary:**
```
📄 Draft Loaded: $ASSET_NAME

**Stats:**
- Total words: <count>
- Sections: <count>
- Target personas: <list>
- Sources cited: <count>

Ready to generate persona-based feedback.
```

---

## Step 3: Load Target Personas

**From draft YAML, identify target personas:**
- Primary persona (required)
- Secondary personas (if applicable)

**Load persona files from `rules/personas/`:**

For each persona referenced in draft:

```bash
# Example: analytics-engineer.md
persona_file="rules/personas/$(basename $persona_ref)"

if [ ! -f "$persona_file" ]; then
  echo "⚠️  Persona file not found: $persona_file"
  echo "Skipping this persona..."
  continue
fi
```

**Extract from each persona file:**
- **Role/title** - Who they are
- **Knowledge level** - Technical depth, domain expertise
- **Goals/priorities** - What they're trying to accomplish
- **Pain points** - Common frustrations and challenges
- **Communication preferences** - Tone, format, length preferences
- **Common questions** - What they typically need to know
- **Technical assumptions** - What they already know vs need explained

**Display loaded personas:**
```
🎭 Personas Loaded (2):

1. **Analytics Engineer** (Primary)
   - Knowledge: Intermediate SQL, basic data modeling
   - Goals: Build reliable data pipelines
   - Preferences: Code examples, practical steps

2. **Data Scientist** (Secondary)
   - Knowledge: Advanced statistics, Python/R
   - Goals: Extract insights quickly
   - Preferences: Concise, exploration-focused

Generating feedback from each perspective...
```

---

## Step 4: Generate Persona-Specific Feedback

For each target persona, analyze the draft from their unique perspective.

### Analysis Framework (Per Persona)

**A. Comprehension Issues**

Read through each section and identify:
- **Unexplained jargon** - Technical terms used without definition
- **Missing context** - Assumptions about prior knowledge
- **Unclear references** - "This," "it," "that" without clear antecedent
- **Logical gaps** - Steps or concepts skipped

For each issue found:
```
❌ **Comprehension Issue** (Section: <name>, Lines: <range>)
- **Problem:** <specific unclear element>
- **Impact:** <how this affects this persona>
- **Fix:** <concrete suggestion>
```

**B. Technical Depth Assessment**

Evaluate if content matches persona's knowledge level:
- **Too advanced** - Uses concepts beyond their typical expertise
- **Too basic** - Over-explains things they already know
- **Appropriate** - Right level for this persona

For depth mismatches:
```
⚠️ **Depth Mismatch** (Section: <name>, Lines: <range>)
- **Issue:** <too advanced / too basic>
- **Example:** <specific text>
- **Impact:** <how this affects this persona>
- **Fix:** <adjust depth appropriately>
```

**C. Missing Information**

From persona's perspective, identify gaps:
- **Prerequisites not stated** - What they need before starting
- **Expected information absent** - What they'd expect to see but isn't there
- **Incomplete steps** - Procedures missing critical details
- **No validation** - Can't verify they did it correctly

For each gap:
```
❌ **Critical Gap** (Section: <name>)
- **Missing:** <what information is absent>
- **Impact:** <how this blocks or confuses this persona>
- **Fix:** <what to add and where>
```

**D. Tone & Style Issues**

Evaluate against persona's communication preferences:
- **Too formal/informal** - Doesn't match their expected tone
- **Too procedural/exploratory** - Wrong framing for their goals
- **Passive/active voice** - Against their preferences

For tone mismatches:
```
⚠️ **Tone Issue** (Section: <name>, Lines: <range>)
- **Current tone:** <description>
- **Persona preference:** <what this persona expects>
- **Impact:** <how this affects engagement>
- **Fix:** <reframe suggestion>
```

**E. Length Assessment**

Compare against persona's preferences:
- **Expected word count** - From persona profile
- **Actual word count** - From draft
- **Verdict** - Too long, too short, or appropriate

```
📏 **Length Assessment**

**Current:** <word count> words
**Expected for <persona>:** <range> words
**Verdict:** <✓ Appropriate / ⚠️ Too long / ⚠️ Too short>

<If mismatch, explain why and suggest cuts/additions>
```

**F. Structure & Flow**

From persona's mental model:
- **Sections in logical order** - Match their learning/task flow
- **Information architecture** - Easy to scan and find what they need
- **Progressive disclosure** - Basics first, then advanced

For structure issues:
```
⚠️ **Flow Issue**
- **Problem:** <what's out of order or hard to navigate>
- **Persona impact:** <why this matters for this persona>
- **Fix:** <restructuring suggestion>
```

---

## Step 5: Generate Feedback Document

**Create feedback file:** `$PROJECT_PATH/feedback/$ASSET_NAME-feedback.md`

```bash
mkdir -p "$PROJECT_PATH/feedback"
feedback_file="$PROJECT_PATH/feedback/$ASSET_NAME-feedback.md"
```

**Structure of feedback document:**

```markdown
# Feedback: <Asset Name>

**Generated:** <timestamp>
**Draft:** <path to draft>
**Draft Version:** <version from YAML>
**Target Personas:** <list with primary/secondary labels>

---

<FOR EACH PERSONA>

## <Persona Name> Persona Feedback

**Overall Assessment:** <1-2 sentence summary>

**Alignment Score:** <percentage> aligned with this persona's needs

### Section-Level Issues

<FOR EACH SECTION WITH ISSUES>

**<Section Name> (Lines <start>-<end>)**

<LIST ALL ISSUES FOUND>
- ❌ Critical issues (blocks understanding or task completion)
- ⚠️ High priority (degrades experience significantly)
- ℹ️ Nice to have (improvements but not blockers)

</FOR EACH SECTION>

### Overall Depth & Length Assessment

**Technical Depth:** <Too advanced / Too basic / ✓ Appropriate>
<Explanation>

**Length:** <Too long / Too short / ✓ Appropriate>
- Current: <word count>
- Expected: <range>
<Explanation if mismatch>

**Code Examples:** <Assessment>
**Visual Aids:** <Assessment if applicable>

### Tone & Style

**Current tone:** <description>
**Expected tone:** <from persona profile>
**Verdict:** <✓ Aligned / ⚠️ Misaligned>
<Explanation if misaligned>

---

</FOR EACH PERSONA>

## Cross-Persona Analysis

<IF MULTIPLE PERSONAS>

### Conflicting Needs

<Identify where personas have different requirements>
- **Data Scientist wants:** <requirement>
- **Analytics Engineer needs:** <conflicting requirement>
- **Recommendation:** <how to balance>

### Shared Issues

<Issues that affect all personas>
1. <Issue affecting everyone>
2. <Another universal issue>

</IF MULTIPLE PERSONAS>

---

## Summary & Recommendations

### Critical Issues (Fix Before Publishing)

<Numbered list of must-fix issues>
1. <Issue> (<which personas affected>)
2. <Issue> (<which personas affected>)

### High Priority

<Issues that significantly impact quality>
3. <Issue> (<which personas affected>)
4. <Issue> (<which personas affected>

### Nice to Have

<Improvements but not blockers>
5. <Issue> (<which personas affected>)
6. <Issue> (<which personas affected>)

### Persona Alignment Summary

- **<Persona 1>:** <percentage>% aligned (<summary>)
- **<Persona 2>:** <percentage>% aligned (<summary>)

### Recommended Next Steps

**Option A: Apply All Critical Fixes**
```
content-writing-skill edit projects/<project>/drafts/<asset>-draft.md --instructions "
Apply critical fixes from feedback:
1. <Fix description>
2. <Fix description>
3. <Fix description>
"
```

**Option B: Selective Fixes**
Review feedback and choose which issues to address.

**Option C: Re-review After Edits**
Apply some fixes, then run feedback again to check progress.

---

## Metadata

**Feedback Session ID:** feedback-<timestamp>
**Personas Reviewed:** <count>
**Total Issues Found:** <count>
  - Critical: <count>
  - High Priority: <count>
  - Nice to Have: <count>
**Draft Word Count:** <count>
**Review Duration:** <estimate based on draft length>
```

**Write feedback document** with all analysis above.

---

## Step 6: Update Draft Metadata

**Read current draft YAML frontmatter.**

**Add feedback session to draft:**

```yaml
feedback_sessions:
  - session_id: feedback-<timestamp>
    timestamp: <ISO 8601>
    personas_reviewed:
      - <persona-1-slug>
      - <persona-2-slug>
    issues_found:
      critical: <count>
      high_priority: <count>
      nice_to_have: <count>
    feedback_file: projects/<project>/feedback/<asset>-feedback.md
    alignment_scores:
      <persona-1-slug>: <percentage>
      <persona-2-slug>: <percentage>
```

**Append to existing feedback_sessions array** (if previous sessions exist).

**Update draft version:**
```yaml
version: <current>.<increment>  # e.g., 1.0 → 1.1
```

**Update last_modified:**
```yaml
last_modified: <timestamp>
```

**Write updated YAML frontmatter** back to draft file.

---

## Step 7: Display Results to User

**Show summary:**

```
✅ Persona-Based Feedback Complete

📊 **Analysis Summary:**

**Personas Reviewed:** <count>
  - <Persona 1> (<primary/secondary>)
  - <Persona 2> (<primary/secondary>)

**Issues Identified:**
  - ❌ Critical: <count>
  - ⚠️ High Priority: <count>
  - ℹ️ Nice to Have: <count>

**Alignment Scores:**
  - <Persona 1>: <percentage>% aligned
  - <Persona 2>: <percentage>% aligned

**Feedback saved to:**
projects/<project>/feedback/<asset>-feedback.md

---

**Critical Issues Found (<count>):**

1. <Brief description> (affects <persona>)
   - Section: <name>, Lines: <range>
   - Fix: <one-line summary>

2. <Brief description> (affects <persona>)
   - Section: <name>, Lines: <range>
   - Fix: <one-line summary>

<...>

---

**What would you like to do next?**

a) **Apply critical fixes** - I'll edit the draft with recommended changes
b) **Review full feedback** - Show/read the detailed feedback file
c) **Selective edits** - Tell me which specific issues to fix
d) **Continue without changes** - Feedback noted, but proceed as-is

Choose (a/b/c/d):
```

**Wait for user response.**

---

## Step 8: Handle User Response

### If (a) - Apply critical fixes

**Generate edit instructions** from critical issues:

```bash
# Collect all critical fixes into instructions
edit_instructions="Apply critical fixes from persona feedback:

$(grep -A 3 "❌ \*\*Critical" "$feedback_file" | \
  awk 'extract fix suggestions' | \
  format as numbered list)
"

# Invoke edit subskill
content-writing-skill edit "$PROJECT_NAME" "$ASSET_NAME" --instructions "$edit_instructions"
```

After edit completes:
```
✅ Critical fixes applied

Edited draft: projects/<project>/drafts/<asset>-draft.md

**Recommended:** Run feedback again to verify fixes resolved issues
```

### If (b) - Review full feedback

**Display or read feedback file:**

```bash
cat "$feedback_file"
# Or use Read tool to show to user
```

Then re-prompt with options (a/c/d).

### If (c) - Selective edits

**Ask user which issues to fix:**

```
Which issues would you like me to address?

You can specify by number (e.g., "1, 3, 5") or describe:

Critical Issues:
1. <issue description>
2. <issue description>
3. <issue description>

High Priority:
4. <issue description>
5. <issue description>

Enter issue numbers or describe what to fix:
```

Wait for user input, then generate targeted edit instructions and invoke edit subskill.

### If (d) - Continue without changes

```
Feedback saved for future reference.

You can apply fixes later with:
  content-writing-skill edit projects/<project>/drafts/<asset>-draft.md

Or re-run feedback after manual edits:
  content-writing-skill feedback <project> <asset>
```

---

## Error Handling

### No Personas Found

```
⚠️  No target personas specified in draft

Cannot generate feedback without knowing target audience.

Options:
1. Add personas to draft YAML frontmatter
2. Specify persona manually: --persona "analytics-engineer"
3. Cancel feedback

The draft should have:
```yaml
target_personas:
  - primary: rules/personas/analytics-engineer.md
  - secondary: rules/personas/data-scientist.md
```

Choose (1/2/3):
```

### Persona File Not Found

```
⚠️  Persona file missing: rules/personas/<name>.md

This persona is referenced in the draft but the file doesn't exist.

Options:
1. Extract this persona first: writing-rules-skill persona --auto-discover
2. Remove from draft and skip this persona
3. Cancel feedback

Choose (1/2/3):
```

### Draft Too Short for Meaningful Feedback

```
⚠️  Draft is very short (<word count> words)

Persona-based feedback works best for drafts >500 words.

Options:
1. Continue anyway (limited feedback)
2. Expand draft first
3. Cancel

Choose (1/2/3):
```

---

## Integration Points

**Called from project-management-skill:**
After draft creation, recommend feedback:
```
Draft complete!

Recommended: Review persona-based feedback
  content-writing-skill feedback <project> <asset>

This checks if the draft works for your target audience.
```

**Called from content-writing-skill main:**
Route feedback operation to this subskill.

**Integration with edit subskill:**
Feedback generates edit instructions that can be directly applied via edit subskill.

---

## Success Criteria

✅ **Feedback generation successful** when:
- All target personas analyzed
- Section-level issues identified with line numbers
- Concrete fix suggestions provided
- Alignment scores calculated
- Feedback document created
- Draft metadata updated with feedback session

✅ **High quality feedback** when:
- Issues are specific (not vague)
- Fixes are actionable (not generic)
- Persona perspective is clear (not generic "users")
- Critical vs nice-to-have properly prioritized
- Cross-persona conflicts identified (if applicable)

---

*This subskill enables quality review from target audience perspective, catching issues before publication and ensuring content serves its intended readers effectively.*
