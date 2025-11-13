# Launch Plan Template

## Overview
- **Purpose:** Cross-functional coordination document for product/feature launch
- **Length:** 2000-3000 words
- **Audience:** Internal (product, engineering, marketing, sales, customer success)
- **Success metrics:** Coordinated launch, all teams ready, measurable outcomes

---

## Style Guidelines

**Note:** This is an INTERNAL document, not published externally. Style customization is not required.

**Tone:**
- Clear and comprehensive
- Cross-functional (addresses all teams)
- Action-oriented (checklists and owners)
- Risk-aware (anticipates issues)

**Format:**
- Structured by function (product, marketing, sales, support)
- Timeline-driven (phases and milestones)
- Checklist-heavy (clear readiness criteria)
- Owner-assigned (accountability for each item)

---

## Research Requirements

**Types of information needed for launch plan:**

1. **Product details** - What's launching
   - Find: `kurt content list --url-contains /product`
   - Or provide: PRD, product specs, feature details, technical docs

2. **Positioning and messaging** - How to talk about it
   - Find: `kurt content search "positioning"` or `kurt content search "messaging"`
   - Or provide: Positioning doc, messaging framework

3. **Market context** - Competitive and customer landscape
   - Research: `kurt research query "[product category] market trends"`
   - Or provide: Competitive analysis, market research

4. **Customer insights** - Who needs this and why
   - Find: `kurt content search "persona"` or `kurt content search "customer"`
   - Or provide: Customer research, beta feedback, use cases

5. **Past launch learnings** - What worked before
   - Find: `kurt content search "launch"` or `kurt content search "retrospective"`
   - Or provide: Previous launch retrospectives, metrics

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Product and strategy:**
```bash
# Product details (discover what pages exist)
kurt content list --url-contains /product

# Search for product specs
kurt content search "spec"
kurt content search "PRD"

# Positioning
kurt content search "positioning"
kurt content search "messaging"
```

**Customer and market:**
```bash
# Customer insights
kurt content search "persona"
kurt content search "customer"

# Market research
kurt research query "[product] market opportunity"
```

**If insufficient sources: Ask user for PRD, positioning doc, or target customer definition**

---

## Structure

