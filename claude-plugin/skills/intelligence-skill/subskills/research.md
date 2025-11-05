# Research Subskill

**Purpose:** External research operations (AI, Reddit, Hacker News, RSS)
**Parent Skill:** intelligence
**Operations:** search, list, get, reddit, hackernews, feeds

**Note:** This subskill provides **presentation guidelines** for research operations. The "Implementation" sections show which kurt CLI commands to call and how to format the output.

---

## Overview

Provides external research capabilities using Perplexity AI and community monitoring sources. These operations wrap `kurt research` CLI commands.

**When to use:**
- AI-powered research on topics
- Monitoring community discussions
- Tracking competitor blogs/announcements
- Gathering reference sources for projects

---

## Operations

### 1. `search "<query>" [--recency hour|day|week|month] [--save]`

**Purpose:** AI-powered research using Perplexity

**Implementation:**
```bash
kurt research search "<query>" \
  ${recency:+--recency $recency} \
  ${save:+--save}
```

**Example:**
```
intelligence search "AI coding tools trends" --recency week --save

Researching: AI coding tools trends
Recency: week

✓ Research complete (3.2s)

**Key developments this week:**
- GitHub Copilot X announced with chat interface [1]
- Cursor raises $60M Series A for AI-first IDE [2]
- Claude Code launches with agentic capabilities [3]

Sources (15):
[1] https://github.blog/copilot-x
[2] https://techcrunch.com/cursor-funding
...

✓ Saved to: sources/research/2025-11-03-ai-coding-tools-trends.md
```

**Options:**
- `--recency`: hour, day (default for news), week, month, or omit for timeless
- `--save`: Save to sources/research/
- `--model`: sonar-reasoning (default), sonar, sonar-pro
- `--output`: markdown (default), json

**Recency guidance:**
- `hour` - Breaking news, real-time events
- `day` - Recent news (default)
- `week` - Trends, weekly roundups
- `month` - Monthly analysis
- Omit - Timeless/general queries

---

### 2. `list [--limit N]`

**Purpose:** Browse past research results

**Implementation:**
```bash
kurt research list ${limit:+--limit $limit}
```

**Example:**
```
intelligence list --limit 10

Recent Research (23 results)

2025-11-03-ai-coding-tools-trends.md
  Query: AI coding tools trends
  Date: 2025-11-03
  Sources: 15

2025-11-02-dbt-vs-dataform.md
  Query: dbt vs Dataform comparison
  Date: 2025-11-02
  Sources: 12

2025-11-01-snowflake-pricing.md
  Query: Snowflake cost optimization
  Date: 2025-11-01
  Sources: 8
```

**Options:**
- `--limit N`: Show only N most recent (default: 20)

---

### 3. `get <filename>`

**Purpose:** Display specific research result

**Implementation:**
```bash
kurt research get <filename>
```

**Example:**
```
intelligence get 2025-11-02-dbt-vs-dataform

Research Result
File: 2025-11-02-dbt-vs-dataform.md

Query: dbt vs Dataform comparison
Date: 2025-11-02
Source: perplexity
Sources: 12 citations

[Full research content with citations]
```

**Note:** Filename can be with or without .md extension

---

### 4. `reddit -s <subreddit> [--keywords "..."] [--min-score N]`

**Purpose:** Monitor Reddit for trending discussions

**Implementation:**
```bash
kurt research reddit -s <subreddit> \
  ${keywords:+--keywords "$keywords"} \
  ${min_score:+--min-score $min_score} \
  --timeframe ${timeframe:-day}
```

**Example:**
```
intelligence reddit -s dataengineering --timeframe day --min-score 10

Monitoring: r/dataengineering

✓ Found 15 posts

#  Title                                                Score  Comments  Relevance
1  "Dagster vs Prefect: Production experience?"         142    87        0.95
2  "How to handle slowly changing dimensions in dbt"     98    45        0.87
3  "Snowflake pricing is getting ridiculous"             76    62        0.82


intelligence reddit -s dataengineering --keywords "dbt,fivetran"

Found 6 posts matching keywords...
```

