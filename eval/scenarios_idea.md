# Kurt Eval Scenarios - Comprehensive Plan

## Overview

This document outlines a comprehensive evaluation strategy for Kurt agent with **20 condensed scenarios** that test all skills, commands, and user workflows using **mock data** to avoid network dependencies.

---

## Mock Data Strategy

### Why Mock Data?

1. **Speed**: No network I/O, scenarios run 10-100x faster
2. **Reliability**: No external dependencies (APIs, websites, rate limits)
3. **Reproducibility**: Same data every run, consistent results
4. **Cost**: No API costs for Firecrawl, Perplexity, etc.
5. **Isolation**: True unit testing of agent behavior

### Feasibility Analysis ✅

**Current Architecture:**
- Kurt uses `requests` and `httpx` for HTTP calls
- Main fetch points:
  - `src/kurt/content/map.py` - Content discovery (httpx)
  - `src/kurt/content/fetch.py` - Content fetching (Firecrawl/Trafilatura)
  - `src/kurt/cms/sanity/adapter.py` - CMS API (requests)
  - `src/kurt/research/perplexity/adapter.py` - AI research (requests)
  - `src/kurt/research/monitoring/reddit.py` - Reddit API (requests)
  - `src/kurt/research/monitoring/hackernews.py` - HN API (requests)

**Mocking Approach:**
- Use `responses` library (for requests) + `pytest-httpx` (for httpx)
- Create mock fixtures in `eval/mock/`
- Patch HTTP clients in workspace setup
- Return static content from `eval/mock/*.md` files

---

## Mock Data Structure

```
eval/
├── mock/
│   ├── README.md                    # Mock data documentation
│   ├── websites/
│   │   ├── acme-corp/
│   │   │   ├── home.md             # Company homepage
│   │   │   ├── about.md            # About page
│   │   │   ├── blog-post-1.md      # Blog article
│   │   │   ├── blog-post-2.md      # Blog article
│   │   │   └── sitemap.xml         # Sitemap for discovery
│   │   ├── acme-docs/
│   │   │   ├── getting-started.md  # Tutorial
│   │   │   ├── api-reference.md    # API docs
│   │   │   ├── guide-advanced.md   # Advanced guide
│   │   │   └── sitemap.xml
│   │   └── competitor-co/
│   │       ├── comparison.md       # For competitive analysis
│   │       └── sitemap.xml
│   ├── cms/
│   │   └── sanity/
│   │       ├── article-1.json      # CMS document
│   │       ├── article-2.json
│   │       ├── types.json          # Content types response
│   │       └── query-results.json  # Search results
│   ├── research/
│   │   ├── perplexity-ai-trends.json    # Perplexity response
│   │   ├── reddit-dataeng.json          # Reddit API response
│   │   └── hackernews-top.json          # HN API response
│   └── analytics/
│       ├── top-pages.json          # Analytics data
│       ├── declining-pages.json
│       └── domain-summary.json
├── mock_server.py               # HTTP mock implementation
└── scenarios_idea.md           # This file
```

---

## Content Pieces Needed

### 1. Company Website (acme-corp.com)

**Persona:** ACME Corp - B2B SaaS company selling developer tools

#### Files:
- `home.md` - Homepage with value proposition, product overview
- `about.md` - Company mission, team, values
- `pricing.md` - Pricing tiers, feature comparison
- `blog-post-1.md` - "How to Build Scalable APIs" (technical, 2000 words)
- `blog-post-2.md` - "ACME Product Launch Announcement" (marketing, 800 words)
- `blog-post-3.md` - "10 Tips for Developer Experience" (listicle, 1500 words)
- `sitemap.xml` - Sitemap with all pages

**Voice/Style:**
- Developer-focused, technical but approachable
- Conversational tone with personality
- Uses code examples, analogies
- First-person plural ("we", "our")

### 2. Documentation Site (docs.acme-corp.com)

**Persona:** Technical documentation for developers

