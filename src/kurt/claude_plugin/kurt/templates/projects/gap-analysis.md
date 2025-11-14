<!--
SETUP INSTRUCTIONS FOR CLAUDE:

When a user clones this template, follow these steps:

1. Ask the user:
   - "Which competitor do you want to analyze?" (get domain)
   - "Has their content been indexed?"
   - If no: "Run: kurt map url https://[competitor-domain] --cluster-urls"
   - Then: "Run: kurt fetch --url-starts-with https://[competitor-domain]"

2. Verify competitor content indexed:
   `kurt content stats --include "https://[competitor-domain]/**"`

3. Discover competitor topic coverage:
   ```bash
   # See what topics they cover
   kurt content list-topics --include "https://[competitor-domain]/**"

   # See what technologies they document
   kurt content list-technologies --include "https://[competitor-domain]/**"

   # Also check traditional clusters
   kurt content list-clusters --include "https://[competitor-domain]/**"
   ```

4. Compare with your topic coverage:
   ```bash
   # Your topic coverage
   kurt content list-topics --include "https://[your-domain]/**"

   # Your technology coverage
   kurt content list-technologies --include "https://[your-domain]/**"
   ```

5. Identify gaps - topics/technologies competitor has that you don't:
   - Compare topic lists side-by-side
   - Look for topics they have with 5+ docs that you have 0-1 docs on
   - Look for technologies they document that you don't

6. Estimate opportunity for each gap:
   - Strategic value: Is this a core product area?
   - Search demand: Use `kurt research query "[topic] search volume"`
   - Customer requests: Ask user for topics customers have requested

7. Prioritize gaps using matrix:
   - HIGH: Strategic + High demand
   - MEDIUM: Strategic OR High demand
   - LOW: Nice to have

8. Populate "Content Gaps Identified" section with prioritized list

9. Create follow-up projects for top 3-5 gaps
-->

<project_level_details>
# Gap Analysis - {{YOUR_DOMAIN}} vs {{COMPETITOR}}

## Goal
Identify high-value content gaps by comparing our documentation/content against {{COMPETITOR_DOMAIN}} to find topics they cover that we don't.

**Prerequisites:**
- ✓ Your content indexed: `kurt content stats --include "https://{{YOUR_DOMAIN}}/**"`
- ✓ Competitor content indexed: `kurt content stats --include "https://{{COMPETITOR_DOMAIN}}/**"`
- ✓ Content indexed with metadata: Run `kurt content index --all` if needed

## Research Required
<!-- External research to understand opportunity -->
- [ ] Search volume research: What topics have high search demand?
- [ ] Customer requests: What documentation do customers ask for?
- [ ] Support ticket analysis: What topics cause most confusion?

## Analysis Required
<!-- Core gap analysis -->
- [ ] Competitor topic clusters: What areas do they cover?
- [ ] Coverage comparison: Do we have equivalent content for each cluster?
- [ ] Gap identification: List topics they have that we don't
- [ ] Opportunity assessment: Estimate strategic value + search demand
- [ ] Prioritization: Score gaps HIGH/MEDIUM/LOW

</project_level_details>

---

<document_details>

## Content Gaps Identified

### Competitor Coverage Overview

**Competitor analyzed:** {{COMPETITOR_DOMAIN}}
**Content analyzed:** {{NUMBER}} pages across {{NUMBER}} topic clusters
**Analysis date:** {{DATE}}

**Their topic clusters:**
1. {{CLUSTER_NAME}} ({{NUMBER}} pages)
2. {{CLUSTER_NAME}} ({{NUMBER}} pages)
3. {{CLUSTER_NAME}} ({{NUMBER}} pages)
[...list all their clusters...]

---

### HIGH Priority Gaps
*Strategic importance + High search demand = Fill these first*

#### Gap 1: {{TOPIC_NAME}}
- **Why important:** {{STRATEGIC_REASON}} (e.g., "Core product feature customers ask about")
- **Competitor has:**
  - {{URL}} - {{CONTENT_TYPE}} (Tutorial, guide, reference, etc.)
  - {{URL}} - {{CONTENT_TYPE}}
- **We need:** {{CONTENT_TYPE_NEEDED}}
- **Estimated opportunity:** HIGH
  - Search volume: {{NUMBER/MONTH}} (if known)
  - Customer requests: {{FREQUENCY}}
  - Strategic value: {{CORE_FEATURE / DIFFERENTIATOR / COMPETITIVE_PARITY}}
- **Effort estimate:** {{HOURS/DAYS}}
- [ ] **Follow-up project created:** Yes/No

#### Gap 2: {{TOPIC_NAME}}
[Repeat structure]

---

### MEDIUM Priority Gaps
*Either strategic OR high demand - Consider for next quarter*

