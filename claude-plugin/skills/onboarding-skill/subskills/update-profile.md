# Update Profile Subskill

**Purpose:** Selectively update existing profile
**Parent Skill:** onboarding-skill
**Pattern:** Menu-driven updates to profile sections

---

## Overview

This subskill allows users to update specific parts of their team profile without running the full onboarding flow.

**Update options:**
- Content map (add/remove organizational domains)
- Analytics configuration (add domains, re-sync)
- Foundation rules (re-extract with new content)
- Team information (company/team/goal details)

---

## Progress Checklist

Copy this checklist and track your progress as you work:

- [ ] Check profile exists
- [ ] Show update menu
- [ ] Get user's selection
- [ ] Execute selected operation(s)
- [ ] Validate each operation completed successfully
- [ ] Update profile.md with changes
- [ ] Validate profile updates
- [ ] Show success message

---

## Step 1: Check Profile Exists

**Validation:** Check if .kurt/profile.md exists

If not:
```
⚠️  No profile found

You need to create a profile first.

Run: /create-profile
```

Exit if validation fails.

Only proceed to Step 2 when profile is validated.

---

## Step 2: Show Update Menu

Display menu:

```
═══════════════════════════════════════════════════════
Update Profile
═══════════════════════════════════════════════════════

What would you like to update?

a) Content Map - Add/remove organizational domains
b) Analytics - Configure or update analytics for domains
c) Foundation Rules - Re-extract publisher, style, personas
d) Team Information - Update company/team/goal details
e) Cancel

Choose one or more (a,b,c,d) or press e to cancel:
```

Wait for user response.

---

## Step 3: Route to Operations

Based on user choice, invoke the appropriate operation(s):

### Option (a): Update Content Map

Read and execute: `map-content.md`

This will:
1. Show current domains in content map
2. Ask if user wants to add or remove domains
3. For new domains: Run `kurt map url` → `kurt fetch` workflow
4. For removal: Ask user to manually remove from sources/ or run `kurt content remove`

After content is updated, ask:
```
Content map updated.

Would you like to re-extract foundation rules with the new content? (y/n):
```

If yes, proceed to option (c) automatically.

**Validation:** Verify content was successfully mapped

Check that:
- `kurt content list` shows new documents
- Profile.md "Content Sources" section can be updated with new counts

If validation fails:
```
⚠️  Content mapping failed

Error: {{ERROR_MESSAGE}}

Would you like to:
a) Retry content mapping
b) Skip and return to menu

Choose: _
```

If retry: Return to beginning of option (a) and try again.
If skip: Return to Step 2 menu.

Only proceed when content mapping is validated or skipped.

Update the "Content Sources" section in `.kurt/profile.md` with new domain count and last updated date.

---

### Option (b): Update Analytics

Read and execute: `setup-analytics.md`

This will:
1. Show current analytics configuration (if any)
2. Offer to add new domains or update existing
3. Connect to analytics platform and sync data

**Validation:** Verify analytics was successfully configured

Check that:
- Analytics connection succeeded
- Profile.md "Analytics" section can be updated with platform details

If validation fails:
```
⚠️  Analytics setup failed

Error: {{ERROR_MESSAGE}}

Would you like to:
a) Retry analytics setup
b) Skip and return to menu

Choose: _
```

If retry: Return to beginning of option (b) and try again.
If skip: Return to Step 2 menu.

Only proceed when analytics setup is validated or skipped.

Update the "Analytics" section in `.kurt/profile.md` with configuration details.

---

### Option (c): Update Foundation Rules

Read and execute: `extract-foundation.md`

This will:
1. Check if sufficient content is available (need at least 10 fetched pages)
2. If not enough content, offer to run map-content first
3. Extract publisher profile, style guide, and/or personas
4. Create/update rule files in `rules/` directory

**Validation:** Verify foundation rules were successfully extracted

Check that:
- Rule files were created in `rules/` directory
- Profile.md "Foundation Rules" section can be updated with rule paths

If validation fails:
```
⚠️  Foundation rules extraction failed

Error: {{ERROR_MESSAGE}}

Would you like to:
a) Retry extraction
b) Skip and return to menu

Choose: _
```

If retry: Return to beginning of option (c) and try again.
If skip: Return to Step 2 menu.

Only proceed when rules extraction is validated or skipped.

Update the "Foundation Rules" section in `.kurt/profile.md` with extracted rule paths.

---

### Option (d): Update Team Information

Ask user what to update:

```
Current information:
- Company: {{COMPANY_NAME}}
- Team/Role: {{TEAM_ROLE}}
- Primary Goal: {{PRIMARY_GOAL}}

Which would you like to update? (separate with commas)

1. Company name
2. Team/role
3. Primary goal

Enter numbers (e.g., 1,3) or press Enter to skip:
```

For each selected field, ask for new value:

```
1. New company name:
>

2. New team/role:
>

3. New primary goal:
>
```

**Validation:** Verify profile.md was updated correctly

Check that:
- Profile.md "Organization" section contains the new values
- `updated` date in frontmatter is current

If validation fails:
```
⚠️  Profile update failed

Error: Couldn't update profile.md

Would you like to:
a) Retry update
b) Skip and return to menu

Choose: _
```

If retry: Return to beginning of option (d) and try again.
If skip: Return to Step 2 menu.

Only proceed when profile update is validated or skipped.

Update the "Organization" section in `.kurt/profile.md` directly with new values.

Also update the `updated` date in the frontmatter.

---

### Option (e): Cancel

```
Update cancelled.
```

Exit without changes.

---

## Step 4: Show Success Message

After updates complete:

```
═══════════════════════════════════════════════════════
✅ Profile Updated
═══════════════════════════════════════════════════════

{{COMPANY_NAME}} - {{TEAM_ROLE}}

Updated:
{{UPDATES_LIST}}

Profile location: .kurt/profile.md
Updated: {{TODAY_DATE}}

───────────────────────────────────────────────────────
What's Next?
───────────────────────────────────────────────────────

{{NEXT_STEPS}}

Ready to create a project? Run: /create-project
```

**Updates list** (dynamically generated based on what was updated):
- If content updated: "✓ Content Map - X domains"
- If analytics updated: "✓ Analytics - Y domains configured"
- If rules updated: "✓ Foundation Rules - Re-extracted"
- If team info updated: "✓ Team Information"

**Next steps** (contextual based on profile state):
- If no content: "💡 Add content sources for better rule extraction"
- If no analytics: "💡 Connect analytics for traffic-based prioritization"
- If no rules: "💡 Extract foundation rules to define your brand voice"
- Always: "Ready to start? Run /create-project"

---

## Key Principles

1. **Selective updates** - Users choose what to update
2. **Delegates to operations** - Reuses specialized subskills
3. **Direct profile updates** - Edits `.kurt/profile.md` directly (no JSON intermediate)
4. **Non-destructive** - Adds without removing existing data
5. **Validation checkpoints** - Each operation is validated before proceeding
6. **Fail gracefully** - Errors in one operation don't block others

---

*This subskill provides selective profile updates by orchestrating specialized operations. All operations include validation checkpoints with retry/skip options.*