#### Files:
- `getting-started.md` - Quickstart tutorial with code
- `api-reference.md` - REST API documentation
- `guide-authentication.md` - Auth guide with examples
- `guide-advanced.md` - Advanced patterns
- `troubleshooting.md` - Common issues and solutions
- `changelog.md` - Version history
- `sitemap.xml`

**Voice/Style:**
- Precise, concise, technical
- Imperative mood for instructions
- Heavy code samples
- Structured with clear headings

### 3. Competitor Site (competitor-co.com)

**Persona:** Competitor with similar product

#### Files:
- `feature-comparison.md` - Feature matrix
- `pricing.md` - Competitor pricing
- `tutorial-basics.md` - Basic tutorial
- `tutorial-advanced.md` - Advanced tutorial
- `case-study.md` - Customer success story
- `sitemap.xml`

**Purpose:** For competitive analysis scenarios (compare gaps, coverage, quality)

### 4. CMS Content (Sanity)

**Persona:** Sanity CMS with articles

#### Files:
- `types.json` - Content type definitions
```json
{
  "types": [
    {"name": "article", "title": "Article"},
    {"name": "tutorial", "title": "Tutorial"},
    {"name": "guide", "title": "Guide"}
  ]
}
```

- `article-1.json` - CMS document
```json
{
  "_id": "article-001",
  "_type": "article",
  "title": "Getting Started with ACME",
  "slug": {"current": "getting-started"},
  "content": "..."
}
```

- `query-results.json` - Search results
- `publish-response.json` - Publish API response

### 5. Research Sources

#### Perplexity AI:
- `perplexity-ai-trends.json` - AI trends research response
- `perplexity-fastapi.json` - FastAPI integration research

#### Reddit:
- `reddit-dataeng.json` - r/dataengineering top posts
- `reddit-python.json` - r/python discussions

#### Hacker News:
- `hackernews-top.json` - Top stories

### 6. Analytics Data

#### Files:
- `top-pages.json` - Top 20 pages by traffic
- `bottom-pages.json` - Low/zero traffic pages
- `trending-pages.json` - Pages with increasing traffic
- `declining-pages.json` - Pages losing traffic (with historical data)
- `domain-summary.json` - Overall domain stats

**Data Structure:**
```json
{
  "pages": [
    {
      "url": "https://docs.acme-corp.com/getting-started",
      "pageviews": 15000,
      "trend": "declining",
      "change_percent": -25.5,
      "last_updated": "2024-06-15"
    }
  ]
}
```

---

## 20 Condensed Scenarios

### **Core User Journeys (10 scenarios)**

#### **S07: Complete Onboarding Flow**
- **Mock Data Used:**
  - `acme-corp/sitemap.xml` - Content discovery
  - `acme-corp/blog-post-*.md` - Rule extraction sources
  - `acme-docs/sitemap.xml` - Docs discovery
- **Tests:** `/create-profile`, questionnaire, content mapping, foundation rule extraction
- **Checks:** Profile created, content indexed, publisher + style + persona rules extracted

#### **S08: Create Simple Project**
- **Status:** ✅ Exists as `03_project_no_sources`
- **Mock Data:** None needed (no external sources)

#### **S09: Create Project with Mixed Sources**
- **Mock Data Used:**
  - `acme-docs/` - Web content
  - `research/perplexity-fastapi.json` - Research
  - Local files (created in setup_commands)
- **Tests:** Project creation + web + local + research sources
- **Checks:** All source types indexed, project.md references all

#### **S10: Content Creation End-to-End**
- **Mock Data Used:**
  - Pre-fetched sources from setup_commands
  - `acme-corp/` content for style rules
- **Tests:** Project → outline → draft → feedback → edit
- **Checks:** Full workflow, lineage tracking, rule application

#### **S11: Resume Project & Continue Work**
- **Mock Data Used:**
  - Pre-created project from setup_commands
  - `acme-docs/getting-started.md` - Missing source to detect
- **Tests:** Create → interrupt → resume → detect gaps
- **Checks:** State persistence, gap detection, recommendations

#### **S12: Clone Template & Customize**
- **Mock Data Used:**
  - `analytics/declining-pages.json` - For audit workflow
  - `acme-docs/` - Content to analyze
