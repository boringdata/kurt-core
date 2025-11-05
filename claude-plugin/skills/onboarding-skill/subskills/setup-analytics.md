# Setup Analytics Subskill

**Purpose:** Configure analytics for organizational domains (optional)
**Parent Skill:** onboarding-skill
**Input:** `.kurt/temp/onboarding-data.json`
**Output:** Updates JSON with analytics configuration

---

## Overview

This subskill offers analytics setup for the domains discovered during content mapping:
1. Detects which domains have content
2. Offers analytics setup (PostHog) for each domain
3. Tests connection and syncs initial data
4. Updates onboarding-data.json with analytics config

**Analytics is optional** - users can skip or set up later.

---

## Step 1: Check Prerequisites

```bash
# Verify content has been mapped
CONTENT_FETCHED=$(jq -r '.content_fetched // false' .kurt/temp/onboarding-data.json)

if [ "$CONTENT_FETCHED" != "true" ]; then
  echo "⚠️  No content fetched yet. Skipping analytics setup."
  echo ""
  echo "You can set up analytics later with:"
  echo "  kurt analytics onboard <domain>"
  echo ""

  # Update JSON and skip
  jq '.analytics_configured = false | .analytics_skipped = true' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json

  exit 0
fi
```

---

## Step 2: Detect Domains from Content

```bash
# Get unique domains from fetched content
DOMAINS=$(kurt content list --with-status FETCHED --format json | \
  jq -r '.[] | .source_url' | \
  sed -E 's|^https?://([^/]+).*|\1|' | \
  sed 's/^www\.//' | \
  sort -u)

# Count domains
DOMAIN_COUNT=$(echo "$DOMAINS" | wc -l | tr -d ' ')

if [ "$DOMAIN_COUNT" -eq 0 ]; then
  echo "⚠️  No domains found in content. Skipping analytics."
  jq '.analytics_configured = false | .analytics_skipped = true' .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
  mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
  exit 0
fi
```

---

## Step 3: Offer Analytics Setup

```
───────────────────────────────────────────────────────
Analytics Integration (Optional)
───────────────────────────────────────────────────────
```

**Explain benefits:**

```
💡 Analytics Integration

Kurt can integrate with PostHog web analytics to help you:
  • Prioritize high-traffic pages for updates
  • Identify pages losing traffic (needs refresh)
  • Spot zero-traffic pages (potentially orphaned)
  • Make data-driven content decisions

Example: When updating tutorials, Kurt will prioritize the ones
getting the most traffic for maximum impact.

Setup takes ~2-3 minutes per domain.
```

**Show detected domains:**

```
We detected content from {{DOMAIN_COUNT}} domain(s):
{{#each DOMAINS}}
  • {{this}}
{{/each}}

Would you like to set up analytics? (Y/n):
```

**Wait for user response**

---

## Step 4: Handle User Choice

### If User Declines (n)

```
Skipped. You can set up analytics later with:
  kurt analytics onboard <domain>

Continuing without analytics...
```

```bash
# Update JSON
jq '.analytics_configured = false | .analytics_skipped = true | .analytics_domains = []' \
  .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json
mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
```

Return to parent skill.

### If User Accepts (Y/yes)

```
Great! Let's set up analytics for your domains.
```

Continue to Step 5.

---

## Step 5: Configure Analytics for Each Domain

```
───────────────────────────────────────────────────────
Configuring Analytics
───────────────────────────────────────────────────────
```

**For each domain:**