#### Gap 3: {{TOPIC_NAME}}
- **Why important:** {{REASON}}
- **Competitor has:** {{URL}} - {{CONTENT_TYPE}}
- **We need:** {{CONTENT_TYPE_NEEDED}}
- **Estimated opportunity:** MEDIUM
  - Search volume: {{NUMBER/MONTH OR "Unknown"}}
  - Customer requests: {{FREQUENCY OR "Occasional"}}
  - Strategic value: {{NICE_TO_HAVE / GOOD_FOR_SEO / COMPLETENESS}}
- **Effort estimate:** {{HOURS/DAYS}}
- [ ] **Follow-up project created:** Yes/No

---

### LOW Priority Gaps
*Nice to have - Consider if time permits*

#### Gap 4: {{TOPIC_NAME}}
- **Why included:** {{REASON}}
- **Competitor has:** {{URL}}
- **We need:** {{CONTENT_TYPE}}
- **Estimated opportunity:** LOW
- **Note:** {{WHY_LOW_PRIORITY}}

---

## Gap Analysis Summary

**Total gaps identified:** {{NUMBER}}
- HIGH priority: {{NUMBER}} gaps
- MEDIUM priority: {{NUMBER}} gaps
- LOW priority: {{NUMBER}} gaps

**Recommended immediate action:**
Fill top {{NUMBER}} HIGH priority gaps (estimated {{EFFORT}} total)

**Content roadmap:**
1. Q{{QUARTER}}: HIGH priority gaps ({{NUMBER}} pieces)
2. Q{{QUARTER}}: MEDIUM priority gaps ({{NUMBER}} pieces)
3. Ongoing: LOW priority as capacity allows

</document_details>

---

<project_tracking>

## Progress Tracking

### Phase 1: Content Indexing
- [ ] Your content indexed: {{NUMBER}} pages from {{YOUR_DOMAIN}}
- [ ] Competitor content indexed: {{NUMBER}} pages from {{COMPETITOR_DOMAIN}}
- [ ] Both clustered into topic groups

### Phase 2: Gap Identification
- [ ] Competitor topic clusters reviewed ({{NUMBER}} clusters)
- [ ] Coverage comparison completed for each cluster
- [ ] Gaps identified: {{NUMBER}} topics they have that we don't
- [ ] Gap list reviewed with team

### Phase 3: Opportunity Assessment
- [ ] Search volume research completed
- [ ] Customer request data gathered
- [ ] Strategic value assessed for each gap
- [ ] Gaps scored and prioritized

### Phase 4: Action Planning
- [ ] Top {{NUMBER}} gaps selected for immediate action
- [ ] Content types defined for each gap
- [ ] Effort estimated
- [ ] Follow-up projects created
- [ ] Timeline/roadmap created

### Phase 5: Execution (Ongoing)
- [ ] Gap 1 content created: {{STATUS}}
- [ ] Gap 2 content created: {{STATUS}}
- [ ] Gap 3 content created: {{STATUS}}
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

### Opportunity Data
- Search volume: {{SOURCE}} (Ahrefs, SEMrush, Google Trends, etc.)
- Customer requests: {{SOURCE}} (Support tickets, sales calls, etc.)
- Strategic context: {{SOURCE}} (Product roadmap, company priorities)

</sources_and_research>

---

## Workflow Instructions

**Step 1: Index Competitor Content (1-2 hours)**
```bash
# Map competitor site
kurt map url https://{{COMPETITOR_DOMAIN}} --cluster-urls

# Fetch competitor content (automatically indexes)
kurt fetch --url-starts-with https://{{COMPETITOR_DOMAIN}} --limit 100

# Verify indexing complete
kurt content stats --include "https://{{COMPETITOR_DOMAIN}}/**"

# View their clusters
kurt content list-clusters --include "https://{{COMPETITOR_DOMAIN}}/**"
```

**Step 2: Compare Topic Coverage (2-3 hours)**

**Discover what competitor covers:**
```bash
# Get their topic breakdown
kurt content list-topics --include "https://{{COMPETITOR_DOMAIN}}/**"

# Get their technology coverage
kurt content list-technologies --include "https://{{COMPETITOR_DOMAIN}}/**"

# Traditional cluster view
kurt content list-clusters --include "https://{{COMPETITOR_DOMAIN}}/**"
```

**Compare with your coverage:**
```bash
# Your topic breakdown
kurt content list-topics --include "https://{{YOUR_DOMAIN}}/**"

# Your technology coverage
kurt content list-technologies --include "https://{{YOUR_DOMAIN}}/**"
```

**Identify gaps - Example workflow:**
```bash
# They cover "authentication" with 15 docs
# Check your coverage
kurt content list --with-topic "authentication" --include "https://{{YOUR_DOMAIN}}/**"

# Found only 2 docs = GAP identified (13 doc deficit)

# They cover "webhooks" with 8 docs
kurt content list --with-topic "webhooks" --include "https://{{YOUR_DOMAIN}}/**"

# Found 0 docs = MAJOR GAP
```

