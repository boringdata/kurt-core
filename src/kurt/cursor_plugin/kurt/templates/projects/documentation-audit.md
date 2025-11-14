<!--
SETUP INSTRUCTIONS FOR CLAUDE:

When a user clones this template, follow these steps:

1. Ask the user:
   - "What domain do you want to audit?" (e.g., docs.company.com)
   - "Do you have analytics configured for this domain?"
   - If no analytics: "Analytics integration required. Run: kurt analytics onboard [domain] --platform posthog"

2. Verify analytics access:
   `kurt analytics list` - confirm domain is configured

3. Run traffic analysis:
   `kurt content list --url-starts-with https://[domain] --with-analytics --format json`

   Look for:
   - High-traffic pages with old lastmod dates (>365 days)
   - Pages with declining traffic trends
   - Pages with zero traffic (orphaned content)

4. Discover topic coverage to categorize issues:
   ```bash
   # See what topics are covered
   kurt content list-topics --include "https://[domain]/**"

   # See what technologies are documented
   kurt content list-technologies --include "https://[domain]/**"
   ```

5. Gather additional context:
   - Product changelog: `kurt content search "changelog"` or `kurt content search "release notes"`
   - Support/feedback: Ask user for common documentation issues from support tickets

6. Categorize findings into audit categories by topic:
   - **CRITICAL**: High-traffic + stale (>365 days old)
   - **HIGH**: Declining traffic (investigate cause)
   - **MEDIUM**: Zero traffic orphaned pages (archive or fix discoverability)
   - **LOW**: Missing content gaps (opportunities)

6. Populate "Audit Findings" section with categorized issues

7. Create action plan based on priority and confirm with user

8. Optionally: Create follow-up projects for major update work
-->

<project_level_details>
# Documentation Audit - {{DOMAIN}}

## Goal
Conduct comprehensive traffic audit of {{DOMAIN}} documentation to identify content health issues: stale high-traffic pages, declining traffic, and orphaned content.

**Prerequisites:**
- ✓ Analytics configured for domain (run `kurt analytics list` to verify)
- ✓ Documentation content fetched (run `kurt content stats` to verify)

## Research Required (Optional)
<!-- Additional context to understand documentation issues -->
- [ ] Product changelog: What's changed recently that might affect docs?
- [ ] Support ticket analysis: What doc issues do customers report?
- [ ] Customer feedback: What documentation pain points exist?

## Analysis Required
<!-- Core audit analysis -->
- [ ] Traffic analysis: Identify high-traffic stale pages (>365 days old)
- [ ] Trend analysis: Find pages with declining traffic
- [ ] Orphaned content: Locate zero-traffic pages
- [ ] Gap analysis: Identify missing documentation topics

</project_level_details>

---

<document_details>

## Audit Findings

### CRITICAL: High-Traffic Stale Content
*Pages with high traffic but outdated (>365 days) - Quick wins, update immediately*

- [ ] {{URL}} - Last updated: {{DATE}}, Pageviews: {{HIGH_NUMBER}}, Issue: {{STALENESS_ISSUE}}
- [ ] {{URL}} - Last updated: {{DATE}}, Pageviews: {{HIGH_NUMBER}}, Issue: {{STALENESS_ISSUE}}
- [ ] {{URL}} - Last updated: {{DATE}}, Pageviews: {{HIGH_NUMBER}}, Issue: {{STALENESS_ISSUE}}

**Priority:** IMMEDIATE - These are high-impact pages serving many users with potentially incorrect info

---

### HIGH: Declining Traffic Pages
*Pages losing traffic - Investigate cause and fix*

- [ ] {{URL}} - Trend: ↓ {{PERCENT}}%, Traffic was: {{OLD_NUMBER}}, Now: {{NEW_NUMBER}}, Possible cause: {{HYPOTHESIS}}
- [ ] {{URL}} - Trend: ↓ {{PERCENT}}%, Traffic was: {{OLD_NUMBER}}, Now: {{NEW_NUMBER}}, Possible cause: {{HYPOTHESIS}}

