# Create Profile Subskill

**Purpose:** Generate `.kurt/profile.md` from collected onboarding data
**Parent Skill:** onboarding-skill
**Input:** `.kurt/temp/onboarding-data.json`
**Output:** `.kurt/profile.md`

---

## Overview

This subskill takes all collected data from the onboarding process and generates a complete team profile file.

---

## Step 1: Load Template and Data

```bash
# Load profile template
TEMPLATE=$(cat .kurt/templates/profile-template.md)

# Load onboarding data
DATA_FILE=".kurt/temp/onboarding-data.json"

# Extract all fields
COMPANY_NAME=$(jq -r '.company_name // "Not specified"' "$DATA_FILE")
TEAM_NAME=$(jq -r '.team_name // "Not specified"' "$DATA_FILE")
INDUSTRY=$(jq -r '.industry // "Not specified"' "$DATA_FILE")
TEAM_ROLE=$(jq -r '.team_role // "Content team"' "$DATA_FILE")

# Dates
CREATED_DATE=$(date +%Y-%m-%d)
UPDATED_DATE=$(date +%Y-%m-%d)
```

---

## Step 2: Format Lists

### Goals

```bash
GOALS=$(jq -r '.goals[]?' "$DATA_FILE")
GOALS_LIST=""

if [ -n "$GOALS" ]; then
  while IFS= read -r goal; do
    GOALS_LIST+="- $goal\n"
  done <<< "$GOALS"
else
  GOALS_LIST="- To be defined\n"
fi
```

### Content Types

```bash
CONTENT_TYPES=$(jq -r '.content_types[]?' "$DATA_FILE")
CONTENT_TYPES_LIST=""

if [ -n "$CONTENT_TYPES" ]; then
  while IFS= read -r type; do
    CONTENT_TYPES_LIST+="- $type\n"
  done <<< "$CONTENT_TYPES"
else
  CONTENT_TYPES_LIST="- To be defined\n"
fi
```

### Personas

```bash
KNOWN_PERSONAS=$(jq -r '.known_personas[]?' "$DATA_FILE")
PERSONA_DESC=$(jq -r '.persona_description // ""' "$DATA_FILE")
PERSONAS_TO_DISCOVER=$(jq -r '.personas_to_discover // false' "$DATA_FILE")

KNOWN_PERSONAS_LIST=""
TO_DISCOVER_PERSONAS=""

if [ -n "$KNOWN_PERSONAS" ]; then
  while IFS= read -r persona; do
    KNOWN_PERSONAS_LIST+="- $persona\n"
  done <<< "$KNOWN_PERSONAS"
else
  KNOWN_PERSONAS_LIST="None specified yet\n"
fi

if [ "$PERSONAS_TO_DISCOVER" = "true" ]; then
  TO_DISCOVER_PERSONAS="To be extracted from content"
  if [ -n "$PERSONA_DESC" ]; then
    TO_DISCOVER_PERSONAS+=": $PERSONA_DESC"
  fi
else
  TO_DISCOVER_PERSONAS="N/A"
fi
```

### Sources

```bash
COMPANY_WEBSITE=$(jq -r '.company_website // "Not specified"' "$DATA_FILE")
DOCS_URL=$(jq -r '.docs_url // ""' "$DATA_FILE")
BLOG_URL=$(jq -r '.blog_url // ""' "$DATA_FILE")
RESEARCH_SOURCES=$(jq -r '.research_sources[]?' "$DATA_FILE")

OTHER_COMPANY_SOURCES=""
[ -n "$DOCS_URL" ] && OTHER_COMPANY_SOURCES+="- Documentation: $DOCS_URL\n"
[ -n "$BLOG_URL" ] && OTHER_COMPANY_SOURCES+="- Blog: $BLOG_URL\n"

RESEARCH_SOURCES_LIST=""
if [ -n "$RESEARCH_SOURCES" ]; then
  while IFS= read -r source; do
    RESEARCH_SOURCES_LIST+="- $source\n"
  done <<< "$RESEARCH_SOURCES"
else
  RESEARCH_SOURCES_LIST="None specified\n"
fi

# Content status
CONTENT_FETCHED=$(jq -r '.content_fetched // false' "$DATA_FILE")
TOTAL_DOCS=$(jq -r '.content_stats.total_documents // 0' "$DATA_FILE")
FETCHED_DOCS=$(jq -r '.content_stats.fetched // 0' "$DATA_FILE")

if [ "$CONTENT_FETCHED" = "true" ]; then
  COMPANY_CONTENT_STATUS="Fetched and indexed ($FETCHED_DOCS documents)"
  RESEARCH_CONTENT_STATUS="Fetched and indexed"
else
  COMPANY_CONTENT_STATUS="Not yet mapped"
  RESEARCH_CONTENT_STATUS="Not yet mapped"
fi
```

