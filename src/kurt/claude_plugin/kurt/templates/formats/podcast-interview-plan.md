# Podcast Interview Plan Template

## Overview
- **Purpose:** Preparation document for podcast appearances
- **Length:** 1000-1500 words (internal prep doc)
- **Audience:** Internal (person being interviewed, comms team)
- **Success metrics:** Key messages delivered, brand mentions, listener engagement

---

## Style Guidelines

**Note:** This is an INTERNAL prep document, not published externally. Style customization is not required.

**However, note your company's podcast appearance preferences:**
- Energy level: [Conversational / Enthusiastic / Professional / Technical]
- Storytelling: [Personal anecdotes / Data-driven / Balanced]
- Product mentions: [Natural / Minimal / Strategic]
- Controversial topics: [Engage / Avoid / Company position only]

---

## Research Requirements

**Types of information needed for podcast prep:**

1. **Podcast research** - Know the show and host
   - Find: Podcast website, recent episodes
   - Research: `kurt research query "[podcast name] typical interview topics"`
   - Or provide: Podcast description, host bio, past guest list

2. **Host research** - Know who's interviewing you
   - Research: `kurt research search --source twitter --query "[host name]"`
   - Or provide: Host's background, their interests, their perspective

3. **Your key messages** - What to emphasize
   - Find: `kurt content search "positioning"`
   - Or provide: Messaging doc, company positioning, recent announcements

4. **Company stories** - Anecdotes to share
   - Find: `kurt content search "customer story"`
   - Or provide: Founding story, pivotal moments, customer wins

---

## Source Requirements

**Before creating interview plan, gather these sources (documented in frontmatter):**

**Podcast intel:**
```bash
# Research the podcast and host
kurt research query "[podcast name] interview style and topics"
kurt research search --source twitter --query "[host name] interests"
```

**Your messaging:**
```bash
# Find positioning and messaging docs
kurt content search "positioning"
kurt content search "messaging"

# Find customer stories
kurt content search "customer"
kurt content search "case study"
```

**If insufficient sources: Ask user for podcast details, host bio, or key messages to deliver**

---

## Structure