**Priority:** HIGH - Understand why traffic is declining (competing page? outdated content? product changes?)

---

### MEDIUM: Zero Traffic (Orphaned Content)
*Pages with no traffic - Archive, redirect, or fix discoverability*

- [ ] {{URL}} - 0 pageviews, Created: {{DATE}}, Decision needed: [Archive / Fix discoverability / Remove]
- [ ] {{URL}} - 0 pageviews, Created: {{DATE}}, Decision needed: [Archive / Fix discoverability / Remove]

**Priority:** MEDIUM - Clean up to improve content quality and maintainability

---

### LOW: Missing Content Gaps
*Topics that should have documentation but don't*

- [ ] {{TOPIC}} - Identified from: {{SOURCE}} (support tickets / customer requests / competitor has it)
- [ ] {{TOPIC}} - Identified from: {{SOURCE}}

**Priority:** LOW to MEDIUM - Opportunities to fill gaps, prioritize by demand

---

## Audit Report Summary

**Total pages analyzed:** {{NUMBER}}
**Date range:** {{START_DATE}} to {{END_DATE}}

**Findings:**
- {{NUMBER}} critical (high-traffic stale)
- {{NUMBER}} high-priority (declining traffic)
- {{NUMBER}} medium-priority (orphaned)
- {{NUMBER}} content gaps identified

**Recommended Actions:**
1. Immediate: Update {{NUMBER}} high-traffic stale pages
2. Short-term: Investigate {{NUMBER}} declining pages
3. Long-term: Address {{NUMBER}} orphaned pages and {{NUMBER}} gaps

</document_details>

---

<project_tracking>

## Progress Tracking

### Phase 1: Traffic Analysis
- [ ] Analytics data pulled for {{DOMAIN}}
- [ ] High-traffic pages identified
- [ ] Stale content flagged (>365 days old)
- [ ] Traffic trends analyzed
- [ ] Zero-traffic pages cataloged

### Phase 2: Issue Categorization
- [ ] Issues categorized by priority
- [ ] Root causes investigated
- [ ] Decision made for each orphaned page
- [ ] Content gaps validated

### Phase 3: Action Planning
- [ ] Immediate updates planned (critical issues)
- [ ] Short-term fixes prioritized (high issues)
- [ ] Long-term improvements scheduled (medium/low)
- [ ] Resource allocation confirmed

### Phase 4: Execution
- [ ] Follow-up projects created for major updates
- [ ] Quick fixes completed
- [ ] Audit report shared with team
- [ ] Next audit scheduled

</project_tracking>

---

<sources_and_research>

## Data Sources

### Analytics Data
- Source: {{ANALYTICS_PLATFORM}} for {{DOMAIN}}
- Date range: {{RANGE}}
- Metrics: Pageviews, unique visitors, time on page, bounce rate

### Documentation Content
- Fetched from: {{DOMAIN}}
- Total pages: {{NUMBER}}
- Last fetched: {{DATE}}

### Additional Context
- Product changelog: {{PATH_OR_URL}}
- Support ticket themes: {{SUMMARY}}
- Customer feedback: {{SUMMARY}}

</sources_and_research>

---

## Workflow Instructions

**Step 1: Pull Analytics Data (30 min)**
```bash
# Verify analytics configured
kurt analytics list

# Sync latest data
kurt analytics sync {{DOMAIN}}

# Get content with analytics
kurt content list --url-starts-with https://{{DOMAIN}} --with-analytics
```

**Step 2: Discover Topic Coverage (15 min)**

Understand what topics and technologies are documented:

```bash
# See all topics covered
kurt content list-topics --include "https://{{DOMAIN}}/**"

# See all technologies documented
kurt content list-technologies --include "https://{{DOMAIN}}/**"

# This will help categorize audit issues by topic area
# e.g., "Authentication docs are stale" vs "Payment docs are stale"
```

