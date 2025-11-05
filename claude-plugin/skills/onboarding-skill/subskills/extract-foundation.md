# Extract Foundation Subskill

**Purpose:** Extract foundation rules (publisher, style, personas) from fetched content
**Parent Skill:** onboarding-skill
**Input:** `.kurt/temp/onboarding-data.json`
**Output:** Updates JSON with extracted rule paths

---

## Overview

This subskill extracts the core rules needed for consistent content creation:
1. Publisher profile (company context)
2. Style guide (writing voice)
3. Target personas (audience profiles)

---

## Step 1: Check Content Status

```bash
# Check if content was fetched
CONTENT_FETCHED=$(jq -r '.content_fetched' .kurt/temp/onboarding-data.json)

if [ "$CONTENT_FETCHED" != "true" ]; then
  echo "⚠️  Content not fetched yet"
  echo ""
  echo "Foundation rules require indexed content for extraction."
  echo ""
  echo "Options:"
  echo "  a) Skip rule extraction (can extract later)"
  echo "  b) Go back and fetch content"
  echo "  c) Cancel onboarding"
  echo ""
  read -p "Choose: " choice

  case "$choice" in
    a)
      # Skip extraction
      jq '.rules_extracted.skipped = true' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
      mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
      exit 0
      ;;
    b)
      # Invoke map-content again
      echo "Returning to content fetching..."
      exit 2  # Signal to parent to re-run map-content
      ;;
    c)
      echo "Onboarding cancelled"
      exit 1
      ;;
  esac
fi

# Check minimum content requirement
FETCHED_COUNT=$(jq -r '.content_stats.fetched' .kurt/temp/onboarding-data.json)

if [ "$FETCHED_COUNT" -lt 3 ]; then
  echo "⚠️  Insufficient content for reliable rule extraction"
  echo ""
  echo "Found: $FETCHED_COUNT documents"
  echo "Recommended: 5-10 documents minimum"
  echo ""
  echo "Options:"
  echo "  a) Continue anyway (rules may be less reliable)"
  echo "  b) Add more content sources"
  echo "  c) Skip rule extraction"
  echo ""
  read -p "Choose: " choice

  case "$choice" in
    a)
      echo "Continuing with available content..."
      ;;
    b)
      echo "Please add more content sources, then retry /start"
      exit 1
      ;;
    c)
      jq '.rules_extracted.skipped = true' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
      mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
      exit 0
      ;;
  esac
fi
```

---

## Step 2-4: Extract Foundation Rules

**Delegate to extract-rules subskill:**

```
───────────────────────────────────────────────────────
Extracting Foundation Rules
───────────────────────────────────────────────────────

Analyzing your content to extract:
• Publisher profile (company context)
• Primary voice (writing style)
• Personas (audience profiles)
```

**Invoke:** `project-management extract-rules --foundation-only`

This delegates to the extract-rules subskill which will:
1. Check prerequisites (content indexed)
2. Show preview of documents to analyze
3. Extract publisher profile
4. Extract primary voice
5. Extract personas
6. Show summary of extracted rules

**The extract-rules subskill owns the extraction logic and provides:**
- Document preview before extraction
- Progress reporting
- Error handling
- Retry logic

**After extraction completes:**