- **Tests:** `/clone-project documentation-audit` → execute audit
- **Checks:** Template loading, intelligence operations

#### **S13: Analytics-Driven Content Update**
- **Mock Data Used:**
  - `analytics/declining-pages.json` - Identify problem pages
  - `analytics/top-pages.json` - Context
  - `acme-docs/getting-started.md` - Existing content to update
- **Tests:** Intelligence (declining, audit) → create project → update content
- **Checks:** Analytics → intelligence → project → content flow

#### **S14: Rule Extraction & Evolution**
- **Mock Data Used:**
  - `acme-corp/` - Blog posts for extraction
  - `acme-docs/` - Docs for extraction
  - Pre-populated feedback data
- **Tests:** Extract rules → create content → feedback → update rules
- **Checks:** All extraction types, feedback patterns, rule updates

#### **S15: CMS Integration Workflow**
- **Mock Data Used:**
  - `cms/sanity/types.json` - CMS config
  - `cms/sanity/article-*.json` - CMS documents
  - `cms/sanity/query-results.json` - Search
- **Tests:** CMS onboard → map → fetch → reference → publish
- **Checks:** Full CMS workflow end-to-end

#### **S16: Research & Competitive Analysis**
- **Mock Data Used:**
  - `research/perplexity-ai-trends.json`
  - `research/reddit-dataeng.json`
  - `competitor-co/` - Competitor content
  - `acme-docs/` - Own content
- **Tests:** Research (search, reddit) → compare-gaps → create project
- **Checks:** Research + content-intelligence operations

---

### **Edge Cases & Error Handling (5 scenarios)**

#### **S17: Missing Onboarding Detection**
- **Mock Data:** None (tests error path)
- **Tests:** `/create-project` without profile
- **Checks:** Detection, guidance, setup assistance

#### **S18: Insufficient Content for Rules**
- **Mock Data:** Only 1 document in `acme-corp/home.md`
- **Tests:** Extract rules with minimal content
- **Checks:** Warning shown, quality control

#### **S19: Network Failure Recovery**
- **Mock Data:** Simulated failures in mock server
- **Tests:** Fetch fails mid-process
- **Checks:** Partial progress saved, retry offered

#### **S20: Invalid Inputs**
- **Mock Data:** None (tests validation)
- **Tests:** Bad project names, invalid CMS creds, circular deps
- **Checks:** Error messages, no crashes

#### **S21: Resume After Multiple Interruptions**
- **Mock Data:** Pre-created project states
- **Tests:** Create → interrupt → resume (multiple cycles)
- **Checks:** State persistence across sessions

---

### **Performance & Scalability (3 scenarios)**

#### **S22: Large Content Mapping**
- **Mock Data Used:**
  - `acme-docs/sitemap.xml` - 5000 URLs listed
  - Select 100 docs actually fetched
- **Tests:** Map 5000+ URLs → cluster → selective fetch
- **Checks:** Batch operations, reasonable time

#### **S23: Complex Project with Many Rules**
- **Mock Data Used:**
  - 20+ rule files from setup_commands
  - Multiple styles, structures, personas
- **Tests:** Work with extensive rules
- **Checks:** Rule loading efficient, context management

#### **S24: Long-Form Content Generation**
- **Mock Data Used:**
  - Multiple source documents
  - Comprehensive outline
- **Tests:** Generate 5000-word guide
- **Checks:** Completes without timeout, quality maintained

---

### **Advanced Workflows (2 scenarios)**

#### **S25: Multi-Project Coordination**
- **Mock Data Used:**
  - Shared rules from setup_commands
  - Sources referenced across projects
- **Tests:** 3 related projects (blog, docs, landing)
- **Checks:** Shared rules work, no conflicts

#### **S26: Custom Rule Type Lifecycle**
- **Mock Data Used:**
  - Content for custom extraction
- **Tests:** Add custom type → extract → apply → feedback → update
- **Checks:** Extensibility, full lifecycle

---

## Mock Server Implementation

### Architecture

