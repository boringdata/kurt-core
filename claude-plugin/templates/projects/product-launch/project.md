# Product Launch Campaign Template

## Goal

Launch [PRODUCT/FEATURE NAME] with comprehensive content across multiple formats: announcement blog post, documentation, tutorial, and marketing assets.

**Multi-format campaign** requiring multiple content deliverables.

## Intent Category

**Content Type:** Multi-format campaign (blog, docs, tutorial, marketing)
**Primary Goal:** Drive awareness and adoption of new product/feature
**Audience:** Mixed (technical users, decision-makers, general audience)

## Sources (Ground Truth)

### From Organizational Knowledge Base

*Reference existing content:*
- Product documentation (existing features)
- API documentation
- Related tutorials
- Brand guidelines
- Previous launch announcements (for format/tone)

### Project-Specific Sources

*Add to `projects/[project-name]/sources/`:*
- Product requirements document (PRD)
- Engineering specifications
- Design mockups/prototypes
- Beta user feedback
- Marketing positioning document

## Targets (Content to Update/Create)

### New Content to Create

*Launch deliverables:*

1. **Announcement Blog Post**
   - Format: Feature announcement with value proposition
   - Length: 800-1200 words

2. **Product Documentation**
   - Sections: Overview, Getting Started, API Reference, Examples
   - Length: 2000-3000 words

3. **Tutorial**
   - Format: Step-by-step implementation guide
   - Length: 1500-2000 words

4. **Quick Start Guide**
   - Format: Concise getting-started
   - Length: 500-800 words

### Existing Content to Update

*Update related content:*
- Main product overview page (add new feature)
- API reference (add new endpoints)
- Pricing page (if pricing changes)
- FAQ (add new feature questions)

## Rules Configuration

### Style

*Multiple voices needed:*
- **Blog post:** rules/style/marketing-voice.md
- **Documentation:** rules/style/technical-docs.md
- **Tutorial:** rules/style/tutorial-voice.md

### Structure

*Templates for each content type:*
- rules/structure/announcement-post.md
- rules/structure/api-documentation.md
- rules/structure/tutorial.md
- rules/structure/quick-start.md

### Personas

*Multiple audiences:*
- Decision-makers (blog post - business value)
- Developers (docs/tutorial - implementation)
- Product users (quick start - immediate value)

### Publisher Profile
- Use rules/publisher/publisher-profile.md

## Progress

- [ ] Product research completed
- [ ] Messaging and positioning defined
- [ ] Blog post drafted
- [ ] Documentation drafted
- [ ] Tutorial drafted
- [ ] Quick start drafted
- [ ] All code examples tested
- [ ] Screenshots captured
- [ ] Marketing review completed
- [ ] Technical review completed
- [ ] All content published
- [ ] Launch promoted

## Next Steps

**Workflow:**

1. **Research & Planning** (1-2 days)
   - Review PRD and specs
   - Identify key features and benefits
   - Define messaging and positioning
   - Determine content deliverables needed

2. **Outlining** (Half day)
   - Create outlines for all deliverables
   - Map feature benefits to content pieces
   - Plan code examples and demos

3. **Content Creation** (1-2 weeks, can parallelize)
   - Draft blog post
   - Write documentation
   - Create tutorial
   - Write quick start guide
   - Test all code examples

4. **Review & Approval** (3-5 days)
   - Marketing review (messaging, positioning)
   - Technical review (accuracy, code examples)
   - Product review (feature completeness)

5. **Publication** (1 day)
   - Publish in coordinated sequence
   - Update related existing content

6. **Promotion**
   - Share on social media
   - Send to email list
   - Track engagement metrics

---

**To use this template:**
1. Clone with `/clone-project product-launch`
2. Customize product name and features
3. Add PRD and specs to sources
4. Adjust deliverables based on launch scope
5. Follow the progress checklist
