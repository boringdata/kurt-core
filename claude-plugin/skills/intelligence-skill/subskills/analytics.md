# Analytics Subskill

**Purpose:** Traffic analysis and analytics queries
**Parent Skill:** intelligence
**Operations:** onboard, sync, list, top, bottom, trending, declining, check, summary

---

## Overview

Provides analytics integration (PostHog) and traffic-based content queries. Use this for:
- Setting up analytics tracking
- Finding high/low traffic pages
- Identifying declining content (needs updates)
- Spotting trending content (expand topics)
- Traffic-based prioritization

---

## Analytics Setup Operations

### 1. Onboard Analytics Domain

**Purpose:** Register a domain for analytics tracking

**Command:**
```bash
kurt analytics onboard <domain> [--platform posthog] [--sync-now]
```

**First run:** Creates `.kurt/analytics-config.json` template
**Second run:** Tests connection and registers domain

**Example:**
```
kurt analytics onboard docs.company.com
kurt analytics onboard docs.company.com --sync-now
```

---

### 2. Sync Analytics Data

**Purpose:** Pull latest traffic data from PostHog

**Command:**
```bash
kurt analytics sync <domain> [--period 60] [--force]
kurt analytics sync --all  # Sync all configured domains
```

**Example:**
```
kurt analytics sync docs.company.com
kurt analytics sync docs.company.com --period 90
kurt analytics sync --all
```

**Notes:**
- Default period: 60 days
- Use `--force` to re-sync even if recently synced
- Data is written to DocumentAnalytics table

---

### 3. List Analytics Domains

**Purpose:** Show all configured analytics domains

**Command:**
```bash
kurt analytics list [--format json]
```

**Example output:**
```
Analytics-enabled domains:

docs.company.com (PostHog)
  Last synced: 2 days ago ⚠️
  Has data: Yes

api.company.com (PostHog)
  Last synced: today
  Has data: Yes
```

---

## Analytics Query Operations

**Prerequisites:** Analytics must be synced first (`kurt analytics sync`)

### 4. Top Pages by Traffic

**Purpose:** Find highest-traffic pages

**Command:**
```bash
kurt content list --with-analytics --order-by pageviews_30d --limit <N>
```

**Example:**
```
kurt content list --with-analytics --order-by pageviews_30d --limit 10
kurt content list --with-analytics --order-by pageviews_30d --limit 20 --include "*docs.company.com*"
```

**Use case:** Identify your most popular content to expand those topics

---

### 5. Bottom Pages / Zero Traffic

**Purpose:** Find lowest-traffic or zero-traffic pages

**Command:**
```bash
# Zero traffic pages (audit candidates)
kurt content list --with-analytics --max-pageviews 0

# Low traffic pages
kurt content list --with-analytics --order-by pageviews_30d --max-pageviews 50 --limit 20
```

**Example:**
```
kurt content list --with-analytics --max-pageviews 0
```

**Use case:** Identify orphaned or deprecated content for cleanup

---

### 6. Trending Pages (Increasing Traffic)

**Purpose:** Find pages with growing traffic

**Command:**
```bash
kurt content list --with-analytics --trend increasing --order-by trend_percentage --limit <N>
```

**Example:**
```
kurt content list --with-analytics --trend increasing --order-by trend_percentage --limit 10
kurt content list --with-analytics --trend increasing --min-pageviews 500 --limit 10
```

**Use case:** Capitalize on momentum by creating related content

---

### 7. Declining Pages (Decreasing Traffic)

**Purpose:** Find pages losing traffic (needs updates)

**Command:**
```bash
kurt content list --with-analytics --trend decreasing --order-by trend_percentage --limit <N>

# Focus on high-traffic pages declining (most urgent)
kurt content list --with-analytics --trend decreasing --min-pageviews 1000 --limit 10
```

**Example:**
```
kurt content list --with-analytics --trend decreasing --min-pageviews 1000 --limit 10
```

**Use case:** Prioritize high-traffic declining pages for urgent updates

---

