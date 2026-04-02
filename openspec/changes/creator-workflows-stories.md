# Creator Workflows: Tech Solo Newsletter Automation (Updated)

Epic: kurt-core-u4xo
Total stories: 35
Blocked by: kurt-core-1uhd (Map/Fetch Refactor)

## kurt-core-u4xo.1: Workflow: Competitive Landscape - Data Model
Priority: P2 | Type: task

Define data model for competitor tracking.

## Tables
- competitors: id, name, platforms JSON, niche, positioning, added_at
- competitor_profiles: id, competitor_id, platform, handle, follower_count, updated_at
- competitor_posts: id, profile_id, post_id, content, engagement, posted_at, is_viral

## Metrics to Track
- Follower count (point-in-time snapshots)
- Posting frequency (posts per week/month)
- Engagement rate (likes + comments / followers)
- Top posts by engagement
- Topics (extracted via LLM)

---

## kurt-core-u4xo.10: Workflow: Content Stats - Performance Analysis
Priority: P2 | Type: task

Analyze your content performance and detect patterns.

## CLI
kurt workflow mystats analyze --output report.md

## LLM Analysis
1. Cluster posts by topic
2. Identify top 10% performers
3. Analyze patterns in high performers:
   - Posting time/day
   - Post length
   - Format (list, story, how-to)
   - Hook style
   - Topics
4. Find underperforming patterns

## Output
- Performance dashboard
- Pattern analysis report
- Recommendations for improvement
- Best posting times heatmap

---

## kurt-core-u4xo.11: Workflow: Profile Optimization - Audit Profiles
Priority: P2 | Type: task

Audit and optimize social profiles.

## CLI
kurt workflow profile audit --platforms linkedin,substack

## LLM Analysis
1. Fetch current profiles
2. Compare to high-performing competitors
3. Analyze:
   - Bio clarity and hook
   - Value proposition
   - CTA effectiveness
   - Visual consistency
   - Keyword optimization

## Output
- Audit report per platform
- Specific improvement suggestions
- Rewritten bio/tagline options

---

## kurt-core-u4xo.12: Workflow: Funnel Optimization - Email Lifecycle Review
Priority: P2 | Type: task

Review and optimize email lifecycle (subscription, welcome, unsubscribe).

## CLI
kurt workflow funnel audit --provider substack

## Steps
1. Export current email templates
2. Analyze each touchpoint:
   - Subscription confirmation
   - Welcome email sequence
   - Re-engagement emails
   - Unsubscribe flow
3. Compare to best practices
4. Generate optimized versions

## Output
- Funnel audit report
- Rewritten email templates
- A/B test suggestions

---

## kurt-core-u4xo.13: Workflow: Greenfield Topics - Competitor Topic Mining
Priority: P2 | Type: task

Mine competitor content for successful topics.

## CLI
kurt workflow greenfield scan --competitors all --since 6months

## Steps
1. Load all competitor posts from last 6 months
2. Extract topics via LLM clustering
3. Score topics by:
   - Average engagement
   - Posting frequency (oversaturated?)
   - Your coverage (have you written about it?)
4. Rank by opportunity score

## Topic Categories
- How X works (explainers)
- Tips & tricks
- Tool comparisons
- Industry trends
- Personal stories/lessons

---

## kurt-core-u4xo.14: Workflow: Greenfield Topics - Opportunity Report
Priority: P2 | Type: task

Generate greenfield topic opportunities report.

## CLI
kurt workflow greenfield report --top 20 --output topics.md

## Greenfield Criteria
- High engagement when competitors post
- Low saturation (few posts on topic)
- You haven't covered it yet
- Matches your expertise

## Output
- Ranked list of greenfield topics
- For each topic:
  - Why it's greenfield
  - Example high-performing posts
  - Suggested angle for you
  - Outline starter

---

## kurt-core-u4xo.15: Workflow: Company Discovery - Product Launch Tracking
Priority: P2 | Type: task