```markdown
---
project: project-name
document: launch-plan
format_template: /kurt/templates/formats/launch-plan.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/product/prd.md
    purpose: "product details and features"
  - path: /sources/positioning-messaging.md
    purpose: "how to talk about the launch"
  - path: /sources/personas/target-customer.md
    purpose: "who this is for"

outline:
  launch-overview:
    sources: [/sources/product/prd.md]
    purpose: "what we're launching and why"
  product-readiness:
    sources: [/sources/product/prd.md]
    purpose: "product team deliverables"
  marketing-readiness:
    sources: [/sources/positioning-messaging.md]
    purpose: "marketing team deliverables"
  sales-readiness:
    sources: []
    purpose: "sales team preparation"
  support-readiness:
    sources: []
    purpose: "customer success preparation"
  timeline:
    sources: []
    purpose: "launch phases and milestones"
  metrics:
    sources: []
    purpose: "how we measure success"
---

# Launch Plan: [PRODUCT/FEATURE NAME]

**Launch owner:** [Name/Role] - Overall coordination
**Launch date:** [Target date]
**Launch type:** [Major product launch / Feature release / Beta launch / GA launch]
**Status:** [Planning / In Progress / Ready / Launched]

**Last updated:** YYYY-MM-DD

---

## Executive Summary

**What we're launching:**
[Product/feature name] - [One sentence description]

**Why this matters:**
[Business objective - revenue opportunity, competitive response, customer need]

**Who it's for:**
[Primary target audience and use case]

**Launch scope:**
- [ ] Full public launch (GA)
- [ ] Limited beta
- [ ] Soft launch (existing customers first)
- [ ] Phased rollout

**Key success metrics:**
1. [Primary metric with target]
2. [Secondary metric with target]
3. [Adoption or revenue goal]

---

## Launch Overview

### Product Details

**Product/Feature name:** [Official name]
**Category:** [What type of product/feature is this]
**Target audience:** [Who will use this]

**Core value proposition:**
[One sentence: What problem it solves and how]

**Key features:**
1. [Feature 1] - [Benefit]
2. [Feature 2] - [Benefit]
3. [Feature 3] - [Benefit]

**Differentiation:**
[What makes this unique vs alternatives]

### Launch Rationale

**Why we're launching this:**
- Business objective: [Revenue, market expansion, competitive, etc.]
- Customer need: [Problem we're solving]
- Strategic importance: [How this fits company strategy]

**Why now:**
[Market timing, competitive pressure, customer demand, etc.]

**What success looks like:**
[Qualitative vision of successful launch - adoption, revenue, market position]

---

## Product Readiness

### Product Team Deliverables

**Engineering:**
- [ ] Product/feature fully built and tested
- [ ] Performance benchmarks met: [Specify requirements]
- [ ] Security review completed
- [ ] Scalability validated for launch traffic
- [ ] Monitoring and alerting configured
- [ ] Rollback plan documented
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

**Design:**
- [ ] UI/UX finalized and reviewed
- [ ] Design system updated (if new patterns)
- [ ] Accessibility requirements met
- [ ] User testing completed with [X] users
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

**Product:**
- [ ] PRD complete and approved
- [ ] Beta testing completed (if applicable)
- [ ] Beta feedback addressed
- [ ] Launch criteria defined and met
- [ ] Go/no-go decision framework ready
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

### Technical Documentation

- [ ] API documentation complete: [URL when published]
- [ ] Product documentation complete: [URL when published]
- [ ] Integration guides complete: [URL when published]
- [ ] Migration guides (if applicable): [URL when published]
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

---

## Marketing Readiness

### Positioning & Messaging

- [ ] Positioning document complete
  - Link: [Path to positioning doc]
  - Approved by: [Stakeholders]
- [ ] Key messages defined
- [ ] Competitive talking points ready
- [ ] Value proposition validated with customers
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

### Content Deliverables

**Core content:**

1. **Announcement blog post**
   - Draft: [Link] | Status: [ ] Outline | [ ] Draft | [ ] Approved
   - Owner: [Name] | Publish date: [Launch day]

2. **Product documentation**
   - Draft: [Link] | Status: [ ] Outline | [ ] Draft | [ ] Approved
   - Owner: [Name] | Publish date: [Before launch]

3. **Tutorial/How-to guide**
   - Draft: [Link] | Status: [ ] Outline | [ ] Draft | [ ] Approved
   - Owner: [Name] | Publish date: [Launch day or shortly after]

4. **Product page** (if new product)
   - Draft: [Link] | Status: [ ] Outline | [ ] Draft | [ ] Approved
   - Owner: [Name] | Publish date: [Launch day]

**Supporting content:**

- [ ] Customer case study (if available)
- [ ] Demo video
- [ ] Launch webinar (if applicable)
- [ ] Social media posts (LinkedIn, Twitter, etc.)
- [ ] Email announcement (customers + prospects)
- [ ] Press release (if major launch)

### Launch Campaign

- [ ] Campaign brief complete: [Link to brief]
- [ ] Landing page ready: [URL]
- [ ] Email sequences ready
- [ ] Social media calendar planned
- [ ] Paid campaigns configured (if applicable)
- [ ] Analytics tracking set up
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

### PR & Communications

- [ ] Press release drafted and approved (if applicable)
- [ ] Media list compiled
- [ ] Analyst briefings scheduled
- [ ] Partner communications planned
- [ ] Internal communications (company all-hands, etc.)
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

---

## Sales Readiness

### Sales Enablement Materials

- [ ] Sales deck/pitch updated with new product/feature
- [ ] One-pager/cheat sheet created
- [ ] Demo environment ready
- [ ] Pricing and packaging confirmed
- [ ] ROI calculator (if applicable)
- [ ] Competitive battle cards updated
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

### Sales Training

- [ ] Product training session scheduled: [Date]
- [ ] Training materials prepared
- [ ] Demo walkthrough recorded
- [ ] FAQ document created
- [ ] Objection handling guide ready
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

### Sales Tools & Processes

- [ ] CRM updated (if new product/SKU)
- [ ] Pricing configured in systems
- [ ] Quote templates updated
- [ ] Contract templates ready (if new terms)
- [ ] Sales process documented
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

---

## Customer Success Readiness

### Support Preparation

- [ ] Support documentation complete
- [ ] Troubleshooting guide created
- [ ] Known issues documented
- [ ] Support team trained on new product/feature
- [ ] Support macros/templates created
- [ ] Escalation process defined
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

### Customer Onboarding

- [ ] Onboarding flow updated (if needed)
- [ ] Getting started guide created
- [ ] Onboarding email sequence ready
- [ ] In-app guides/tooltips (if applicable)
- [ ] Customer webinar planned (if applicable)
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

### Customer Communications

- [ ] Existing customer announcement email
- [ ] Customer success team briefed
- [ ] Beta users thanked and notified
- [ ] Community announcement prepared
- Owner: [Name] | Due: [Date] | Status: [Not started / In progress / Complete]

---

## Launch Timeline

### Phase 1: Pre-Launch (-4 weeks to -2 weeks)

**Focus:** Content creation, team preparation

**Milestones:**
- [ ] All content outlined
- [ ] Product documentation drafted
- [ ] Sales enablement materials drafted
- [ ] Support materials drafted
- [ ] Launch campaign planned

**Weekly sync:** [Day/time] | Owner: [Name]

### Phase 2: Launch Prep (-2 weeks to Launch)

**Focus:** Finalization, reviews, readiness

**Milestones:**
- [ ] All content reviewed and approved
- [ ] Sales training completed
- [ ] Support training completed
- [ ] Landing page live (soft launch if applicable)
- [ ] Launch go/no-go meeting: [Date, 1 week before launch]

**Daily sync:** [Time] | Owner: [Name]

### Phase 3: Launch Week

**Launch day:** [Date]

**Launch sequence:**
1. **Morning of launch:**
   - [ ] Product/feature enabled in production
   - [ ] Documentation published
   - [ ] Landing page live (if not already)

2. **Midday:**
   - [ ] Blog post published
   - [ ] Email sent to customers
   - [ ] Social posts go live
   - [ ] Press release distributed (if applicable)

3. **Throughout day:**
   - [ ] Monitor for issues
   - [ ] Engage with social comments
   - [ ] Track analytics
   - [ ] Support team ready for questions

**Launch war room:** [Slack channel / meeting room] | Team available: [Hours]

### Phase 4: Post-Launch (Week 1-4)

**Focus:** Monitoring, optimization, amplification

**Week 1:**
- [ ] Daily performance review
- [ ] Quick fixes for any issues
- [ ] Continued social amplification
- [ ] Follow-up content published

**Week 2-4:**
- [ ] Weekly performance review
- [ ] Campaign optimization
- [ ] Customer feedback collected
- [ ] Iterate on messaging if needed

**Post-launch retrospective:** [Date, 2-4 weeks after launch] | Owner: [Name]

---

## Success Metrics & Tracking

### Product Adoption Metrics

**Week 1 targets:**
- New signups/activations: [Number]
- Feature adoption (% of users): [%]
- Active usage: [Metric and target]

**Month 1 targets:**
- Total users: [Number]
- Feature adoption: [%]
- Retention: [%]

**Quarter 1 targets:**
- ARR/Revenue impact: $[Amount]
- Market penetration: [Metric]
- Customer satisfaction: [Score]

### Marketing Performance

**Launch week:**
- Blog post views: [Target]
- Landing page visits: [Target]
- Email open rate: [Target %]
- Email click rate: [Target %]
- Social engagement: [Target]

**Month 1:**
- Total reach: [Number]
- Leads generated: [Number]
- MQLs: [Number]
- Opportunities created: [Number]

### Sales Performance

**Month 1:**
- Deals closed with new product: [Number]
- Revenue from new product: $[Amount]
- Pipeline created: $[Amount]
- Sales cycle impact: [Faster/slower than average]

### Support & Success

**Launch week:**
- Support tickets: [Expected number]
- Critical issues: [Target: 0]
- Average resolution time: [Target]
- Customer satisfaction: [Target score]

### Tracking & Reporting

**Dashboard:** [Link to real-time dashboard]
**Daily report:** [Who receives, what's included]
**Weekly review:** [Meeting time] | Attendees: [Team]
**Post-launch analysis:** [Date, 2-4 weeks after] | Owner: [Name]

---

## Go / No-Go Criteria

**Launch decision date:** [1 week before launch]
**Decision makers:** [Names/roles]

### Go Criteria (Must meet ALL)

**Product readiness:**
- [ ] All P0 features complete and tested
- [ ] No critical bugs
- [ ] Performance requirements met
- [ ] Security review passed
- [ ] Rollback plan in place

**Content readiness:**
- [ ] All core content approved and ready to publish
- [ ] Documentation complete
- [ ] Landing page ready

**Team readiness:**
- [ ] Sales team trained
- [ ] Support team trained
- [ ] Launch sequence planned

**Business readiness:**
- [ ] Pricing finalized
- [ ] Legal/compliance cleared
- [ ] Go-to-market strategy approved

### No-Go Triggers (Any one triggers delay)

- ❌ Critical product bugs or security issues
- ❌ Major content gaps (docs, messaging)
- ❌ Team not trained or prepared
- ❌ Market timing concerns (competitor launch, major event conflict)
- ❌ Legal/compliance issues

### Contingency Plan

**If we need to delay:**
- Communications plan: [Who notifies whom]
- Customer communication: [Message and channel]
- Internal communication: [Message to team]
- Revised timeline: [How determined]

---

## Risks & Mitigation

### Product Risks

**Risk: [Product doesn't perform as expected]**
- Likelihood: [High / Medium / Low]
- Impact: [High / Medium / Low]
- Mitigation: [Extensive testing, phased rollout, etc.]
- Owner: [Name]

**Risk: [Technical issues at launch]**
- Likelihood: [High / Medium / Low]
- Impact: [High / Medium / Low]
- Mitigation: [War room, monitoring, rollback plan]
- Owner: [Name]

### Market Risks

**Risk: [Competitor launches similar product]**
- Likelihood: [High / Medium / Low]
- Impact: [High / Medium / Low]
- Mitigation: [Emphasize differentiation, prepared messaging]
- Owner: [Name]

**Risk: [Low customer interest]**
- Likelihood: [High / Medium / Low]
- Impact: [High / Medium / Low]
- Mitigation: [Beta validation, targeted launch, feedback loop]
- Owner: [Name]

### Execution Risks

**Risk: [Content not ready in time]**
- Likelihood: [High / Medium / Low]
- Impact: [High / Medium / Low]
- Mitigation: [Early start, buffer time, priorities defined]
- Owner: [Name]

**Risk: [Teams not aligned]**
- Likelihood: [High / Medium / Low]
- Impact: [High / Medium / Low]
- Mitigation: [Regular syncs, shared plan, clear ownership]
- Owner: [Name]

---

## Post-Launch Retrospective (Complete After)

**Retrospective date:** [2-4 weeks after launch]
**Attendees:** [Cross-functional team]

### What Went Well

- [Specific success 1]
- [Specific success 2]
- [Specific success 3]

### What Didn't Go Well

- [Challenge or failure 1]
- [Why it happened]
- [How to prevent next time]

### Key Learnings

1. [Learning 1]
2. [Learning 2]
3. [Learning 3]

### Recommendations for Next Launch

- [Actionable recommendation based on learnings]
- [Process improvement]
- [Resource allocation change]

### Final Metrics vs Targets

| Metric | Target | Actual | Variance |
|--------|--------|--------|----------|
| [Metric 1] | [Target] | [Actual] | [%] |
| [Metric 2] | [Target] | [Actual] | [%] |
| [Metric 3] | [Target] | [Actual] | [%] |

```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/launch-plan.md`

**Step 1: YAML frontmatter + outline**
- List all major sections
- Map sources (PRD, positioning, personas)
- Identify what exists vs needs creation
- Set status: `outline`

**Step 2: Define launch scope**
- What exactly is launching
- Why now (business rationale)
- Who it's for (target audience)
- Success criteria

**Step 3: Map cross-functional dependencies**
- Product team deliverables
- Marketing deliverables
- Sales enablement needs
- Support preparation

**Step 4: Create detailed timeline**
- Work backward from launch date
- Identify critical path items
- Build in buffer time
- Set milestones and check-ins

**Step 5: Define go/no-go criteria**
- Must-have requirements
- Decision makers
- Decision timeline
- Contingency plan

**Step 6: Identify risks**
- Product, market, execution risks
- Likelihood and impact
- Mitigation strategies
- Owners for each risk

**Step 7: Get cross-functional buy-in**
- Review with all teams
- Adjust based on feedback
- Get commitment on deliverables and dates
- Finalize and distribute

**Step 8: Track execution**
- Weekly (or daily near launch) check-ins
- Update status of deliverables
- Flag blockers early
- Coordinate across teams

---

## Launch Plan Checklist

**4-6 weeks before launch:**
- [ ] Launch plan created and approved
- [ ] Cross-functional team assembled
- [ ] Product readiness criteria defined
- [ ] Content plan outlined
- [ ] Sales enablement plan started
- [ ] Support preparation started

**2-4 weeks before launch:**
- [ ] All content drafted
- [ ] Sales training scheduled
- [ ] Support training scheduled
- [ ] Launch campaign ready
- [ ] Analytics tracking configured
- [ ] Go/no-go criteria reviewed

**1 week before launch:**
- [ ] All content approved
- [ ] Sales team trained
- [ ] Support team trained
- [ ] Landing page ready
- [ ] Email sequences loaded
- [ ] Go/no-go decision made

**Launch day:**
- [ ] Product live
- [ ] Content published
- [ ] Emails sent
- [ ] Social posts live
- [ ] Team monitoring
- [ ] Issues triaged quickly

**Post-launch:**
- [ ] Daily/weekly performance reviews
- [ ] Quick optimizations
- [ ] Feedback collected
- [ ] Retrospective completed

---

## Success Factors

**Great launch plans:**
- Cross-functional (all teams represented)
- Timeline-driven (clear milestones)
- Risk-aware (identified and mitigated)
- Metric-focused (clear success criteria)
- Flexible (contingency plans ready)

**Red flags:**
- ❌ Single function planning alone (usually marketing)
- ❌ Unrealistic timeline (insufficient preparation time)
- ❌ No go/no-go criteria (launch happens regardless)
- ❌ Unclear success metrics (can't measure outcomes)
- ❌ No risk planning (surprised by predictable issues)
