# Check Onboarding Subskill

**Purpose:** Verify onboarding complete before project work
**Parent Skill:** project-management
**Pattern:** Check → Fail fast or Load context

---

## Overview

This subskill ensures onboarding is complete before allowing project work.

**Checks:**
1. Profile exists (.kurt/profile.md)
2. Load organizational context from profile
3. Display onboarding summary
4. Offer to complete missing pieces via onboarding operations

**Key principle:** Onboarding-skill owns all setup logic. This subskill only checks and loads.

---

## Step 1: Check Profile Exists

```bash
# Verify profile exists
if [ ! -f ".kurt/profile.md" ]; then
  echo "⚠️  No team profile found"
  echo ""
  echo "Please complete onboarding first:"
  echo "  /create-profile"
  echo ""
  echo "This sets up your organizational context:"
  echo "  • Content map (your websites/docs)"
  echo "  • Foundation rules (brand voice, personas)"
  echo "  • Analytics (optional, for traffic-based prioritization)"
  echo ""
  echo "Takes 10-15 minutes. Required before creating projects."
  exit 1
fi

echo "✓ Profile found"
echo ""
```

---

## Step 2: Load Context from Profile

Parse profile for key information needed during project creation:

```bash
# Parse profile for key info
COMPANY_NAME=$(grep "^# " .kurt/profile.md | head -1 | sed 's/# //')
TEAM_NAME=$(grep "Team:" .kurt/profile.md | sed 's/.*Team: //')
INDUSTRY=$(grep "Industry:" .kurt/profile.md | sed 's/.*Industry: //')

# Content map status
CONTENT_DOMAINS=$(grep -A 20 "## Content Map" .kurt/profile.md | grep "^- " | wc -l | tr -d ' ')

# Get domain list for later use
DOMAIN_LIST=$(grep -A 20 "## Content Map" .kurt/profile.md | grep "^- " | sed 's/^- //')

# Rules status
PUBLISHER_STATUS=$(grep "Publisher Profile:" .kurt/profile.md)
STYLE_STATUS=$(grep "Style Guides:" .kurt/profile.md)
PERSONA_STATUS=$(grep "Personas:" .kurt/profile.md)

# Analytics status
ANALYTICS_ENABLED=$(grep "Status:" .kurt/profile.md | grep -q "Analytics enabled" && echo "true" || echo "false")

if [ "$ANALYTICS_ENABLED" = "true" ]; then
  ANALYTICS_DOMAINS=$(grep -A 10 "## Analytics Configuration" .kurt/profile.md | grep "^\*\*" | sed 's/\*\*\(.*\)\*\* (.*/\1/')
fi
```

---

## Step 3: Display Onboarding Summary

Show summary of organizational context:

```
✅ Onboarding Complete

Company: $COMPANY_NAME
Team: $TEAM_NAME
Industry: $INDUSTRY

Content Map:
$DOMAIN_LIST

Foundation Rules:
$PUBLISHER_STATUS
$STYLE_STATUS
$PERSONA_STATUS

Analytics: $([ "$ANALYTICS_ENABLED" = "true" ] && echo "✓ Enabled" || echo "○ Not configured")
$(if [ "$ANALYTICS_ENABLED" = "true" ]; then
  echo "Domains with traffic data:"
  echo "$ANALYTICS_DOMAINS" | while read domain; do
    [ -n "$domain" ] && echo "  • $domain"
  done
fi)

Ready for project work.
```

---

## Step 4: Check for Incomplete Onboarding

If critical pieces are missing, offer to complete via onboarding operations:

### If No Content Mapped

```bash
if [ "$CONTENT_DOMAINS" -eq 0 ]; then
  echo ""
  echo "⚠️  No organizational content mapped yet"
  echo ""
  echo "Adding content helps with:"
  echo "  • Foundation rule extraction"
  echo "  • Understanding existing content"
  echo "  • Avoiding content duplication"
  echo ""
  read -p "Would you like to add content now? (Y/n): " choice

  if [ "$choice" != "n" ] && [ "$choice" != "N" ]; then
    echo ""
    echo "Invoking onboarding operation..."
    onboarding setup-content

    # Regenerate profile
    echo ""
    echo "Updating profile..."
    onboarding create-profile --update

    echo ""
    echo "✓ Content map updated"
  fi
fi
```