### CMS

```bash
CMS_PLATFORM=$(jq -r '.cms_platform // "none"' "$DATA_FILE")
CMS_CONFIGURED=$(jq -r '.cms_configured // false' "$DATA_FILE")

if [ "$CMS_PLATFORM" != "none" ] && [ "$CMS_CONFIGURED" = "true" ]; then
  CMS_STATUS="Configured ($CMS_PLATFORM)"
else
  CMS_STATUS="Not configured"
fi
```

### Analytics

```bash
ANALYTICS_CONFIGURED=$(jq -r '.analytics_configured // false' "$DATA_FILE")
ANALYTICS_DOMAINS_JSON=$(jq -r '.analytics_domains // []' "$DATA_FILE")
ANALYTICS_DOMAINS_COUNT=$(echo "$ANALYTICS_DOMAINS_JSON" | jq 'length')

if [ "$ANALYTICS_CONFIGURED" = "true" ] && [ "$ANALYTICS_DOMAINS_COUNT" -gt 0 ]; then
  # Analytics is configured, format domain details
  ANALYTICS_DOMAINS=""

  for i in $(seq 0 $(($ANALYTICS_DOMAINS_COUNT - 1))); do
    DOMAIN=$(echo "$ANALYTICS_DOMAINS_JSON" | jq -r ".[$i].domain")
    PLATFORM=$(echo "$ANALYTICS_DOMAINS_JSON" | jq -r ".[$i].platform")
    LAST_SYNCED=$(echo "$ANALYTICS_DOMAINS_JSON" | jq -r ".[$i].last_synced")
    PAGEVIEWS=$(echo "$ANALYTICS_DOMAINS_JSON" | jq -r ".[$i].pageviews_60d")
    DOCS_WITH_DATA=$(echo "$ANALYTICS_DOMAINS_JSON" | jq -r ".[$i].documents_with_data")
    P25=$(echo "$ANALYTICS_DOMAINS_JSON" | jq -r ".[$i].thresholds.p25")
    P75=$(echo "$ANALYTICS_DOMAINS_JSON" | jq -r ".[$i].thresholds.p75")

    ANALYTICS_DOMAINS+="**$DOMAIN** ($PLATFORM)\n"
    ANALYTICS_DOMAINS+="- Last synced: $LAST_SYNCED\n"
    ANALYTICS_DOMAINS+="- Documents with traffic data: $DOCS_WITH_DATA\n"
    ANALYTICS_DOMAINS+="- Total pageviews (60d): $PAGEVIEWS\n"
    ANALYTICS_DOMAINS+="- Traffic thresholds:\n"
    ANALYTICS_DOMAINS+="  - HIGH: >$P75 views/month (top 25%)\n"
    ANALYTICS_DOMAINS+="  - MEDIUM: $P25-$P75 views/month (middle 50%)\n"
    ANALYTICS_DOMAINS+="  - LOW: 1-$P25 views/month (bottom 25%)\n"
    ANALYTICS_DOMAINS+="  - ZERO: 0 views/month\n\n"
  done
else
  # Analytics not configured
  ANALYTICS_DOMAINS=""
fi
```

### Competitors

```bash
COMPETITORS_JSON=$(jq -r '.competitors // []' "$DATA_FILE")
COMPETITORS_COUNT=$(echo "$COMPETITORS_JSON" | jq 'length')

if [ "$COMPETITORS_COUNT" -gt 0 ]; then
  COMPETITORS_LIST=""
  for i in $(seq 0 $(($COMPETITORS_COUNT - 1))); do
    COMPETITOR=$(echo "$COMPETITORS_JSON" | jq -r ".[$i]")
    COMPETITORS_LIST+="- $COMPETITOR\n"
  done
else
  COMPETITORS_LIST="None specified yet\n\nAdd competitors during competitive analysis projects or update profile.md directly."
fi
```

