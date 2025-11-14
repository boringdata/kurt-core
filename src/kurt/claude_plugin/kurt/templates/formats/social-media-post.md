# Social Media Post Template

## Overview
- **Purpose:** Drive engagement, awareness, traffic, or specific action on social platforms
- **Length:** Platform-dependent (see below)
- **Platforms:** LinkedIn, Twitter/X, Facebook, Instagram (adapt per platform)
- **Success metrics:** Engagement rate, clicks, shares, conversions

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Platform Focus:**
- Primary: [LinkedIn / Twitter / Facebook / Instagram / Multi-platform]
- Adaptation: [same message across all / customized per platform]

**Opening Hook:**
- Style: [question / stat / bold claim / story / emoji]
- Examples: "[hook 1]", "[hook 2]"

**Content Style:**
- Format: [text-only / text+link / visual-heavy]
- Length: [short / medium / long-form]
- Line breaks: [frequent / minimal]

**Tone:**
- Formality: [1-10 scale]
- Voice: [we / you / personal]
- Energy level: [enthusiastic / professional / casual]

**DO/DON'T Examples (from their actual posts):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Hashtags:**
- Usage: [frequent / occasional / minimal / none]
- Count: [X hashtags typical]
- Style: [branded / trending / descriptive]

**Visual Elements:**
- Style: [product screenshots / graphics / photos / minimal]
- Frequency: [always / often / occasional]

**CTA:**
- Explicitness: [direct link / soft "learn more" / question / none]
- Placement: [beginning / end / comments]

---

## Platform Guidelines

### LinkedIn (Professional B2B)
- **Length:** 1300-2000 characters optimal (can go longer)
- **Format:** Line breaks between paragraphs, emoji optional
- **Hook:** First 2 lines critical (before "see more")
- **Best for:** Thought leadership, company updates, professional insights
- **Links:** Place in first comment or inline

### Twitter/X
- **Length:** 280 characters max (threads for longer)
- **Format:** Concise, punchy, thread-friendly
- **Hook:** First tweet must grab attention
- **Best for:** Quick insights, hot takes, real-time updates
- **Links:** Include inline (auto-shortened)

### Facebook
- **Length:** 40-80 characters for highest engagement (can go longer)
- **Format:** Conversational, personal
- **Hook:** Strong first line
- **Best for:** Community building, events, behind-the-scenes
- **Links:** Place in post or first comment

### Instagram
- **Length:** 2200 characters max (but caption often secondary to visual)
- **Format:** Line breaks, emoji-heavy, storytelling
- **Hook:** First line (before "more")
- **Best for:** Visual storytelling, brand personality, culture
- **Links:** Bio link only (unless Stories/Reels)

---

## Research Requirements

**Types of information needed for social posts:**

1. **Content/message** - What you're sharing
   - Find: `kurt content search "<topic>"`
   - Or provide: Blog post, product update, announcement, insight to share

2. **Trending topics** - What's relevant now
   - Search discussions: `kurt research search --source hackernews --query "[industry topic]"`
   - Search discussions: `kurt research search --source reddit --query "[trend]"`
   - Or provide: Industry news, current events, trending hashtags

3. **Audience insights** - What resonates
   - Or provide: Past post performance data, audience research, engagement patterns

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Core message/content:**
```bash
# If promoting content
kurt content search "<topic>"

# Get the piece you're promoting
kurt content get <doc-id>
```

**Context/validation:**
```bash
# Related content for context
kurt content list --url-contains /blog/
kurt content list --url-contains /docs/
```

**If insufficient sources: Ask user for the content to promote, key message, or topic to discuss**

---

## Structure

```markdown
---
project: project-name
document: social-post-YYYY-MM-DD-topic
format_template: /kurt/templates/formats/social-media-post.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/blog/article-name.md
    purpose: "content being promoted"

outline:
  hook:
    sources: [/sources/blog/article-name.md]
    purpose: "attention-grabbing opening"
  body:
    sources: [/sources/blog/article-name.md]
    purpose: "value/insight"
  cta:
    sources: []
    purpose: "action or engagement"
---

## LinkedIn Version

[Hook: First 2 lines that appear before "see more"]
[Make these count - they determine if people expand]

[Body: 3-5 short paragraphs with line breaks]
[Share insight, story, or value]
[Keep paragraphs 1-2 sentences]

[CTA or question to drive engagement]

[Optional: Relevant hashtags]

---

## Twitter/X Version

[Single tweet OR thread]

Tweet 1 (Hook):
[280 char max - grab attention]

[If thread:]
Tweet 2:
[Continue the thought]

Tweet 3:
[Deliver value or insight]

Tweet 4:
[CTA or link]

---

## Facebook Version

[Short, conversational hook]

[Brief value or story - keep it personal]

[Question or CTA to drive engagement]

---

## Instagram Version (Caption)

[Strong first line - before "more"]

[2-3 short paragraphs with lots of line breaks]
[Storytelling or emotional connection]
[More casual than LinkedIn]

[CTA]

[Hashtags - typically 5-15 for Instagram]
[#Hashtag1 #Hashtag2 #Hashtag3...]

---

## Notes

**Visual needs:**
- LinkedIn: [Describe image/graphic needed]
- Twitter: [Image requirements]
- Facebook: [Visual needs]
- Instagram: [Primary visual - this is the main content]
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/social-post-YYYY-MM-DD-topic.md`

