<!--
SETUP INSTRUCTIONS FOR CLAUDE:

When a user clones this template, follow these steps:

1. Ask the user:
   - "What product/feature are you launching?" (get name)
   - "Do you have the PRD, specs, or product info available?"
   - If yes: "Please share or provide path to PRD/specs"
   - If no: "I'll need product details. Can you provide:
     - What it does (core functionality)
     - Who it's for (target audience)
     - Why it matters (key benefits)
     - How it works (basic technical approach)"

2. Determine launch scope:
   Ask: "What content deliverables do you need for this launch?
   Common options:
   - Announcement blog post
   - Product documentation
   - Tutorial/how-to guide
   - Quick start guide
   - Marketing email
   - Social posts
   - Product page updates

   Which of these apply?"

3. Gather reference materials:
   ```bash
   # Find existing product docs for style
   kurt content list --url-contains /docs/
   kurt content list --url-contains /product/

   # Find previous launch announcements for format
   kurt content list | grep -i "announc\|launch"

   # If not fetched:
   kurt content fetch https://[domain]/path
   ```

4. Define messaging and positioning:
   - Key features: What are the 3-5 main features?
   - Target audience: Who is this for?
   - Value proposition: What problem does it solve?
   - Differentiators: What makes it unique?

5. Populate "Launch Deliverables" section with specific content pieces

6. Create timeline:
   - When is launch date?
   - When do drafts need review?
   - What's the publication sequence?

7. For each deliverable, determine:
   - Format template to use (from kurt/templates/formats/)
   - Sources needed
   - Target audience
   - Key messages to include
-->

<project_level_details>
# Product Launch - {{PRODUCT_NAME}}

## Goal
Launch {{PRODUCT_NAME}} with comprehensive content campaign across multiple formats to drive awareness and adoption.

**Launch date:** {{DATE}}

**Prerequisites:**
- ✓ Product specs/PRD available
- ✓ Product is ready (beta/production)
- ✓ Target audience defined
- ✓ Key messaging/positioning defined

## Research Required
<!-- Understand the product and competitive context -->
- [ ] Product functionality: What does it do? How does it work?
- [ ] Target audience: Who is this for? What's their use case?
- [ ] Competitive landscape: How does this compare to alternatives?
- [ ] Customer pain points: What problems does this solve?
- [ ] Beta feedback: What did early users say? (if available)

## Content Planning Required
<!-- Determine deliverables and messaging -->
- [ ] Launch deliverables: Which content pieces needed?
- [ ] Messaging framework: Key benefits, value props, differentiators
- [ ] Audience mapping: Which content for which persona?
- [ ] Example planning: What demos/code examples to show?
- [ ] Timeline: When does each piece need to be ready?

</project_level_details>

---

<document_details>

## Launch Deliverables

### Core Messaging

**Product name:** {{PRODUCT_NAME}}
**Tagline:** {{ONE_LINE_DESCRIPTION}}

**Target audience:**
- Primary: {{AUDIENCE_1}} (e.g., "Backend developers building APIs")
- Secondary: {{AUDIENCE_2}} (e.g., "Engineering leaders evaluating tools")

**Key value propositions:**
1. {{VALUE_PROP_1}} (e.g., "Reduce API response time by 10x")
2. {{VALUE_PROP_2}} (e.g., "Deploy in minutes, not hours")
3. {{VALUE_PROP_3}} (e.g., "Auto-scales without configuration")

**Key features:**
1. {{FEATURE_1}} - {{BENEFIT_1}}
2. {{FEATURE_2}} - {{BENEFIT_2}}
3. {{FEATURE_3}} - {{BENEFIT_3}}

**Differentiators:**
- {{DIFF_1}} (e.g., "Only solution with built-in caching")
- {{DIFF_2}} (e.g., "Works with existing infrastructure")

---

### Content Pieces to Create

#### 1. Announcement Blog Post
- **Format template:** `/kurt/templates/formats/blog-post-thought-leadership.md`
- **Target audience:** Mixed (decision-makers + technical users)
- **Goal:** Generate awareness and excitement
- **Length:** 800-1200 words
- **Key messages:** Value props, key features, how it helps
- **CTA:** "Get started" or "Learn more"
- **Status:** [ ] Outlined | [ ] Drafted | [ ] Reviewed | [ ] Published
- **Draft location:** `projects/{{PROJECT}}/drafts/announcement-blog-post.md`

