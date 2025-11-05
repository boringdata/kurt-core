# Create Profile Subskill

**Purpose:** Complete onboarding flow for new teams
**Parent Skill:** onboarding-skill
**Pattern:** Quick setup with inline questions, optional integrations
**Output:** `.kurt/profile.md`

---

## Overview

This subskill guides users through a streamlined onboarding process:

1. Ask 3 basic questions in one turn
2. Generate profile.md with the basics
3. Offer optional integrations (content mapping, analytics, CMS)
4. Show success message with next steps

**Key principles:**
- Fast and simple - get started in under 2 minutes
- Optional integrations can be added later via /update-profile
- Profile creation is not blocked by integration setup

---

## Progress Checklist

Copy this checklist and track your progress as you work:

- [ ] Check prerequisites (.kurt/ directory exists)
- [ ] Welcome user and ask 3 basic questions
- [ ] Parse user responses
- [ ] Generate profile.md with basic info
- [ ] Validate profile was created successfully
- [ ] Offer optional integrations (content, analytics, CMS)
- [ ] Execute selected integrations (if any)
- [ ] Show success message with next steps

---

## Step 1: Check Prerequisites

**Validation:** Check if .kurt/ directory exists

If not:
```
⚠️  Kurt not initialized

Run: kurt init
Then retry: /create-profile
```

Exit if validation fails.

---

## Step 2: Welcome and Basic Questions

Display welcome message and ask the core questions:

```
═══════════════════════════════════════════════════════
Welcome to Kurt!
═══════════════════════════════════════════════════════

Let me set up your Kurt profile with a few quick questions:

1. What company/organization are you working for?
2. What's your role or team? (e.g., Marketing, DevRel, Product)
3. What's your primary communication/marketing goal?

Answer with numbered responses like:
1. Acme Corp
2. DevRel team
3. Drive developer adoption through educational content

(You can update these anytime by running /update-profile)
```

Wait for user response.

**Parse responses:**
- Extract lines starting with "1.", "2.", "3."
- Store values for profile generation

**Validation:** Verify all 3 responses were provided

If any are missing:
```
⚠️  Missing information

I need all 3 responses to create your profile. Please provide:
[List missing numbers]
```

Return to Step 2 and ask again.

Only proceed to Step 3 when all responses are validated.

---

## Step 3: Generate Basic Profile

Create `.kurt/profile.md` with the collected information:

```markdown
---
created: {{TODAY_DATE}}
updated: {{TODAY_DATE}}
---

# {{COMPANY_NAME}} - Kurt Profile

## Organization

**Company:** {{COMPANY_NAME}}
**Team/Role:** {{TEAM_ROLE}}
**Primary Goal:** {{PRIMARY_GOAL}}

---

## Content Sources

### Organizational Content
Not yet configured.

Run `/update-profile` to add:
- Company website
- Documentation sites
- Blog or other content sources

### Content Status
- Total documents indexed: 0
- Last updated: Not yet configured

---

## Analytics

Not yet configured.

Run `/update-profile` to connect analytics platforms for traffic-based prioritization.

---

## Foundation Rules

### Publisher Profile
Not yet extracted.

This defines your brand voice and content principles.

### Style Guides
None yet.

### Personas
None yet.

---

## Projects

No projects created yet.

Run `/create-project` to start your first project.

---

## Next Steps

1. **Map your content** (optional but recommended)
   - Run: `/update-profile` and select "Content mapping"
   - This helps Kurt understand your existing content

2. **Connect analytics** (optional)
   - Run: `/update-profile` and select "Analytics setup"
   - Enables traffic-based content prioritization

3. **Create your first project**
   - Run: `/create-project`
   - Start working on content immediately

---

*You can update this profile anytime by running `/update-profile` or editing this file directly.*
```

**Validation:** Verify profile.md was created successfully

Check that:
- File exists at .kurt/profile.md
- File contains all expected sections (Organization, Content Sources, Analytics, Foundation Rules, Projects, Next Steps)
- Company, Team/Role, and Primary Goal are populated with user's responses