### 8. Check Traffic for Specific URLs

**Purpose:** Get traffic data for URL pattern

**Command:**
```bash
kurt content list --include "<pattern>" --with-analytics
```

**Example:**
```
kurt content list --include "*bigquery*" --with-analytics
kurt content list --include "*/tutorials/*" --with-analytics --order-by pageviews_30d
```

**Use case:** Analyze traffic for specific content sections

---

### 9. Traffic Summary / Overview

**Purpose:** Get overall analytics statistics

**Command:**
```bash
kurt content stats --with-analytics [--include "<pattern>"]
```

**Example:**
```
kurt content stats --with-analytics
kurt content stats --include "*docs.company.com*" --with-analytics
```

**Example output:**
```
Document Statistics:
─────────────────────────────────────────
Total Documents:     234
  Not Fetched:       12
  Fetched:           220
  Error:             2

Traffic Statistics (30 days):
─────────────────────────────────────────
  Total Pageviews:   156,789
  Average:           456.7 views/page
  Median:            123 views/page
  P75 (HIGH):        890 views
  P25 (LOW):         45 views

Traffic Tiers:
  ZERO traffic:       12 pages ( 5%)
  LOW:                58 pages (25%)
  MEDIUM:            116 pages (50%)
  HIGH:               48 pages (21%)

Trends:
  Increasing ↑:       67 pages (29%)
  Stable →:           89 pages (38%)
  Decreasing ↓:       78 pages (33%)
```

**Use case:** Quick health check of content traffic distribution

---

## Complete Setup Workflow

**1. Configure PostHog credentials**
```bash
# First run creates template
kurt analytics onboard docs.company.com

# Edit .kurt/analytics-config.json with your credentials
# Then run again to test connection
kurt analytics onboard docs.company.com
```

**2. Initial sync**
```bash
kurt analytics sync docs.company.com --period 90
```

**3. Verify data**
```bash
kurt analytics list
kurt content stats --with-analytics
```

**4. Keep data fresh**
```bash
# Run periodically (e.g., daily cron job)
kurt analytics sync --all
```

---

## Common Workflows

### Workflow 1: Find urgent update candidates
```bash
# High-traffic pages that are declining (most critical)
kurt content list --with-analytics --trend decreasing --min-pageviews 1000 --limit 10
```

### Workflow 2: Audit zero-traffic content
```bash
# Find zero-traffic pages for cleanup
kurt content list --with-analytics --max-pageviews 0
```

### Workflow 3: Identify expansion opportunities
```bash
# Find trending high-traffic topics
kurt content list --with-analytics --trend increasing --min-pageviews 500 --limit 10
```

### Workflow 4: Domain health check
```bash
# Get traffic overview for a domain
kurt content stats --include "*docs.company.com*" --with-analytics
```

---

## Error Handling

### Analytics not configured
```
⚠️ Analytics not configured for this domain

To enable:
1. kurt analytics onboard <domain>
2. Edit .kurt/analytics-config.json with PostHog credentials
3. kurt analytics sync <domain>
```

### No analytics data
```
⚠️ No analytics data available

Check:
1. Has analytics been synced? kurt analytics list
2. Run sync: kurt analytics sync <domain>
3. Verify content exists: kurt content list --include "*<domain>*"
```

### Analytics data stale
```
⚠️ Analytics data is stale (last synced: 10 days ago)

Recommendation:
kurt analytics sync <domain>
```

---

## Tips

**Traffic Categorization:**
- **ZERO**: 0 pageviews → Orphaned or deprecated content
- **LOW**: ≤ P25 (25th percentile) → Limited reach
- **MEDIUM**: P25 < views ≤ P75 → Normal traffic
- **HIGH**: > P75 (75th percentile) → Popular content

**Prioritization:**
1. **CRITICAL**: High-traffic + declining → Immediate updates needed
2. **HIGH**: Medium/High-traffic + declining → Update soon
3. **MEDIUM**: Zero traffic → Audit and cleanup
4. **LOW**: Low traffic + stable → Monitor