#### 2. Product Documentation
- **Format template:** `/kurt/templates/formats/documentation-tutorial.md`
- **Target audience:** Developers implementing the product
- **Goal:** Enable successful implementation
- **Sections needed:**
  - Overview (what it is, when to use)
  - Getting Started
  - Core Concepts
  - API Reference (if applicable)
  - Examples
  - Troubleshooting
- **Length:** 2000-3000 words
- **Status:** [ ] Outlined | [ ] Drafted | [ ] Reviewed | [ ] Published
- **Draft location:** `projects/{{PROJECT}}/drafts/product-documentation.md`

#### 3. Tutorial / How-To Guide
- **Format template:** `/kurt/templates/formats/documentation-tutorial.md`
- **Target audience:** Developers building their first integration
- **Goal:** Working implementation in 30 minutes
- **Structure:** Step-by-step with code examples
- **Length:** 1500-2000 words
- **Status:** [ ] Outlined | [ ] Drafted | [ ] Reviewed | [ ] Published
- **Draft location:** `projects/{{PROJECT}}/drafts/tutorial.md`

#### 4. Quick Start Guide
- **Format template:** `/kurt/templates/formats/documentation-tutorial.md` (condensed)
- **Target audience:** Developers wanting immediate value
- **Goal:** "Hello World" in 5 minutes
- **Length:** 500-800 words
- **Status:** [ ] Outlined | [ ] Drafted | [ ] Reviewed | [ ] Published
- **Draft location:** `projects/{{PROJECT}}/drafts/quick-start.md`

#### 5. Product Page (Optional)
- **Format template:** `/kurt/templates/formats/product-page.md`
- **Target audience:** Prospects evaluating the product
- **Goal:** Drive sign-ups or trials
- **Sections:** Hero, features, use cases, proof, CTA
- **Status:** [ ] Outlined | [ ] Drafted | [ ] Reviewed | [ ] Published
- **Draft location:** `projects/{{PROJECT}}/drafts/product-page.md`

#### 6. Marketing Email (Optional)
- **Format template:** `/kurt/templates/formats/marketing-email.md`
- **Target audience:** Existing users/subscribers
- **Goal:** Drive traffic to announcement
- **Length:** 200-400 words
- **Status:** [ ] Outlined | [ ] Drafted | [ ] Reviewed | [ ] Published
- **Draft location:** `projects/{{PROJECT}}/drafts/launch-email.md`

#### 7. Social Media Posts (Optional)
- **Format template:** `/kurt/templates/formats/social-media-post.md`
- **Platforms:** LinkedIn, Twitter, etc.
- **Goal:** Amplify announcement
- **Status:** [ ] Outlined | [ ] Drafted | [ ] Reviewed | [ ] Published
- **Draft location:** `projects/{{PROJECT}}/drafts/social-posts.md`

---

### Existing Content to Update

*Pages that need updates to reference new product/feature:*

- [ ] **{{PAGE_NAME}}** ({{URL}})
  - Update needed: {{DESCRIPTION}} (e.g., "Add new feature to features list")
  - Format: Quick edit vs full rewrite

---

### Code Examples & Demos

*All code examples must be tested before publication:*

- [ ] **Example 1:** {{DESCRIPTION}} (e.g., "Basic setup and initialization")
  - Code: {{LANGUAGE}}
  - Location: `projects/{{PROJECT}}/examples/example-1.{{EXT}}`
  - Tested: Yes/No

- [ ] **Example 2:** {{DESCRIPTION}} (e.g., "Advanced use case with custom config")
  - Code: {{LANGUAGE}}
  - Location: `projects/{{PROJECT}}/examples/example-2.{{EXT}}`
  - Tested: Yes/No

---

### Visual Assets Needed

*Screenshots, diagrams, or other visuals:*

- [ ] Architecture diagram showing how product works
- [ ] Screenshots of key features/UI
- [ ] Demo video (optional)
- [ ] Product logo/icon

</document_details>

---

<project_tracking>

## Progress Tracking

### Phase 1: Research & Planning
- [ ] Product specs/PRD reviewed
- [ ] Target audience defined
- [ ] Key features and benefits identified
- [ ] Messaging and positioning defined
- [ ] Deliverables list finalized
- [ ] Timeline and deadlines set
- [ ] Reference content gathered (previous launches, existing docs)

