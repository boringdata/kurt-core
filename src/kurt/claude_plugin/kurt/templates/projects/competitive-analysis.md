<!--
SETUP INSTRUCTIONS FOR CLAUDE:

When a user clones this template, follow these steps:

1. Ask the user:
   - "Which competitor do you want to analyze?" (get domain)
   - "Has their content been indexed?"
   - If no: "Run: kurt content map url https://[competitor-domain]"
   - Then: "Run: kurt content fetch --include 'https://[competitor-domain]/**'"

2. Verify both content sets indexed:
   `kurt content stats --url-starts-with https://[your-domain]`
   `kurt content stats --url-starts-with https://[competitor-domain]`

3. Identify shared topics and technologies:
   ```bash
   # See what topics each covers
   kurt content list-topics --include "https://[your-domain]/**"
   kurt content list-topics --include "https://[competitor-domain]/**"

   # See what technologies each documents
   kurt content list-technologies --include "https://[your-domain]/**"
   kurt content list-technologies --include "https://[competitor-domain]/**"

   # Also check traditional clusters
   kurt content list-clusters --include "https://[your-domain]/**"
   kurt content list-clusters --include "https://[competitor-domain]/**"
   ```

   Compare lists to find overlapping topics/technologies

4. For each shared topic/technology, compare quality:
   - Retrieve both versions: `kurt content get [doc-id]`
   - Compare on dimensions:
     - Breadth: What subtopics do they cover that we don't?
     - Depth: How detailed are their explanations vs ours?
     - Examples: Do they have more/better code examples?
     - Visuals: Do they use diagrams, screenshots we lack?
     - Structure: Is their organization clearer?
   - Rate: ✅ We're better | 🟡 Equal | ❌ They're better

5. Prioritize gaps using analytics:
   `kurt content list --url-starts-with https://[your-domain] --with-analytics`

   - CRITICAL: High-traffic topics where they're better (❌)
   - HIGH: Medium-traffic topics where they're better (❌)
   - MEDIUM: Low-traffic or minor quality gaps (❌)

6. Populate "Quality Gaps Identified" section with specific improvements

7. Create follow-up projects for top 3-5 improvement items
-->

<project_level_details>
# Competitive Analysis - {{YOUR_DOMAIN}} vs {{COMPETITOR}}

## Goal
Compare our documentation quality against {{COMPETITOR_DOMAIN}} across shared topics to identify where we're weaker and create improvement plan.

**Prerequisites:**
- ✓ Your content indexed: `kurt content stats --url-starts-with https://{{YOUR_DOMAIN}}`
- ✓ Competitor content indexed: `kurt content stats --url-starts-with https://{{COMPETITOR_DOMAIN}}`
- ✓ Analytics configured (optional but recommended): `kurt analytics list`

## Research Required
<!-- Understanding current performance and priorities -->
- [ ] Analytics data: Which topics get the most traffic?
- [ ] Support tickets: Which topics cause confusion or require updates?
- [ ] Customer feedback: What do users say about our docs vs competitors?

## Analysis Required
<!-- Core competitive quality analysis -->
- [ ] Topic identification: What topics do both we and competitor cover?
- [ ] Quality comparison: For each shared topic, rate quality dimensions
- [ ] Gap categorization: Prioritize by traffic + quality gap
- [ ] Improvement planning: Define specific enhancements needed

</project_level_details>

---

<document_details>

## Quality Gaps Identified

### Competitor Overview

**Competitor analyzed:** {{COMPETITOR_DOMAIN}}
**Content analyzed:** {{NUMBER}} pages across {{NUMBER}} topic clusters
**Shared topics:** {{NUMBER}} topics we both cover
**Analysis date:** {{DATE}}

---

### CRITICAL: High-Traffic Quality Gaps
*High traffic + They're better = Immediate improvement needed*

#### Gap 1: {{TOPIC_NAME}}
- **Why they're better:** {{REASON}} (e.g., "3x more code examples, includes troubleshooting section, has diagrams")
- **Quality dimensions:**
  - Breadth: {{COMPARISON}} (e.g., "They cover 5 subtopics, we cover 2")
  - Depth: {{COMPARISON}} (e.g., "Their explanations are more detailed")
  - Examples: {{COMPARISON}} (e.g., "They have 8 code examples, we have 2")
  - Visuals: {{COMPARISON}} (e.g., "They have architecture diagram, we don't")
  - Structure: {{COMPARISON}} (e.g., "Their organization is clearer")
- **Our page:** {{YOUR_URL}}
  - Traffic: {{PAGEVIEWS}}/month
  - Last updated: {{DATE}}
