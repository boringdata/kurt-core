# Technically Newsroom: Automated Content Pipeline
## Vision Document & Technical Specification

---

## Executive Summary

This document describes an automated newsroom system for Technically, built as an extension to [kurt-core](https://github.com/boringdata/kurt-core). The system handles the full content lifecycle:

**Topic Discovery → Brief Creation → Writer Assignment → Visual/Video Production → Publishing → Distribution → Analytics**

The architecture prioritizes:
- **Deterministic steps** where possible (API calls, transforms) to reduce token consumption
- **LLM batch steps** for classification/scoring (parallel, tracked, cost-efficient)
- **Agentic execution** only when complex reasoning/tool use is required
- **Human-in-the-loop** at key decision points (topic approval, editorial review, correspondent recording)

Built on kurt-core's DBOS workflow foundation, with custom workflows, models, and integrations defined in user-space.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Macro Workflows](#macro-workflows)
3. [Micro Workflows (Step Details)](#micro-workflows)
4. [Database Models](#database-models)
5. [Integration Requirements](#integration-requirements)
6. [CLI Commands](#cli-commands)
7. [Technical Architecture](#technical-architecture)
8. [Implementation Phases](#implementation-phases)

---

## System Overview

### Why Kurt-Core?

Kurt-core provides:
- **DBOS workflows** — Durable, observable, recoverable execution
- **LLMStep** — Batch LLM calls with concurrency, tracking, cost metrics
- **Agent execution** — Claude CLI subprocess with guardrails
- **TracingHooks** — Token/cost tracking to database
- **Existing integrations** — Reddit, HN, RSS signals as starting points

We extend kurt with custom workflows, models, and integrations for newsroom operations.

### Workflow Types

| Type | When to Use | Token Cost |
|------|-------------|------------|
| `@DBOS.step()` | Deterministic Python (API calls, transforms) | Zero |
| `LLMStep` | Batch classification/scoring | ~$0.01-0.05 per item |
| `agent_execution_step` | Complex reasoning, tool use, research | ~$0.10-1.00 per run |

### Human-in-the-Loop Gates

| Gate | Decision Maker | Mechanism |
|------|----------------|-----------|
| Topic approval | Editor | Slack interactive buttons |
| Brief approval | Editor | Asana task status |
| Visual approval | Designer (optional) | Review queue |
| Publish approval | Editor | CMS workflow |
| Correspondent recording | Correspondent | Manual (calendar scheduled) |

---

## Macro Workflows

### Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MACRO WORKFLOW MAP                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  M1: TOPIC PIPELINE              M2: BRIEF & ASSIGNMENT      M3: PRODUCTION    │
│  ┌───────────────────┐           ┌───────────────────┐       ┌──────────────┐  │
│  │ Sources → Scored  │           │ Topic → Writer    │       │ Brief → Assets│  │
│  │ Topics → Approved │           │ Assignment        │       │ (Visual+Video)│  │
│  │                   │           │                   │       │              │  │
│  │ Scheduled: 15 min │           │ Triggered: Manual │       │ Triggered:   │  │
│  │ + Daily digest    │           │ or on approval    │       │ On approval  │  │
│  └───────────────────┘           └───────────────────┘       └──────────────┘  │
│                                                                                 │
│  M4: PUBLISHING                  M5: DISTRIBUTION            M6: ANALYTICS     │
│  ┌───────────────────┐           ┌───────────────────┐       ┌──────────────┐  │
│  │ Draft → CMS →     │           │ Published →       │       │ Performance  │  │
│  │ Scheduled Publish │           │ Social + Newsletter│      │ → Feedback   │  │
│  │                   │           │                   │       │ → Tuning     │  │
│  │ Triggered: On     │           │ Triggered: On     │       │              │  │
│  │ editor approval   │           │ publish           │       │ Weekly cycle │  │
│  └───────────────────┘           └───────────────────┘       └──────────────┘  │
│                                                                                 │
│  M7: CORRESPONDENT RECRUITING                                                   │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │ Topic/Beat → Find Experts on Social → Score/Rank → Outreach Pipeline      │ │
│  │                                                                           │ │
│  │ Triggered: On demand or when new beat identified                          │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### M1: Topic Pipeline

**Purpose:** Continuously discover, score, and surface story-worthy topics.

**Schedule:**
- Ingestion: Every 15 minutes
- Digest: Daily at 9am

**Pipeline:**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           M1: TOPIC PIPELINE                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  FETCH (Parallel, Pure Python)                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │   RSS    │ │  Reddit  │ │    HN    │ │ Twitter  │ │  GitHub  │             │
│  │  Feeds   │ │Subreddits│ │  Front   │ │  Lists   │ │ Trending │             │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘             │
│       │            │            │            │            │                    │
│       └────────────┴────────────┴────────────┴────────────┘                    │
│                                 │                                               │
│                                 ▼                                               │
│  DEDUPE (Pure Python)    ┌─────────────┐                                       │
│                          │   Dedupe    │                                       │
│                          │  vs. Known  │                                       │
│                          └──────┬──────┘                                       │
│                                 │                                               │
│                                 ▼                                               │
│  SCORE (LLMStep - Batch) ┌─────────────┐                                       │
│                          │   Score:    │                                       │
│                          │ • Relevance │  ~$0.01/topic                         │
│                          │ • Timeliness│                                       │
│                          │ • Uniqueness│                                       │
│                          │ • Audience  │                                       │
│                          └──────┬──────┘                                       │
│                                 │                                               │
│                                 ▼                                               │
│  PERSIST (Transaction)   ┌─────────────┐                                       │
│                          │   Save to   │                                       │
│                          │  Database   │                                       │
│                          └──────┬──────┘                                       │
│                                 │                                               │
│                    ┌────────────┴────────────┐                                 │
│                    ▼                         ▼                                 │
│  NOTIFY      ┌──────────┐             ┌──────────┐                            │
│              │  Daily   │             │  Alert   │                            │
│              │  Digest  │             │ (Score   │                            │
│              │  (9am)   │             │  > 85)   │                            │
│              └──────────┘             └──────────┘                            │
│                                                                                 │
│  Output: Slack with [Approve] [Reject] [Assign] buttons                        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Scoring Dimensions (0-100 each):**

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Relevance | 30% | How relevant to Technically's beat? |
| Timeliness | 25% | Breaking news (high) vs. evergreen (lower) |
| Uniqueness | 20% | Already covered elsewhere? |
| Audience Fit | 15% | Would our startup/developer audience care? |
| Competition | 10% | Can we add unique value vs competitors? |

---

### M2: Brief & Assignment

**Purpose:** Generate research brief, create writing assignment, notify writer.

**Trigger:** Editor approves topic (Slack button) or auto-approval (score > 90)

**Pipeline:**

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        M2: BRIEF & ASSIGNMENT                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  INPUT                   ┌─────────────┐                                       │
│                          │  Approved   │                                       │
│                          │   Topic     │                                       │
│                          └──────┬──────┘                                       │
│                                 │                                               │
│                                 ▼                                               │
│  RESEARCH (Agent Step)   ┌─────────────────────────────────────────────┐       │
│                          │  Deep Research Agent                        │       │
│                          │  • Find primary sources                     │       │
│                          │  • Gather expert perspectives               │       │
│                          │  • Collect data/statistics                  │       │
│                          │  • Identify interview contacts              │       │
│                          │                                             │       │
│                          │  Tools: WebSearch, WebFetch, Read, Write    │       │
│                          │  Output: research-{topic}.md                │       │
│                          └──────────────┬──────────────────────────────┘       │
│                                         │                                       │
│                                         ▼                                       │
│  COMPETITOR SCAN         ┌─────────────────────────────────────────────┐       │
│  (Pure Python)           │  Search: TechCrunch, Verge, Ars, Wired     │       │
│                          │  Extract: angles, coverage gaps             │       │
│                          └──────────────┬──────────────────────────────┘       │
│                                         │                                       │
│                                         ▼                                       │
│  GENERATE BRIEF          ┌─────────────────────────────────────────────┐       │
│  (LLMStep)               │  Create structured brief:                   │       │
│                          │  • 3 headline options                       │       │
│                          │  • Story angle/hook                         │       │
│                          │  • Key facts (with sources)                 │       │
│                          │  • SEO keywords                             │       │
│                          │  • Visual suggestions                       │       │
│                          │  • Suggested word count                     │       │
│                          └──────────────┬──────────────────────────────┘       │
│                                         │                                       │
│                    ┌────────────────────┼────────────────────┐                 │
│                    ▼                    ▼                    ▼                 │
│              ┌──────────┐        ┌──────────┐        ┌──────────┐             │
│              │  Create  │        │  Create  │        │  Notify  │             │
│              │  Google  │        │  Asana   │        │  Writer  │             │
│              │   Doc    │        │   Task   │        │  (Slack) │             │
│              └──────────┘        └──────────┘        └──────────┘             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Brief Structure:**

```markdown
# Brief: {Title}

## Story Angle
{One paragraph on the unique angle}

## Headline Options
1. {Option 1}
2. {Option 2}
3. {Option 3}

## Key Facts
- {Fact 1} (Source: {url})
- {Fact 2} (Source: {url})
...

## Sources
### Primary
- {url}: {why it matters}
### Secondary
- {url}: {context}

## Competitor Coverage
| Publication | Angle | Gap for Us |
|-------------|-------|------------|
| ...         | ...   | ...        |

## Interview Contacts
- {Name}, {Title} at {Company} - {Twitter/LinkedIn}

## SEO
- Target keywords: {kw1}, {kw2}, {kw3}
- Suggested word count: {n}

## Visual Needs
- [ ] Featured image: {concept}
- [ ] Diagram: {concept}
- [ ] Video: {yes/no}
```

---

### M3: Production (Visual & Video)

**Purpose:** Generate all visual assets and prepare video pre-production.

#### M3a: Visual Asset Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        M3a: VISUAL ASSET PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  FEATURED IMAGE                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐                 │
│  │ Generate │───▶│  DALL-E  │───▶│  Apply   │───▶│  Upload  │                 │
│  │  Prompt  │    │ Generate │    │  Brand   │    │Cloudinary│                 │
│  │ (LLMStep)│    │  (API)   │    │ Template │    │          │                 │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘                 │
│                                                                                 │
│  TECHNICAL DIAGRAMS (Technically's Signature Style)                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐ │
│  │ Generate │───▶│  Render  │───▶│   Nano   │───▶│   Add    │───▶│ Upload  │ │
│  │ Mermaid  │    │ Mermaid  │    │ Banana 3 │    │ Branding │    │Cloudinary│ │
│  │ (LLMStep)│    │  (CLI)   │    │  Style   │    │          │    │         │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └─────────┘ │
│                                                                                 │
│  DATA VISUALIZATIONS                                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                                 │
│  │ Extract  │───▶│ Generate │───▶│  Upload  │                                 │
│  │   Data   │    │  Chart   │    │Cloudinary│                                 │
│  │          │    │(Flourish)│    │          │                                 │
│  └──────────┘    └──────────┘    └──────────┘                                 │
│                                                                                 │
│  SOCIAL CARDS                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                                 │
│  │ Generate │───▶│  Apply   │───▶│  Upload  │                                 │
│  │   Copy   │    │ Template │    │Cloudinary│                                 │
│  │ (LLMStep)│    │ (Canva)  │    │          │                                 │
│  └──────────┘    └──────────┘    └──────────┘                                 │
│                                                                                 │
│  OUTPUT: All variants in DAM                                                   │
│  └── story-slug/                                                               │
│      ├── featured-1200x630.png (OG/social)                                    │
│      ├── hero-1920x1080.png                                                   │
│      ├── thumb-400x300.png                                                    │
│      ├── diagrams/                                                            │
│      └── social/                                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### M3b: Video Pre-Production

**Important:** Correspondents record their own video (home studio or iPhone). This workflow prepares everything they need.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        M3b: VIDEO PRE-PRODUCTION                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  SCRIPT GENERATION                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  Input: Article content                                              │     │
│  │  Output: 90-second video script                                      │     │
│  │                                                                      │     │
│  │  Structure:                                                          │     │
│  │  • Hook (5 sec)                                                      │     │
│  │  • Context (15 sec)                                                  │     │
│  │  • Key Point 1 (20 sec)                                              │     │
│  │  • Key Point 2 (20 sec)                                              │     │
│  │  • Key Point 3 (20 sec)                                              │     │
│  │  • CTA (10 sec)                                                      │     │
│  │                                                                      │     │
│  │  Tone: Conversational but authoritative                              │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                     │                                          │
│                                     ▼                                          │
│  SHOT LIST GENERATION                                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  Break script into shots:                                            │     │
│  │                                                                      │     │
│  │  | # | Type      | Duration | Content           | Visual          | │     │
│  │  |---|-----------|----------|-------------------|-----------------|  │     │
│  │  | 1 | Talking   | 5s       | Hook              | Correspondent   |  │     │
│  │  | 2 | B-roll    | 10s      | Context           | Diagram 1       |  │     │
│  │  | 3 | Talking   | 15s      | Point 1           | Correspondent   |  │     │
│  │  | 4 | B-roll    | 5s       | Point 1 visual    | Diagram 2       |  │     │
│  │  | ...                                                              | │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                     │                                          │
│                                     ▼                                          │
│  DIAGRAM GENERATION                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  For each shot requiring diagram:                                    │     │
│  │  → Call M3a diagram pipeline                                         │     │
│  │  → Output: Styled diagrams ready for video                          │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                     │                                          │
│                                     ▼                                          │
│  SCHEDULING                                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  • Check correspondent availability                                  │     │
│  │  • Create calendar event with:                                       │     │
│  │    - Script link                                                     │     │
│  │    - Shot list link                                                  │     │
│  │    - Diagram assets                                                  │     │
│  │    - Recording instructions                                          │     │
│  │  • Send Slack notification                                           │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
│  POST-PRODUCTION (After correspondent uploads footage)                         │
│  ┌──────────────────────────────────────────────────────────────────────┐     │
│  │  • Ingest footage to Descript                                        │     │
│  │  • Auto-transcription                                                │     │
│  │  • Editor assembles rough cut                                        │     │
│  │  • Export → YouTube → Embed in article                               │     │
│  └──────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### M4: Publishing

**Purpose:** Transform approved content into CMS draft, schedule publication.

**Trigger:** Editor marks brief as "ready to publish"

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           M4: PUBLISHING                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────┐                                                              │
│  │ Google Doc   │  (Writer's finished article)                                 │
│  │ (Approved)   │                                                              │
│  └──────┬───────┘                                                              │
│         │                                                                       │
│         ▼                                                                       │
│  ┌──────────────┐                                                              │
│  │  Transform   │  • Fetch via Google Docs API                                 │
│  │ to Markdown  │  • Clean formatting                                          │
│  │              │  • Extract metadata                                          │
│  └──────┬───────┘                                                              │
│         │                                                                       │
│         ▼                                                                       │
│  ┌──────────────┐                                                              │
│  │   Generate   │  • Meta title (optimized for CTR)                            │
│  │     SEO      │  • Meta description                                          │
│  │   Metadata   │  • Schema markup (Article, Author, etc.)                     │
│  │  (LLMStep)   │                                                              │
│  └──────┬───────┘                                                              │
│         │                                                                       │
│         ▼                                                                       │
│  ┌──────────────┐                                                              │
│  │   Attach     │  • Featured image from DAM                                   │
│  │   Assets     │  • Diagrams                                                  │
│  │              │  • Video embed (if applicable)                               │
│  └──────┬───────┘                                                              │
│         │                                                                       │
│         ▼                                                                       │
│  ┌──────────────┐                                                              │
│  │  Create CMS  │  • Push to Sanity via API                                    │
│  │    Draft     │  • Generate preview URL                                      │
│  │              │  • Set scheduled publish time                                │
│  └──────┬───────┘                                                              │
│         │                                                                       │
│         ▼                                                                       │
│  ┌──────────────┐                                                              │
│  │   Notify     │  • Slack to editor with preview link                         │
│  │   Editor     │  • "Review and publish" prompt                               │
│  └──────────────┘                                                              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### M5: Distribution

**Purpose:** Amplify published content across channels.

**Trigger:** Article published (CMS webhook)

**Timing:**
- T+0: Website, Twitter thread, LinkedIn
- T+2h: Community posts (Discord, Reddit if appropriate)
- T+24h: Newsletter digest inclusion
- T+24h: Twitter reminder

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           M5: DISTRIBUTION                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  IMMEDIATE (T+0)                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                         │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │  │
│  │  │   Generate   │    │   Generate   │    │     Post     │              │  │
│  │  │   Twitter    │    │   LinkedIn   │    │   Threads    │              │  │
│  │  │   Thread     │    │     Post     │    │ (Parallel)   │              │  │
│  │  │  (LLMStep)   │    │  (LLMStep)   │    │              │              │  │
│  │  └──────────────┘    └──────────────┘    └──────────────┘              │  │
│  │                                                                         │  │
│  │  Twitter Thread Format:                                                 │  │
│  │  1. Hook + link                                                        │  │
│  │  2. Key insight 1                                                      │  │
│  │  3. Key insight 2                                                      │  │
│  │  4. Key insight 3                                                      │  │
│  │  5. CTA + link                                                         │  │
│  │                                                                         │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  SAME DAY (T+2h)                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  • Post to Discord community                                           │  │
│  │  • Post to relevant Slack communities (if applicable)                  │  │
│  │  • Submit to HN/Reddit (manual review queue)                           │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  NEXT DAY (T+24h)                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  • Add to newsletter digest queue                                      │  │
│  │  • Post Twitter reminder: "In case you missed it..."                   │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

### M6: Analytics & Feedback Loop

**Purpose:** Track performance, identify patterns, tune scoring.

**Schedule:** Weekly (Monday morning)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      M6: ANALYTICS & FEEDBACK LOOP                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  DATA COLLECTION (Continuous)                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │  │
│  │  │   GA4   │ │ Search  │ │ Twitter │ │LinkedIn │ │Newsletter│          │  │
│  │  │         │ │ Console │ │   API   │ │   API   │ │   API   │          │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘          │  │
│  │       └───────────┴───────────┴───────────┴───────────┘                │  │
│  │                              │                                          │  │
│  │                              ▼                                          │  │
│  │                    ┌─────────────────┐                                  │  │
│  │                    │ Article Metrics │                                  │  │
│  │                    │     Table       │                                  │  │
│  │                    └─────────────────┘                                  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  WEEKLY ANALYSIS                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                                                                         │  │
│  │  Performance Report:                                                    │  │
│  │  ┌───────────────────────────────────────────────────────────────────┐ │  │
│  │  │ TOP PERFORMERS                                                    │ │  │
│  │  │ • Which topics drove most traffic?                               │ │  │
│  │  │ • Which formats had best engagement?                             │ │  │
│  │  │ • Which distribution channels performed?                         │ │  │
│  │  │ • Which correspondents' videos performed best?                   │ │  │
│  │  │                                                                   │ │  │
│  │  │ UNDERPERFORMERS                                                   │ │  │
│  │  │ • Topics with high score but low actual traffic                  │ │  │
│  │  │ • High bounce rate articles                                      │ │  │
│  │  │ • Low video completion rates                                     │ │  │
│  │  │                                                                   │ │  │
│  │  │ SEO OPPORTUNITIES                                                 │ │  │
│  │  │ • Keywords ranking 5-15 (optimize potential)                     │ │  │
│  │  │ • New ranking keywords to double down on                         │ │  │
│  │  └───────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                         │  │
│  │                              │                                          │  │
│  │                              ▼                                          │  │
│  │                                                                         │  │
│  │  Feedback Actions:                                                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │   Update     │  │   Adjust     │  │   Notify     │                 │  │
│  │  │   Scoring    │  │   Content    │  │    Team      │                 │  │
│  │  │   Weights    │  │   Strategy   │  │   (Slack)    │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  │                                                                         │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Metrics Tracked Per Article:**

| Category | Metrics |
|----------|---------|
| Traffic | Pageviews, unique visitors, avg time on page, bounce rate |
| SEO | Organic traffic, keyword rankings, backlinks |
| Social | Impressions, engagements, shares, clicks |
| Video | Views, completion rate, avg watch time |
| Newsletter | Open rate, click rate |
| Business | Newsletter signups, lead captures |

---

### M7: Correspondent Recruiting

**Purpose:** Find subject matter experts for stories and potential correspondents.

**Trigger:** On demand, or when new beat identified

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      M7: CORRESPONDENT RECRUITING                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  INPUT                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  • Topic or beat to find experts for                                   │  │
│  │  • Expertise criteria (technical depth, communication skills, etc.)    │  │
│  │  • Geography preferences (optional)                                    │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                          │
│                                     ▼                                          │
│  DISCOVERY (Parallel, via Apify actors)                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │ Twitter  │  │ LinkedIn │  │  GitHub  │  │ Podcast  │               │  │
│  │  │  Search  │  │  Search  │  │ Contrib. │  │  Guests  │               │  │
│  │  │          │  │          │  │  Search  │  │          │               │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘               │  │
│  │       └─────────────┴─────────────┴─────────────┘                      │  │
│  │                           │                                             │  │
│  │                           ▼                                             │  │
│  │                  ┌─────────────────┐                                   │  │
│  │                  │  Raw Candidate  │                                   │  │
│  │                  │      List       │                                   │  │
│  │                  └─────────────────┘                                   │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                          │
│                                     ▼                                          │
│  ENRICHMENT (Pure Python)                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  For each candidate:                                                   │  │
│  │  • Follower count, engagement rate                                     │  │
│  │  • Recent content themes                                               │  │
│  │  • Bio/headline keywords                                               │  │
│  │  • Cross-platform presence                                             │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                          │
│                                     ▼                                          │
│  SCORING (LLMStep)                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  Score each candidate on:                                              │  │
│  │  • Relevance to topic/beat                                             │  │
│  │  • Authority (credentials, following, engagement)                      │  │
│  │  • Accessibility (active on socials, responds to DMs)                  │  │
│  │  • Content quality (writing samples, video presence)                   │  │
│  │  • Fit with Technically's voice                                        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                     │                                          │
│                                     ▼                                          │
│  OUTREACH PREP (LLMStep)                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  Generate personalized outreach for top candidates:                    │  │
│  │  • Reference their specific work                                       │  │
│  │  • Explain the opportunity                                             │  │
│  │  • Clear CTA                                                           │  │
│  │                                                                         │  │
│  │  Output: Draft messages for human review before sending                │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
│  OUTPUT                                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  • Ranked candidate list in `technically_experts` table                │  │
│  │  • Draft outreach messages (queued for manual send)                    │  │
│  │  • Slack notification with top 10 candidates                           │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Micro Workflows

### Step Type Reference

| Type | Decorator | Use Case | Cost |
|------|-----------|----------|------|
| Pure Python | `@DBOS.step()` | API calls, transforms, I/O | Free |
| LLM Batch | `LLMStep` | Classification, scoring, generation | ~$0.01-0.05/item |
| Transaction | `@DBOS.transaction()` | Database writes | Free |
| Agent | `agent_execution_step()` | Complex reasoning, tool use | ~$0.10-1.00/run |

### Complete Step Catalog

#### Topic Pipeline (M1)

| ID | Step Name | Type | Input | Output |
|----|-----------|------|-------|--------|
| T1 | `fetch_rss_step` | DBOS.step | RSS feed URLs | Raw topics |
| T2 | `fetch_reddit_step` | DBOS.step | Subreddit list | Raw topics |
| T3 | `fetch_hackernews_step` | DBOS.step | Config (timeframe, limit) | Raw topics |
| T4 | `fetch_twitter_step` | DBOS.step | Lists, hashtags, accounts | Raw topics |
| T5 | `fetch_github_trending_step` | DBOS.step | Language, timeframe | Raw topics |
| T6 | `dedupe_topics_step` | DBOS.step | Raw topics | New topics only |
| T7 | `score_topics_step` | LLMStep | Topics | Scored topics |
| T8 | `persist_topics` | DBOS.transaction | Scored topics | DB records |
| T9 | `post_slack_digest_step` | DBOS.step | Top topics | Slack message ID |
| T10 | `post_slack_alert_step` | DBOS.step | High-score topic | Slack message ID |

#### Brief & Assignment (M2)

| ID | Step Name | Type | Input | Output |
|----|-----------|------|-------|--------|
| B1 | `fetch_topic_step` | DBOS.step | Topic ID | Topic details |
| B2 | `research_topic_step` | Agent | Topic | Research doc |
| B3 | `find_competitors_step` | DBOS.step | Topic | Competitor coverage |
| B4 | `generate_brief_step` | LLMStep | Topic + research | Brief content |
| B5 | `create_google_doc_step` | DBOS.step | Brief | Doc URL |
| B6 | `create_asana_task_step` | DBOS.step | Brief + Doc URL | Task ID |
| B7 | `persist_brief` | DBOS.transaction | Brief data | DB record |
| B8 | `notify_writer_step` | DBOS.step | Brief + Writer | Slack DM ID |

#### Visual Production (M3a)

| ID | Step Name | Type | Input | Output |
|----|-----------|------|-------|--------|
| V1 | `analyze_visual_needs_step` | LLMStep | Brief | Asset requirements |
| V2 | `generate_image_prompt_step` | LLMStep | Brief/article | DALL-E prompt |
| V3 | `generate_image_step` | DBOS.step | Prompt | Raw image path |
| V4 | `apply_brand_template_step` | DBOS.step | Image | Branded image |
| V5 | `generate_mermaid_step` | LLMStep | Concept | Mermaid code |
| V6 | `render_mermaid_step` | DBOS.step | Mermaid code | Base PNG |
| V7 | `style_transfer_step` | DBOS.step | Base PNG + style | Styled PNG |
| V8 | `upload_cloudinary_step` | DBOS.step | Image + config | Cloudinary URLs |
| V9 | `persist_visual_asset` | DBOS.transaction | Asset data | DB record |

#### Video Production (M3b)

| ID | Step Name | Type | Input | Output |
|----|-----------|------|-------|--------|
| VD1 | `generate_script_step` | LLMStep | Article | Video script |
| VD2 | `generate_shot_list_step` | LLMStep | Script | Shot list |
| VD3 | `identify_diagram_needs_step` | DBOS.step | Shot list | Diagram concepts |
| VD4 | `schedule_recording_step` | DBOS.step | Correspondent + time | Calendar event |
| VD5 | `notify_correspondent_step` | DBOS.step | Video project | Slack/email |
| VD6 | `persist_video_project` | DBOS.transaction | Project data | DB record |
| VD7 | `ingest_footage_step` | DBOS.step | Footage URL | Descript project |
| VD8 | `upload_youtube_step` | DBOS.step | Final video | YouTube ID |

#### Publishing (M4)

| ID | Step Name | Type | Input | Output |
|----|-----------|------|-------|--------|
| P1 | `fetch_google_doc_step` | DBOS.step | Doc URL | Raw content |
| P2 | `transform_to_markdown_step` | DBOS.step | Raw content | Clean markdown |
| P3 | `generate_seo_metadata_step` | LLMStep | Article | Meta title, desc, schema |
| P4 | `attach_assets_step` | DBOS.step | Brief ID | Asset URLs |
| P5 | `create_cms_draft_step` | DBOS.step | Content + assets | CMS ID + preview URL |
| P6 | `schedule_publish_step` | DBOS.step | CMS ID + time | Scheduled |
| P7 | `persist_article` | DBOS.transaction | Article data | DB record |
| P8 | `notify_editor_step` | DBOS.step | Article + preview | Slack message |

#### Distribution (M5)

| ID | Step Name | Type | Input | Output |
|----|-----------|------|-------|--------|
| D1 | `generate_twitter_thread_step` | LLMStep | Article | Thread tweets |
| D2 | `generate_linkedin_post_step` | LLMStep | Article | Post content |
| D3 | `generate_newsletter_entry_step` | LLMStep | Article | Newsletter blurb |
| D4 | `post_twitter_step` | DBOS.step | Thread | Tweet IDs |
| D5 | `post_linkedin_step` | DBOS.step | Post | Post ID |
| D6 | `queue_newsletter_step` | DBOS.step | Entry | Queue ID |
| D7 | `post_community_step` | DBOS.step | Summary | Post IDs |
| D8 | `schedule_reminder_step` | DBOS.step | Article | Scheduled job ID |
| D9 | `persist_social_posts` | DBOS.transaction | Post data | DB records |

#### Analytics (M6)

| ID | Step Name | Type | Input | Output |
|----|-----------|------|-------|--------|
| A1 | `sync_ga4_step` | DBOS.step | Date range | Traffic metrics |
| A2 | `sync_search_console_step` | DBOS.step | Date range | SEO metrics |
| A3 | `sync_twitter_metrics_step` | DBOS.step | Post IDs | Engagement data |
| A4 | `sync_linkedin_metrics_step` | DBOS.step | Post IDs | Engagement data |
| A5 | `sync_newsletter_metrics_step` | DBOS.step | Campaign IDs | Email metrics |
| A6 | `aggregate_performance_step` | DBOS.step | All metrics | Per-article scores |
| A7 | `analyze_patterns_step` | LLMStep | Performance data | Insights |
| A8 | `generate_weekly_report_step` | LLMStep | Analysis | Report markdown |
| A9 | `update_scoring_weights_step` | DBOS.step | Performance vs predictions | New weights |
| A10 | `persist_metrics` | DBOS.transaction | Metrics | DB records |
| A11 | `notify_team_step` | DBOS.step | Report | Slack message |

#### Recruiting (M7)

| ID | Step Name | Type | Input | Output |
|----|-----------|------|-------|--------|
| R1 | `identify_expertise_step` | LLMStep | Topic/beat | Search criteria |
| R2 | `search_twitter_step` | DBOS.step | Criteria | Raw candidates |
| R3 | `search_linkedin_step` | DBOS.step | Criteria | Raw candidates |
| R4 | `search_github_step` | DBOS.step | Criteria | Raw candidates |
| R5 | `enrich_profiles_step` | DBOS.step | Candidates | Enriched profiles |
| R6 | `score_candidates_step` | LLMStep | Profiles | Scored candidates |
| R7 | `generate_outreach_step` | LLMStep | Top candidates | Draft messages |
| R8 | `persist_experts` | DBOS.transaction | Candidate data | DB records |
| R9 | `notify_recruiting_step` | DBOS.step | Top candidates | Slack message |

---

## Database Models

### Entity Relationship Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATABASE SCHEMA                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐  │
│  │  TopicSource    │         │     Topic       │         │     Brief       │  │
│  │                 │────────▶│                 │────────▶│                 │  │
│  │  • RSS feeds    │   has   │  • title        │ becomes │  • headlines    │  │
│  │  • Subreddits   │  many   │  • scores       │         │  • research     │  │
│  │  • Twitter lists│         │  • status       │         │  • sources      │  │
│  └─────────────────┘         └────────┬────────┘         └────────┬────────┘  │
│                                       │                           │            │
│                                       │                           │            │
│                              ┌────────▼────────┐         ┌────────▼────────┐  │
│                              │    Writer       │         │  VisualAsset    │  │
│                              │                 │◀────────│                 │  │
│                              │  • name         │ assigned│  • type         │  │
│                              │  • beats        │   to    │  • cloudinary   │  │
│                              │  • capacity     │         │  • mermaid_code │  │
│                              └─────────────────┘         └─────────────────┘  │
│                                                                    │           │
│                                                          ┌────────▼────────┐  │
│                                                          │  VideoProject   │  │
│                                                          │                 │  │
│                                                          │  • script       │  │
│                                                          │  • shot_list    │  │
│                                                          │  • correspondent│  │
│                                                          └────────┬────────┘  │
│                                                                   │           │
│  ┌─────────────────┐         ┌─────────────────┐         ┌───────▼─────────┐  │
│  │   SocialPost    │◀────────│    Article      │◀────────│                 │  │
│  │                 │   has   │                 │ produces│     (Brief)     │  │
│  │  • platform     │  many   │  • content      │         │                 │  │
│  │  • external_id  │         │  • cms_id       │         │                 │  │
│  │  • metrics      │         │  • published_at │         │                 │  │
│  └─────────────────┘         └────────┬────────┘         └─────────────────┘  │
│                                       │                                        │
│                              ┌────────▼────────┐                              │
│                              │ ArticleMetrics  │                              │
│                              │                 │                              │
│                              │  • traffic      │                              │
│                              │  • social       │                              │
│                              │  • seo          │                              │
│                              └─────────────────┘                              │
│                                                                                 │
│  ┌─────────────────┐                                                          │
│  │     Expert      │  (Standalone - for recruiting)                           │
│  │                 │                                                          │
│  │  • name         │                                                          │
│  │  • platforms    │                                                          │
│  │  • score        │                                                          │
│  │  • outreach     │                                                          │
│  └─────────────────┘                                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Table Specifications

#### `technically_topics`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| topic_id | str | Unique identifier (UUID) |
| source_type | str | rss, reddit, hackernews, twitter, github, manual |
| source_url | str | Original URL |
| source_name | str | Feed name, subreddit, etc. |
| title | str | Topic title |
| description | str | Summary/snippet |
| score_relevance | int | 0-100 |
| score_timeliness | int | 0-100 |
| score_uniqueness | int | 0-100 |
| score_audience_fit | int | 0-100 |
| score_competition | int | 0-100 |
| score_total | float | Weighted composite |
| scoring_reasoning | str | LLM explanation |
| status | enum | discovered, scored, approved, rejected, assigned, published |
| external_score | int | Upvotes, likes from source |
| tags_json | list | Topic tags |
| beat | str | AI, Cloud, Startups, etc. |
| reviewed_by | str | Editor who approved/rejected |
| reviewed_at | datetime | When reviewed |
| assigned_writer_id | str | FK to Writer |
| brief_id | str | FK to Brief |
| created_at | datetime | |
| updated_at | datetime | |

#### `technically_topic_sources`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| source_id | str | Unique identifier |
| source_type | str | rss, reddit, hackernews, twitter |
| source_url | str | RSS URL, subreddit name, etc. |
| source_name | str | Human-readable name |
| enabled | bool | Is this source active? |
| check_interval_minutes | int | How often to check |
| last_checked_at | datetime | |
| include_keywords_json | list | Keywords to match |
| exclude_keywords_json | list | Keywords to filter out |
| min_external_score | int | Minimum upvotes/likes |
| default_beat | str | Default beat assignment |

#### `technically_briefs`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| brief_id | str | Unique identifier |
| topic_id | str | FK to Topic |
| title | str | Working title |
| headline_options_json | list | 3 headline suggestions |
| story_angle | str | Unique angle |
| hook | str | Opening hook |
| key_facts_json | list | Facts with sources |
| source_links_json | list | {url, title, type} |
| competitor_coverage_json | list | What competitors wrote |
| interview_contacts_json | list | Potential sources |
| target_keywords_json | list | SEO keywords |
| suggested_word_count | int | Target length |
| content_format | str | blog_post, deep_dive, news, tutorial |
| visual_suggestions_json | list | Image/diagram ideas |
| requires_diagrams | bool | |
| requires_video | bool | |
| status | enum | draft, ready, assigned, in_progress, submitted, in_review, approved, published |
| assigned_writer_id | str | FK to Writer |
| assigned_editor_id | str | |
| google_doc_url | str | |
| asana_task_id | str | |
| due_date | datetime | |
| created_at | datetime | |
| updated_at | datetime | |

#### `technically_writers`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| writer_id | str | Unique identifier |
| name | str | |
| email | str | |
| slack_user_id | str | For notifications |
| beats_json | list | ["AI", "Cloud"] |
| can_record_video | bool | Can be correspondent |
| max_weekly_assignments | int | Capacity |
| current_assignments | int | Active count |
| is_active | bool | |

#### `technically_visual_assets`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| asset_id | str | Unique identifier |
| brief_id | str | FK to Brief |
| asset_type | enum | featured_image, hero, thumbnail, diagram, chart, social_card, video_thumbnail |
| status | enum | pending, generating, review, approved, rejected, uploaded |
| prompt | str | Generation prompt |
| mermaid_code | str | For diagrams |
| style_reference | str | Style prompt for Nano Banana |
| local_path | str | Temp path |
| cloudinary_url | str | Final URL |
| cloudinary_public_id | str | For management |
| variants_json | dict | {size_name: url} |
| width | int | |
| height | int | |
| alt_text | str | Accessibility |
| created_at | datetime | |

#### `technically_video_projects`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| video_id | str | Unique identifier |
| brief_id | str | FK to Brief |
| script_content | str | Full script |
| script_approved | bool | |
| estimated_duration_seconds | int | |
| shot_list_json | list | Shot breakdown |
| diagram_asset_ids_json | list | FKs to VisualAsset |
| correspondent_id | str | FK to Writer |
| recording_scheduled_at | datetime | |
| recording_completed_at | datetime | |
| raw_footage_url | str | Cloud storage |
| edit_project_url | str | Descript link |
| status | enum | pending, scripted, scheduled, recorded, editing, review, approved, published |
| final_video_url | str | |
| youtube_video_id | str | |
| youtube_url | str | |
| created_at | datetime | |

#### `technically_articles`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| article_id | str | Unique identifier |
| brief_id | str | FK to Brief |
| title | str | Final title |
| slug | str | URL slug |
| content_markdown | str | Full content |
| excerpt | str | Summary |
| meta_title | str | SEO title |
| meta_description | str | SEO description |
| canonical_url | str | |
| keywords_json | list | |
| categories_json | list | |
| tags_json | list | |
| featured_image_asset_id | str | FK to VisualAsset |
| video_id | str | FK to VideoProject |
| author_id | str | FK to Writer |
| author_name | str | Display name |
| status | enum | draft, scheduled, published, unpublished |
| cms_id | str | Sanity document ID |
| cms_last_synced_at | datetime | |
| scheduled_for | datetime | |
| published_at | datetime | |
| created_at | datetime | |

#### `technically_social_posts`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| post_id | str | Unique identifier |
| article_id | str | FK to Article |
| platform | str | twitter, linkedin, threads |
| content | str | Post content |
| thread_json | list | For Twitter threads |
| status | enum | draft, scheduled, posted, failed |
| scheduled_for | datetime | |
| posted_at | datetime | |
| external_post_id | str | Platform's ID |
| external_url | str | Link to post |
| impressions | int | |
| engagements | int | |
| clicks | int | |
| created_at | datetime | |

#### `technically_article_metrics`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| article_id | str | FK to Article |
| date | date | Metrics date |
| pageviews | int | |
| unique_visitors | int | |
| avg_time_on_page | float | seconds |
| bounce_rate | float | |
| organic_traffic | int | |
| social_traffic | int | |
| referral_traffic | int | |
| keyword_rankings_json | list | {keyword, position} |
| backlinks | int | |
| social_shares | int | |
| social_engagements | int | |
| newsletter_clicks | int | |
| video_views | int | |
| video_completion_rate | float | |

#### `technically_experts`

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| expert_id | str | Unique identifier |
| name | str | |
| title | str | Job title |
| company | str | |
| bio | str | |
| twitter_handle | str | |
| twitter_followers | int | |
| linkedin_url | str | |
| github_username | str | |
| email | str | If known |
| expertise_areas_json | list | |
| score_relevance | int | |
| score_authority | int | |
| score_accessibility | int | |
| score_total | float | |
| outreach_status | enum | none, drafted, sent, responded, converted |
| outreach_draft | str | |
| notes | str | |
| source_campaign | str | Which search found them |
| created_at | datetime | |
| updated_at | datetime | |

---

## Integration Requirements

### Extensions to Kurt's Existing Integrations

Kurt already has `kurt integrations research` with Reddit, HN, RSS, and Perplexity. Extend with:

| Integration | Purpose | API/Method | Priority |
|-------------|---------|------------|----------|
| **Twitter/X Signals** | Topic discovery from tech Twitter | Twitter API v2 or Apify | P1 |
| **GitHub Trending** | Trending repos, releases | GitHub API | P2 |
| **Google Alerts** | Keyword monitoring | Email parsing or RSS | P3 |

### New Integrations Required

#### Phase 1: Core Pipeline (Weeks 1-4)

| Integration | Purpose | API/Method |
|-------------|---------|------------|
| **Slack** | Notifications, interactive approvals, digests | Slack SDK (slack_sdk) |
| **Google Docs** | Brief templates, fetch content | Google Docs API |
| **Asana** | Task management, status sync | Asana API |
| **Cloudinary** | Image/video asset storage, transforms | Cloudinary SDK |

#### Phase 2: Production (Weeks 5-8)

| Integration | Purpose | API/Method |
|-------------|---------|------------|
| **DALL-E** | Featured image generation | OpenAI Images API |
| **Mermaid CLI** | Diagram rendering | Local CLI (mmdc) |
| **Nano Banana 3** | Diagram style transfer | API (TBD) |
| **Google Calendar** | Correspondent scheduling | Google Calendar API |
| **Descript** | Video editing, transcription | Descript API |

#### Phase 3: Distribution (Weeks 9-10)

| Integration | Purpose | API/Method |
|-------------|---------|------------|
| **Twitter API** | Post threads, read engagement | Twitter API v2 |
| **LinkedIn API** | Post updates, read engagement | LinkedIn Marketing API |
| **Beehiiv** | Newsletter integration | Beehiiv API |
| **YouTube** | Video upload, metadata | YouTube Data API |

#### Phase 4: Analytics & Recruiting (Weeks 11-12)

| Integration | Purpose | API/Method |
|-------------|---------|------------|
| **GA4** | Traffic analytics | Google Analytics Data API |
| **Search Console** | SEO metrics | Search Console API |
| **Apify** | Social scraping for expert discovery | Apify API |

### Integration Architecture

Each integration follows kurt's pattern:

```
extensions/integrations/{name}/
├── __init__.py          # Exports client class
├── client.py            # API client implementation
├── config.py            # Configuration schema
├── cli.py               # Optional CLI commands
└── tests/
    └── test_{name}.py
```

**Example: Slack Integration**

```python
# extensions/integrations/slack/client.py

class SlackClient:
    """Slack integration for newsroom notifications."""

    def __init__(self, token: str = None):
        self.client = WebClient(token=token or os.environ["SLACK_BOT_TOKEN"])

    def post_topic_digest(self, topics: list[dict], channel: str) -> str:
        """Post daily digest with interactive buttons."""
        ...

    def post_high_score_alert(self, topic: dict, channel: str) -> str:
        """Post immediate alert for high-scoring topic."""
        ...

    def notify_writer(self, writer_slack_id: str, brief: dict) -> str:
        """DM writer about new assignment."""
        ...

    def handle_topic_approval(self, payload: dict) -> dict:
        """Handle interactive button callback."""
        ...
```

---

## CLI Commands

### Topic Management

```bash
# Ingestion
kurt topics ingest                          # Run ingestion now
kurt topics ingest --source reddit          # Specific source only
kurt topics ingest --background             # Run in background
kurt topics ingest --dry-run                # Preview without saving

# Listing and filtering
kurt topics list                            # All topics
kurt topics list --status approved          # By status
kurt topics list --score-min 80             # By score
kurt topics list --beat "AI"                # By beat
kurt topics list --since "2024-01-01"       # By date

# Actions
kurt topics show <topic-id>                 # Full details
kurt topics approve <topic-id>              # Approve topic
kurt topics approve <topic-id> --assign <writer-id>  # Approve and assign
kurt topics reject <topic-id> --reason "..." # Reject with reason
kurt topics score <topic-id>                # Re-score a topic

# Sources
kurt topics sources list                    # List configured sources
kurt topics sources add --type rss --url "..." --name "..."
kurt topics sources disable <source-id>
```

### Brief Management

```bash
# Generation
kurt briefs generate <topic-id>             # Generate brief
kurt briefs generate <topic-id> --writer <id>  # Generate and assign
kurt briefs generate <topic-id> --skip-research  # Use existing research

# Listing
kurt briefs list                            # All briefs
kurt briefs list --status in_progress       # By status
kurt briefs list --writer <id>              # By writer

# Actions
kurt briefs show <brief-id>                 # Full details
kurt briefs assign <brief-id> --writer <id> # Assign to writer
kurt briefs update-status <brief-id> --status submitted
```

### Production

```bash
# Images
kurt production image <brief-id>            # Generate featured image
kurt production image <brief-id> --type diagram --concept "..."
kurt production image <brief-id> --regenerate  # Try again

# Diagrams (Mermaid → Nano Banana pipeline)
kurt production diagram <brief-id> --concept "API request flow"
kurt production diagram <brief-id> --mermaid-file diagram.mmd

# Video
kurt production video prepare <brief-id>    # Full pre-production
kurt production video script <brief-id>     # Script only
kurt production video schedule <video-id> --correspondent <id> --time "..."

# Assets
kurt production assets list <brief-id>      # List all assets
kurt production assets upload <brief-id> --file local.png --type diagram
```

### Publishing

```bash
# CMS
kurt publish sync <brief-id>                # Push to CMS
kurt publish preview <article-id>           # Get preview URL
kurt publish schedule <article-id> --time "2024-01-20T09:00:00"
kurt publish now <article-id>               # Publish immediately

# Distribution
kurt publish distribute <article-id>        # Full distribution
kurt publish distribute <article-id> --platforms twitter,linkedin
kurt publish twitter <article-id>           # Twitter only
kurt publish linkedin <article-id>          # LinkedIn only
```

### Analytics

```bash
# Sync
kurt analytics sync                         # Sync all sources
kurt analytics sync --source ga4            # Specific source
kurt analytics sync --since "2024-01-01"    # Date range

# Reports
kurt analytics report                       # Weekly report
kurt analytics report --period month        # Monthly
kurt analytics report --article <id>        # Single article

# Performance
kurt analytics top --period week --limit 10 # Top performers
kurt analytics underperforming              # Articles below expectations
```

### Recruiting

```bash
# Discovery
kurt experts find --topic "AI agents" --platforms twitter,linkedin
kurt experts find --beat "Cloud" --limit 50

# Management
kurt experts list                           # All experts
kurt experts list --status drafted          # By outreach status
kurt experts show <expert-id>               # Full profile

# Outreach
kurt experts draft-outreach <expert-id>     # Generate outreach
kurt experts mark-sent <expert-id>          # Mark as sent
kurt experts mark-responded <expert-id>     # Mark as responded
```

---

## Technical Architecture

### Project Structure

```
technically/
├── kurt.config                     # Kurt configuration
├── .kurt/
│   └── kurt.sqlite                 # Database
├── .agents/
│   └── AGENTS.md                   # Agent instructions
├── workflows/                      # Agent workflows (.md)
│   ├── topic-research.md
│   ├── competitor-analysis.md
│   └── expert-outreach.md
│
├── extensions/                     # Python extensions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── topics.py
│   │   ├── briefs.py
│   │   ├── production.py
│   │   ├── publishing.py
│   │   └── recruiting.py
│   │
│   ├── workflows/
│   │   ├── topics/
│   │   │   ├── config.py
│   │   │   ├── steps.py
│   │   │   └── workflow.py
│   │   ├── briefs/
│   │   ├── production/
│   │   ├── publishing/
│   │   ├── distribution/
│   │   ├── analytics/
│   │   └── recruiting/
│   │
│   └── integrations/
│       ├── slack/
│       ├── google_docs/
│       ├── asana/
│       ├── cloudinary/
│       ├── dalle/
│       ├── mermaid/
│       ├── nano_banana/
│       ├── twitter/
│       ├── linkedin/
│       ├── youtube/
│       ├── ga4/
│       ├── search_console/
│       └── apify/
│
├── sources/                        # Fetched content (kurt default)
└── projects/                       # Writing projects (kurt default)
```

### Workflow Execution Model

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        EXECUTION MODEL                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         DBOS WORKFLOW                                   │   │
│  │                                                                         │   │
│  │   @DBOS.workflow()                                                     │   │
│  │   def topic_ingestion_workflow(config):                                │   │
│  │       │                                                                 │   │
│  │       ├── fetch_rss_step()         # DBOS.step - Pure Python           │   │
│  │       ├── fetch_reddit_step()      # DBOS.step - Pure Python           │   │
│  │       ├── dedupe_step()            # DBOS.step - Pure Python           │   │
│  │       │                                                                 │   │
│  │       ├── score_topics_step.run()  # LLMStep - Batch LLM               │   │
│  │       │   └── Queue (concurrency=5)                                    │   │
│  │       │       ├── process_row() → LLM call                             │   │
│  │       │       ├── process_row() → LLM call                             │   │
│  │       │       └── ...                                                  │   │
│  │       │                                                                 │   │
│  │       ├── persist_topics()         # DBOS.transaction - DB write       │   │
│  │       │                                                                 │   │
│  │       └── notify_slack_step()      # DBOS.step - Pure Python           │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                          │
│                                     │ Durability                               │
│                                     ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        POSTGRES (via DBOS)                              │   │
│  │                                                                         │   │
│  │   • Workflow state                                                     │   │
│  │   • Step checkpoints                                                   │   │
│  │   • Event streams                                                      │   │
│  │   • Recovery on failure                                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                        SQLITE (kurt)                                    │   │
│  │                                                                         │   │
│  │   • Domain models (topics, briefs, articles, etc.)                     │   │
│  │   • LLM traces (costs, tokens)                                         │   │
│  │   • Integration configs                                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Topic ingestion working end-to-end

- [ ] Set up project structure with extensions folder
- [ ] Implement topic models
- [ ] Extend kurt signals with Twitter/GitHub
- [ ] Implement topic scoring LLMStep
- [ ] Build Slack integration (notifications, buttons)
- [ ] CLI: `kurt topics` commands

**Deliverable:** Daily topic digest in Slack with approve/reject

### Phase 2: Brief Pipeline (Weeks 3-4)
**Goal:** Topic → Brief → Writer assignment

- [ ] Implement brief models
- [ ] Build research agent workflow
- [ ] Implement brief generation LLMStep
- [ ] Build Google Docs integration
- [ ] Build Asana integration
- [ ] CLI: `kurt briefs` commands

**Deliverable:** Approved topic auto-generates brief, creates doc, assigns writer

### Phase 3: Visual Production (Weeks 5-6)
**Goal:** Automated image and diagram generation

- [ ] Implement visual asset models
- [ ] Build Cloudinary integration
- [ ] Build DALL-E integration
- [ ] Build Mermaid CLI integration
- [ ] Build Nano Banana 3 integration
- [ ] CLI: `kurt production image/diagram` commands

**Deliverable:** Brief triggers asset generation, uploads to DAM

### Phase 4: Video Pipeline (Weeks 7-8)
**Goal:** Video pre-production automated

- [ ] Implement video project models
- [ ] Build script generation LLMStep
- [ ] Build shot list generation
- [ ] Build Google Calendar integration
- [ ] Build correspondent notification flow
- [ ] CLI: `kurt production video` commands

**Deliverable:** Brief with video flag triggers full pre-prod package

### Phase 5: Publishing (Weeks 9-10)
**Goal:** Draft → CMS → Publish

- [ ] Implement article models
- [ ] Extend kurt's Sanity integration
- [ ] Build SEO metadata generation
- [ ] Build publishing workflow
- [ ] CLI: `kurt publish` commands

**Deliverable:** Approved content auto-syncs to CMS, schedules publish

### Phase 6: Distribution (Weeks 11-12)
**Goal:** Automated social amplification

- [ ] Implement social post models
- [ ] Build Twitter integration
- [ ] Build LinkedIn integration
- [ ] Build newsletter integration
- [ ] Build distribution workflow
- [ ] CLI: `kurt publish distribute` commands

**Deliverable:** Published article triggers coordinated social distribution

### Phase 7: Analytics & Recruiting (Weeks 13-14)
**Goal:** Performance tracking and feedback loop

- [ ] Implement metrics models
- [ ] Build GA4 integration
- [ ] Build Search Console integration
- [ ] Build weekly report workflow
- [ ] Implement expert models
- [ ] Build Apify integration for social scraping
- [ ] Build recruiting workflow
- [ ] CLI: `kurt analytics` and `kurt experts` commands

**Deliverable:** Weekly performance reports, expert discovery pipeline

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Topics surfaced per day | 50-100 | Count in DB |
| Topic → Brief time | < 2 hours | Workflow duration |
| Brief → Published time | < 5 days | Status timestamps |
| Visual asset generation | < 5 min | Workflow duration |
| Distribution coverage | 100% of articles | Social posts created |
| Scoring accuracy | 70%+ correlation | Predicted vs actual traffic |
| Cost per article | < $5 in LLM | LLM traces sum |

---

## Open Questions

1. **Nano Banana 3 API** — What's the exact API interface for style transfer?
2. **Video editing** — Descript API vs. manual editing workflow?
3. **Newsletter platform** — Beehiiv, Substack, or custom?
4. **Expert outreach** — Automated DMs or manual send?
5. **Multi-tenant** — Single workspace or support for multiple publications?

---

*Document Version: 1.0*
*Last Updated: January 2026*
*For: Technically Newsroom Project*