```bash
# Get paths of extracted rules
PUBLISHER_PATH=$(ls rules/publisher/publisher-profile.md 2>/dev/null)
STYLE_FILES=$(ls rules/style/*.md 2>/dev/null)
PERSONA_FILES=$(ls rules/personas/*.md 2>/dev/null)
PERSONA_COUNT=$(echo "$PERSONA_FILES" | wc -l | tr -d ' ')

# Update JSON with rule paths
if [ -n "$PUBLISHER_PATH" ]; then
  jq --arg path "$PUBLISHER_PATH" \
     '.rules_extracted.publisher = {
       "extracted": true,
       "path": $path
     }' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
else
  jq '.rules_extracted.publisher = {
    "extracted": false,
    "error": "Extraction failed or skipped"
  }' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
fi

if [ -n "$STYLE_FILES" ]; then
  STYLE_FILE=$(echo "$STYLE_FILES" | head -1)
  STYLE_NAME=$(basename "$STYLE_FILE" .md)

  jq --arg path "$STYLE_FILE" \
     --arg name "$STYLE_NAME" \
     '.rules_extracted.style = {
       "extracted": true,
       "path": $path,
       "name": $name
     }' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
else
  jq '.rules_extracted.style = {
    "extracted": false,
    "error": "Extraction failed or skipped"
  }' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
fi

if [ "$PERSONA_COUNT" -gt 0 ]; then
  PERSONAS_JSON=$(echo "$PERSONA_FILES" | jq -R -s 'split("\n") | map(select(length > 0))')

  jq --argjson personas "$PERSONAS_JSON" \
     --arg count "$PERSONA_COUNT" \
     '.rules_extracted.personas = {
       "extracted": true,
       "count": ($count | tonumber),
       "files": $personas
     }' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
else
  jq '.rules_extracted.personas = {
    "extracted": false,
    "error": "Extraction failed or skipped"
  }' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
fi
```

---

## Step 5: Summary

```
───────────────────────────────────────────────────────
Foundation Rules Extracted
───────────────────────────────────────────────────────

{{#if PUBLISHER_EXTRACTED}}
✓ Publisher Profile
  rules/publisher/publisher-profile.md
{{/if}}

{{#if STYLE_EXTRACTED}}
✓ Style Guide ({{STYLE_TYPE}})
  {{STYLE_PATH}}
{{/if}}

{{#if PERSONAS_EXTRACTED}}
✓ Personas ({{PERSONA_COUNT}})
{{#each PERSONA_FILES}}
  {{this}}
{{/each}}
{{/if}}

{{#if ANY_FAILED}}
⚠️  Some extractions failed

You can extract missing rules later with:
{{#if NOT PUBLISHER_EXTRACTED}}  writing-rules-skill publisher --auto-discover{{/if}}
{{#if NOT STYLE_EXTRACTED}}  writing-rules-skill style --type corporate --auto-discover{{/if}}
{{#if NOT PERSONAS_EXTRACTED}}  writing-rules-skill persona --audience-type all --auto-discover{{/if}}
{{/if}}
```

---

## Step 6: Return Control

Return success. Parent skill continues to create-profile step.

---

## Error Handling

**If writing-rules-skill not available:**
```
❌ Error: writing-rules-skill not found

This skill should be available in .claude/skills/

Check your Kurt plugin installation.
```

**If all extractions fail:**
```
⚠️  No rules could be extracted

This might be because:
  • Content is insufficient (need 5+ documents)
  • Content is not indexed (need FETCHED status)
  • Content doesn't have clear patterns

Options:
  a) Skip rule extraction (create profile without rules)
  b) Add more content and retry
  c) Cancel onboarding

Choose: _
```

**If partial success:**
```
⚠️  Some rules extracted, but not all

Extracted: {{SUCCESS_LIST}}
Failed: {{FAILED_LIST}}

Continue with partial extraction? (y/n):
```

---

## Output Format

Updates `.kurt/temp/onboarding-data.json` with:

```json
{
  ...existing fields...,
  "rules_extracted": {
    "publisher": {
      "extracted": true,
      "path": "rules/publisher/publisher-profile.md"
    },
    "style": {
      "extracted": true,
      "path": "rules/style/technical-developer-voice.md",
      "name": "technical-developer-voice",
      "type": "technical-docs"
    },
    "personas": {
      "extracted": true,
      "count": 2,
      "files": [
        "rules/personas/backend-engineer.md",
        "rules/personas/platform-engineer.md"
      ]
    }
  }
}
```

---

*This subskill extracts foundation rules using the writing-rules-skill.*
