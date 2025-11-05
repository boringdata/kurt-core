# Extract Foundation Subskill

**Purpose:** Extract foundation rules (publisher profile, style guide, personas) from content
**Parent Skill:** onboarding-skill
**Pattern:** Check content → Extract rules → Validate → Update profile
**Output:** Rule files in `rules/` directory, updated profile.md

---

## Overview

This subskill extracts the core rules needed for consistent content creation:

1. Publisher profile (company context and brand voice)
2. Style guide (writing patterns and tone)
3. Target personas (audience profiles)

These "foundation rules" define your organization's content identity and are used across all projects.

**Key principles:**
- Optional (can skip and extract later)
- Requires fetched content (minimum 5-10 documents recommended)
- Delegates extraction logic to project-management-skill's extract-rules subskill
- Validates extracted rules exist

---

## Progress Checklist

Copy this checklist and track your progress as you work:

- [ ] Check content is available (minimum 5 documents)
- [ ] Explain what foundation rules are
- [ ] Ask if user wants to extract rules
- [ ] Delegate to extract-rules subskill
- [ ] Validate rules were extracted
- [ ] Update profile.md with rule paths

---

## Step 1: Check Prerequisites

**Validation:** Check if sufficient content is available

Run: `kurt content list --with-status FETCHED | wc -l`

If less than 5 documents:
```
⚠️  Insufficient content for reliable rule extraction

Found: {{COUNT}} documents
Recommended: 5-10 documents minimum

Foundation rules work best with diverse content samples.

Would you like to:
a) Continue anyway (rules may be less reliable)
b) Add more content first
c) Skip rule extraction

Choose: _
```

If (a): Display warning and continue to Step 2.
If (b): Exit and recommend user runs map-content to add more sources.
If (c): Exit with message "Skipped. Run /update-profile to extract rules later."

Only proceed to Step 2 when user accepts risk or has sufficient content.

---

## Step 2: Explain Foundation Rules

Display explanation:

```
───────────────────────────────────────────────────────
Extract Foundation Rules
───────────────────────────────────────────────────────

Foundation rules capture your organization's content identity:

✓ Publisher Profile - Company context, brand principles,
  content goals (used across all content)

✓ Style Guide - Writing voice, tone, formatting patterns
  (ensures consistency)

✓ Personas - Target audience profiles with goals, pain points,
  and preferences (guides content strategy)

These rules are extracted by analyzing your existing content
and will be used for all future content projects.

Extraction takes ~3-5 minutes.

───────────────────────────────────────────────────────

Would you like to extract foundation rules? (y/n):
```

Wait for user response.

If no:
```
Skipped. You can extract foundation rules later with:
  /update-profile → Foundation Rules
```

Exit.

If yes: Continue to Step 3.

---

## Step 3: Extract Rules

Delegate to project-management-skill's extract-rules subskill:

```
Analyzing your content to extract foundation rules...
```

Read and execute the extract-rules subskill from project-management-skill with foundation-only mode.

The extract-rules subskill will:
1. Analyze fetched content
2. Extract publisher profile
3. Extract style guide
4. Extract personas
5. Create rule files in `rules/` directory
6. Show preview and get user approval for each

**Validation:** Verify rules were extracted

After extract-rules returns, check that rule files exist:
- Publisher: `rules/publisher/publisher-profile.md`
- Style: Check for files in `rules/style/*.md`
- Personas: Check for files in `rules/personas/*.md`

Count extracted rules:
- Publisher: exists (yes/no)
- Style guides: count files
- Personas: count files

If no rules were extracted:
```
⚠️  No rules were extracted

This might be because:
- Extraction was cancelled
- Content didn't have clear patterns
- Insufficient content diversity

Would you like to:
a) Retry extraction
b) Skip - I'll extract rules later

Choose: _
```

If retry: Return to beginning of Step 3.
If skip: Continue to Step 4 with no rules extracted.

Only proceed to Step 4 when extraction completes (with or without rules).

---

## Step 4: Display Summary

Show what was extracted:

```
───────────────────────────────────────────────────────
Foundation Rules Extracted
───────────────────────────────────────────────────────

{{#if PUBLISHER_EXISTS}}
✓ Publisher Profile
  rules/publisher/publisher-profile.md
{{else}}
⚠ Publisher Profile - Not extracted
{{/if}}

{{#if STYLE_COUNT > 0}}
✓ Style Guide ({{STYLE_COUNT}} style{{STYLE_COUNT > 1 ? "s" : ""}})
{{#each STYLE_FILES}}
  {{this}}
{{/each}}
{{else}}
⚠ Style Guide - Not extracted
{{/if}}

{{#if PERSONA_COUNT > 0}}
✓ Personas ({{PERSONA_COUNT}} persona{{PERSONA_COUNT > 1 ? "s" : ""}})
{{#each PERSONA_FILES}}
  {{this}}
{{/each}}
{{else}}
⚠ Personas - Not extracted
{{/if}}

{{#if ANY_MISSING}}

You can extract missing rules later with:
  /update-profile → Foundation Rules
{{/if}}
```

---

## Step 5: Update Profile

Update the "Foundation Rules" section in `.kurt/profile.md`:

For publisher profile:
- If extracted: Show path and status
- If not: Show "Not yet extracted" with instructions

For style guides:
- List each style file with path
- If none: Show "None yet" with instructions

For personas:
- List each persona file with path
- If none: Show "None yet" with instructions

Update profile.md:

```markdown
## Foundation Rules

### Publisher Profile
{{#if PUBLISHER_EXISTS}}
✓ Extracted

File: rules/publisher/publisher-profile.md
{{else}}
Not yet extracted.

Run: /update-profile → Foundation Rules
{{/if}}

### Style Guides
{{#if STYLE_COUNT > 0}}
Count: {{STYLE_COUNT}}

{{#each STYLE_FILES}}
- {{basename}} ({{path}})
{{/each}}
{{else}}
None yet.

Run: /update-profile → Foundation Rules
{{/if}}

### Personas
{{#if PERSONA_COUNT > 0}}
Count: {{PERSONA_COUNT}}

{{#each PERSONA_FILES}}
- {{basename}} ({{path}})
{{/each}}
{{else}}
None yet.

Run: /update-profile → Foundation Rules
{{/if}}
```

Also update the `updated` date in the frontmatter.

**Validation:** Verify profile.md was updated

Check that:
- Profile.md exists and is readable
- Foundation Rules section was updated
- Rule counts and paths are accurate
- Updated date is current

If validation fails:
```
⚠️  Failed to update profile.md

Error: {{ERROR_MESSAGE}}

Rules were extracted successfully, but profile.md couldn't be updated.
You can manually edit .kurt/profile.md to add the rule paths.

Continue anyway? (y/n):
```

If no: Exit with error.
If yes: Continue to Step 6.

Only proceed to Step 6 when profile update is validated or user chooses to continue.

---

## Step 6: Success Message

Display completion summary:

```
═══════════════════════════════════════════════════════
✅ Foundation Rules Extraction Complete
═══════════════════════════════════════════════════════

Extracted: {{TOTAL_EXTRACTED}} rule file(s)
{{#if TOTAL_MISSING > 0}}
Skipped: {{TOTAL_MISSING}} rule type(s)
{{/if}}

Your foundation rules are ready to use in projects.

Next steps:
- Review extracted rules in rules/ directory
- Create your first project: /create-project
{{#if ANY_MISSING}}
- Extract missing rules: /update-profile → Foundation Rules
{{/if}}
```

---

*This subskill handles foundation rules extraction by delegating to extract-rules subskill with validation at each step.*