```python
# eval/mock_server.py

import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch
import responses
from pytest_httpx import HTTPXMock

class MockHTTPServer:
    """Provides mock HTTP responses for eval scenarios."""

    def __init__(self, mock_dir: Path):
        self.mock_dir = mock_dir
        self.url_mappings = {}

    def load_mocks(self):
        """Load all mock files into memory."""
        # Load website mocks
        self._load_website_mocks()
        # Load CMS mocks
        self._load_cms_mocks()
        # Load research mocks
        self._load_research_mocks()
        # Load analytics mocks
        self._load_analytics_mocks()

    def _load_website_mocks(self):
        """Map URLs to markdown files."""
        # https://acme-corp.com/home -> mock/websites/acme-corp/home.md
        # https://docs.acme-corp.com/getting-started -> mock/websites/acme-docs/getting-started.md

    def get_mock_response(self, url: str) -> Dict[str, Any]:
        """Get mock response for a URL."""
        # Map URL to mock file
        # Return content with appropriate headers

    def patch_http_clients(self):
        """Patch requests and httpx to use mocks."""
        # Use responses library for requests
        # Use pytest-httpx for httpx
        pass
```

### Integration with Workspace

```python
# eval/framework/workspace.py (modification)

class IsolatedWorkspace:
    def __init__(self, ..., use_mocks: bool = True):
        self.use_mocks = use_mocks
        self.mock_server = None

    def setup(self):
        # ... existing setup ...

        if self.use_mocks:
            from eval.mock_server import MockHTTPServer
            mock_dir = Path(__file__).parent.parent / "mock"
            self.mock_server = MockHTTPServer(mock_dir)
            self.mock_server.load_mocks()
            self.mock_server.patch_http_clients()
```

---

## Implementation Plan

### Phase 1: Mock Infrastructure ✅
1. ✅ Feasibility analysis (DONE)
2. ⏳ Create `eval/mock/` directory structure
3. ⏳ Implement `MockHTTPServer` in `eval/mock_server.py`
4. ⏳ Add `responses` and `pytest-httpx` to dependencies
5. ⏳ Integrate with `IsolatedWorkspace`

### Phase 2: Mock Content Creation
1. Create company website content (acme-corp)
2. Create documentation content (acme-docs)
3. Create competitor content (competitor-co)
4. Create CMS mock data (Sanity)
5. Create research mock data (Perplexity, Reddit, HN)
6. Create analytics mock data

### Phase 3: Scenario Implementation
1. Implement S07-S16 (core journeys)
2. Implement S17-S21 (edge cases)
3. Implement S22-S24 (performance)
4. Implement S25-S26 (advanced)

### Phase 4: Validation & Refinement
1. Run all scenarios
2. Measure coverage (skills, commands, subskills)
3. Refine mock data based on failures
4. Document patterns and best practices

---

## Benefits Summary

### With Mock Data:
- ⚡ **10-100x faster** execution (no network I/O)
- 🎯 **100% reproducible** (same data every time)
- 💰 **Zero API costs** (no Firecrawl, Perplexity, etc.)
- 🔒 **Isolated** (no external dependencies)
- 🧪 **True unit tests** (test agent behavior, not APIs)
- 📊 **Comprehensive coverage** (can test edge cases easily)

### Tradeoffs:
- ⚠️ **Initial setup time** (creating realistic mock data)
- ⚠️ **Maintenance** (mock data may need updates)
- ⚠️ **Realism** (mocks may not capture all API behaviors)

**Recommendation:** Use mocks for 95% of scenarios, keep 2-3 "smoke test" scenarios that hit real APIs to validate integration.

---

## Next Steps

1. ✅ **Review this plan** - Confirm approach and scope
2. ⏳ **Create mock infrastructure** - Implement `MockHTTPServer`
3. ⏳ **Generate mock content** - Create realistic company/docs content
4. ⏳ **Implement scenarios** - Build out 20 scenarios in `scenarios.yaml`
5. ⏳ **Run & iterate** - Test, measure coverage, refine

---

*This plan ensures comprehensive coverage of all Kurt features while maintaining fast, reliable, and cost-effective eval scenarios.*