Find companies that launched tech products 1-2 years ago.

## CLI
kurt workflow companies discover --launched 1-2years --niche 'developer tools,SaaS'

## Data Sources
- Product Hunt launches (1-2 years ago)
- Crunchbase funding rounds
- Tech news mentions
- GitHub trending (historical)

## Filters
- Launched 12-24 months ago
- Tech/SaaS product
- Has funding or revenue signals
- Not already doing content marketing

---

## kurt-core-u4xo.16: Workflow: Company Discovery - Content Gap Analysis
Priority: P2 | Type: task

Analyze if discovered companies are doing content in your niche.

## CLI
kurt workflow companies analyze --output prospects.md

## Steps
1. For each company, check:
   - Blog activity
   - Social presence
   - Newsletter
   - Content in your niche specifically
2. Score content gap (bigger gap = better prospect)
3. Identify decision makers (LinkedIn)

## Output
- Prospect list with scores
- Contact suggestions
- Outreach angle per company

---

## kurt-core-u4xo.17: Workflow: Company Discovery - Outreach Automation
Priority: P2 | Type: task

Generate sponsored content outreach for prospects.

## CLI
kurt workflow companies outreach --prospects top10 --dry-run

## Steps
1. Load top prospects
2. Generate personalized pitch:
   - Why they should sponsor
   - Your audience fit
   - Content ideas for them
   - Pricing/packages
3. Draft outreach email
4. Track sent/responses

## Safety
- Dry-run mode
- Human approval before send
- CRM integration for tracking

---

## kurt-core-u4xo.18: Workflow: Writing - Source Gathering
Priority: P2 | Type: task

Gather sources for a specific content project.

## CLI
kurt workflow write sources --topic 'How RAG works' --output sources/

## Steps
1. Input: topic or brief
2. Search for relevant sources:
   - Competitor posts on topic
   - Technical docs/papers
   - HackerNews discussions
   - Reddit threads
   - Official documentation
3. Fetch and extract content
4. Organize by relevance

## Output
- sources/ folder with markdown files
- sources/index.md with summary
- Relevance scores per source

---

## kurt-core-u4xo.19: Workflow: Writing - Multi-LLM Outline Generation
Priority: P2 | Type: task

Generate outline using multiple LLMs for best results.

## CLI
kurt workflow write outline --sources sources/ --models gpt4,claude,gemini --output outline.md

## Steps
1. Load gathered sources
2. Generate outline with each LLM:
   - GPT-4: structure-focused
   - Claude: depth-focused
   - Gemini: breadth-focused
3. Merge/compare outlines
4. Present options or synthesized version

## Output
- outline-gpt4.md
- outline-claude.md
- outline-gemini.md
- outline-merged.md (best of each)

---

## kurt-core-u4xo.2: Workflow: Competitive Landscape - Competitor Discovery
Priority: P2 | Type: task

Implement competitor discovery across platforms.

## CLI
kurt workflow competitors discover --niche 'tech newsletter' --platforms linkedin,twitter,substack

## Steps
1. Use kurt map profile to search each platform
2. Filter by follower count thresholds
3. Store in competitors table
4. Link platform profiles

## Apify Actors
- LinkedIn: profile search by keywords
- Twitter: profile search
- Substack: publication search

---

## kurt-core-u4xo.20: Workflow: Writing - Markdown to Substack Exporter
Priority: P2 | Type: task

Export markdown content to Substack format.

## CLI
kurt workflow write export --input draft.md --platform substack --output substack-ready.html

## Steps
1. Parse markdown
2. Convert to Substack-compatible HTML:
   - Handle images (upload/embed)
   - Format code blocks
   - Convert links
   - Handle footnotes
   - Preserve formatting
3. Generate preview
4. Optional: direct publish via API

## Features
- Image optimization
- Embed support (tweets, YouTube)
- Draft mode vs publish
- Schedule support

---

## kurt-core-u4xo.21: Workflow: Writing - Meme/Visual Finder
Priority: P2 | Type: task

