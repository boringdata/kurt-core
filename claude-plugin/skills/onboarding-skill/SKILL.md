---
name: onboarding
description: One-time team setup that creates Kurt profile and foundation rules
---

# Onboarding Skill

**Purpose:** Organizational setup and profile management
**Entry:** `/create-profile` or `/update-profile` commands
**Output:** `.kurt/profile.md` + foundation rules + indexed content

---

## Overview

This skill manages organizational onboarding through modular operations:

1. **create-profile** - Complete onboarding flow for new teams
2. **update-profile** - Update existing profile (selective updates)
3. **setup-content** - Map and fetch organizational content
4. **setup-analytics** - Configure analytics for domains (optional)
5. **setup-rules** - Extract foundation rules (publisher, style, personas)

**Key principle:** Operations are standalone and composable. They can be invoked independently OR as part of create-profile/update-profile flows.

---

## Operations

### create-profile
Complete onboarding flow for new teams.

**Entry:** `/create-profile` or `onboarding create-profile`

**Flow:**
1. Questionnaire - Capture team context
2. Map content - Organizational websites
3. Setup analytics - Optional traffic configuration
4. Extract rules - Foundation rules
5. Create profile - Generate `.kurt/profile.md`

See: `subskills/create-profile.md`

### update-profile
Update existing profile with selective changes.

**Entry:** `/update-profile` or `onboarding update-profile`

**Options:**
- Update content map (add/remove domains)
- Update analytics configuration
- Re-extract foundation rules
- Update team information

See: `subskills/update-profile.md`

### setup-content
Map and fetch organizational content.

**Entry:** `onboarding setup-content`

**Called by:**
- create-profile subskill
- update-profile subskill
- project-management check-onboarding (if content missing)

See: `subskills/map-content.md`

### setup-analytics
Configure analytics for organizational domains.

**Entry:** `onboarding setup-analytics`

**Called by:**
- create-profile subskill (optional)
- update-profile subskill
- project-management check-onboarding (if user wants analytics)

See: `subskills/setup-analytics.md`

### setup-rules
Extract foundation rules from organizational content.

**Entry:** `onboarding setup-rules`

**Called by:**
- create-profile subskill
- update-profile subskill
- project-management check-onboarding (if rules missing)

See: `subskills/extract-foundation.md`

---

## Routing Logic

```bash
# Parse first argument to determine operation
OPERATION=$1

case "$OPERATION" in
  create-profile)
    # Full onboarding flow
    invoke: subskills/create-profile.md
    ;;

  update-profile)
    # Selective updates to existing profile
    invoke: subskills/update-profile.md
    ;;

  setup-content)
    # Map and fetch organizational content
    invoke: subskills/map-content.md
    ;;

  setup-analytics)
    # Configure analytics
    invoke: subskills/setup-analytics.md
    ;;

  setup-rules)
    # Extract foundation rules
    invoke: subskills/extract-foundation.md
    ;;

  *)
    echo "Unknown operation: $OPERATION"
    echo ""
    echo "Available operations:"
    echo "  create-profile    - Complete onboarding for new teams"
    echo "  update-profile    - Update existing profile"
    echo "  setup-content     - Map organizational content"
    echo "  setup-analytics   - Configure analytics"
    echo "  setup-rules       - Extract foundation rules"
    echo ""
    echo "Usage: onboarding <operation>"
    exit 1
    ;;
esac
```

---

## Step 1: Welcome Message

```
═══════════════════════════════════════════════════════
Welcome to Kurt!
═══════════════════════════════════════════════════════

I'll help you set up Kurt for your team. This takes 5-10 minutes.

You can skip questions you're unsure about - we'll help you discover
the answers as you work.

Press Enter to start...
```

Wait for user to press Enter.

---

## Step 2: Run Questionnaire

Invoke: `onboarding-skill/subskills/questionnaire`

This captures:
- Company name, team, industry
- Communication goals
- Content types created
- Target personas
- Source content URLs
- CMS configuration (optional)
- Workflow description (optional)

**Output:** JSON file with all captured data at `.kurt/temp/onboarding-data.json`

---

## Step 3: Map Content (if sources provided)

Check if sources were provided:

```bash
SOURCES=$(jq -r '.sources | length' .kurt/temp/onboarding-data.json)

if [ "$SOURCES" -gt 0 ]; then
  echo ""
  echo "───────────────────────────────────────────────────────"
  echo "Step 1/3: Mapping Content Sources"
  echo "───────────────────────────────────────────────────────"
  echo ""

  # Invoke map-content subskill
  # This calls kurt CLI to map and fetch
fi
```

Invoke: `onboarding-skill/subskills/map-content`

**Input:** Sources from onboarding-data.json
**Output:** Updates onboarding-data.json with content stats

