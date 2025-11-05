# Map Content Subskill

**Purpose:** Map and fetch content from sources captured in questionnaire
**Parent Skill:** onboarding-skill
**Input:** `.kurt/temp/onboarding-data.json`
**Output:** Updates JSON with content statistics

---

## Overview

This subskill takes the sources from the questionnaire and:
1. Maps content using `kurt map url`
2. Optionally fetches content using `kurt fetch`
3. Updates onboarding-data.json with content stats

---

## Step 1: Load Sources from JSON

```bash
# Read sources from onboarding data
COMPANY_WEBSITE=$(jq -r '.company_website // empty' .kurt/temp/onboarding-data.json)
DOCS_URL=$(jq -r '.docs_url // empty' .kurt/temp/onboarding-data.json)
RESEARCH_SOURCES=$(jq -r '.research_sources[]?' .kurt/temp/onboarding-data.json)
CMS_PLATFORM=$(jq -r '.cms_platform // "none"' .kurt/temp/onboarding-data.json)
CMS_CONFIGURED=$(jq -r '.cms_configured // false' .kurt/temp/onboarding-data.json)

# Build list of all URLs to map
URLS_TO_MAP=()
[ -n "$COMPANY_WEBSITE" ] && URLS_TO_MAP+=("$COMPANY_WEBSITE")
[ -n "$DOCS_URL" ] && URLS_TO_MAP+=("$DOCS_URL")
while IFS= read -r url; do
  [ -n "$url" ] && URLS_TO_MAP+=("$url")
done <<< "$RESEARCH_SOURCES"
```

---

## Step 2: Map Content Sources

```
───────────────────────────────────────────────────────
Mapping Content Sources
───────────────────────────────────────────────────────
```

**For each URL:**

```bash
for url in "${URLS_TO_MAP[@]}"; do
  echo ""
  echo "Discovering content from: $url"
  echo ""

  # Map URL with clustering
  kurt map url "$url" --cluster-urls

  if [ $? -eq 0 ]; then
    echo "✓ Mapped successfully"
  else
    echo "⚠️  Failed to map: $url"
    echo ""
    echo "Options:"
    echo "  a) Retry"
    echo "  b) Skip this source"
    echo "  c) Cancel mapping"
    echo ""
    read -p "Choose: " choice

    case "$choice" in
      a)
        # Retry
        kurt map url "$url" --cluster-urls
        ;;
      b)
        # Skip
        echo "Skipped: $url"
        continue
        ;;
      c)
        # Cancel
        echo "Mapping cancelled"
        exit 1
        ;;
    esac
  fi
done
```

**If CMS configured:**

```bash
if [ "$CMS_CONFIGURED" = "true" ] && [ "$CMS_PLATFORM" != "none" ]; then
  echo ""
  echo "Mapping CMS content from: $CMS_PLATFORM"
  echo ""

  # Map CMS with clustering
  kurt map cms --platform "$CMS_PLATFORM" --cluster-urls

  if [ $? -eq 0 ]; then
    echo "✓ CMS content mapped"
  else
    echo "⚠️  Failed to map CMS content"
  fi
fi
```

---

## Step 3: Display Mapping Summary

```bash
# Get content statistics
TOTAL_MAPPED=$(kurt content list --with-status NOT_FETCHED | wc -l)
CLUSTERS=$(kurt cluster-urls --format json | jq '. | length')
```

```
───────────────────────────────────────────────────────
Content Discovery Summary
───────────────────────────────────────────────────────

✓ Discovered {{TOTAL_MAPPED}} documents
✓ Organized into {{CLUSTERS}} topic clusters

{{#if COMPANY_WEBSITE}}
  • {{COMPANY_WEBSITE}}: {{COMPANY_PAGES}} pages
{{/if}}
{{#if DOCS_URL}}
  • {{DOCS_URL}}: {{DOCS_PAGES}} pages
{{/if}}
{{#each RESEARCH_SOURCES}}
  • {{this}}: {{PAGES}} pages
{{/each}}
{{#if CMS_CONFIGURED}}
  • CMS ({{CMS_PLATFORM}}): {{CMS_DOCS}} documents
{{/if}}

───────────────────────────────────────────────────────

Would you like to fetch this content now? (y/n):
```

**Wait for user response**

---

## Step 4: Fetch Content (If User Confirms)

**If yes:**

```
Fetching and indexing content...
This may take a few minutes...
```

```bash
# Fetch all mapped content
kurt fetch --with-status NOT_FETCHED

if [ $? -eq 0 ]; then
  FETCHED_COUNT=$(kurt content list --with-status FETCHED | wc -l)
  echo ""
  echo "✓ $FETCHED_COUNT documents fetched and indexed"
  echo "✓ Content ready for analysis"
  echo ""

  # Update JSON
  jq '.content_fetched = true' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
else
  echo "⚠️  Some content failed to fetch"
  echo ""
  echo "You can retry later with: kurt fetch --with-status NOT_FETCHED"
  echo ""

  # Update JSON with partial fetch
  jq '.content_fetched = false' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
fi
```

**If no:**

```
Skipped. You can fetch content later with:
  kurt fetch --with-status NOT_FETCHED
```

```bash
# Update JSON
jq '.content_fetched = false' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
```

---

## Step 5: Update JSON with Content Stats

```bash
# Get final stats
TOTAL_DOCS=$(kurt content list | wc -l)
FETCHED_DOCS=$(kurt content list --with-status FETCHED | wc -l)
NOT_FETCHED_DOCS=$(kurt content list --with-status NOT_FETCHED | wc -l)

# Update JSON with stats
jq --arg total "$TOTAL_DOCS" \
   --arg fetched "$FETCHED_DOCS" \
   --arg not_fetched "$NOT_FETCHED_DOCS" \
   '.content_stats = {
     "total_documents": ($total | tonumber),
     "fetched": ($fetched | tonumber),
     "not_fetched": ($not_fetched | tonumber)
   }' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json

mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
```

---

## Step 6: Return Control to Parent

Return success. Parent skill (onboarding-skill) continues to next step (extract-foundation).

---

## Error Handling

**If kurt CLI not available:**
```
❌ Error: kurt CLI not found

Please install kurt-core:
  pip install kurt-core

Then verify installation:
  kurt --version
```

Exit with error code 1.

**If kurt database not initialized:**
```
❌ Error: Kurt database not initialized

Please run:
  kurt init

Then retry: /start
```

Exit with error code 1.

**If all URLs fail to map:**
```
⚠️  No content could be mapped

This might be because:
  • URLs are inaccessible
  • No sitemap found and crawling failed
  • Network issues

Options:
  a) Retry with different URLs
  b) Skip content mapping (add sources later)
  c) Cancel onboarding

Choose: _
```

**If fetch fails:**
```
⚠️  Content fetch failed

Error: {{ERROR_MESSAGE}}

Options:
  a) Retry fetch
  b) Continue without fetching (can fetch later)
  c) Cancel onboarding

Choose: _
```

---

## Output Format

Updates `.kurt/temp/onboarding-data.json` with:

```json
{
  ...existing fields...,
  "content_fetched": true,
  "content_stats": {
    "total_documents": 47,
    "fetched": 47,
    "not_fetched": 0
  }
}
```

---

*This subskill handles all content mapping and fetching using kurt CLI.*