Create gap list with document counts:
- **Topic:** {{THEIR_TOPIC}}
  - Their docs: {{NUMBER}}
  - Your docs: {{NUMBER}}
  - Gap: {{DEFICIT}} (e.g., "13 doc deficit")
- **Technology:** {{TECH_THEY_COVER}}
  - Their docs: {{NUMBER}}
  - Your docs: {{NUMBER}}
  - Gap: {{MISSING/DEFICIT}}

**Step 3: Assess Opportunity (2-3 hours)**

For each gap, research:

**Search demand:**
```bash
# Use Perplexity to estimate search volume
kurt research query "[topic] search volume and demand"

# Check discussions
kurt research search --source hackernews --query "[topic]"
kurt research search --source reddit --query "[topic]"
```

**Customer demand:**
- Ask user: "Do customers request documentation on [topic]?"
- Check support tickets
- Review sales call notes

**Strategic value:**
- Core product feature? (HIGH)
- Competitive differentiator? (HIGH)
- Nice-to-have completeness? (LOW)

**Step 4: Prioritize Gaps (1 hour)**

Use scoring matrix:

| Strategic Value | Search Demand | Priority |
|----------------|---------------|----------|
| HIGH | HIGH | 🔴 CRITICAL |
| HIGH | MEDIUM | 🟡 HIGH |
| MEDIUM | HIGH | 🟡 HIGH |
| MEDIUM | MEDIUM | 🔵 MEDIUM |
| LOW | HIGH | 🔵 MEDIUM |
| * | LOW | ⚪ LOW |

**Step 5: Create Content Roadmap (1 hour)**

**Immediate (This quarter):**
- Top 3-5 HIGH priority gaps
- Quick wins that close critical gaps

**Short-term (Next quarter):**
- Remaining HIGH priority gaps
- Top MEDIUM priority gaps

**Long-term (Future):**
- MEDIUM and LOW priority gaps
- Maintain parity as competitor adds content

**Step 6: Create Follow-Up Projects (30 min)**

For each HIGH priority gap:
```markdown
/create-project

Project goal: Create [content type] for [topic] to close gap vs [competitor]

Sources needed:
- Your product docs on [topic]
- Competitor content for reference (don't copy, learn from approach)
- Customer use cases

Format: [Tutorial / Guide / Reference / etc.]
```

**Step 7: Execute & Track (Ongoing)**

As gaps are filled:
- Mark completed in project tracking
- Measure performance (traffic, engagement)
- Monitor competitor for new content
- Update gap analysis quarterly

---

## Prioritization Framework

### HIGH Priority = Must Have
- ✓ Core product feature we support but don't document
- ✓ High customer demand (frequent requests)
- ✓ High search volume (SEO opportunity)
- ✓ Competitive disadvantage if missing

### MEDIUM Priority = Should Have
- ✓ Good feature coverage but not critical
- ✓ Moderate search demand
- ✓ Improves content completeness
- ✓ Helps with specific customer segments

### LOW Priority = Nice to Have
- ✓ Edge cases or advanced topics
- ✓ Low search demand
- ✓ Not customer-requested
- ✓ Competitor may have it but not popular

---

## Common Gap Patterns

**Missing Content Types:**
- They have tutorials, you only have reference → Need tutorials
- They have examples, you only have theory → Need code examples
- They have troubleshooting, you don't → Need debugging guides

**Missing Topic Areas:**
- They cover integrations comprehensively → Need integration docs
- They have advanced topics, you stop at basics → Need advanced content
- They document edge cases → Need completeness

**Missing Audience Content:**
- They have content for specific personas → Need persona-specific content
- They have industry-specific examples → Need industry variations

---

## Success Metrics

**Gap Closure Progress:**
- X of Y HIGH priority gaps filled
- X of Y MEDIUM priority gaps filled
- % content parity with competitor

**Performance of Gap-Fill Content:**
- Traffic to new gap-fill pages
- Engagement metrics (time on page, bounce rate)
- Customer feedback on new content
- Support ticket reduction for covered topics

**Competitive Position:**
- Topic coverage comparison: You have X%, competitor has Y%
- Search visibility improvements
- Customer perception of documentation quality

---

## Next Analysis

**Frequency:** Quarterly (every 3 months)

**Quick Check (Monthly):**
- New competitor content published?
- New gaps emerged?
- Priority shifts based on product changes?

**Full Analysis (Quarterly):**
- Complete re-analysis of coverage
- Re-prioritize based on new data
- Adjust roadmap as needed
- Consider multiple competitors

**Pro tip:** Set up alerts for competitor content:
- RSS feeds if available
- Regular site checks
- Automated change detection
