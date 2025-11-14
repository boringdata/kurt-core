# Product Update Newsletter Template

## Overview
- **Purpose:** Keep customers informed of product changes, new features, improvements
- **Length:** 400-800 words (scannable sections)
- **Cadence:** Weekly, bi-weekly, or monthly
- **Success metrics:** Open rate, click-through to feature docs, feature adoption

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Subject Line:**
- Pattern: [date-based / feature-focused / emoji usage]
- Examples: "[subject 1]", "[subject 2]"

**Opening:**
- Style: [greeting / summary / theme]
- Example: "[paste actual opening]"

**Update Format:**
- Structure: [headline + description / bullets / categories]
- Length per update: [X sentences]
- Visual style: [emojis / icons / plain]

**Tone:**
- Formality: [1-10 scale]
- Voice: [we / you / neutral]
- Personality: [enthusiastic / professional / technical]

**DO/DON'T Examples (from their actual newsletters):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Categorization:**
- Sections: [New Features / Improvements / Bug Fixes / Coming Soon]
- Order: [importance / category / chronological]

**Links:**
- Style: [inline / dedicated section / learn more buttons]
- Frequency: [every item / major items only]

**Closing:**
- Style: [feedback request / next issue date / sign-off]
- Example: "[copy closing]"

---

## Research Requirements

**Types of information needed for product newsletters:**

1. **Product changes** - What shipped, what changed
   - Find: `kurt content search "changelog|release|update"`
   - Find: `kurt content search "version|release" --include "*/docs/*"`
   - Or provide: Changelog, release notes, Jira/Linear completed tickets

2. **Feature details** - What new features do
   - Find: `kurt content list --url-contains /docs/`
   - Or provide: Feature specs, documentation, product briefs

3. **User impact** - Why users should care
   - Or provide: Product manager notes, user research, feedback

**For advanced discovery/analysis**, see `instructions/find-sources.md`

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Recent changes:**
```bash
# Search for changelogs and release notes
kurt content search "changelog|release-note"
kurt content search "version" --include "*/docs/*"

# If not fetched:
kurt content fetch --urls "<changelog-url>"
```

**Feature documentation:**
```bash
# Find docs for new features
kurt content search "<feature-name>" --include "*/docs/*"
```

**If insufficient sources: Ask user for changelog, release notes, or list of shipped items**

---

## Structure

```markdown
---
project: project-name
document: newsletter-YYYY-MM-DD
format_template: /kurt/templates/formats/product-update-newsletter.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/internal/changelog-march.md
    purpose: "shipped features and fixes"
  - path: /sources/docs/new-api-endpoint.md
    purpose: "feature details"
  - path: /sources/internal/product-roadmap-q2.md
    purpose: "coming soon preview"

outline:
  opening:
    sources: []
    purpose: "greeting and theme"
  new-features:
    sources: [/sources/internal/changelog-march.md, /sources/docs/new-api-endpoint.md]
    purpose: "major new capabilities"
  improvements:
    sources: [/sources/internal/changelog-march.md]
    purpose: "enhancements and updates"
  bug-fixes:
    sources: [/sources/internal/changelog-march.md]
    purpose: "issues resolved"
  coming-soon:
    sources: [/sources/internal/product-roadmap-q2.md]
    purpose: "preview of next release"
---

**Subject:** [Product Name] Updates - [Month/Date]

---

Hi {{FirstName}},

[Opening: brief greeting or theme for this update period]

[Optional: Highlight of most exciting update]

---

## 🎉 New Features

### [Feature Name]
[2-3 sentences: what it is, why it matters, who it's for]
[Link: Read the docs →]

### [Feature Name]
[2-3 sentences: what it is, why it matters, who it's for]
[Link: Read the docs →]

---

## ✨ Improvements

- **[Improvement 1]** - [1 sentence explanation]
- **[Improvement 2]** - [1 sentence explanation]
- **[Improvement 3]** - [1 sentence explanation]

---

## 🐛 Bug Fixes

- Fixed [issue description]
- Resolved [issue description]
- Corrected [issue description]

---

## 🔮 Coming Soon

[1-2 paragraph preview of what's next]

[Optional: Link to roadmap or beta program]

---

[Closing paragraph: thanks, feedback request, or next issue date]

[Sign-off]
[Team/Company name]

---

[View in browser] | [Update preferences] | [Unsubscribe]
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/newsletter-YYYY-MM-DD.md`