### Workflows

```bash
WORKFLOW_DESC=$(jq -r '.workflow_description // ""' "$DATA_FILE")
HAS_WORKFLOW=$(jq -r '.has_workflow_to_create // false' "$DATA_FILE")

if [ -n "$WORKFLOW_DESC" ]; then
  WORKFLOWS_LIST="To be created: $WORKFLOW_DESC\n\nRun: workflow-skill add"
else
  WORKFLOWS_LIST="None defined yet\n\nRun: workflow-skill add to create workflows"
fi
```

---

## Step 3: Format Extracted Rules

### Publisher

```bash
PUBLISHER_EXTRACTED=$(jq -r '.rules_extracted.publisher.extracted // false' "$DATA_FILE")
PUBLISHER_PATH=$(jq -r '.rules_extracted.publisher.path // ""' "$DATA_FILE")

if [ "$PUBLISHER_EXTRACTED" = "true" ]; then
  PUBLISHER_STATUS="Extracted"
else
  PUBLISHER_STATUS="Not yet extracted"
  PUBLISHER_PATH="Run: writing-rules-skill publisher --auto-discover"
fi
```

### Style

```bash
STYLE_EXTRACTED=$(jq -r '.rules_extracted.style.extracted // false' "$DATA_FILE")
STYLE_PATH=$(jq -r '.rules_extracted.style.path // ""' "$DATA_FILE")
STYLE_NAME=$(jq -r '.rules_extracted.style.name // ""' "$DATA_FILE")

if [ "$STYLE_EXTRACTED" = "true" ]; then
  STYLE_COUNT=1
  STYLE_LIST="- $STYLE_NAME ($STYLE_PATH)\n"
else
  STYLE_COUNT=0
  STYLE_LIST="None yet. Run: writing-rules-skill style --type corporate --auto-discover\n"
fi
```

### Structure

```bash
# Count structure files (may exist from previous work)
STRUCTURE_FILES=$(ls rules/structure/*.md 2>/dev/null | wc -l)

if [ "$STRUCTURE_FILES" -gt 0 ]; then
  STRUCTURE_COUNT=$STRUCTURE_FILES
  STRUCTURE_LIST=""
  for file in rules/structure/*.md; do
    name=$(basename "$file" .md)
    STRUCTURE_LIST+="- $name ($file)\n"
  done
else
  STRUCTURE_COUNT=0
  STRUCTURE_LIST="None yet. Run: writing-rules-skill structure --type <type> --auto-discover\n"
fi
```

### Personas

```bash
PERSONAS_EXTRACTED=$(jq -r '.rules_extracted.personas.extracted // false' "$DATA_FILE")
PERSONA_COUNT=$(jq -r '.rules_extracted.personas.count // 0' "$DATA_FILE")
PERSONA_FILES=$(jq -r '.rules_extracted.personas.files[]?' "$DATA_FILE")

if [ "$PERSONAS_EXTRACTED" = "true" ]; then
  PERSONA_LIST=""
  while IFS= read -r file; do
    name=$(basename "$file" .md)
    PERSONA_LIST+="- $name ($file)\n"
  done <<< "$PERSONA_FILES"
else
  PERSONA_LIST="None yet. Run: writing-rules-skill persona --audience-type all --auto-discover\n"
fi
```

### Custom Rules

```bash
# Check if custom rule types exist
CUSTOM_RULES=$(yq '.rule_types | to_entries | .[] | select(.value.built_in != true) | .key' rules/rules-config.yaml 2>/dev/null)

if [ -n "$CUSTOM_RULES" ]; then
  CUSTOM_RULES_STATUS="Custom rule types defined:\n"
  while IFS= read -r rule_type; do
    CUSTOM_RULES_STATUS+="- $rule_type\n"
  done <<< "$CUSTOM_RULES"
else
  CUSTOM_RULES_STATUS="None. Create with: writing-rules-skill add\n"
fi
```

---

## Step 4: Calculate Next Steps