**Step 3: Identify Issues (1-2 hours)**

Find high-traffic stale pages:
```bash
# Pages with high traffic but old lastmod dates
kurt content list --url-starts-with https://{{DOMAIN}} --with-analytics | \
  # Filter for pages >365 days old with >1000 pageviews
```

Find declining traffic:
```bash
# Compare traffic over time periods
# Identify pages with >30% traffic decrease
```

Find orphaned pages:
```bash
# Pages with 0 pageviews in date range
kurt content list --url-starts-with https://{{DOMAIN}} --with-analytics | \
  # Filter for 0 pageviews
```

**Step 4: Categorize Issues by Topic (1 hour)**

For each issue identified, determine which topic(s) it relates to:

```bash
# Check what topics a specific problematic page covers
kurt content get <doc-id>
# Look at the topics field in metadata

# See all pages on a specific topic
kurt content list --with-topic "authentication" --include "https://{{DOMAIN}}/**"

# Cross-reference with analytics
kurt content list --with-topic "authentication" --with-analytics
```

This helps identify patterns like:
- "All authentication docs are stale"
- "Webhook documentation has declining traffic"
- "API reference pages are orphaned"

**Step 5: Gather Additional Context (30 min)**
```bash
# Find product changes
kurt content search "changelog"
kurt content search "release notes"

# Ask user for support ticket themes
# Ask user for customer feedback on docs
```

**Step 6: Categorize & Prioritize (1 hour)**

For each issue, determine:
- Impact: High traffic = high impact
- Urgency: Stale + high traffic = urgent
- Effort: Quick fix vs major rewrite
- Action: Update / Archive / Investigate
- Topic area: Which topic does this affect?

**Step 7: Create Action Plan (30 min)**

**Immediate (This week):**
- Update top 5-10 high-traffic stale pages
- Critical fixes only

**Short-term (This month):**
- Investigate declining traffic causes
- Fix or archive medium-priority issues

**Long-term (This quarter):**
- Address orphaned content
- Create new content for gaps
- Improve discoverability

**Step 6: Execute (Ongoing)**

Create follow-up projects:
- Major rewrites → New project per page/section
- Quick updates → Batch into single update project
- New content → New content creation project

**Step 7: Report & Schedule (30 min)**
- Share findings with team
- Track progress on updates
- Schedule next audit (quarterly recommended)

---

## Common Patterns & Tips

**High-Traffic Stale = Quick Wins**
- These are your highest ROI updates
- Focus here first
- Users are actively reading outdated info

**Declining Traffic Causes:**
- New competing page was created → Consolidate or redirect
- Content became outdated → Update to current
- Product changed → Reflect new reality
- Search ranking dropped → SEO optimization needed

**Zero Traffic Analysis:**
- Check if page is linked from anywhere → Discoverability issue
- Check if topic is still relevant → May need archiving
- Check if content duplicates another page → Consolidate

**Content Gap Validation:**
- High support volume on topic = definitely needed
- Competitor has it = probably needed
- Product roadmap includes it = will be needed soon
- Old forum posts asking about it = unmet need

---

## Success Metrics

**Audit Completeness:**
- ✓ All pages analyzed
- ✓ Issues categorized
- ✓ Actions prioritized

**Update Progress:**
- X of Y critical pages updated
- X of Y high-priority issues resolved
- X of Y content gaps filled

**Impact Metrics (Track After Updates):**
- Traffic improvements on updated pages
- Reduced support tickets for covered topics
- Improved documentation satisfaction scores

---

## Next Audit

**Frequency:** Quarterly recommended (every 3 months)

**Quick Check (Monthly):**
- New zero-traffic pages
- Major traffic drops
- New high-traffic pages (ensure they stay fresh)

**Full Audit (Quarterly):**
- Complete analysis across all metrics
- Trend analysis over multiple months
- Comprehensive action planning