- **Their page:** {{COMPETITOR_URL}}
- **Specific improvements needed:**
  - {{IMPROVEMENT_1}} (e.g., "Add 5 more code examples covering edge cases")
  - {{IMPROVEMENT_2}} (e.g., "Create architecture diagram")
  - {{IMPROVEMENT_3}} (e.g., "Add troubleshooting section")
- **Effort estimate:** {{HOURS/DAYS}}
- [ ] **Improvement project created:** Yes/No

#### Gap 2: {{TOPIC_NAME}}
[Repeat structure]

---

### HIGH: Medium-Traffic Quality Gaps
*Moderate traffic + They're better = Important to address*

#### Gap 3: {{TOPIC_NAME}}
- **Why they're better:** {{REASON}}
- **Quality dimensions:**
  - Breadth: {{COMPARISON}}
  - Depth: {{COMPARISON}}
  - Examples: {{COMPARISON}}
  - Visuals: {{COMPARISON}}
  - Structure: {{COMPARISON}}
- **Our page:** {{YOUR_URL}} ({{PAGEVIEWS}}/month)
- **Their page:** {{COMPETITOR_URL}}
- **Specific improvements needed:**
  - {{IMPROVEMENT_1}}
  - {{IMPROVEMENT_2}}
- **Effort estimate:** {{HOURS/DAYS}}
- [ ] **Improvement project created:** Yes/No

---

### MEDIUM: Lower-Priority Quality Gaps
*Low traffic or minor gaps - Address if time permits*

#### Gap 4: {{TOPIC_NAME}}
- **Why they're better:** {{REASON}}
- **Our page:** {{YOUR_URL}}
- **Their page:** {{COMPETITOR_URL}}
- **Improvements needed:** {{BRIEF_LIST}}
- **Note:** {{WHY_LOWER_PRIORITY}}

---

### Our Strengths (No Action Needed)
*Topics where we're already competitive or better*

- ✅ **{{TOPIC_NAME}}** - We're better because: {{REASON}}
  - Our page: {{YOUR_URL}}
  - Their page: {{COMPETITOR_URL}}
- ✅ **{{TOPIC_NAME}}** - We're better because: {{REASON}}
- 🟡 **{{TOPIC_NAME}}** - Roughly equal quality

---

## Analysis Summary

**Total shared topics analyzed:** {{NUMBER}}
- CRITICAL priority gaps: {{NUMBER}}
- HIGH priority gaps: {{NUMBER}}
- MEDIUM priority gaps: {{NUMBER}}
- Our strengths (better or equal): {{NUMBER}}

**Overall assessment:**
{{SUMMARY_PARAGRAPH}} (e.g., "We're competitive on fundamental topics but lag on advanced features. Priority: Add examples and visuals to high-traffic pages.")

**Recommended immediate action:**
Improve top {{NUMBER}} CRITICAL gaps (estimated {{EFFORT}} total)

**Improvement roadmap:**
1. Q{{QUARTER}}: CRITICAL gaps ({{NUMBER}} pages)
2. Q{{QUARTER}}: HIGH priority gaps ({{NUMBER}} pages)
3. Ongoing: MEDIUM gaps as capacity allows

</document_details>

---

<project_tracking>

## Progress Tracking

### Phase 1: Content Indexing
- [ ] Your content indexed: {{NUMBER}} pages from {{YOUR_DOMAIN}}
- [ ] Competitor content indexed: {{NUMBER}} pages from {{COMPETITOR_DOMAIN}}
- [ ] Both clustered into topic groups
- [ ] Analytics synced for traffic data (optional)

### Phase 2: Topic Identification
- [ ] Your topic clusters reviewed ({{NUMBER}} clusters)
- [ ] Competitor topic clusters reviewed ({{NUMBER}} clusters)
- [ ] Shared topics identified: {{NUMBER}} overlapping topics
- [ ] Prioritized by traffic for analysis

### Phase 3: Quality Comparison
- [ ] Quality dimensions defined (breadth, depth, examples, visuals, structure)
- [ ] Comparison completed for all {{NUMBER}} shared topics
- [ ] Rating applied: ✅ Better | 🟡 Equal | ❌ Weaker
- [ ] Traffic data incorporated for prioritization