```bash
CONFIGURED_DOMAINS=()

for domain in $DOMAINS; do
  echo ""
  echo "Setting up analytics for: $domain"
  echo ""

  # Prompt for PostHog details
  echo "Platform: PostHog (currently the only supported platform)"
  echo ""

  read -p "PostHog Project ID (phc_...): " PROJECT_ID

  # Validate project ID format
  if [[ ! "$PROJECT_ID" =~ ^phc_ ]]; then
    echo "⚠️  Invalid format. PostHog project IDs start with 'phc_'"
    echo ""
    echo "Options:"
    echo "  a) Retry"
    echo "  b) Skip this domain"
    echo "  c) Skip all analytics"
    echo ""
    read -p "Choose: " choice

    case "$choice" in
      a)
        # Retry this domain
        continue
        ;;
      b)
        # Skip this domain
        echo "Skipped: $domain"
        continue
        ;;
      c)
        # Skip all
        echo "Skipping all analytics setup"
        break
        ;;
    esac
  fi

  read -sp "PostHog API Key (phx_...): " API_KEY
  echo ""

  # Validate API key format
  if [[ ! "$API_KEY" =~ ^phx_ ]]; then
    echo "⚠️  Invalid format. PostHog API keys start with 'phx_'"
    echo ""
    echo "Options:"
    echo "  a) Retry"
    echo "  b) Skip this domain"
    echo ""
    read -p "Choose: " choice

    case "$choice" in
      a)
        # Retry this domain
        continue
        ;;
      b)
        # Skip this domain
        echo "Skipped: $domain"
        continue
        ;;
    esac
  fi

  echo ""
  echo "Testing connection..."

  # Run onboard command
  kurt analytics onboard "https://$domain" \
    --platform posthog \
    --project-id "$PROJECT_ID" \
    --api-key "$API_KEY"

  if [ $? -eq 0 ]; then
    echo "✓ Connected to PostHog"
    echo ""

    # Initial sync
    echo "Syncing initial analytics data..."
    kurt analytics sync "$domain"

    if [ $? -eq 0 ]; then
      echo "✓ Analytics configured for $domain"
      CONFIGURED_DOMAINS+=("$domain")
    else
      echo "⚠️  Sync failed for $domain"
      echo "You can retry later with: kurt analytics sync $domain"
      # Still count as configured since connection works
      CONFIGURED_DOMAINS+=("$domain")
    fi
  else
    echo "❌ Failed to connect to PostHog"
    echo ""
    echo "Please check:"
    echo "  • Project ID is correct"
    echo "  • API key has read permissions"
    echo "  • Network connection is working"
    echo ""
    echo "Options:"
    echo "  a) Retry this domain"
    echo "  b) Skip this domain"
    echo "  c) Skip all remaining domains"
    echo ""
    read -p "Choose: " choice

    case "$choice" in
      a)
        # Retry - will loop again
        continue
        ;;
      b)
        # Skip this domain
        echo "Skipped: $domain"
        continue
        ;;
      c)
        # Skip all remaining
        echo "Skipping remaining domains"
        break
        ;;
    esac
  fi

  echo ""
done
```

---

## Step 6: Display Analytics Summary

```bash
CONFIGURED_COUNT=${#CONFIGURED_DOMAINS[@]}

if [ $CONFIGURED_COUNT -gt 0 ]; then
  echo ""
  echo "───────────────────────────────────────────────────────"
  echo "Analytics Configuration Complete"
  echo "───────────────────────────────────────────────────────"
  echo ""
  echo "✓ Configured analytics for $CONFIGURED_COUNT domain(s):"

  for domain in "${CONFIGURED_DOMAINS[@]}"; do
    # Get stats for this domain
    TOTAL_VIEWS=$(kurt analytics summary "$domain" --format json 2>/dev/null | jq -r '.pageviews_60d_total // 0')
    DOCS_WITH_DATA=$(kurt analytics summary "$domain" --format json 2>/dev/null | jq -r '.documents_with_data // 0')

    echo "  • $domain"
    echo "    - $DOCS_WITH_DATA documents with traffic data"
    if [ "$TOTAL_VIEWS" -gt 0 ]; then
      echo "    - $TOTAL_VIEWS pageviews (last 60 days)"
    fi
  done

  echo ""
  echo "✓ Analytics data will help prioritize content updates"
  echo "✓ Data auto-syncs when stale (>7 days)"
  echo ""
else
  echo ""
  echo "⚠️  No domains configured with analytics"
  echo ""
  echo "You can set up analytics later with:"
  echo "  kurt analytics onboard <domain>"
  echo ""
fi
```

---

## Step 7: Update JSON with Analytics Config