---

## Step 4: Setup Analytics (optional, if content fetched)

Check if content was fetched:

```bash
CONTENT_FETCHED=$(jq -r '.content_fetched' .kurt/temp/onboarding-data.json)

if [ "$CONTENT_FETCHED" = "true" ]; then
  echo ""
  echo "───────────────────────────────────────────────────────"
  echo "Step 2/4: Analytics Setup (Optional)"
  echo "───────────────────────────────────────────────────────"
  echo ""
fi
```

Invoke: `onboarding-skill/subskills/setup-analytics`

**Input:** Domains detected from content in onboarding-data.json
**Output:** Updates onboarding-data.json with analytics configuration
**Note:** Optional step - user can skip without blocking

---

## Step 5: Extract Foundation Rules (if content fetched)

Check if content was fetched:

```bash
CONTENT_FETCHED=$(jq -r '.content_fetched' .kurt/temp/onboarding-data.json)

if [ "$CONTENT_FETCHED" = "true" ]; then
  echo ""
  echo "───────────────────────────────────────────────────────"
  echo "Step 3/4: Extract Foundation Rules"
  echo "───────────────────────────────────────────────────────"
  echo ""
fi
```

Invoke: `onboarding-skill/subskills/extract-foundation`

**Input:** Content status from onboarding-data.json
**Output:** Creates rules files, updates onboarding-data.json with rule paths

---

## Step 6: Create Profile

Always run (even if steps 3-5 skipped):

```
───────────────────────────────────────────────────────
Step 4/4: Creating Your Profile
───────────────────────────────────────────────────────

Generating your Kurt profile...
```

Invoke: `onboarding-skill/subskills/create-profile`

**Input:** All data from onboarding-data.json
**Output:** `.kurt/profile.md`

---

## Step 6: Cleanup

```bash
# Remove temporary data file
rm .kurt/temp/onboarding-data.json

# Create temp directory for future use
mkdir -p .kurt/temp
```

---

## Step 7: Success Message

```
═══════════════════════════════════════════════════════
🎉 Setup Complete!
═══════════════════════════════════════════════════════

Your Kurt profile is ready:
  Location: .kurt/profile.md

{{COMPLETION_SUMMARY}}

───────────────────────────────────────────────────────
What's Next?
───────────────────────────────────────────────────────

{{NEXT_STEPS}}

Need help? Type /help or see .kurt/profile.md for your setup
```

**Completion summary based on what was done:**
- If content mapped: "✓ Content mapped: X documents"
- If rules extracted: "✓ Rules extracted: publisher, style, personas"
- If workflow mentioned: "Suggestion: Run `workflow-skill add` to codify your workflow"

**Next steps based on gaps:**
- If no content: "1. Map content: kurt map url <website>"
- If no rules: "2. Extract rules: writing-rules-skill publisher --auto-discover"
- If workflow mentioned: "3. Define workflow: workflow-skill add"
- Always: "4. Create project: /create-project"

---

## Error Handling

**If subskill fails:**
```
⚠️  {{SUBSKILL_NAME}} failed

Error: {{ERROR_MESSAGE}}

Options:
  a) Retry
  b) Skip this step
  c) Cancel onboarding

Choose: _
```

**If .kurt/ directory doesn't exist:**
```
⚠️  Kurt not initialized

Run: kurt init
Then retry: /start
```

---

## Integration Points

**Called by:**
- `/create-profile` slash command → create-profile operation
- `/update-profile` slash command → update-profile operation
- `project-management check-onboarding` → Can invoke setup-content, setup-analytics, setup-rules if incomplete

**Invokes:**
- `onboarding-skill/subskills/questionnaire` - Capture team context
- `onboarding-skill/subskills/map-content` - Map organizational content
- `onboarding-skill/subskills/setup-analytics` - Configure analytics
- `onboarding-skill/subskills/extract-foundation` - Extract foundation rules
- `onboarding-skill/subskills/create-profile` - Generate/update profile
- `onboarding-skill/subskills/update-profile` - Selective profile updates
- `project-management extract-rules --foundation-only` - Delegates rule extraction
- `writing-rules-skill` - For extracting rules (via extract-foundation)

**Calls:**
- `kurt CLI` - For content mapping (`kurt map`), fetching (`kurt fetch`), analytics
- `writing-rules-skill` - For rule extraction
- `project-management extract-rules` - Delegates foundation rule extraction

**Creates:**
- `.kurt/profile.md` - Team profile with organizational context
- `.kurt/temp/onboarding-data.json` - Temporary data (deleted after create-profile)
- Foundation rules - Publisher profile, primary voice, personas
- Analytics configuration - Stored in profile.md

---

*This skill owns all organizational setup. Operations are composable and can be invoked independently or as part of create/update flows.*
