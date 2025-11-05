# Documentation Audit Project Template

## Goal

Conduct comprehensive traffic audit of [DOMAIN] documentation to identify content issues: stale high-traffic pages, declining traffic, and zero-traffic orphaned content.

**Before using:** ✓ Analytics must be configured for domain

## Intent Category

**Content Type:** Audit / Analysis
**Primary Goal:** Identify documentation health issues and create action plan
**Audience:** Internal (content team planning)

## Sources (Ground Truth)

### From Organizational Knowledge Base

*Documentation being audited:*
- /sources/[domain]/docs/

### Project-Specific Sources

*Add to this audit:*
- Product changelog (to identify stale content)
- Support ticket data (common issues not in docs)
- Customer feedback on documentation

## Targets (Content to Update/Create)

### Audit Findings

**Issue Category 1: High-Traffic Stale Content**
*Content with high traffic but outdated (needs refresh)*

- [ ] /docs/page1 - Last updated: [DATE], Traffic: HIGH, Issue: [Outdated API]
- [ ] /docs/page2 - Last updated: [DATE], Traffic: HIGH, Issue: [Deprecated]

**Issue Category 2: Declining Traffic**
*Content losing traffic (needs investigation)*

- [ ] /docs/page3 - Trend: ↓ 45%, Cause: [New competing page? Outdated?]
- [ ] /docs/page4 - Trend: ↓ 30%, Cause: [Product change?]

**Issue Category 3: Zero Traffic (Orphaned)**
*Content with no traffic (deprecated or poor discoverability)*

- [ ] /docs/page5 - 0 pageviews, Decision: Archive or improve discoverability?
- [ ] /docs/page6 - 0 pageviews, Decision: Remove or update?

**Issue Category 4: Missing Content**
*Gaps identified (high-value topics without documentation)*

- [ ] [Topic] - Identified from: [Support tickets, customer requests]

### New Content to Create

*Audit deliverable:*
- Comprehensive audit report (this project.md)
- Action plan with prioritized fixes

## Rules Configuration

### Style
- Use rules/style/technical-docs.md

### Structure
- Use rules/structure/[appropriate-doc-type].md

### Personas
- Use rules/personas/developer.md or technical personas

### Publisher Profile
- Use rules/publisher/publisher-profile.md

## Progress

- [ ] Traffic audit completed
- [ ] Issues categorized
- [ ] Findings prioritized
- [ ] Action plan created
- [ ] Follow-up projects created

## Next Steps

**Workflow:**

1. **Run Traffic Audit** (1-2 hours)

   Ask Claude to run a traffic audit:
   > Run intelligence audit-traffic for <your-domain>

   This generates findings in categories:
   - High-traffic stale (>365 days old, high traffic)
   - Declining traffic (↓ trend)
   - Zero traffic (orphaned pages)
   - Missing content gaps

2. **Categorize Issues** (2-3 hours)
   - Review each finding
   - Determine root cause
   - Assign priority based on traffic volume + urgency

3. **Create Action Plan** (1 hour)
   - **Immediate** (CRITICAL): High-traffic stale, rapidly declining
   - **Short-term** (HIGH): Medium-traffic issues
   - **Long-term** (MEDIUM/LOW): Zero-traffic, content gaps

4. **Create Follow-Up Projects**
   - Major updates: Create dedicated update project
   - Content gaps: Create new content project
   - Archival: Document deprecation plan

5. **Report & Track**
   - Share findings with team
   - Schedule next audit (quarterly recommended)

---

**Common Findings:**
- High-traffic stale = Quick wins (update high-impact pages)
- Declining traffic = Investigate cause
- Zero traffic = Discoverability issue or truly deprecated?
- Missing content = Opportunity to fill gaps

---

**To use this template:**
1. Clone with `/clone-project documentation-audit`
2. Specify domain in goal
3. Run traffic analysis queries
4. Categorize findings in Targets section
5. Create follow-up projects for major work
