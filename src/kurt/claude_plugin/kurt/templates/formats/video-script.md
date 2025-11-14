# Video Script Template

## Overview
- **Purpose:** Script for product demos, tutorials, or explainer videos
- **Length:** 60-90 seconds (150-225 words) for short / 3-5 min (450-750 words) for long
- **Audience:** Varies by video type (prospects, users, general audience)
- **Success metrics:** View completion rate, engagement, conversions

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Tone:**
- Personality: [Casual / Professional / Enthusiastic / Technical]
- Pacing: [Fast / Moderate / Slow and clear]
- Energy: [High energy / Calm / Conversational]

**Script style:**
- Language: [Conversational / Script-like / Natural speech]
- Complexity: [Simple / Moderate / Technical]
- Humor: [Playful / Minimal / None]

**DO/DON'T Examples (from their actual videos):**

✅ **DO:** "[Copy script excerpt that exemplifies their video style]"
- Why this works: [Reason - conversational, clear, engaging, etc.]

❌ **DON'T:** "[Contrasting example - too stiff, too complex, etc.]"
- Reason: [Why they avoid this - not authentic, confusing, etc.]

---

## Research Requirements

**Types of information needed for video script:**

1. **Video type** - What kind of video is this
   - Product demo (show product in action)
   - Tutorial (teach how to do something)
   - Explainer (explain concept or feature)
   - Testimonial (customer story)
   - Company/brand video

2. **Existing video examples** - Style and structure reference
   - Find: `kurt content search "video"`
   - Or provide: Links to your existing videos, competitor videos for reference

3. **Product/feature details** - What to show
   - Find: `kurt content list --url-contains /product`
   - Search: `kurt content search "[feature name]"`
   - Or provide: Product docs, feature specs, screenshots

4. **Target audience** - Who watches this
   - Find: `kurt content search "persona"`
   - Or provide: Audience description, their pain points, their goals

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Video references:**
```bash
# Find existing videos or video scripts
kurt content search "video"
kurt content search "demo"
kurt content search "tutorial"
```

**Product information:**
```bash
# Discover product pages
kurt content list --url-contains /product
kurt content list --url-contains /features

# Search for specific feature
kurt content search "[feature-name]"
```

**Audience insights:**
```bash
# Find persona docs
kurt content search "persona"
kurt content search "customer"
```

**If insufficient sources: Ask user for video examples, product screenshots/demo, or target audience definition**

---

## Structure