### Phase 2: Outlining
- [ ] Blog post outline created
- [ ] Documentation structure defined
- [ ] Tutorial steps outlined
- [ ] Quick start outline created
- [ ] Code examples planned
- [ ] Visual assets identified
- [ ] All outlines approved

### Phase 3: Content Creation
- [ ] Announcement blog post drafted
- [ ] Product documentation drafted
- [ ] Tutorial drafted
- [ ] Quick start guide drafted
- [ ] Marketing email drafted (if applicable)
- [ ] Social posts drafted (if applicable)
- [ ] All code examples written and tested
- [ ] Screenshots/diagrams created

### Phase 4: Review & Approval
- [ ] Marketing review (messaging, positioning, voice)
- [ ] Technical review (accuracy, code examples, completeness)
- [ ] Product review (feature descriptions, benefits)
- [ ] Legal review (claims, compliance) (if required)
- [ ] Final edits incorporated

### Phase 5: Publication
- [ ] Documentation published to docs site
- [ ] Blog post published
- [ ] Product page updated (if applicable)
- [ ] Existing content updated
- [ ] All links verified working

### Phase 6: Promotion
- [ ] Email sent to subscribers
- [ ] Social posts published
- [ ] Internal team notified
- [ ] Press/media outreach (if applicable)
- [ ] Performance tracking started

</project_tracking>

---

<sources_and_research>

## Data Sources

### Product Information
- PRD/Specs: {{PATH_OR_DESCRIPTION}}
- Engineering docs: {{PATH}}
- Design mockups: {{PATH}}
- Beta feedback: {{SUMMARY}}

### Reference Content
- Previous launches: {{LINKS}}
- Existing product docs: {{DOMAIN}}/docs/
- Brand guidelines: {{PATH}}

### Research Data
- Competitive analysis: {{SUMMARY_OR_PATH}}
- Customer interviews: {{SUMMARY}}
- Market research: {{SOURCE}}

</sources_and_research>

---

## Workflow Instructions

**Step 1: Gather Product Information (1-2 days)**

Ask user for core product materials:
- PRD or product specs
- Feature list with benefits
- Target audience description
- Positioning/messaging (if available)

If product content already indexed:
```bash
# Discover what product pages exist
kurt content list --url-contains /product
kurt content list --url-contains /docs/

# Search for product information
kurt content search "product"
kurt content search "feature"

# Get relevant docs
kurt content get <doc-id>
```

**Step 2: Research Competitive Context (1-2 hours)**

Understand how this fits in the market:

```bash
# Research competitor solutions
kurt research query "[product category] solutions comparison"

# Check discussions
kurt research search --source hackernews --query "[product category]"
kurt research search --source reddit --query "[product category] tools"
```

**Step 3: Define Messaging Framework (2-3 hours)**

Work with user to define:

**Target audience:**
- Primary: Who will use this most?
- Secondary: Who influences the decision?

**Value propositions:**
- What problems does it solve?
- What outcomes does it deliver?
- Why is it better than alternatives?

**Key features:**
- What are the 3-5 headline features?
- What benefit does each deliver?

**Differentiators:**
- What makes this unique?
- Why choose this over competitors?

**Step 4: Determine Deliverables (30 min)**

Ask user: "What content do you need for this launch?"

**Standard set:**
- Announcement blog post
- Product documentation
- Tutorial or quick start

**Optional additions:**
- Marketing email
- Social posts
- Product page
- Video script
- Press release

**Step 5: Create Outlines (Half day)**

For each deliverable, create outline using appropriate format template:

```markdown
# Create draft with outline
# Follow format template from /kurt/templates/formats/

# Document in project plan which format template each deliverable uses
```

**Step 6: Draft Content (1-2 weeks, can parallelize)**

Work through each deliverable:

1. Start with announcement blog post (establishes messaging)
2. Then documentation (provides technical foundation)
3. Then tutorial (practical implementation)
4. Then supporting content (email, social, etc.)

**Important:**
- Use format templates for each content type
- Reference sources in frontmatter
- Test all code examples
- Create/gather visual assets

**Step 6.5: Validate Documentation Coverage (30 min)**

Before proceeding to review, verify all necessary topics and technologies are documented:

```bash
# Check what topics are covered in your documentation
kurt content list-topics --include "https://{{YOUR_DOMAIN}}/docs/**"

# Check what technologies are documented
kurt content list-technologies --include "https://{{YOUR_DOMAIN}}/docs/**"

# Verify each product feature has corresponding documentation
kurt content list --with-topic "[feature-name]"
```

**Coverage checklist:**
- [ ] All key features have documentation
- [ ] All supported technologies/integrations documented
- [ ] Getting started guide exists
- [ ] API reference complete (if applicable)
- [ ] Troubleshooting guide exists
- [ ] Migration guide exists (if updating existing product)

**If gaps found:**
- Add missing documentation to deliverables list
- Prioritize based on importance to launch
- May require adjusting launch timeline

**Step 7: Review Cycle (3-5 days)**

Multiple review types:

**Marketing review:**
- Is messaging consistent?
- Does it match brand voice?
- Are value props clear?

**Technical review:**
- Are code examples correct?
- Is technical detail accurate?
- Does implementation work?

**Product review:**
- Are features described correctly?
- Is anything missing?
- Are benefits accurately stated?

**Step 8: Publish in Sequence (Launch day)**

**Recommended sequence:**
1. Documentation goes live first (so links work)
2. Blog post published
3. Product page updated (if applicable)
4. Email sent to list
5. Social posts go out
6. Internal announcement

**Commands:**
```bash
# If publishing to CMS
kurt integrations cms publish --file <path> --content-type <type>

# Verify links work
# Check all cross-references
```

**Step 9: Promote (1 week)**

- Social media posts
- Email follow-ups
- Community engagement
- Press outreach (if applicable)

**Step 10: Measure & Iterate (Ongoing)**

Track performance:
```bash
# If analytics configured
kurt integrations analytics sync [domain]
kurt content list --with-analytics

# Monitor:
# - Traffic to announcement, docs, tutorial
# - Sign-ups or conversions
# - Social engagement
# - Support tickets (quality signal)
```

---

## Content Coordination Tips

**Start with Messaging:**
- Define core messages first
- Use consistent language across all pieces
- Create shared glossary for feature names

**Reuse Strategically:**
- Extract key sections for reuse (value props, feature descriptions)
- Adapt tone for each format (marketing vs technical)
- Keep code examples consistent across docs and tutorial

**Test Everything:**
- All code examples must actually work
- All links must resolve
- All screenshots must be current

**Sequence Matters:**
- Documentation before blog post (so you can link to it)
- Blog post before social (so there's something to link to)
- Email after blog post goes live

**Plan for Updates:**
- Product will evolve post-launch
- Keep documentation updated
- Track feedback for improvements

---

## Launch Checklist

**Pre-Launch (1 week before):**
- [ ] All content drafted and approved
- [ ] All code examples tested
- [ ] All visual assets ready
- [ ] Publication sequence planned
- [ ] Promotion plan ready
- [ ] Analytics tracking configured

**Launch Day:**
- [ ] Documentation published
- [ ] Blog post published
- [ ] Product page updated
- [ ] Email sent
- [ ] Social posts published
- [ ] Internal team notified
- [ ] All links verified working

**Post-Launch (1 week after):**
- [ ] Performance metrics reviewed
- [ ] Feedback collected
- [ ] Quick fixes made (if needed)
- [ ] Follow-up content planned

---

## Success Metrics

**Awareness:**
- Blog post views
- Social engagement (likes, shares, comments)
- Email open/click rates

**Adoption:**
- Documentation page views
- Tutorial completion (time on page)
- Sign-ups or trials started

**Quality:**
- Time on page (engagement)
- Bounce rate (relevance)
- Support tickets (clarity)
- User feedback/comments

**Track over time:**
- Week 1: Launch spike
- Month 1: Sustained interest
- Quarter 1: Long-tail discovery

---

## Common Launch Patterns

**Small Feature Launch:**
- Blog post + documentation + quick start
- 1-2 week timeline
- Light promotion

**Major Product Launch:**
- Full content suite (blog, docs, tutorial, marketing)
- 3-4 week timeline
- Heavy promotion, press outreach

**Beta to GA Launch:**
- Update existing beta docs
- Announcement post highlighting improvements
- Migration guide for beta users

**API/Developer Tool Launch:**
- Heavy emphasis on documentation and examples
- Interactive demos or playgrounds
- Developer community engagement