**Options:**
- `-s <subreddit>`: Subreddit name (required)
- `--keywords "word1,word2"`: Filter by keywords
- `--min-score N`: Minimum upvotes threshold
- `--timeframe`: hour, day (default), week, month
- `--output`: table (default), json

**Multi-subreddit:**
```bash
intelligence reddit -s "dataengineering+datascience"
```

---

### 5. `hackernews [--keywords "..."] [--min-score N]`

**Purpose:** Monitor Hacker News for trending tech discussions

**Implementation:**
```bash
kurt research hackernews \
  ${keywords:+--keywords "$keywords"} \
  ${min_score:+--min-score $min_score} \
  --timeframe ${timeframe:-day}
```

**Example:**
```
intelligence hackernews --keywords "AI" --timeframe day

Monitoring: Hacker News (day)
Keywords: AI

✓ Found 12 stories

#  Title                                            Points  Comments  Relevance
1  "Show HN: Open source AI coding assistant"       324     142       0.98
2  "AI won't replace developers, but..."            287     203       0.94
3  "Anthropic announces Claude 3.5"                 245     156       0.91
```

**Options:**
- `--keywords "word1,word2"`: Filter by keywords
- `--min-score N`: Minimum points (default: 10)
- `--timeframe`: hour, day (default), week, month
- `--output`: table (default), json

---

### 6. `feeds <feed-url> [--keywords "..."] [--since "7 days"]`

**Purpose:** Monitor RSS/Atom feeds for new content

**Implementation:**
```bash
kurt research feeds <feed-url> \
  ${since:+--since "$since"} \
  ${keywords:+--keywords "$keywords"}
```

**Example:**
```
intelligence feeds https://blog.getdbt.com/rss.xml --since "7 days"

Monitoring feed: https://blog.getdbt.com/rss.xml
Since: 2025-10-27 00:00

✓ Found 3 entries

#  Title                                   Published    Domain
1  "Introducing dbt Cloud IDE v2"          2025-11-01   blog.getdbt.com
2  "dbt Semantic Layer updates"            2025-10-29   blog.getdbt.com
3  "How we use dbt at Scale"               2025-10-28   blog.getdbt.com


intelligence feeds https://blog.getdbt.com/rss.xml --keywords "semantic layer"

Found 1 entry matching keywords...
```

**Options:**
- `<feed-url>`: RSS/Atom feed URL (required)
- `--since "N days|hours|weeks"`: Only entries since
- `--keywords "word1,word2"`: Filter by keywords
- `--limit N`: Max entries (default: 50)
- `--output`: table (default), json

**Common feeds:**
- dbt blog: `https://blog.getdbt.com/rss.xml`
- Fivetran blog: `https://fivetran.com/blog/rss.xml`
- Airbyte blog: `https://airbyte.com/blog/rss.xml`

---

## API Key Configuration

### Perplexity API (Required for `search`)

**Setup:**
1. Get API key from: https://www.perplexity.ai/settings/api
2. Edit `.kurt/research-config.json`:
```json
{
  "perplexity": {
    "api_key": "pplx-...",
    "default_model": "sonar-reasoning",
    "default_recency": "day",
    "max_tokens": 4000,
    "temperature": 0.2
  }
}
```

### Reddit/HN/Feeds (No API key needed)

Reddit, Hacker News, and RSS monitoring work without authentication.

---

## Error Handling

### Perplexity not configured
```
⚠️ Perplexity not configured

Add your API key to .kurt/research-config.json:
{
  "perplexity": {
    "api_key": "your-key-here"
  }
}

Get API key from: https://www.perplexity.ai/settings/api
```

### No results found
```
No posts found matching criteria

Try:
- Broader time window: --timeframe week
- Lower score threshold: --min-score 5
- Different keywords or subreddit
```

### Feed fetch failed
```
⚠️ Failed to fetch feed: https://example.com/rss.xml

Possible causes:
- Feed URL changed or moved
- Temporary network issue
- Feed no longer exists

Check feed URL in browser first
```

---

## Key Principles

1. **External sources** - Gathers information from outside your content
2. **Saved as markdown** - Research files in sources/research/, NOT in database
3. **Time-sensitive** - Use recency filters appropriately
4. **Composable** - Can be combined in workflows for systematic monitoring
