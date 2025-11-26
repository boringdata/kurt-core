"""Show source ingestion workflow instructions."""

import click


@click.command()
def source_workflow_cmd():
    """Show instructions for adding sources (URLs, CMS, pasted content)."""
    content = """
═══════════════════════════════════════════════════════════════════
SOURCE WORKFLOW
═══════════════════════════════════════════════════════════════════

WHEN TO USE THIS WORKFLOW
─────────────────────────────────────────────────────────────────
User shares URL, CMS content, or pastes text → Ingest for use in
writing projects.

All operations return status + file paths created.

═══════════════════════════════════════════════════════════════════
SOURCE TYPE DETECTION & ROUTING
═══════════════════════════════════════════════════════════════════

Detect source type using these signals, then route to workflow:

1. CMS CONTENT
   URL Patterns: *.sanity.studio/*, app.contentful.com/*, */wp-admin/*
   Natural Language: "from my CMS", "in Sanity", "our Contentful"
   → Follow CMS Workflow

2. SINGLE WEB PAGE
   URL Patterns: Specific page URL beyond homepage
                 (e.g., /blog/article-name, /docs/guide-name)
   Natural Language: "this article", "this page", "this guide"
   → Follow Single Page Workflow

3. FULL WEBSITE/DOMAIN
   URL Patterns: Homepage or subdomain root (ends with / or domain only)
   Natural Language: "their docs", "competitor site", "the website"
   → Follow Full Site Workflow

4. PASTED CONTENT
   Pattern: Multi-line text blob (>100 chars, no URL)
   Detection: User pastes markdown, code, or text directly
   → Follow Pasted Content Workflow

═══════════════════════════════════════════════════════════════════
CMS WORKFLOW
═══════════════════════════════════════════════════════════════════

STEP 1: Check Configuration
─────────────────────────────────────────────────────────────────

Run: kurt integrations cms status

  NOT CONFIGURED:
    ASK USER: "I see you're using {platform}. Set it up now?
               Takes 2 minutes."
    If yes: kurt integrations cms onboard --platform {platform}
    If no: Stop here

  CONFIGURED:
    Continue to Step 2

STEP 2: Determine Scope & Execute
─────────────────────────────────────────────────────────────────

A. SINGLE DOCUMENT (specific CMS URL or document name)

User shared specific document → fetch immediately:

kurt integrations cms search --platform {platform} --query "{doc_name}"
kurt content map cms --platform {platform} --instance {instance}
kurt content fetch --with-status NOT_FETCHED --priority 1

Result: "Fetched '{title}' from {platform}. Ready to use."

B. SEARCH & SELECT (user describes content, doesn't know exact doc)

User describes what they need → search and let them pick:

kurt integrations cms search --platform {platform} --query "{user_description}"

ASK USER: Show results, they select which ones

kurt content fetch --url {selected_urls} --priority 1

C. BULK IMPORT (user wants "all articles", entire content type, or full CMS)

User wants large import → map WITH clustering, fetch in background:

kurt content map cms --platform {platform} --instance {instance} \\
  --content-type {type} --cluster-urls

kurt content fetch --in-cluster "{relevant_cluster}" --priority 5 --background

Tell user: "Mapped {count} {content_type} documents and created
{cluster_count} topic clusters. Fetching {relevant_cluster} in
background for your {project_goal}."

WHY cluster CMS content?
  • Groups articles by topic automatically
  • Enables fetching by theme instead of guessing URL patterns
  • Project-aware: Fetch relevant clusters, skip irrelevant ones

STEP 3: Keeping CMS Content Up to Date
─────────────────────────────────────────────────────────────────

WHEN TO UPDATE:
  • Before starting a new project - ensure latest content
  • User asks - "check for new content", "update from CMS"
  • Regular intervals - monthly for active content sources

HOW TO DISCOVER NEW CONTENT:

kurt content map cms --platform {platform} --instance {instance}

How it works:
  • Checks CMS for all documents
  • Only creates records for NEW documents not in database
  • Existing documents skipped (checks by source_url)
  • Returns count of new vs. existing documents

AFTER DISCOVERING NEW CONTENT:
Apply same logic from Step 2 based on count:
  • 1-5 new docs → Single Document (Step 2A): Fetch immediately
  • 6-50 new docs → Search & Select (Step 2B): Show list, user selects
  • >50 new docs → Bulk Import (Step 2C): Cluster + background fetch

INCREMENTAL VS. FULL REFRESH:

Incremental (Default - Recommended):
kurt content fetch --with-status NOT_FETCHED
kurt content fetch --with-status ERROR  # Retry failed

Full Refresh (Use Sparingly):
kurt content fetch --include "sanity/prod/*" --refetch

⚠️  Full refresh with --refetch will:
  • Re-download ALL documents (even unchanged)
  • Re-run metadata extraction for changed content
  • Take significantly longer
  • Use more LLM API credits

WHEN to use --refetch:
  • Major CMS content updates (rewrote 50% of articles)
  • Changed content structure or format
  • Debugging content issues
  • NOT for routine updates (use incremental)

═══════════════════════════════════════════════════════════════════
SINGLE PAGE WORKFLOW
═══════════════════════════════════════════════════════════════════

User shared specific page URL → fetch immediately (fast operation):

kurt content fetch --url {url} --priority 1

Result - Show summary immediately:
  • "Fetched: {title}"
  • "Type: {content_type}, {word_count} words"
  • If in project: "Added to project sources."

No verification needed - synchronous operation, result is immediate.

═══════════════════════════════════════════════════════════════════
FULL SITE WORKFLOW
═══════════════════════════════════════════════════════════════════

STEP 1: Quick Size Estimate
─────────────────────────────────────────────────────────────────

Run dry-run to check size (fast, doesn't save):

kurt content map url {homepage_url} --dry-run

STEP 2: Smart Execution Based on Size
─────────────────────────────────────────────────────────────────

SMALL SITE (<50 pages):
Map + fetch inline (fast enough):

kurt content map url {homepage_url}
kurt content fetch --with-status NOT_FETCHED --priority 1

Tell user: "Mapped and fetched 30 pages from {domain}."

MEDIUM SITE (50-200 pages):
Map inline, fetch selectively in background:

kurt content map url {homepage_url}
kurt content fetch --include "{relevant_sections}" --background --priority 5

Tell user: "Mapped {count} pages from {domain}. Fetching
{relevant_sections} in background for your {project_goal}."

LARGE SITE (>200 pages):
Map inline WITH clustering, fetch in background:

kurt content map url {homepage_url} --cluster-urls
kurt content fetch --in-cluster "{cluster_name}" --background --priority 10

Tell user: "Mapping {domain}... Found {count} pages and created
{cluster_count} topic clusters. Fetching {relevant_cluster} in
background for your {project_goal}. Let's continue."

WHY cluster during map?
  • Organizes content immediately for intelligent fetching
  • Clusters based on URL patterns, titles, descriptions
  • Enables cluster-based source discovery later

STEP 3: Project-Aware Section Selection
─────────────────────────────────────────────────────────────────

If in project context, intelligently determine which sections to fetch:

TUTORIAL/GUIDE PROJECT:
  Fetch: /docs/*, /guides/*, /tutorials/*, /learn/*
  Skip: /blog/*, /about/*, /pricing/*, /legal/*

PRODUCT PAGE PROJECT:
  Fetch: homepage, /product/*, /features/*, /solutions/*, /integrations/*
  Skip: /blog/*, /support/*, /docs/*, /careers/*

BLOG/THOUGHT LEADERSHIP PROJECT:
  Fetch: /blog/* (filter by keywords related to project topic)
  Skip: /docs/*, /product/*, /support/*

COMPETITIVE ANALYSIS PROJECT:
  Fetch: homepage, 2-3 key product/feature pages (not entire site)
  Skip: blog archives, full documentation

NO PROJECT CONTEXT:
  ASK USER: "Found {count} pages on {domain}. Which sections should
             I fetch now?"
  Show detected sections: "/docs/ (50 pages), /blog/ (120 pages)"
  User picks sections, or "all", or "just map for now"

STEP 4: Keeping Site Content Up to Date
─────────────────────────────────────────────────────────────────

WHEN TO UPDATE:
  • Before starting new project - ensure latest content
  • User asks - "check for new pages", "refresh sitemap"
  • Regular intervals - monthly for active content sources
  • After major site updates or launches

HOW TO DISCOVER NEW PAGES:

kurt content map url {homepage_or_sitemap_url}

How it works:
  • Re-crawls sitemap or website
  • Only creates records for NEW URLs not in database
  • Existing URLs skipped (checks by source_url)
  • Returns count of new vs. existing pages

AFTER DISCOVERING NEW PAGES:
  1. Run dry-run: kurt content map url {url} --dry-run
  2. Apply same logic from Step 2 based on total size
  3. Selective fetch for new pages only:
     kurt content fetch --with-status NOT_FETCHED

═══════════════════════════════════════════════════════════════════
PASTED CONTENT WORKFLOW
═══════════════════════════════════════════════════════════════════

User pasted text blob → save and index immediately

STEP 1: Detect Format
  • Markdown with YAML frontmatter → .md
  • Plain markdown (headings, lists) → .md
  • Code (detect language from syntax) → .{language}
  • Plain text → .txt

STEP 2: Save to Project Sources

Determine path:
  • In project: /projects/{project-name}/sources/{descriptive-name}.{ext}
  • Not in project: /sources/{descriptive-name}.{ext}

Infer descriptive name from:
  • Frontmatter title (if present)
  • First heading (if markdown)
  • First line (if plain text, cleaned up)

STEP 3: Index Immediately

kurt content fetch --file {filepath} --priority 1

STEP 4: Confirm

"Saved as `{filepath}` and indexed. Ready to use for your {document_type}."

═══════════════════════════════════════════════════════════════════
PRIORITY ASSIGNMENT (AUTOMATIC)
═══════════════════════════════════════════════════════════════════

⚠️  IMPORTANT: Never ask user about priority or background mode.
Infer automatically from context:

PRIORITY 1 (Immediate - Run Inline):
  • Single pages user explicitly shared
  • CMS docs user mentioned by name
  • Pasted content
  • Small sites (<50 pages)
  • Any source user is actively waiting for

PRIORITY 5 (Background - Medium):
  • Medium sites (50-200 pages)
  • CMS bulk imports (specific content type)
  • Related research materials
  • Competitor site analysis

PRIORITY 10 (Background - Low):
  • Large sites (>200 pages) after mapping
  • Full CMS imports (all content types) after mapping
  • Reference materials during profile setup
  • Exploratory/future research

⚠️  Mapping always runs inline (foreground) so we know what
sections/content exists before deciding what to fetch.

═══════════════════════════════════════════════════════════════════
RESULT HANDLING
═══════════════════════════════════════════════════════════════════

INLINE OPERATIONS (Priority 1):
Show immediate result:
  ✓ Fetched: "Getting Started with Stripe"
    Type: Tutorial, 2,400 words
    Added to project sources.

Continue conversation immediately - no verification step needed.

BACKGROUND OPERATIONS (Priority 5+):
Acknowledge start, don't block:
  Mapping docs.stripe.com in background (est. 5 min)...
  [Continue conversation while it runs]

When complete (if user still in session):
  ✓ Finished mapping docs.stripe.com - 180 pages indexed.
    Fetched /docs/* and /guides/* for your API integration tutorial.

PROJECT CONTEXT UPDATES:
If in project, silently update plan.md with:
  • New sources added
  • Relevant page counts
  • Status: mapped, fetched, ready to use

Show summary: "Project now has {count} sources ({relevant_count}
directly relevant to {goal})."

═══════════════════════════════════════════════════════════════════
CONTENT INDEXING
═══════════════════════════════════════════════════════════════════

After fetching content, Kurt extracts metadata (topics, technologies,
content type, structural features) for better discovery.

WHEN TO INDEX:
  • Automatically indexed during fetch (most content)
  • Manual indexing: After bulk fetches or to re-index

MANUAL INDEXING COMMANDS:
kurt content index --all              # Index all fetched content
kurt content index <doc-id>           # Index specific document
kurt content index --include "*/docs/*"  # Index by URL pattern

WHAT GETS EXTRACTED:
  • Content Type: tutorial, guide, blog, reference, product_page
  • Topics: Primary topics covered (e.g., "authentication", "API design")
  • Technologies: Tools/languages mentioned (e.g., "Python", "Docker")
  • Structure: Code examples, step-by-step procedures, narrative

USING INDEXED METADATA:
kurt content list --with-content-type tutorial --with-entity "Technology:Python"
kurt content list --with-entity "Topic:authentication"
kurt content get <doc-id>  # View indexed metadata

For complete discovery methods: kurt show discovery-methods

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())