```markdown
---
project: project-name
document: video-script-[video-name]
format_template: /kurt/templates/formats/video-script.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/product/feature-details.md
    purpose: "product information to demo"
  - path: /sources/videos/reference-video.md
    purpose: "style reference"

outline:
  hook:
    sources: []
    purpose: "grab attention in first 5 seconds"
  problem:
    sources: [/sources/product/feature-details.md]
    purpose: "establish pain point"
  solution:
    sources: [/sources/product/feature-details.md]
    purpose: "show how product solves it"
  demo:
    sources: [/sources/product/feature-details.md]
    purpose: "walkthrough of key features"
  cta:
    sources: []
    purpose: "what to do next"
---

# Video Script: [Video Title]

**Video Type:** [Product Demo / Tutorial / Explainer / Testimonial / Brand]
**Target Length:** [60-90 sec / 2-3 min / 5 min]
**Target Audience:** [Who this is for]
**Goal:** [What action we want them to take]

---

## Pre-Production Notes

**Visuals needed:**
- Screen recordings: [List screens/features to record]
- B-roll: [Additional footage needed]
- Graphics: [Logos, text overlays, animations]
- Screenshots: [Specific screens to capture]

**Audio needs:**
- Voiceover: [Professional VO / Founder / Team member]
- Music: [Upbeat / Calm / None]
- Sound effects: [UI clicks / Transitions / None]

**Recording environment:**
- Clean demo environment with test data
- Updated UI (latest version)
- Prepared user account

---

## Script (Two-Column Format)

| TIME | VISUAL | AUDIO |
|------|---------|-------|
| **0:00-0:05** | [Opening shot - logo/product interface] | **HOOK:** [Attention-grabbing opening line] |
| | *Production note: Fast-paced cuts, upbeat music starts* | *Example: "Tired of spending hours on [task]? What if you could do it in 30 seconds?"* |
| | | |
| **0:05-0:15** | [Show problem - frustrated user / messy workflow] | **PROBLEM:** [Set up the pain point] |
| | *Show: Screenshots of current painful process* | *"Most teams struggle with [specific problem]. They're stuck using [old method], which means [negative consequence]."* |
| | | |
| **0:15-0:25** | [Transition to product - logo/interface] | **INTRODUCTION:** [Introduce your product] |
| | *Show: Product logo and tagline* | *"Meet [Product Name]. The [category] that [main benefit]."* |
| | | |
| **0:25-1:30** | [Demo of key features] | **DEMO/SOLUTION:** [Show how it works] |
| | *Screen recording: Feature 1* | *"Here's how it works. First, you [action 1]. See how [Product] automatically [benefit]?"* |
| | | |
| | *Screen recording: Feature 2* | *"Next, [action 2]. In just one click, [outcome]. No more [old painful way]."* |
| | | |
| | *Screen recording: Feature 3* | *"And here's the best part: [unique feature]. This means [key benefit customers care about]."* |
| | | |
| **1:30-1:45** | [Show results - happy user / data] | **OUTCOME:** [Demonstrate the value] |
| | *Show: Before/after comparison or metrics* | *"Teams using [Product] save [X hours] per week and [improve metric by Y%]."* |
| | | |
| **1:45-2:00** | [CTA screen - product logo, website] | **CALL TO ACTION:** [Tell them what to do next] |
| | *Text overlay: "Try [Product] Free"* | *"Ready to [achieve outcome]? Start your free trial at [website]. No credit card required."* |
| | *URL: yourproduct.com* | *"That's [website URL]. Get started in less than 5 minutes."* |

---

## Detailed Scene Breakdown

### Scene 1: Hook (0:00-0:05)
**Duration:** 5 seconds
**Goal:** Stop the scroll, grab attention

**Visual:**
- [Describe opening shot]
- Example: "Quick cut montage of frustrated users clicking through complex workflows"

**Audio/Script:**
"[Hook line - question, bold statement, or relatable pain]"

**Example:**
"What if I told you [surprising claim]?"
or
"[Relatable problem] driving you crazy?"

**Production notes:**
- Fast-paced editing
- Upbeat music starts
- Bold text overlay with key question/stat

---

### Scene 2: Problem (0:05-0:20)
**Duration:** 15 seconds
**Goal:** Establish the pain point they can relate to

**Visual:**
- [Show current painful process]
- Example: "Screen recording of user manually copying data between 5 different tools"

**Audio/Script:**
"[Describe the problem clearly]

Most [target audience] spend [time amount] on [painful task]. They're stuck [current bad method], which leads to [negative consequences - errors, wasted time, frustration]."

**Production notes:**
- Show relatable frustration
- Use before footage or competitor workflow if appropriate
- Text overlay emphasizing time wasted or errors made

---

### Scene 3: Introduction (0:20-0:30)
**Duration:** 10 seconds
**Goal:** Introduce your product as the solution

**Visual:**
- Product logo animation
- Clean shot of main product interface
- Brand colors

**Audio/Script:**
"That's why we built [Product Name].

[Product] is the [category/description] that [primary value proposition]."

**Example:**
"That's why we built Acme. Acme is the API monitoring platform that catches issues before your customers do."

**Production notes:**
- Smooth transition from problem to solution
- Brand logo prominently displayed
- Music swells slightly

---

### Scene 4: Demo/How It Works (0:30-1:30)
**Duration:** 60 seconds (adjust based on video length)
**Goal:** Show key features and how they solve the problem

**Feature 1 Demo (0:30-0:50):**
**Visual:**
- Screen recording of first key feature
- Mouse movements should be deliberate and clear
- Zoom in on important UI elements

**Audio/Script:**
"Here's how simple it is. [Describe action 1 clearly].

Watch this - in just [timeframe], [Product] automatically [benefit]. No more [old painful way]."

**Production notes:**
- Highlight UI elements as they're mentioned
- Show real results, not placeholder data
- Keep mouse movements smooth and purposeful

---

**Feature 2 Demo (0:50-1:10):**
**Visual:**
- Screen recording of second key feature
- Show end result clearly

**Audio/Script:**
"Next, [action 2]. See how [feature 2] [demonstrates benefit]?

This means [concrete outcome customer cares about - saved time, fewer errors, happier team]."

**Production notes:**
- Connect feature to customer benefit
- Show before/after or improvement clearly

---

**Feature 3 / Unique Value (1:10-1:30):**
**Visual:**
- Screen recording of differentiating feature
- or montage showing multiple features

**Audio/Script:**
"And here's what makes [Product] special: [unique capability].

This is something you can't get with [alternative solutions]. It means [powerful outcome]."

**Production notes:**
- Emphasize differentiation
- Show the "wow" moment
- Visual should be impressive

---

### Scene 5: Social Proof / Results (1:30-1:45)
**Duration:** 15 seconds
**Goal:** Build trust and show real outcomes

**Visual:**
- Customer logos
- Before/after metrics
- Testimonial quote on screen
- or happy customer using product

**Audio/Script:**
"[Customers like Companies X, Y, Z / Teams / Thousands of users] are already using [Product].

They're [achieving outcome - saving X hours, increasing Y by Z%, reducing errors by A%]."

**Optional testimonial quote:**
"'[Product] changed how we work. We're [specific improvement].' - [Name, Company]"

**Production notes:**
- Show recognizable logos if available
- Display metrics prominently
- Keep it brief but credible

---

### Scene 6: Call to Action (1:45-2:00)
**Duration:** 15 seconds
**Goal:** Drive immediate action

**Visual:**
- Product logo and website
- Clear CTA button/text
- QR code (if relevant for certain distribution)

**Audio/Script:**
"Ready to [achieve benefit they care about]?

Get started at [website URL]. Try [Product] free for [X days] - no credit card required.

That's [slow, clear pronunciation of URL]. See you inside!"

**Production notes:**
- CTA should be crystal clear
- URL displayed prominently entire time
- Consider end screen with clickable elements (for YouTube)
- Music fades out

---

## Alternative Formats

### 60-Second Version (Social Media)
Condense to essential: Hook (5s) → Problem (10s) → Solution (30s) → CTA (15s)

### Tutorial Format (3-5 min)
Structure: Intro (15s) → Prerequisites (30s) → Step 1 (60s) → Step 2 (60s) → Step 3 (60s) → Recap (30s) → CTA (15s)

### Explainer Format (90 sec)
Structure: Hook (5s) → Problem (20s) → How it works (40s) → Benefits (15s) → Proof (10s) → CTA (10s)

---

## Production Checklist

**Pre-Production:**
- [ ] Script finalized and approved
- [ ] Storyboard or shot list created
- [ ] Screen recordings captured
- [ ] B-roll footage gathered
- [ ] Graphics designed (lower thirds, text overlays)
- [ ] Voiceover recorded (or talent booked)
- [ ] Music selected and licensed

**Production:**
- [ ] All footage captured
- [ ] Quality check (resolution, lighting, audio)
- [ ] Backup copies made

**Post-Production:**
- [ ] Edit assembled per script
- [ ] Graphics and text overlays added
- [ ] Color correction applied
- [ ] Audio mixed (voiceover, music, SFX balanced)
- [ ] Captions/subtitles added
- [ ] Multiple format exports (YouTube, social, website)

**Distribution:**
- [ ] Thumbnail created
- [ ] Video title and description written
- [ ] Keywords/tags identified
- [ ] Upload to platforms
- [ ] Embed on website
- [ ] Promote across channels

---

## Video Specifications by Platform

**YouTube:**
- Resolution: 1920x1080 (1080p) or 3840x2160 (4K)
- Aspect ratio: 16:9
- Length: 2-5 min ideal for retention
- Thumbnail: 1280x720
- File format: MP4

**Social Media (LinkedIn, Twitter, Facebook):**
- Resolution: 1920x1080 or 1080x1080 (square)
- Aspect ratio: 16:9 or 1:1
- Length: 30-90 sec (shorter is better)
- Captions: REQUIRED (most watch muted)
- File format: MP4

**Instagram:**
- Resolution: 1080x1080 (square) or 1080x1920 (stories)
- Aspect ratio: 1:1 or 9:16
- Length: Feed (60 sec max), Stories/Reels (90 sec max)
- Captions: Recommended
- File format: MP4

**Website:**
- Resolution: 1920x1080
- Aspect ratio: 16:9
- Length: 60-120 sec (attention span shorter on websites)
- Autoplay (muted): Consider
- File format: MP4 (compressed for fast loading)

---

## Workflow: Outline to Final Script

**Create:** `projects/<project>/drafts/video-script-[name].md`

**Step 1: Define video goal and type**
- What's the primary goal? (awareness, education, conversion)
- What type? (demo, tutorial, explainer)
- Who's the audience?
- What action should they take after watching?

**Step 2: Research and gather assets**
- Find existing video examples for style reference
- Collect product screenshots/features to demo
- Gather customer proof (if using testimonials)
- Identify key messages to convey

**Step 3: Outline key scenes**
- Hook (first 5 seconds)
- Problem (establish pain)
- Solution (introduce product)
- Demo (show how it works)
- Results (prove value)
- CTA (what to do next)

**Step 4: Write detailed script**
- Draft visual and audio for each scene
- Time each section (aim for target length)
- Ensure natural, conversational language
- Add production notes for editors

**Step 5: Review and refine**
- Read script aloud (does it sound natural?)
- Time it (too long? cut fluff)
- Stakeholder review (product accuracy, messaging)
- Finalize before production

**Step 6: Production planning**
- Create shot list from script
- Record screen demos
- Book voiceover talent or record yourself
- Gather all assets (graphics, music, footage)

---

## Tips for Effective Video Scripts

**Hook viewers fast:**
- First 3-5 seconds are critical
- Start with question, bold claim, or relatable problem
- Don't waste time with long intros

**Show, don't just tell:**
- Demonstrate features in action
- Use real examples, not placeholders
- Show outcomes, not just features

**Keep it conversational:**
- Write how you speak, not how you write
- Read script aloud to catch awkward phrasing
- Use contractions, simple words

**Match visuals to audio:**
- What you show should match what you say
- Time captions to sync with visuals
- Don't show complex visual while explaining something else

**Include captions:**
- Most social videos watched muted
- Captions increase completion rate
- Make text legible and concise

**End with clear CTA:**
- One specific action
- Make it easy (free trial, visit website)
- Repeat URL or CTA verbally and visually

---

## Customizing This Template (One-Time Setup)

**Complete the [CUSTOMIZATION NEEDED] section by:**

1. **Watch 3-5 of your existing videos:**
```bash
# Find existing video content or scripts
kurt content search "video"
```

2. **Analyze their style:**
- What's the energy level? (high energy vs calm)
- What's the pacing? (fast cuts vs slow and clear)
- How conversational is the script?
- Do they use humor or stay serious?

3. **Extract DO/DON'T examples:**
- Copy script excerpts that exemplify your video style
- Note what makes them effective

4. **Update the [CUSTOMIZATION NEEDED] section** with:
- Tone preferences (casual, professional, enthusiastic)
- Pacing preferences (fast, moderate, clear)
- Script style (conversational, natural, scripted)
- DO/DON'T examples from actual video scripts

**This customization is done ONCE, then this template is reused for all future video scripts.**