### If No Foundation Rules

```bash
# Check if publisher profile exists
if ! grep -q "Publisher Profile:" .kurt/profile.md; then
  echo ""
  echo "⚠️  Foundation rules not extracted yet"
  echo ""
  echo "Foundation rules ensure:"
  echo "  • Consistent brand voice"
  echo "  • Appropriate messaging"
  echo "  • Content matches your audience"
  echo ""
  read -p "Would you like to extract foundation rules now? (Y/n): " choice

  if [ "$choice" != "n" ] && [ "$choice" != "N" ]; then
    # Check content exists first
    content_count=$(kurt content list --with-status FETCHED 2>/dev/null | wc -l | tr -d ' ')

    if [ "$content_count" -lt 10 ]; then
      echo ""
      echo "⚠️  Need at least 10 fetched pages to extract rules"
      echo "Please add organizational content first."
      echo ""
      read -p "Add content now? (Y/n): " add_content

      if [ "$add_content" != "n" ] && [ "$add_content" != "N" ]; then
        onboarding setup-content
      fi
    fi

    echo ""
    echo "Invoking onboarding operation..."
    onboarding setup-rules

    # Regenerate profile
    echo ""
    echo "Updating profile..."
    onboarding create-profile --update

    echo ""
    echo "✓ Foundation rules extracted"
  fi
fi
```

### If No Analytics (Informational Only)

```bash
if [ "$ANALYTICS_ENABLED" != "true" ]; then
  echo ""
  echo "○ Analytics not configured"
  echo ""
  echo "Analytics enables traffic-based prioritization:"
  echo "  • Identify high-traffic pages to update"
  echo "  • Find declining traffic (needs refresh)"
  echo "  • Data-driven content decisions"
  echo ""
  echo "You can add analytics anytime with: /update-profile"
  echo ""
fi
```

**Note:** Don't block on analytics - it's optional.

---

## Step 5: Return Context to Parent

Export loaded context for parent workflow to use:

```bash
# Store context in variables for parent to access
export PROFILE_COMPANY="$COMPANY_NAME"
export PROFILE_TEAM="$TEAM_NAME"
export PROFILE_INDUSTRY="$INDUSTRY"
export PROFILE_DOMAINS="$DOMAIN_LIST"
export PROFILE_ANALYTICS="$ANALYTICS_ENABLED"
```

Parent workflow (create-project or resume-project) can now use this context.

---

## Error Handling

### If profile is corrupted

```bash
if ! grep -q "^# " .kurt/profile.md; then
  echo "⚠️  Profile file appears corrupted"
  echo ""
  echo "The profile exists but couldn't be parsed."
  echo ""
  echo "Options:"
  echo "  a) View profile (for debugging)"
  echo "  b) Recreate profile (/create-profile)"
  echo "  c) Cancel"
  echo ""
  read -p "Choose: " choice

  case "$choice" in
    a)
      cat .kurt/profile.md
      exit 1
      ;;
    b)
      echo "Recreating profile..."
      onboarding create-profile
      ;;
    c)
      exit 1
      ;;
  esac
fi
```

### If onboarding operation fails

```
⚠️  Onboarding operation failed: setup-content

You can:
  • Retry manually: onboarding setup-content
  • Continue without (skip for now)
  • Update profile later: /update-profile

Continue anyway? (y/n):
```

---

## Usage Notes

**Called from:**
- create-project.md (Step 2.5 - before collecting project sources)
- resume-project.md (Step 4 - after loading project context)

**Can invoke onboarding operations:**
- `onboarding setup-content` - If no content mapped
- `onboarding setup-rules` - If no foundation rules
- `onboarding create-profile --update` - To regenerate profile

**Does NOT:**
- Implement content mapping (→ onboarding-skill)
- Implement rule extraction (→ onboarding-skill)
- Implement analytics setup (→ onboarding-skill)

---

## Key Design Principles

1. **Fail fast** - No profile = immediate error with guidance
2. **Load context** - Parse profile for project creation
3. **Delegate setup** - Invoke onboarding operations if incomplete
4. **Non-blocking** - Can skip optional pieces
5. **Onboarding owns setup** - This only checks and loads

---

*This subskill verifies onboarding is complete by checking profile and loading context. All setup logic lives in onboarding-skill.*
