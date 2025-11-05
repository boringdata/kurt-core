# Mock Data for Kurt Eval Scenarios

This directory contains mock HTTP responses for testing Kurt agent behavior without network dependencies.

## Structure

```
mock/
├── websites/          # Mock website content
│   ├── acme-corp/    # Company website (blog, marketing)
│   ├── acme-docs/    # Documentation site
│   └── competitor-co/ # Competitor site for analysis
├── cms/              # CMS API responses
│   └── sanity/       # Sanity CMS mock data
├── research/         # External research API responses
│   ├── Perplexity AI responses
│   ├── Reddit API responses
│   └── Hacker News API responses
└── analytics/        # Analytics data
    └── Traffic metrics, trends, summaries
```

## Mock Companies

### ACME Corp (acme-corp.com)
**Industry:** B2B SaaS - Developer Tools
**Product:** API management platform for developers
**Voice:** Technical, approachable, conversational
**Audience:** Software engineers, DevOps, technical leads

**Content Mix:**
- Marketing pages (home, about, pricing)
- Technical blog posts
- Product announcements
- Developer-focused content

### ACME Docs (docs.acme-corp.com)
**Type:** Technical Documentation
**Voice:** Precise, concise, imperative
**Audience:** Developers integrating with ACME

**Content Mix:**
- Getting started tutorials
- API reference
- Authentication guides
- Troubleshooting docs
- Changelogs

### Competitor Co (competitor-co.com)
**Purpose:** Competitive analysis testing
**Content:** Similar product, different positioning

## Usage

Mock data is automatically loaded by `eval/mock_server.py` and patched into HTTP clients during scenario execution.

**URL Mapping:**
- `https://acme-corp.com/home` → `websites/acme-corp/home.md`
- `https://docs.acme-corp.com/getting-started` → `websites/acme-docs/getting-started.md`
- `https://api.sanity.io/...` → `cms/sanity/*.json`

## Content Guidelines

### Website Content (.md files)
- **Realistic length**: 800-2000 words for blog posts, 300-800 for pages
- **Consistent voice**: Match persona for each site
- **Metadata headers**: Include YAML frontmatter (title, date, author, etc.)
- **Rich formatting**: Use headings, code blocks, lists, links
- **Variety**: Mix technical, marketing, tutorial content

### CMS Data (.json files)
- **Match Sanity schema**: Use real Sanity document structure
- **Portable text**: Content in Sanity's portable text format
- **Metadata**: Include _id, _type, slug, timestamps
- **Relationships**: Reference other documents where appropriate

### Research Data (.json files)
- **Match API responses**: Use actual API response structure
- **Realistic content**: Real-looking discussions, questions, answers
- **Timestamps**: Recent dates for relevance
- **Scores/votes**: Realistic engagement metrics

### Analytics Data (.json files)
- **Pageview ranges**: 0-50K pageviews (realistic for docs)
- **Trends**: Mix of growing, stable, declining
- **Timestamps**: Historical data for trend calculations
- **URL patterns**: Match website structure

## Adding New Mock Data

1. Create file in appropriate directory
2. Follow naming convention: `kebab-case.md` or `.json`
3. Include realistic metadata
4. Update `mock_server.py` URL mappings if needed
5. Document in this README

## Testing Mock Data

```bash
# Test that mock data is loaded correctly
uv run python -c "from eval.mock_server import MockHTTPServer; from pathlib import Path; server = MockHTTPServer(Path('eval/mock')); server.load_mocks(); print(f'Loaded {len(server.url_mappings)} URL mappings')"
```

## Content Pieces Status

### Websites (20/20) ✅
- [x] acme-corp/home.md
- [x] acme-corp/about.md
- [x] acme-corp/pricing.md
- [x] acme-corp/blog-post-1.md (How to Build Scalable APIs)
- [x] acme-corp/blog-post-2.md (Product Launch)
- [x] acme-corp/blog-post-3.md (10 Tips for DX)
- [x] acme-corp/sitemap.xml
- [x] acme-docs/getting-started.md
- [x] acme-docs/api-reference.md
- [x] acme-docs/guide-authentication.md
- [x] acme-docs/guide-advanced.md
- [x] acme-docs/troubleshooting.md
- [x] acme-docs/changelog.md
- [x] acme-docs/sitemap.xml
- [x] competitor-co/feature-comparison.md
- [x] competitor-co/pricing.md
- [x] competitor-co/tutorial-basics.md
- [x] competitor-co/tutorial-advanced.md
- [x] competitor-co/case-study.md
- [x] competitor-co/sitemap.xml

### CMS (5/5) ✅
- [x] sanity/types.json
- [x] sanity/article-1.json
- [x] sanity/article-2.json
- [x] sanity/query-results.json
- [x] sanity/publish-response.json

### Research (5/5) ✅
- [x] perplexity-ai-trends.json
- [x] perplexity-fastapi.json
- [x] reddit-dataeng.json
- [x] reddit-python.json
- [x] hackernews-top.json

### Analytics (5/5) ✅
- [x] top-pages.json
- [x] bottom-pages.json
- [x] trending-pages.json
- [x] declining-pages.json
- [x] domain-summary.json

**Total: 35/35 mock files created** ✅

---

*Mock data enables fast, reproducible, cost-free eval scenarios while testing realistic agent behavior.*