```bash
NEXT_STEPS_LIST=""

# Content not mapped
if [ "$TOTAL_DOCS" -eq 0 ]; then
  NEXT_STEPS_LIST+="1. Map content sources:\n"
  [ -n "$COMPANY_WEBSITE" ] && NEXT_STEPS_LIST+="   kurt map url $COMPANY_WEBSITE --cluster-urls\n"
  NEXT_STEPS_LIST+="\n"
fi

# Content mapped but not fetched
if [ "$TOTAL_DOCS" -gt 0 ] && [ "$CONTENT_FETCHED" != "true" ]; then
  NEXT_STEPS_LIST+="2. Fetch content:\n"
  NEXT_STEPS_LIST+="   kurt fetch --with-status NOT_FETCHED\n\n"
fi

# Publisher not extracted
if [ "$PUBLISHER_EXTRACTED" != "true" ]; then
  NEXT_STEPS_LIST+="3. Extract publisher profile:\n"
  NEXT_STEPS_LIST+="   writing-rules-skill publisher --auto-discover\n\n"
fi

# Style not extracted
if [ "$STYLE_EXTRACTED" != "true" ]; then
  NEXT_STEPS_LIST+="4. Extract style guide:\n"
  NEXT_STEPS_LIST+="   writing-rules-skill style --type corporate --auto-discover\n\n"
fi

# Personas not extracted
if [ "$PERSONAS_EXTRACTED" != "true" ]; then
  NEXT_STEPS_LIST+="5. Extract personas:\n"
  NEXT_STEPS_LIST+="   writing-rules-skill persona --audience-type all --auto-discover\n\n"
fi

# Workflow to create
if [ "$HAS_WORKFLOW" = "true" ]; then
  NEXT_STEPS_LIST+="6. Define workflow:\n"
  NEXT_STEPS_LIST+="   workflow-skill add\n\n"
fi

# Always suggest creating project
NEXT_STEPS_LIST+="7. Create your first project:\n"
NEXT_STEPS_LIST+="   /create-project\n"

# If nothing needed
if [ -z "$NEXT_STEPS_LIST" ]; then
  NEXT_STEPS_LIST="You're all set! Create a project with:\n  /create-project\n"
fi
```

---

## Step 5: Replace Template Placeholders