Find relevant memes and visuals for content.

## CLI
kurt workflow write visuals --topic 'RAG explained' --output visuals/

## Steps
1. Extract key concepts from content
2. Search for relevant:
   - Memes (imgflip, knowyourmeme)
   - Diagrams (existing explanatory visuals)
   - Screenshots (relevant tools/UIs)
   - Stock illustrations
3. Score by relevance and humor
4. Download and organize

## Output
- visuals/ folder with images
- visuals/suggestions.md with placement recommendations
- Attribution/license info

---

## kurt-core-u4xo.22: Workflow: Writing - End-to-End Pipeline
Priority: P2 | Type: task

Orchestrate the full writing pipeline.

## CLI
kurt workflow write full --topic 'How RAG works' --output drafts/rag/

## Pipeline Steps
1. Source gathering (W8_1)
2. Outline generation (W8_2)
3. [Manual: Write draft in your editor]
4. Visual finder (W8_4)
5. Export to Substack (W8_3)

## TOML Workflow Definition


## Features
- Progress tracking
- Resume from any step
- Parallel source + visual gathering

---

## kurt-core-u4xo.23: Infrastructure: Workflow TOML Definitions
Priority: P1 | Type: task

Create TOML workflow definitions for all creator workflows.

## Files
- workflows/competitive-landscape.toml
- workflows/adjacent-discovery.toml
- workflows/collab-scouting.toml
- workflows/content-stats.toml
- workflows/profile-optimization.toml
- workflows/greenfield-topics.toml
- workflows/company-discovery.toml
- workflows/writing-pipeline.toml

## Per Workflow
- Input parameters
- Step definitions
- Output schemas
- Schedule configuration

---

## kurt-core-u4xo.24: Infrastructure: Creator Workflow CLI Commands
Priority: P1 | Type: task

Add CLI commands for creator workflows.

## Commands
kurt workflow competitors <discover|sync|analyze>
kurt workflow adjacent <discover|recommend>
kurt workflow collab <discover|analyze>
kurt workflow mystats <import|analyze>
kurt workflow profile <audit>
kurt workflow funnel <audit>
kurt workflow greenfield <scan|report>
kurt workflow companies <discover|analyze|outreach>
kurt workflow write <sources|outline|export|visuals|full>

## Features
- Consistent --output, --dry-run flags
- Progress display
- JSON output mode
- Help text with examples

---

## kurt-core-u4xo.25: Infrastructure: LLM Analysis Prompts Library
Priority: P2 | Type: task

Create reusable LLM prompts for workflow analysis tasks.

## Prompts
- Topic extraction from posts
- Competitor positioning analysis
- Gap analysis
- Content performance patterns
- Profile optimization suggestions
- Pitch email generation
- Outline generation (multiple styles)

## Format
- prompts/ folder with markdown templates
- Variable interpolation support
- Version tracking
- A/B testing support

---

## kurt-core-u4xo.26: Infrastructure: Workflow Output Reports
Priority: P2 | Type: task

Create report templates for workflow outputs.

## Reports
- Competitive leaderboard (table + charts)
- Content performance dashboard
- Greenfield topics list
- Prospect pipeline
- Collaboration targets

## Features
- Markdown output
- HTML export with charts
- JSON for programmatic use
- Incremental updates

---

## kurt-core-u4xo.27: Data Model: Adjacent Publishers & Recommendations
Priority: P1 | Type: task

Define tables for adjacent-niche discovery workflow.

## Tables
- adjacent_publishers: id, platform, handle, name, niche, follower_count, posts_per_month, discovered_at
- recommendation_requests: id, publisher_id, status (pending/sent/accepted/declined), sent_at, response_at, message

## Indexes
- adjacent_publishers: (platform, follower_count), (niche)
- recommendation_requests: (status, sent_at)

---

## kurt-core-u4xo.28: Data Model: Collaboration Targets & Outreach
Priority: P1 | Type: task