```bash
# Build JSON array of configured domains
DOMAINS_JSON="[]"
for domain in "${CONFIGURED_DOMAINS[@]}"; do
  # Get analytics metadata
  PLATFORM="posthog"
  LAST_SYNCED=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Get traffic stats if available
  STATS=$(kurt analytics summary "$domain" --format json 2>/dev/null || echo '{}')
  PAGEVIEWS_60D=$(echo "$STATS" | jq -r '.pageviews_60d_total // 0')
  DOCS_WITH_DATA=$(echo "$STATS" | jq -r '.documents_with_data // 0')
  P25=$(echo "$STATS" | jq -r '.p25_pageviews_30d // 0')
  P75=$(echo "$STATS" | jq -r '.p75_pageviews_30d // 0')

  # Add to array
  DOMAINS_JSON=$(echo "$DOMAINS_JSON" | jq \
    --arg domain "$domain" \
    --arg platform "$PLATFORM" \
    --arg last_synced "$LAST_SYNCED" \
    --arg pageviews "$PAGEVIEWS_60D" \
    --arg docs_with_data "$DOCS_WITH_DATA" \
    --arg p25 "$P25" \
    --arg p75 "$P75" \
    '. + [{
      "domain": $domain,
      "platform": $platform,
      "last_synced": $last_synced,
      "pageviews_60d": ($pageviews | tonumber),
      "documents_with_data": ($docs_with_data | tonumber),
      "thresholds": {
        "p25": ($p25 | tonumber),
        "p75": ($p75 | tonumber)
      }
    }]')
done

# Update onboarding JSON
jq \
  --argjson domains "$DOMAINS_JSON" \
  --arg configured "$([ $CONFIGURED_COUNT -gt 0 ] && echo 'true' || echo 'false')" \
  '.analytics_configured = ($configured == "true") |
   .analytics_skipped = false |
   .analytics_domains = $domains' \
  .kurt/temp/onboarding-data.json > .kurt/temp/onboarding-data.tmp.json

mv .kurt/temp/onboarding-data.tmp.json .kurt/temp/onboarding-data.json
```

---

## Step 8: Return Control to Parent

Return success. Parent skill (onboarding-skill) continues to next step (extract-foundation).

---

## Error Handling

**If kurt analytics command not available:**
```
❌ Error: Analytics commands not available

Your kurt-core version may not support analytics.

Please upgrade kurt-core:
  pip install --upgrade kurt-core

Then verify:
  kurt analytics --help
```

Exit with error code 1.

**If PostHog connection fails repeatedly:**
```
⚠️  Unable to connect to PostHog after multiple attempts

Common issues:
  • Incorrect project ID or API key
  • Network connectivity problems
  • PostHog service outage

You can:
  • Continue without analytics (skip)
  • Set up analytics later: kurt analytics onboard <domain>
  • Check PostHog status: https://status.posthog.com
```

User can choose to skip or cancel.

**If sync fails but connection works:**
```
⚠️  Connection successful but initial sync failed

This might be temporary. You can:
  • Continue setup (retry sync later)
  • Retry sync now
  • Skip this domain

Analytics will still be configured, but no data yet.
```

---

## Output Format

Updates `.kurt/temp/onboarding-data.json` with:

```json
{
  ...existing fields...,
  "analytics_configured": true,
  "analytics_skipped": false,
  "analytics_domains": [
    {
      "domain": "docs.company.com",
      "platform": "posthog",
      "last_synced": "2025-11-02T12:00:00Z",
      "pageviews_60d": 45234,
      "documents_with_data": 221,
      "thresholds": {
        "p25": 45,
        "p75": 890
      }
    },
    {
      "domain": "blog.company.com",
      "platform": "posthog",
      "last_synced": "2025-11-02T12:05:00Z",
      "pageviews_60d": 12890,
      "documents_with_data": 65,
      "thresholds": {
        "p25": 20,
        "p75": 450
      }
    }
  ]
}
```

---

## Notes

- **Optional step:** Users can skip entirely without blocking onboarding
- **Per-domain:** Each domain gets its own PostHog configuration
- **Validation:** Project ID and API key formats are validated
- **Initial sync:** Runs immediately after setup to get baseline data
- **Error recovery:** Multiple retry options if setup fails
- **Future-proof:** Designed to support additional platforms (GA4, Plausible)

---

*This subskill handles optional analytics setup during onboarding.*