### Phase 4: Gap Categorization
- [ ] CRITICAL gaps identified (high traffic + weaker)
- [ ] HIGH priority gaps identified (medium traffic + weaker)
- [ ] MEDIUM gaps identified (low traffic or minor)
- [ ] Strengths documented (topics where we're better)

### Phase 5: Improvement Planning
- [ ] Top {{NUMBER}} gaps selected for immediate action
- [ ] Specific improvements defined for each
- [ ] Effort estimated
- [ ] Follow-up projects created
- [ ] Timeline/roadmap created

### Phase 6: Execution (Ongoing)
- [ ] Gap 1 improvements implemented: {{STATUS}}
- [ ] Gap 2 improvements implemented: {{STATUS}}
- [ ] Gap 3 improvements implemented: {{STATUS}}
- [ ] Performance tracking started

</project_tracking>

---

<sources_and_research>

## Data Sources

### Your Content
- Domain: {{YOUR_DOMAIN}}
- Pages analyzed: {{NUMBER}}
- Topic clusters: {{NUMBER}}
- Last fetched: {{DATE}}

### Competitor Content
- Domain: {{COMPETITOR_DOMAIN}}
- Pages analyzed: {{NUMBER}}
- Topic clusters: {{NUMBER}}
- Last fetched: {{DATE}}

### Performance Data
- Analytics: {{SOURCE}} (PostHog, etc.)
- Date range: {{RANGE}}
- Metrics: Pageviews, time on page, bounce rate

### Context Data
- Support tickets: {{SOURCE}}
- Customer feedback: {{SOURCE}}
- User research: {{SOURCE}}

</sources_and_research>

---

## Workflow Instructions

**Step 1: Index Both Content Sets (1-2 hours)**

```bash
# Verify your content indexed
kurt content stats --url-starts-with https://{{YOUR_DOMAIN}}

# If not indexed:
kurt content map url https://{{YOUR_DOMAIN}}
kurt content fetch --include 'https://{{YOUR_DOMAIN}}/**'

# Index competitor content
kurt content map url https://{{COMPETITOR_DOMAIN}}
kurt content fetch --include 'https://{{COMPETITOR_DOMAIN}}/**'

# View both cluster sets
kurt content list-clusters --url-starts-with https://{{YOUR_DOMAIN}}
kurt content list-clusters --url-starts-with https://{{COMPETITOR_DOMAIN}}
```

**Step 2: Discover Topic and Technology Coverage (1 hour)**

Discover what topics and technologies both you and competitor cover:

```bash
# Your topic coverage
kurt content list-topics --include "https://{{YOUR_DOMAIN}}/**"

# Competitor topic coverage
kurt content list-topics --include "https://{{COMPETITOR_DOMAIN}}/**"

# Your technology coverage
kurt content list-technologies --include "https://{{YOUR_DOMAIN}}/**"

# Competitor technology coverage
kurt content list-technologies --include "https://{{COMPETITOR_DOMAIN}}/**"

# Also check traditional clusters
kurt content list-clusters --include "https://{{YOUR_DOMAIN}}/**"
kurt content list-clusters --include "https://{{COMPETITOR_DOMAIN}}/**"
```

**Step 3: Identify Shared Topics (30 min)**

Compare the lists to find overlap:

- **Shared Topics:** Topics that appear in both lists
  - Example: Both cover "authentication" with 10+ docs each
- **Shared Technologies:** Technologies both document
  - Example: Both document "React", "Python", "PostgreSQL"

Create comparison list:
- **Topic: authentication**
  - Your docs: {{NUMBER}}
  - Their docs: {{NUMBER}}
  - Quality comparison needed: YES
- **Topic: webhooks**
  - Your docs: {{NUMBER}}
  - Their docs: {{NUMBER}}
  - Quality comparison needed: YES
- **Technology: React**
  - Your docs: {{NUMBER}}
  - Their docs: {{NUMBER}}
  - Quality comparison needed: YES

**Step 4: Get Traffic Data for Prioritization (30 min)**

```bash
# Sync analytics (if configured)
kurt analytics sync {{YOUR_DOMAIN}}

# Get traffic for your pages
kurt content list --url-starts-with https://{{YOUR_DOMAIN}} --with-analytics

# Identify high-traffic topics to prioritize
```

**Step 5: Quality Comparison (4-6 hours)**

For each shared topic/technology, retrieve both versions and compare:

```bash
# Get your page
kurt content get <your-doc-id>

# Get competitor page
kurt content get <competitor-doc-id>
```

**Compare on five dimensions:**

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Breadth** | ✅🟡❌ | Subtopics covered |
| **Depth** | ✅🟡❌ | Detail level |
| **Examples** | ✅🟡❌ | Code quality/quantity |
| **Visuals** | ✅🟡❌ | Diagrams, screenshots |
| **Structure** | ✅🟡❌ | Organization clarity |

**Overall:** ✅ We're better | 🟡 Equal | ❌ They're better

Repeat for all shared topics.

**Step 6: Categorize Gaps (1-2 hours)**

Use prioritization matrix:

| Traffic | Quality | Priority |
|---------|---------|----------|
| HIGH | ❌ They're better | 🔴 CRITICAL |
| MEDIUM | ❌ They're better | 🟡 HIGH |
| LOW | ❌ They're better | 🔵 MEDIUM |
| ANY | ✅🟡 We're equal/better | ✅ STRENGTH |

**Step 7: Define Improvements (2-3 hours)**

For each gap (especially CRITICAL/HIGH), specify exactly what to improve:

**Example:**
- Topic: API Authentication
- Gap: ❌ They're better
- Why: They have 8 examples, 2 diagrams, troubleshooting section
- Improvements needed:
  1. Add 5 more code examples covering OAuth, API keys, JWT
  2. Create sequence diagram for auth flow
  3. Add troubleshooting section with common errors
- Effort: 8 hours

**Step 8: Create Improvement Projects (30 min)**

For each CRITICAL/HIGH gap, create follow-up project:

```bash
# Create improvement project
/create-project

Project goal: Improve [topic] documentation to competitive quality with [competitor]

Improvements needed:
- [Improvement 1]
- [Improvement 2]
- [Improvement 3]

Sources:
- Current page for editing
- Competitor page for reference (learn from structure, don't copy)
- Additional product docs if needed
```

**Step 9: Execute & Track (Ongoing)**

As improvements are made:
- Mark completed in project tracking
- Measure impact (traffic, time on page, support tickets)
- Re-compare quarterly to track progress
- Monitor competitor for new changes

---

## Quality Assessment Framework

### Breadth (Subtopic Coverage)
- **✅ Better:** We cover more subtopics comprehensively
- **🟡 Equal:** Similar subtopic coverage
- **❌ Weaker:** They cover important subtopics we miss

### Depth (Detail Level)
- **✅ Better:** Our explanations are more thorough
- **🟡 Equal:** Similar level of detail
- **❌ Weaker:** Their explanations are more comprehensive

### Examples (Code Quality/Quantity)
- **✅ Better:** We have more/better examples
- **🟡 Equal:** Similar example coverage
- **❌ Weaker:** They have more examples or cover more cases

### Visuals (Diagrams, Screenshots)
- **✅ Better:** We have helpful visuals they lack
- **🟡 Equal:** Similar visual aids
- **❌ Weaker:** They have diagrams/screenshots that aid understanding

### Structure (Organization Clarity)
- **✅ Better:** Our organization is clearer
- **🟡 Equal:** Both well-organized
- **❌ Weaker:** Their structure is easier to follow

---

## Common Quality Gap Patterns

**Missing Examples:**
- They have real-world code examples, we only have snippets
- They cover edge cases, we only show happy path
- They show multiple approaches, we show one

**Missing Visuals:**
- They have architecture diagrams, we don't
- They use screenshots to clarify UI, we only describe
- They have flowcharts for complex processes

**Missing Sections:**
- They have troubleshooting guides, we don't
- They have "Common Mistakes" sections
- They have "Best Practices" or "Tips" callouts

**Structural Issues:**
- Their progressive disclosure is better (basics first, advanced later)
- Their headings are more descriptive
- Their navigation/ToC is clearer

**Breadth Gaps:**
- They cover subtopics we skip (e.g., they document all API methods, we document main ones)
- They have content for multiple personas, we focus on one

---

## Success Metrics

**Gap Closure Progress:**
- X of Y CRITICAL gaps addressed
- X of Y HIGH gaps addressed
- % quality parity achieved

**Impact of Improvements:**
- Traffic changes to improved pages
- Time on page improvements
- Bounce rate reductions
- Support ticket decreases for covered topics

**Competitive Position:**
- Shared topic quality comparison: X topics better, Y equal, Z weaker
- Trend over time (quarterly re-analysis)

---

## Next Analysis

**Frequency:** Quarterly (every 3 months)

**Quick Check (Monthly):**
- New competitor content published?
- Quality changes to their key pages?
- New topics they've added?

**Full Analysis (Quarterly):**
- Re-analyze all shared topics
- Check for new shared topics
- Measure improvement impact
- Adjust priorities based on performance
- Consider additional competitors

**Pro tip:** Monitor competitor docs:
- Set up change detection alerts
- Track their changelog/release notes
- Review their content strategy shifts