Define tables for collaboration scouting workflow.

## Tables
- collab_targets: id, platform, handle, name, follower_count, niche, topics_covered JSON, gaps_identified JSON
- collab_outreach: id, target_id, status (draft/sent/followed_up/accepted/declined), pitch_content, sent_at, follow_ups JSON

## Tracking
- Follow-up cadence
- Response tracking
- Blacklist support

---

## kurt-core-u4xo.29: Data Model: Company Prospects & Outreach
Priority: P1 | Type: task

Define tables for company discovery workflow.

## Tables
- company_prospects: id, name, website, launched_at, funding JSON, content_gap_score, verified_at
- company_outreach: id, prospect_id, contact_name, contact_linkedin, status, pitch_content, sent_at

## Verification Fields
- has_blog, has_newsletter, content_in_niche
- decision_maker_found

---

## kurt-core-u4xo.3: Workflow: Competitive Landscape - Posts Collection
Priority: P2 | Type: task

Collect posts from tracked competitors.

## CLI
kurt workflow competitors sync --since 3months

## Steps
1. For each competitor profile, use kurt map posts
2. Fetch post content with kurt fetch posts
3. Calculate engagement metrics
4. Flag viral posts (> 2x average engagement)
5. Store in competitor_posts table

## Scheduling
- Daily sync for new posts
- Weekly full refresh

---

## kurt-core-u4xo.30: Data Model: My Content & Performance
Priority: P1 | Type: task

Define tables for content stats workflow.

## Tables
- my_posts: id, platform, post_id, content, posted_at, likes, comments, shares, views, subscriber_count_at_post
- my_performance_snapshots: id, post_id, snapshot_at, metrics JSON
- my_content_patterns: id, pattern_type, description, posts JSON, score

## Metrics
- Baseline calculations
- Top 10% threshold definition
- Engagement rate normalization

---

## kurt-core-u4xo.31: Integration: External API Connectors
Priority: P1 | Type: task

Define integrations needed beyond map/fetch tools.

## Required Integrations
- Substack API: recommendations, publish/schedule (if available)
- Product Hunt API: historical launches
- Crunchbase API: funding data (paid)
- Alternative: use web scraping with rate limits

## Fallback Strategy
For each integration, define:
- Primary: official API
- Fallback: Apify actor
- Last resort: manual input

## Cost Estimates
Document API costs per workflow

---

## kurt-core-u4xo.32: Compliance: Rate Limits & TOS Guardrails
Priority: P1 | Type: task

Define compliance guardrails for all workflows.

## Rate Limits (per platform)
- LinkedIn: max 100 profile views/day
- Twitter: per Apify actor limits
- Substack: TBD (no official limits)

## Outreach Limits
- Max 10 recommendations/day
- Max 5 cold outreaches/day
- 7-day cooldown between follow-ups

## Required Features
- Dry-run mode (mandatory first run)
- Human approval before send
- Audit log for all actions
- Opt-out/blacklist support

---

## kurt-core-u4xo.33: Workflow: Data Refresh & Sync Strategy
Priority: P2 | Type: task

Define refresh cadence for all tracked data.

## Refresh Schedules
- Competitor profiles: weekly follower snapshots
- Competitor posts: daily new posts check
- Adjacent publishers: monthly re-check
- Company prospects: weekly verification

## Dedupe Logic
- URL normalization
- Platform ID matching
- Fuzzy name matching

## Retention Policy
- Keep 12 months of snapshots
- Archive old data to cold storage

---

## kurt-core-u4xo.34: Workflow: Outreach Lifecycle Management
Priority: P2 | Type: task

Track outreach across all workflows.

## Unified Outreach Tracking
- Status: draft, queued, sent, opened, replied, accepted, declined
- Follow-up scheduling
- Response tracking

## Features
- Weekly outreach caps (configurable)
- Blacklist management
- Template versioning
- A/B testing support

---

## kurt-core-u4xo.35: Workflow: Writing - Content QA & Verification
Priority: P2 | Type: task

