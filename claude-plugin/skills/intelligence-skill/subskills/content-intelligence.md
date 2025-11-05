# Content Intelligence Subskill

**Purpose:** Content analysis combining metadata + analytics for project planning
**Parent Skill:** intelligence
**Operations:** identify-affected, audit-traffic, impact-estimate, compare-gaps, compare-coverage, compare-quality

---

## Overview

Provides content analysis for project planning by combining content metadata with traffic data. These operations help identify which content needs work and estimate opportunities.

**Primary use:** Project planning (Step 4 - identify targets)

**When to use:**
- Finding content to update (identify-affected, audit-traffic)
- Estimating value of new content (impact-estimate)
- Competitive analysis (compare-gaps, compare-coverage, compare-quality)

**Competitor domain handling:**
- When used during project creation (Step 4), competitor domain is passed as parameter
- When used within an existing project, read competitor from project.md "Competitor Context" section:
  ```bash
  # Extract competitor domain from current project
  COMPETITOR=$(grep "^**Analyzing:**" project.md | cut -d' ' -f2)
  ```
- For gap/competitive analysis projects, the specific competitor being analyzed is stored in project.md and should be used for all operations

---

## Operations

### 1. `identify-affected --search-term <term> [--content-type <type>]`

**Purpose:** Find content by keyword with traffic-based prioritization

**What it does:**
- Searches for content matching the term
- Gets traffic data for matching pages
- Categorizes by traffic level (HIGH/MEDIUM/LOW/ZERO)
- Prioritizes by urgency (traffic × trend)

**Implementation:**
```bash
# Get content matching term with analytics
kurt content list --include "*<term>*" --with-analytics --order-by pageviews_30d

# With content type filter
kurt content list --include "*<term>*" --with-content-type <type> --with-analytics --order-by pageviews_30d

# Get traffic thresholds for categorization
kurt content stats --with-analytics --format json
```

**Example:**
```
intelligence identify-affected --search-term "bigquery" --content-type tutorial

Found 23 tutorials matching "bigquery":

🚨 CRITICAL (high traffic + declining):
1. "Python SDK Guide" - 2,103 views/month, ↓ -8%, 720 days old

🎯 HIGH (high traffic):
2. "BigQuery Quickstart" - 3,421 views/month, ↑ +15%, 850 days old
3. "SQL Best Practices" - 1,850 views/month, → stable

📊 MEDIUM (medium traffic): 10 tutorials
📝 LOW (low traffic): 5 tutorials
⚠️ ZERO TRAFFIC: 2 tutorials

Recommendation: Start with CRITICAL, then HIGH priority items
```

---

### 2. `audit-traffic --domain <domain>`

**Purpose:** Comprehensive traffic audit identifying issues

**What it does:**
- Analyzes all content for domain
- Identifies high-traffic stale pages (>365 days old)
- Finds declining traffic pages
- Locates zero-traffic orphaned content

**Implementation:**
```bash
# Get traffic overview
kurt content stats --include "*<domain>*" --with-analytics

# Find declining high-traffic pages
kurt content list --include "*<domain>*" --with-analytics --trend decreasing --min-pageviews 1000

# Find zero-traffic pages
kurt content list --include "*<domain>*" --with-analytics --max-pageviews 0

# Get top pages to check staleness
kurt content list --include "*<domain>*" --with-analytics --order-by pageviews_30d --limit 20
```

**Example:**
```
intelligence audit-traffic --domain docs.company.com

Traffic Audit: docs.company.com
- 234 total pages
- 222 with traffic (95%)
- 12 ZERO traffic (5%)

🚨 HIGH-TRAFFIC STALE (10 pages need refresh):
1. "BigQuery Quickstart" (3,421 views, 850 days old)

📉 DECLINING TRAFFIC (14 pages need investigation):
1. "Python SDK Guide" (↓ -8%, -168 views/month)

⚠️ ZERO TRAFFIC (12 pages orphaned or deprecated)

Recommendations:
1. Update 10 high-traffic stale pages (max impact)
2. Investigate 14 declining pages (prevent further drops)
3. Audit 12 zero-traffic pages (clean up or improve)
```

---

### 3. `impact-estimate --topic <topic> --domain <domain>`

**Purpose:** Estimate traffic potential of creating new content

**What it does:**
- Finds existing content related to topic
- Calculates total and average traffic
- Estimates potential for new content on topic

**Implementation:**
```bash
# Find related content with traffic
kurt content list --include "*<topic>*" --include "*<domain>*" --with-analytics --order-by pageviews_30d

# Get stats for this subset
kurt content stats --include "*<topic>*" --include "*<domain>*" --with-analytics --format json
```