**Step 1: YAML frontmatter + outline**
- Identify core message/content to promote
- Note hook angle
- Map sources
- Set status: `outline`

**Step 2: Write post(s) below frontmatter**
- Update status to `draft`
- Start with platform-agnostic message
- Adapt for each platform
- Match company's social style
- Reference sources: `<!-- Source: /path -->`

**Step 3: Character count check**
- Twitter: Must be ≤280 chars per tweet
- Instagram: ≤2200 chars
- LinkedIn: Can be long but hook critical
- Facebook: Short performs better

**Step 4: Visual planning**
- Note what images/graphics needed
- Describe or link to visuals
- Consider platform best practices

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing social posts for this company

**Goal:** Fill in "[CUSTOMIZATION NEEDED]" section with company's social media style

### Step 1: Get Company's Social Posts

**Ask user for examples:**
"I need 5-10 recent social media posts from [company] to understand your style. Can you:
- Provide links to recent posts (LinkedIn, Twitter, etc.)
- Share screenshot or paste text of successful posts
- Give me access to view your social profiles

Which platform do you use most? (I'll focus there for style)"

**Cannot scrape:** Social posts aren't in kurt database - user must provide

### Step 2: Collect 5-10 Examples (Iterative with User)

**Ask user:**
"Please share 5-10 recent posts that represent your style well. Looking for:
- Mix of content types (product updates, insights, shares)
- Posts that performed well (high engagement)
- Recent posts (last 3 months)

You can paste the text or send links."

**Save provided posts:**
- As: `projects/<project>/style-examples/social-posts.md`
- Analyze from these

**Maximum: 10 examples**

### Step 3: Analyze Examples

**For each post, note:**

**Platform:**
- Which platform(s) do they use most?
- Do they adapt message per platform or post same across all?

**Opening hooks:**
- How do they start posts? (question, stat, bold claim, emoji)
- Copy 3-5 actual opening lines

**Content style:**
- Length: short and punchy vs longer form?
- Format: frequent line breaks or paragraph blocks?
- Emoji usage: frequent, occasional, rare?

**Tone:**
- Formality 1-10
- Personal voice ("I") or company voice ("we")?
- Energy: enthusiastic, professional, casual?

**DO/DON'T Examples:**
- Find 2-3 posts showing their best social style
- Write contrasting examples showing what they avoid
- Note why (too sales-y, too casual, wrong platform fit, etc.)

**Hashtags:**
- How many hashtags typical?
- Style: branded (#CompanyName), trending, descriptive?
- Copy hashtag patterns

**Visuals:**
- Always include image or sometimes text-only?
- Type: product screenshots, graphics, photos?

**CTA:**
- How direct? ("Download now" vs "Thoughts?")
- Where placed? (end of post, comments)
- Copy typical CTAs

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]":**

```markdown
## Style Guidelines

**Platform Focus:**
- Primary: [their main platform]
- Adaptation: [their approach]

**Opening Hook:**
- Style: [observed pattern]
- Examples: "[hook 1]", "[hook 2]"

**Content Style:**
- Format: [their format]
- Length: [typical length]
- Line breaks: [their usage]

**Tone:**
- Formality: [X/10]
- Voice: [we / you / personal]
- Energy level: [their energy]

**DO/DON'T Examples (from their actual posts):**

✅ **DO:** "[Copy exemplary posts]"

❌ **DON'T:** "[Contrasting example]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Hashtags:**
- Usage: [their frequency]
- Count: [X typical]
- Style: [their style]

**Visual Elements:**
- Style: [their approach]
- Frequency: [always / often / occasional]

**CTA:**
- Explicitness: [their style]
- Placement: [where they put it]
```

**Save the updated template file**

### Troubleshooting

**Don't have access to company's social posts?**
- Ask user: "I need 5-10 example posts to match your style. Can you share links or paste text?"
- Essential: Cannot create template without seeing actual posts

**Posts vary widely by platform?**
- Note different styles per platform
- Ask user: "Your LinkedIn style is different from Twitter. Should I match both or focus on one?"

**No consistent style yet?**
- Ask user: "You don't have many posts yet. What style do you prefer?
  - Professional/formal (LinkedIn-style)
  - Conversational/casual (Twitter-style)
  - Visual storytelling (Instagram-style)"

**Need the content to promote?**
- Ask user: "What are we promoting in this post? Please provide:
  - Blog post URL or content
  - Product update details
  - Announcement or news to share"