Add QA step to writing pipeline.

## QA Checks
- Fact verification (claims + sources)
- Citation formatting
- Plagiarism check (basic similarity)
- Broken link detection
- Image alt text

## Output
- QA report with issues
- Severity levels (blocker, warning, info)
- Auto-fix suggestions where possible

---

## kurt-core-u4xo.4: Workflow: Competitive Landscape - Analysis & Differentiator
Priority: P2 | Type: task

Analyze competitors and identify differentiators.

## CLI
kurt workflow competitors analyze --output report.md

## LLM Analysis Steps
1. Extract main topics from posts (clustering)
2. Identify posting patterns (time, format, length)
3. Analyze positioning from bio + content
4. Compare vs. user's profile to find differentiators
5. Generate competitive matrix report

## Output
Markdown report with:
- Leaderboard table (followers, frequency, engagement)
- Topic overlap visualization
- Differentiator analysis per competitor
- Opportunities/gaps identified

---

## kurt-core-u4xo.5: Workflow: Adjacent-Niche Discovery - Substack Search
Priority: P2 | Type: task

Discover Substack publishers in adjacent niches.

## CLI
kurt workflow adjacent discover --niche 'AI,productivity,startups' --followers 10000-20000 --frequency 2+/month

## Steps
1. Search Substack for niche keywords
2. Filter by follower count (10k-20k sweet spot)
3. Check posting frequency (2-3+ posts/month = active)
4. Store qualified publishers

## Filters
- Follower range: configurable (default 10k-20k)
- Min posts/month: configurable (default 2)
- Exclude: already following, already contacted

---

## kurt-core-u4xo.6: Workflow: Adjacent-Niche Discovery - Auto Recommendation Requests
Priority: P2 | Type: task

Automatically send Substack recommendation requests.

## CLI
kurt workflow adjacent recommend --limit 10 --dry-run

## Steps
1. Get qualified publishers from discovery
2. Check if already recommended/contacted
3. Generate personalized request message via LLM
4. Send recommendation request via Substack API/automation
5. Track sent requests and responses

## Safety
- Daily limit on requests (prevent spam)
- Dry-run mode for preview
- Personalization required (no generic messages)
- Cooldown period between requests

---

## kurt-core-u4xo.7: Workflow: Collaboration Scouting - Find Large Publishers
Priority: P2 | Type: task

Find large Substack publishers for cross-post collaboration.

## CLI
kurt workflow collab discover --min-followers 50000 --niche 'tech,business'

## Steps
1. Search Substack for large publishers (50k+ followers)
2. Filter to adjacent niches
3. Analyze their content topics
4. Identify gaps in their coverage
5. Store collaboration targets

## Output
- Publisher profile + stats
- Content analysis (topics covered)
- Gap analysis (topics NOT covered that you could fill)

---

## kurt-core-u4xo.8: Workflow: Collaboration Scouting - Gap Analysis & Pitch
Priority: P2 | Type: task

Analyze content gaps and generate collaboration pitches.

## CLI
kurt workflow collab analyze --publisher <name> --output pitch.md

## LLM Steps
1. Analyze publisher's last 50 posts for topics
2. Compare with your expertise areas
3. Identify 2-3 topics you could guest-write
4. Generate personalized pitch email
5. Suggest cross-post ideas

## Output
- Gap analysis report
- Draft pitch email (editable)
- Suggested topics with rationale

---

## kurt-core-u4xo.9: Workflow: Content Stats - Import Own Content
Priority: P2 | Type: task

Import and track your own content across platforms.

## CLI
kurt workflow mystats import --platforms linkedin,substack,twitter

## Steps
1. Connect to your profiles via API/Apify
2. Import all posts with engagement metrics
3. Store in my_posts table
4. Calculate baseline metrics

## Data Collected
- Post content, date, platform
- Likes, comments, shares, views
- Subscriber count at time of post
- Post format (text, carousel, video, thread)

---