**Example:**
```
intelligence impact-estimate --topic "security" --domain docs.company.com

Impact Estimate: Missing "Security" documentation

Related Content: 8 pages related to security/authentication
Total traffic: 8,500 views/month
Average: 1,062 views/month per page

Impact Assessment: 🎯 HIGH IMPACT
- Related content gets 8,500+ views/month
- Security is critical topic
- Competitors have 5-8 security docs each

Estimated traffic for new security docs: 500-2000 views/month per page

Recommendation: Create security documentation suite
```

---

### 4. `compare-gaps --own <domain> --competitor <domain>`

**Purpose:** Find missing content vs competitor

**What it does:**
- Compares your content to competitor's
- Identifies topics they cover that you don't
- Prioritizes gaps by strategic value

**Implementation:**
```bash
# List your content by cluster
kurt content list-clusters
kurt content list --include "*<own-domain>*"

# List competitor content by cluster
kurt content list --include "*<competitor-domain>*"

# Compare topics covered (manual analysis of clusters)
```

**Example:**
```
intelligence compare-gaps --own docs.yourco.com --competitor docs.competitor.com

Content Gap Analysis: yourco vs competitor

MISSING TOPICS (they have, you don't):

🎯 HIGH PRIORITY:
1. Security & Compliance (8 docs)
2. Integration Guides (12 docs)

📊 MEDIUM PRIORITY:
3. Advanced Features (5 docs)
4. Troubleshooting (7 docs)

Recommendation: Focus on Security & Compliance first
```

---

### 5. `compare-coverage --own <domain> --competitor <domain>`

**Purpose:** Compare content type and topic coverage

**What it does:**
- Counts content by type for both domains
- Compares topic cluster coverage
- Shows coverage gaps

**Implementation:**
```bash
# Get counts by content type for your domain
kurt content list --include "*<own-domain>*" --with-content-type tutorial
kurt content list --include "*<own-domain>*" --with-content-type guide
# ... repeat for other types

# Same for competitor
kurt content list --include "*<competitor-domain>*" --with-content-type tutorial
kurt content list --include "*<competitor-domain>*" --with-content-type guide

# Compare cluster coverage
kurt content list-clusters
```

**Example:**
```
intelligence compare-coverage --own docs.yourco.com --competitor docs.competitor.com

Content Coverage Comparison:

CONTENT TYPE:
Type            | Yours | Theirs | Gap
Tutorials       |   15  |   28   | -13 ⚠️
Guides          |   18  |   32   | -14 ⚠️
Examples        |    8  |   24   | -16 ⚠️

TOPIC COVERAGE:
Topic          | Yours | Theirs | Coverage
Integrations   |    6  |   24   | 25% 🚨
Authentication |    8  |   15   | 53% ⚠️

Recommendations:
1. Add 13+ tutorials (biggest gap)
2. Expand integrations coverage
```

---

### 6. `compare-quality --own <domain> --competitor <domain>`

**Purpose:** Compare content depth and quality metrics

**What it does:**
- Compares average word count by content type
- Compares code examples per doc
- Compares update frequency

**Implementation:**
```bash
# Get content details with metadata
kurt content list --include "*<own-domain>*" --format json
kurt content list --include "*<competitor-domain>*" --format json

# Analyze metadata fields:
# - word_count (from metadata)
# - has_code_examples (from structural elements)
# - last_updated (from published_date/updated_at)
```

**Example:**
```
intelligence compare-quality --own docs.yourco.com --competitor docs.competitor.com

Content Quality Comparison:

DEPTH METRICS:
Tutorials:
  Avg word count:     1,200 vs 2,400  ⚠️ (50% of theirs)
  Code examples/doc:    1.2 vs 3.8    ⚠️

UPDATE FREQUENCY:
Your content: 3 updates/month, avg age 420 days
Their content: 15 updates/month, avg age 180 days ⚠️

Recommendations:
1. Expand tutorials (50% shorter than theirs)
2. Add more code examples
3. Update more frequently
```

---

## Error Handling

### Analytics not configured
```
⚠️ Analytics required for this operation

To enable:
1. kurt analytics onboard <domain>
2. kurt analytics sync <domain>
```

### No results found
```
No content found matching criteria

Try:
- Broader search term
- Check content is fetched: kurt content list
```

### Competitor content not indexed
```
⚠️ Competitor content not indexed yet

To analyze competitor:
1. kurt map url <competitor-url>
2. kurt fetch --include "<competitor-domain>/*"
3. Re-run comparison
```

---

## Key Principles

1. **Traffic-based prioritization** - Factor in traffic + urgency for maximum impact
2. **Actionable recommendations** - Always suggest specific next steps
3. **Context for planning** - Used during project planning (Step 4)
4. **Visual hierarchy** - Clear categories (CRITICAL/HIGH/MEDIUM/LOW/ZERO)