If validation fails:
```
⚠️  Profile creation failed

I wasn't able to create your profile file. Please check:
- Do you have write permissions for the .kurt/ directory?
- Is there enough disk space?

Would you like to retry? (y/n):
```

If yes: Return to Step 3 and regenerate.
If no: Exit with error message.

Only proceed to Step 4 when validation passes.

Display confirmation:
```
✓ Profile created: .kurt/profile.md
```

---

## Step 4: Optional Integration Setup

Ask if user wants to set up optional integrations now:

```
Would you like to set up any of these now? (optional, can do later via /update-profile)

a) Map content sources (website, docs, blog)
b) Connect analytics (Google Analytics, Plausible)
c) Configure CMS integration (Sanity, Contentful, WordPress)
d) Skip for now - I'll do this later

Choose one or more (a,b,c) or press d to skip:
```

**Handle response:**

If user chooses **a) Map content sources:**
- Read and execute: `map-content.md`
- Update profile.md with mapped content info

If user chooses **b) Connect analytics:**
- Read and execute: `setup-analytics.md`
- Update profile.md with analytics configuration

If user chooses **c) Configure CMS:**
- Delegate to `kurt:cms-interaction-skill` for CMS setup
- Update profile.md with CMS configuration

If user chooses **d) Skip:**
- Continue to Step 6 (success message)

**Validation:** For each integration executed, verify it completed successfully

If any integration fails:
```
⚠️  {{INTEGRATION_NAME}} setup failed

Error: {{ERROR_MESSAGE}}

Would you like to:
a) Retry this integration
b) Skip and continue
c) Exit onboarding

Choose: _
```

If retry: Return to the failed integration step and try again.
If skip: Continue to next integration or Step 5.
If exit: Show partial success message and exit.

Only proceed to Step 5 when all selected integrations are complete or skipped.

---

## Step 5: Optional Foundation Rules Extraction

If user completed content mapping in Step 4, ask:

```
Your content is now mapped. Would you like to extract foundation rules from your content?

Foundation rules capture your brand voice, style patterns, and target personas.
This takes 3-5 minutes.

Extract foundation rules now? (y/n):
```

If yes:
- Read and execute: `extract-foundation.md`
- Update profile.md with extracted rules info

If no:
- Add to next steps in success message

**Validation:** If foundation rules extraction was attempted, verify it completed

If extraction fails:
```
⚠️  Foundation rules extraction failed

Error: {{ERROR_MESSAGE}}

Would you like to:
a) Retry extraction
b) Skip - I'll do this later with /update-profile

Choose: _
```

If retry: Return to beginning of Step 5 and try again.
If skip: Continue to Step 6.

Only proceed to Step 6 when extraction is complete or skipped.

---

## Step 6: Success Message

Display completion message:

```
═══════════════════════════════════════════════════════
🎉 Profile Created!
═══════════════════════════════════════════════════════

Your Kurt profile is ready: .kurt/profile.md

{{COMPLETION_SUMMARY}}

───────────────────────────────────────────────────────
What's Next?
───────────────────────────────────────────────────────

{{NEXT_STEPS}}

Remember: You can update your profile anytime with /update-profile
```

**Completion summary (based on what was done):**
- Always: "✓ Basic profile created"
- If content mapped: "✓ Content mapped: X documents"
- If analytics configured: "✓ Analytics configured"
- If CMS configured: "✓ CMS integrated: [platform name]"
- If rules extracted: "✓ Foundation rules extracted"

**Next steps (based on what's missing):**
- If no content mapped: "1. Map your content with /update-profile"
- If no analytics: "2. Connect analytics for traffic insights with /update-profile"
- If no rules: "3. Extract foundation rules with /update-profile"
- Always: "4. Create your first project with /create-project"

---

*This subskill provides a quick, streamlined onboarding experience with optional depth. All critical operations include validation checkpoints to ensure reliability.*