**Step 1: YAML frontmatter + outline**
- List sections (new, improvements, fixes, coming soon)
- Map changelog/sources to sections
- Set status: `outline`

**Step 2: Gather all changes**
- Review changelog, Jira/Linear, release notes
- Categorize: new features vs improvements vs fixes
- Prioritize: most impactful changes first

**Step 3: Write newsletter below frontmatter**
- Update status to `draft`
- Keep descriptions concise (2-3 sentences max)
- Link to detailed docs
- Match company's newsletter style
- Reference sources: `<!-- Source: /path -->`

**Step 4: Review with product team**
- Verify technical accuracy
- Confirm links work
- Check nothing is missing

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing product newsletter for this company

**Goal:** Fill in "[CUSTOMIZATION NEEDED]" section with company's newsletter style

### Step 1: Find Company's Past Newsletters

**Check archives or ask user:**
"I need 3-5 example product update newsletters from [company]. Can you:
- Forward recent newsletters
- Provide links to archived versions
- Paste newsletter content directly"

**If you have archives:**
```bash
# Search saved newsletters
ls projects/<project>/style-examples/newsletters/
```

### Step 2: Select 3-5 Examples (Iterative with User)

**Ask user:**
"Can you provide 3-5 recent product update newsletters? These help me match your style."

**Save provided newsletters:**
- As: `projects/<project>/style-examples/newsletter-1.md`
- Analyze from these files

**Maximum: 5 examples**

### Step 3: Analyze Examples

**For each newsletter, note:**

**Subject lines:**
- What pattern? (date, feature name, emoji)
- Copy 3-5 actual subject lines

**Opening:**
- Standard greeting or thematic?
- Do they preview the highlight?
- Copy 2-3 openings

**Update format:**
- How structured? (headlines + description, bullets, plain list)
- How long is each update? (sentences)
- Use emojis or icons?
- Copy example section

**Categorization:**
- What sections? (New/Improvements/Fixes/Coming Soon)
- Order of importance or category?
- Do they have "coming soon" preview?

**Tone:**
- Formality 1-10
- Enthusiastic or matter-of-fact?
- Technical depth

**DO/DON'T Examples:**
- Find 2-3 sentences showing best newsletter style
- Write contrasting examples
- Note why they avoid certain patterns

**Links:**
- Inline links or "Learn more" buttons?
- Every item or just major ones?
- Copy link format

**Closing:**
- Ask for feedback?
- Preview next newsletter date?
- Copy closing style

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]":**

```markdown
## Style Guidelines

**Subject Line:**
- Pattern: [observed pattern]
- Examples: "[subject 1]", "[subject 2]"

**Opening:**
- Style: [their approach]
- Example: "[actual opening]"

**Update Format:**
- Structure: [their structure]
- Length per update: [X sentences]
- Visual style: [emojis / icons / plain]

**Tone:**
- Formality: [X/10]
- Voice: [we / you / neutral]
- Personality: [enthusiastic / professional / technical]

**DO/DON'T Examples (from their actual newsletters):**

✅ **DO:** "[Copy exemplary sentences]"

❌ **DON'T:** "[Contrasting example]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Categorization:**
- Sections: [their sections]
- Order: [their ordering]

**Links:**
- Style: [their style]
- Frequency: [when they link]

**Closing:**
- Style: [their approach]
- Example: "[copy closing]"
```

**Save the updated template file**

### Troubleshooting

**Don't have access to past newsletters?**
- Ask user: "I need 3-5 example newsletters. Can you forward or paste them?"
- Check: Company blog for newsletter archives

**No newsletters exist yet?**
- Ask user: "This is the first newsletter. What style do you prefer?"
- Offer: "I can suggest a format based on Stripe's style, then customize as you create more"

**Need changelog or release notes?**
- Ask user: "I need a list of what shipped. Can you provide:
  - Changelog or release notes
  - Jira/Linear completed tickets
  - Product manager summary of changes"

**Don't know what's coming soon?**
- Ask user: "Do you want a 'coming soon' section? If yes, what's planned?"
- Optional: Skip coming soon section if no roadmap available