```bash
# Replace all placeholders
PROFILE_CONTENT="$TEMPLATE"

# Simple replacements
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{CREATED_DATE\}\}/$CREATED_DATE}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{UPDATED_DATE\}\}/$UPDATED_DATE}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{COMPANY_NAME\}\}/$COMPANY_NAME}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{INDUSTRY\}\}/$INDUSTRY}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{TEAM_NAME\}\}/$TEAM_NAME}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{TEAM_ROLE\}\}/$TEAM_ROLE}"

# Lists (using printf for newlines)
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{GOALS_LIST\}\}/$(printf "$GOALS_LIST")}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{CONTENT_TYPES_LIST\}\}/$(printf "$CONTENT_TYPES_LIST")}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{KNOWN_PERSONAS_LIST\}\}/$(printf "$KNOWN_PERSONAS_LIST")}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{TO_DISCOVER_PERSONAS\}\}/$TO_DISCOVER_PERSONAS}"

# Sources
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{COMPANY_WEBSITE\}\}/$COMPANY_WEBSITE}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{DOCS_URL\}\}/$DOCS_URL}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{BLOG_URL\}\}/$BLOG_URL}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{OTHER_COMPANY_SOURCES\}\}/$(printf "$OTHER_COMPANY_SOURCES")}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{RESEARCH_SOURCES_LIST\}\}/$(printf "$RESEARCH_SOURCES_LIST")}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{COMPANY_CONTENT_STATUS\}\}/$COMPANY_CONTENT_STATUS}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{RESEARCH_CONTENT_STATUS\}\}/$RESEARCH_CONTENT_STATUS}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{CMS_PLATFORM\}\}/$CMS_PLATFORM}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{CMS_STATUS\}\}/$CMS_STATUS}"

# Analytics (handle conditional sections)
if [ "$ANALYTICS_CONFIGURED" = "true" ]; then
  # Remove the {{^ANALYTICS_CONFIGURED}} section
  PROFILE_CONTENT=$(echo "$PROFILE_CONTENT" | sed '/{{^ANALYTICS_CONFIGURED}}/,/{{\/ANALYTICS_CONFIGURED}}/d')
  # Remove conditional tags
  PROFILE_CONTENT=$(echo "$PROFILE_CONTENT" | sed 's/{{#ANALYTICS_CONFIGURED}}//')
  PROFILE_CONTENT=$(echo "$PROFILE_CONTENT" | sed 's/{{\/ANALYTICS_CONFIGURED}}//')
  # Replace analytics placeholders
  PROFILE_CONTENT=$(echo "$PROFILE_CONTENT" | sed "s|{{#ANALYTICS_DOMAINS}}|$ANALYTICS_DOMAINS|")
  PROFILE_CONTENT=$(echo "$PROFILE_CONTENT" | sed 's/{{\/ANALYTICS_DOMAINS}}//')
else
  # Remove the {{#ANALYTICS_CONFIGURED}} section
  PROFILE_CONTENT=$(echo "$PROFILE_CONTENT" | sed '/{{#ANALYTICS_CONFIGURED}}/,/{{\/ANALYTICS_CONFIGURED}}/d')
  # Remove conditional tags for not-configured section
  PROFILE_CONTENT=$(echo "$PROFILE_CONTENT" | sed 's/{{^ANALYTICS_CONFIGURED}}//')
  PROFILE_CONTENT=$(echo "$PROFILE_CONTENT" | sed 's/{{\/ANALYTICS_CONFIGURED}}//')
fi

# Competitors
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{COMPETITORS_LIST\}\}/$(printf "$COMPETITORS_LIST")}"

# Workflows
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{WORKFLOWS_LIST\}\}/$(printf "$WORKFLOWS_LIST")}"

# Rules
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{PUBLISHER_STATUS\}\}/$PUBLISHER_STATUS}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{PUBLISHER_PATH\}\}/$PUBLISHER_PATH}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{STYLE_COUNT\}\}/$STYLE_COUNT}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{STYLE_LIST\}\}/$(printf "$STYLE_LIST")}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{STRUCTURE_COUNT\}\}/$STRUCTURE_COUNT}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{STRUCTURE_LIST\}\}/$(printf "$STRUCTURE_LIST")}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{PERSONA_COUNT\}\}/$PERSONA_COUNT}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{PERSONA_LIST\}\}/$(printf "$PERSONA_LIST")}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{CUSTOM_RULES_STATUS\}\}/$(printf "$CUSTOM_RULES_STATUS")}"

# Content stats
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{TOTAL_DOCS\}\}/$TOTAL_DOCS}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{COMPANY_DOCS\}\}/$FETCHED_DOCS}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{RESEARCH_DOCS\}\}/0}"
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{LAST_INDEXED\}\}/$CREATED_DATE}"

# Next steps
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{NEXT_STEPS_LIST\}\}/$(printf "$NEXT_STEPS_LIST")}"

# User notes (empty for now)
PROFILE_CONTENT="${PROFILE_CONTENT//\{\{USER_NOTES\}\}/}"
```

---

## Step 6: Write Profile File

```bash
echo "Creating your Kurt profile..."

# Write to .kurt/profile.md
echo "$PROFILE_CONTENT" > .kurt/profile.md

if [ $? -eq 0 ]; then
  echo "✓ Profile created: .kurt/profile.md"
else
  echo "❌ Error: Could not create profile file"
  echo ""
  echo "Check permissions on .kurt/ directory"
  exit 1
fi
```

---

## Step 7: Display Profile Preview

```
───────────────────────────────────────────────────────
Profile Created
───────────────────────────────────────────────────────

Company: {{COMPANY_NAME}}
Team: {{TEAM_NAME}}
Content types: {{CONTENT_TYPE_COUNT}}
Rules extracted: {{RULES_EXTRACTED_COUNT}}
Content indexed: {{TOTAL_DOCS}} documents

───────────────────────────────────────────────────────

View your full profile:
  cat .kurt/profile.md

Update your profile anytime by editing:
  .kurt/profile.md
```

---

## Step 8: Return Success

Return success to parent skill for final success message.

---

## Error Handling

**If template missing:**
```
❌ Error: Profile template not found

Expected: .kurt/templates/profile-template.md

Please check your Kurt plugin installation.
```

**If .kurt/ directory not writable:**
```
❌ Error: Cannot write to .kurt/ directory

Check permissions:
  ls -la .kurt/
```

**If data file missing:**
```
❌ Error: Onboarding data not found

Expected: .kurt/temp/onboarding-data.json

This file should have been created by the questionnaire subskill.
Please restart onboarding: /start
```

---

## Output

Creates `.kurt/profile.md` with complete team profile based on all collected data.

---

*This subskill generates the final profile file from collected onboarding data.*