```markdown
---
project: project-name
document: podcast-interview-plan-[podcast-name]
format_template: /kurt/templates/formats/podcast-interview-plan.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/podcasts/[podcast-name]-research.md
    purpose: "podcast style and typical topics"
  - path: /sources/positioning-messaging.md
    purpose: "key messages to convey"
  - path: /sources/stories/company-story.md
    purpose: "anecdotes and stories to share"

outline:
  podcast-research:
    sources: [/sources/podcasts/[podcast-name]-research.md]
    purpose: "understand show format and audience"
  key-messages:
    sources: [/sources/positioning-messaging.md]
    purpose: "what to emphasize"
  topic-areas:
    sources: []
    purpose: "areas to cover"
  stories:
    sources: [/sources/stories/company-story.md]
    purpose: "anecdotes to share"
  questions:
    sources: []
    purpose: "anticipated questions and answers"
---

# Podcast Interview Plan: [PODCAST NAME]

**Guest:** [Name, Title]
**Podcast:** [Podcast Name]
**Host:** [Host Name]
**Recording Date:** YYYY-MM-DD
**Episode Theme:** [If known - topic or angle]
**Audience:** [Who listens - developers, founders, marketers, etc.]

---

## Podcast Research

### About the Show

**Podcast Name:** [Name]
**Host:** [Host name and brief bio]
**Format:** [Interview / Panel / Solo with guest / Conversational]
**Episode Length:** Typically [X] minutes
**Audience:** [Who listens - size, demographics, interests]

**Show Description:**
[What the podcast is about, its perspective, its mission]

**Typical Topics:**
- [Topic area 1 they often cover]
- [Topic area 2]
- [Topic area 3]

**Recent Notable Guests:**
- [Guest 1, Company/Role] - [Episode theme]
- [Guest 2, Company/Role] - [Episode theme]
- [Guest 3, Company/Role] - [Episode theme]

**Interview Style:**
- [Deep technical / High-level strategic / Storytelling / Debate]
- [Prepared questions / Free-flowing / Challenging / Supportive]
- [Formal / Casual / Conversational]

### About the Host

**Name:** [Host Name]
**Background:** [Their experience, company, role]

**Their Perspective/Interests:**
- [Known interest 1 - helps guide conversation]
- [Known interest 2]
- [Hot button topic they care about]

**Their Interviewing Style:**
[How they typically conduct interviews - probing, supportive, challenging, etc.]

**Relevant Context:**
[Anything about host that's relevant - investor in space, former founder, known skeptic of X, enthusiast for Y]

---

## Your Key Messages

**Primary Message (The One Thing):**
[If listeners remember only ONE thing, it should be this]

**Example:** "[Company] is changing how [audience] approaches [problem] by [unique approach]."

**Supporting Messages (Top 3-5):**

1. **Message 1:** [Key point about product/company/vision]
   - Supporting evidence: [Metric, customer story, or proof point]
   - Natural way to bring it up: [Topic that leads to this]

2. **Message 2:** [Key point]
   - Supporting evidence: [Proof]
   - Natural way to bring it up: [Topic]

3. **Message 3:** [Key point]
   - Supporting evidence: [Proof]
   - Natural way to bring it up: [Topic]

**What NOT to say:**
- ❌ [Topic or claim to avoid - e.g., unannounced features, competitive trash talk]
- ❌ [Sensitive topic - e.g., specific customer names without permission]
- ❌ [Overused buzzwords or jargon that sounds inauthentic]

---

## Topic Areas to Cover

### Topic 1: [Area - e.g., "Company Origin Story"]

**Why it matters:** [Why this topic resonates with audience]

**Key points to hit:**
- [Point 1 - e.g., "What problem inspired us to start"]
- [Point 2 - e.g., "The 'aha' moment"]
- [Point 3 - e.g., "How we validated the idea"]

**Story to tell:**
[Brief anecdote that illustrates this - 2-3 sentences]

**Tie to message:**
[How this connects to your key messages]

---

### Topic 2: [Area - e.g., "Industry Trends"]

**Why it matters:** [Relevance to audience]

**Key points to hit:**
- [Point 1 - your unique perspective]
- [Point 2 - contrarian take if applicable]
- [Point 3 - where the industry is heading]

**Story to tell:**
[Example or case study that illustrates your point]

**Tie to message:**
[How this reinforces positioning]

---

### Topic 3: [Area - e.g., "Product/Solution Deep Dive"]

**Why it matters:** [Why audience cares]

**Key points to hit:**
- [How it works differently than alternatives]
- [The insight that led to this approach]
- [Results customers are seeing]

**Story to tell:**
[Customer success story - specific, concrete, relatable]

**Tie to message:**
[Connection to key messages]

---

## Stories & Anecdotes

**Have 3-5 compelling stories ready to deploy when relevant:**

### Story 1: [Company Founding / Origin]

**Setup:** [Brief context - when, where, circumstances]

**Story:**
[2-3 paragraphs telling the story - make it vivid, specific, relatable]

**Lesson/Takeaway:**
[What this illustrates - resilience, customer obsession, innovation, etc.]

**When to use:**
- Question about how you got started
- Talking about problem/solution fit
- Discussing persistence or learning

---

### Story 2: [Customer Win / Impact]

**Setup:** [Who the customer is - without naming if not permitted]

**Story:**
[The problem they had, how your product helped, the outcome]

**Lesson/Takeaway:**
[What this proves about your approach]

**When to use:**
- Question about impact or results
- Discussing who you serve
- Proving product-market fit

---

### Story 3: [Pivotal Moment / Learning]

**Setup:** [Context]

**Story:**
[What happened, what you learned, how it changed things]

**Lesson/Takeaway:**
[Insight or wisdom gained]

**When to use:**
- Question about challenges or failures
- Discussing evolution of strategy
- Advice for others in similar situation

---

## Anticipated Questions & Answers

**Prepare answers for likely questions:**

### Q: "Tell me about [Company]. What do you do?"

**Answer (30 sec version):**
"[Company] is [what you do] for [target audience]. We help [audience] [achieve outcome] by [unique approach].

What makes us different is [key differentiator]. We've worked with [companies/customers like X] to [result achieved].

I started [Company] because [brief origin story - 1-2 sentences]."

**Key messages to weave in:**
- [Message 1]
- [Differentiation point]

---

### Q: "How did you come up with this idea?"

**Answer:**
[Tell origin story - make it personal, specific, and interesting]

**Story to tell:** [Reference Story 1 above]

**Key messages:**
- Deep understanding of customer pain
- [Other relevant message]

---

### Q: "Who are your customers? Who's this for?"

**Answer:**
"We primarily work with [target audience - be specific]. These are [description of who they are].

They typically come to us when [trigger event or pain point]. For example, [brief customer story or example].

[Optional: Who it's NOT for if relevant]"

**Key messages:**
- Clear ICP definition
- Customer understanding

---

### Q: "What's the biggest challenge you're facing?"

**Answer:**
"Right now, our biggest challenge is [honest, strategic challenge].

[Brief explanation of challenge and why it matters]

We're approaching it by [how you're tackling it]. [Optional: What we've learned so far]."

**Note:** Be honest but strategic - don't reveal vulnerabilities competitors could exploit

---

### Q: "Where do you see [industry/company] in 5 years?"

**Answer:**
"I think [industry] is heading toward [trend or shift].

We're seeing [evidence of this trend]. What that means for [audience] is [implication].

At [Company], we're positioning for this by [strategic direction]. Our vision is [aspirational but grounded future state]."

**Key messages:**
- Thought leadership on industry
- Strategic positioning

---

### Q: "What advice would you give to [entrepreneurs/people in the space]?"

**Answer:**
"The most important thing I've learned is [key lesson].

[Brief story or example that illustrates this lesson]

My advice: [Specific, actionable advice]. [Optional: What I wish I'd known earlier]."

**Key messages:**
- Authenticity and generosity
- Share real wisdom, not platitudes

---

## Questions to Ask the Host

**Come prepared with 1-2 thoughtful questions for the host:**

**Question 1:**
"[Thoughtful question based on their work/perspective]"

**Why:** Shows you've done research, makes it conversational, not just promotional

**Question 2:**
"What do you think about [trend/topic related to the episode]?"

**Why:** Engages the host, could lead to interesting discussion

---

## Do's and Don'ts

### DO:

✅ **Be conversational and authentic**
- Speak naturally, not like you're reading talking points
- It's okay to pause and think
- Show personality and enthusiasm

✅ **Tell specific stories**
- Use real examples, names (if permitted), numbers
- Make abstract ideas concrete with stories
- Stories are more memorable than facts

✅ **Engage with the host**
- Listen actively, respond to what they're saying
- Build on their points
- Ask follow-up questions

✅ **Bridge to your messages**
- When asked anything, bridge to key points
- "That's a great question. What I've found is [key message]..."

✅ **Provide value to listeners**
- Share real insights, not just promotion
- Give actionable advice
- Be generous with knowledge

✅ **Mention the company naturally**
- Weave in product mentions organically
- Connect to broader points
- Use customer stories as examples

### DON'T:

❌ **Don't be overly promotional**
- This isn't a sales pitch
- Listeners will tune out if it's just an ad
- Let your insights sell the company

❌ **Don't use jargon or buzzwords**
- Speak plainly
- If you must use technical terms, explain them
- Avoid marketing speak

❌ **Don't bad-mouth competitors**
- Be classy and focused on your approach
- Acknowledge others' strengths when fair
- Differentiate without denigrating

❌ **Don't reveal confidential information**
- Unannounced products/features
- Specific customer details without permission
- Sensitive metrics or financials

❌ **Don't ramble**
- Keep answers focused and concise
- 1-2 minutes max per answer typically
- Let the host guide the conversation

❌ **Don't be defensive**
- If challenged, stay open and thoughtful
- Acknowledge valid criticisms
- Use disagreement as opportunity for nuance

---

## Technical Prep

**Before recording:**

**Audio Setup:**
- [ ] Test microphone (use good quality mic, not laptop)
- [ ] Quiet environment (no background noise)
- [ ] Headphones (prevent echo/feedback)
- [ ] Stable internet connection (for remote recordings)

**Logistics:**
- [ ] Confirm recording time/timezone
- [ ] Get Zoom/Riverside/call link in advance
- [ ] Join 5 min early to test setup
- [ ] Have water nearby (for dry mouth)

**Materials:**
- [ ] This interview plan reviewed
- [ ] Key messages memorized (not reading)
- [ ] Stories fresh in mind
- [ ] Notes accessible but not distracting

---

## Post-Interview Actions

**After recording:**

- [ ] Thank the host (email follow-up)
- [ ] Share any promised resources or links
- [ ] Add podcast appearance to company media page
- [ ] Prepare social promotion for when episode drops
- [ ] Notify team when episode is live
- [ ] Share episode with customers/prospects
- [ ] Capture learnings for next podcast prep

**Social promotion when live:**
- LinkedIn post sharing episode
- Twitter thread with key highlights
- Email to relevant contacts
- Internal company announcement

---

## Success Metrics

**How to measure this appearance:**

**Immediate:**
- Episode published and promoted
- Key messages successfully delivered
- Company mentioned and linked in show notes

**Short-term (2-4 weeks):**
- Download/listen numbers (if shared by podcast)
- Social engagement (shares, comments)
- Website traffic spike from referral
- Leads mentioning podcast

**Long-term:**
- Ongoing discovery from evergreen episode
- Relationship built with host/audience
- Credibility in the space enhanced
- Follow-on podcast invitations

---

## Customizing This Template

**For each podcast appearance:**

1. **Research the show:** Listen to 2-3 recent episodes
2. **Research the host:** Understand their perspective and interests
3. **Tailor your stories:** Choose anecdotes relevant to their audience
4. **Prepare your messages:** What do you want listeners to remember
5. **Anticipate questions:** Based on show style and your background
6. **Practice:** Don't memorize, but rehearse key stories and points

**Goal: Sound prepared but conversational, strategic but authentic.**
