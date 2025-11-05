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
- Team information (company/team details)

---

## Step 1: Check Profile Exists

```bash
# Verify profile exists
if [ ! -f ".kurt/profile.md" ]; then
  echo "⚠️  No profile found"
  echo ""
  echo "You need to create a profile first."
  echo ""
  echo "Run: /create-profile"
  exit 1
fi

echo "✓ Profile found"
echo ""
```

---

## Step 2: Show Update Menu

```
═══════════════════════════════════════════════════════
Update Profile
═══════════════════════════════════════════════════════

What would you like to update?

a) Content Map - Add/remove organizational domains
b) Analytics - Configure or update analytics for domains
c) Foundation Rules - Re-extract publisher, style, personas
d) Team Information - Update company/team details
e) All of the above
f) Cancel

Choose: _
```

**Wait for user response**

---

## Step 3: Route to Operations

Based on user choice, invoke the appropriate operation(s):

### Option (a): Update Content Map

```
Updating content map...
```

**Invoke:** `onboarding setup-content`

This will:
1. Show current domains in content map
2. Ask if user wants to add or remove domains
3. For new domains: Run map → cluster → fetch workflow
4. For removal: Remove from sources/ and update profile

**After completion:**
```
Content map updated.

Would you like to re-extract foundation rules with the new content? (Y/n):
```

If yes, invoke `onboarding setup-rules`

---

### Option (b): Update Analytics

```
Updating analytics configuration...
```

**Invoke:** `onboarding setup-analytics`

This will:
1. Show current analytics configuration
2. Offer to add new domains or update existing
3. Run analytics onboard/sync for selected domains

---

### Option (c): Update Foundation Rules

```
Re-extracting foundation rules...
```

**Prerequisites check:**
```bash
# Verify content is available
content_count=$(kurt content list --with-status FETCHED 2>/dev/null | wc -l | tr -d ' ')

if [ "$content_count" -lt 10 ]; then
  echo "⚠️  Need at least 10 fetched pages to extract rules"
  echo ""
  echo "Would you like to add more content first? (Y/n):"
  read -p "> " choice

  if [ "$choice" != "n" ]; then
    # Invoke setup-content
    onboarding setup-content
  fi
fi
```

**Invoke:** `onboarding setup-rules`

This delegates to `project-management extract-rules --foundation-only` which will:
1. Show current rules
2. Offer to re-extract publisher, style, or personas
3. Use writing-rules-skill with preview mode

---

### Option (d): Update Team Information

```
Updating team information...
```

**Invoke:** `onboarding-skill/subskills/questionnaire --update-only`

This will:
1. Show current team information from profile
2. Ask which fields to update
3. Update onboarding-data.json (or just update directly)

---

### Option (e): Update All

Run all update operations in sequence:

```
Running complete profile update...

Step 1/4: Content Map
```

Invoke: `onboarding setup-content`

```
Step 2/4: Analytics
```

Invoke: `onboarding setup-analytics`

```
Step 3/4: Foundation Rules
```

Invoke: `onboarding setup-rules`

```
Step 4/4: Team Information
```

Invoke: `onboarding-skill/subskills/questionnaire --update-only`

---

### Option (f): Cancel

```
Update cancelled.
```

Exit without changes.

---

## Step 4: Regenerate Profile

After any updates complete, regenerate the profile.md file:

```
Updating profile...
```

**Invoke:** `onboarding-skill/subskills/create-profile --update`

This will:
1. Load existing profile data
2. Merge with any updated information
3. Regenerate `.kurt/profile.md`

---

## Step 5: Show Updated Summary

```
═══════════════════════════════════════════════════════
✅ Profile Updated
═══════════════════════════════════════════════════════

{{COMPANY_NAME}} - {{TEAM_NAME}}

Updated:
{{#if CONTENT_UPDATED}}
✓ Content Map - {{DOMAIN_COUNT}} domains
{{/if}}
{{#if ANALYTICS_UPDATED}}
✓ Analytics - {{ANALYTICS_DOMAIN_COUNT}} domains configured
{{/if}}
{{#if RULES_UPDATED}}
✓ Foundation Rules - Re-extracted
{{/if}}
{{#if INFO_UPDATED}}
✓ Team Information - Updated
{{/if}}

Profile location: .kurt/profile.md

───────────────────────────────────────────────────────
What's Next?
───────────────────────────────────────────────────────

{{#if CONTENT_UPDATED or RULES_UPDATED}}
Your updated foundation is ready for project work.
{{/if}}

{{#if NOT ANALYTICS_CONFIGURED}}
💡 Consider setting up analytics for traffic-based content prioritization.
Run: /update-profile → choose option (b)
{{/if}}

Ready to create a project? Run: /create-project
```

---

## Error Handling

### If operation fails

```
⚠️  Update failed: {{OPERATION_NAME}}

Error: {{ERROR_MESSAGE}}

Options:
a) Retry this operation
b) Skip and continue with other updates
c) Cancel all updates

Choose: _
```

### If profile is corrupted

```
⚠️  Profile appears to be corrupted

The profile file exists but couldn't be parsed.

Options:
a) View profile file (for debugging)
b) Backup and recreate (runs /create-profile)
c) Cancel

Choose: _
```

---

## Key Design Principles

1. **Selective updates** - Users choose what to update, not all-or-nothing
2. **Delegates to operations** - Reuses setup-content, setup-analytics, setup-rules
3. **Profile regeneration** - Always regenerates profile.md after changes
4. **Non-destructive** - Can add content/analytics without removing existing
5. **Fail gracefully** - Errors in one operation don't block others

---

*This subskill provides selective profile updates by orchestrating onboarding operations.*
