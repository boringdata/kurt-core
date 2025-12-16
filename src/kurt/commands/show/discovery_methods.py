"""Show source discovery methods instructions."""

import click


@click.command()
def discovery_methods_cmd():
    """Show detailed methods for discovering and retrieving existing content."""
    content = """
═══════════════════════════════════════════════════════════════════
DISCOVERY METHODS
═══════════════════════════════════════════════════════════════════

WHEN TO USE THESE METHODS
─────────────────────────────────────────────────────────────────
Discovering and retrieving existing content from Kurt's database.

Use when:
  • User wants to find existing sources on a topic
  • Need to discover related or prerequisite content
  • Exploring what content exists before fetching new sources

⚠️  IMPORTANT: Core Principles
  • Tool usage: Must use kurt CLI (never grep/filesystem operations)
  • Iterative gathering: Try 3-5 query variants, combine methods,
    fan out to related topics
  • plan.md updates: Update after every action (single source of truth)

═══════════════════════════════════════════════════════════════════
METHOD 1: TOPIC/TECHNOLOGY DISCOVERY
═══════════════════════════════════════════════════════════════════

See what topics and technologies exist across indexed content,
identify coverage gaps.

COMMANDS:
kurt content list-entities topic               # All topics with counts
kurt content list-entities topic --min-docs 5  # Common topics (5+ docs)
kurt content list-entities technology          # All technologies

# Filter to specific sections
kurt content list-entities topic --include "*/docs/*"
kurt content list-entities technology --include "*/docs/*"

# JSON output for programmatic use
kurt content list-entities topic --format json

WHEN TO USE:
  • Understanding what topics/tech are covered
  • Identifying content gaps
  • Planning what to fetch

WORKFLOW EXAMPLE:
  1. Run: kurt content list-entities topic
     → See: "authentication" (15 docs), "webhooks" (3 docs)
  2. Notice "webhooks" has low coverage
  3. Run: kurt content list --with-entity "Topic:webhooks"
     → See which 3 docs exist
  4. Identify need for more webhook content
     → Fetch additional webhook guides

═══════════════════════════════════════════════════════════════════
METHOD 2: SEMANTIC SEARCH
═══════════════════════════════════════════════════════════════════

Full-text search through fetched document content.

COMMANDS:
kurt content search "authentication"                # Search all content
kurt content search "webhooks" --include "*/docs/*" # Filter by URL
kurt content search "OAuth" --case-sensitive        # Case-sensitive

WHEN TO USE:
  • Finding documents by keyword
  • Searching for specific concepts

REQUIRES: ripgrep (`brew install ripgrep`)

═══════════════════════════════════════════════════════════════════
METHOD 3: CLUSTER-BASED DISCOVERY
═══════════════════════════════════════════════════════════════════

Browse content organized by topic clusters.

COMMANDS:
kurt content list-clusters                     # See all topic clusters
kurt content list --in-cluster "API Tutorials" # List docs in cluster
kurt content fetch --in-cluster "Getting Started" --priority 1

WHEN TO USE:
  • Exploring content by theme
  • Large content collections

NOTE: Clusters created during mapping with --cluster-urls flag

═══════════════════════════════════════════════════════════════════
METHOD 4: LINK-BASED DISCOVERY
═══════════════════════════════════════════════════════════════════

Navigate document relationships through internal links.

COMMANDS:
kurt content links <doc-id> --direction outbound  # Show outbound links
kurt content links <doc-id> --direction inbound   # Show inbound links

WHEN TO USE:
  • Finding prerequisite reading
  • Discovering related content
  • Understanding dependencies

HOW ANCHOR TEXT IS INTERPRETED:
  • "Prerequisites", "Read this first", "Before you start"
    → prerequisite docs
  • "See also", "Related", "Learn more about"
    → related content
  • "Example", "Try this", "Sample"
    → example docs
  • Other anchor text → general references

═══════════════════════════════════════════════════════════════════
METHOD 5: KNOWLEDGE GRAPH SEARCH
═══════════════════════════════════════════════════════════════════

Filter by entities (topics, technologies, companies) and relationships
extracted during indexing.

ENTITY FILTERING:
kurt content list --with-entity "Python"                    # Any type
kurt content list --with-entity "authentication"            # Any type
kurt content list --with-entity "Topic:authentication"      # Specific type
kurt content list --with-entity "Technology:Docker"
kurt content list --with-entity "Company:Google"
kurt content list --with-entity "Product:FastAPI"

RELATIONSHIP FILTERING:
kurt content list --with-relationship integrates_with
kurt content list --with-relationship depends_on
kurt content list --with-relationship "integrates_with:FastAPI"
kurt content list --with-relationship "depends_on::Python"
kurt content list --with-relationship "integrates_with:FastAPI:Pydantic"

COMBINE FILTERS:
kurt content list --with-content-type tutorial --with-entity "Technology:React"
kurt content list --with-entity "Topic:deployment" --with-entity "Technology:Kubernetes"

VIEW METADATA:
kurt content get <doc-id>  # Shows entities, relationships, content type

WHEN TO USE:
  • Filtering by extracted entities, relationships, or content type

NOTE: Requires running `kurt content index` first to extract metadata.

AVAILABLE FILTERS:
  --with-entity
    Format: "Name" (all types) or "Type:Name" (specific type)
    Types: Topic, Technology, Product, Feature, Company, Integration

  --with-relationship
    Format: "Type", "Type:Source", "Type:Source:Target"
    Types: mentions, part_of, integrates_with, enables, related_to,
           depends_on, replaces

  --with-content-type
    Filter by: tutorial, guide, blog, reference, etc.

═══════════════════════════════════════════════════════════════════
METHOD 6: DIRECT RETRIEVAL
═══════════════════════════════════════════════════════════════════

Query documents by metadata, status, or properties.

COMMANDS:
kurt content list                                    # All documents
kurt content list --include "*/docs/*"               # Filter by URL
kurt content list --include "https://example.com*"
kurt content list --with-status FETCHED              # Filter by status
kurt content list --with-status NOT_FETCHED
kurt content list --with-content-type tutorial       # Filter by type
kurt content list --in-cluster "API Guides"          # Filter by cluster

# Combine filters
kurt content list --with-status FETCHED --include "*/api/*" --with-content-type reference

# Get specific document
kurt content get <doc-id>

# Content statistics
kurt content stats
kurt content stats --include "*docs.example.com*"

WHEN TO USE:
  • Need specific filtering by URL, status, type, or analytics

═══════════════════════════════════════════════════════════════════
WHICH METHOD TO USE?
═══════════════════════════════════════════════════════════════════

I WANT TO UNDERSTAND WHAT TOPICS/TECH ARE COVERED:
  → Topic/Technology Discovery
  Example: "What topics do we have content about?"
  → kurt content list-entities topic

I KNOW THE EXACT TOPIC/KEYWORD:
  → Semantic Search
  Example: "Find all docs mentioning webhooks"
  → kurt content search "webhooks"

I WANT DOCS ABOUT A SPECIFIC ENTITY OR RELATIONSHIP:
  → Knowledge Graph Search
  Example: "Show me all Python tutorials"
  → kurt content list --with-content-type tutorial --with-entity "Technology:Python"

I WANT TO EXPLORE BY THEME:
  → Cluster-Based Discovery
  Example: "Show me all tutorial content"
  → kurt content list-clusters

I HAVE A DOCUMENT AND WANT RELATED ONES:
  → Link-Based Discovery
  Example: "Show me links from this doc"
  → Check anchor text for relationships

I NEED SPECIFIC FILTERING:
  → Direct Retrieval
  Example: "Show all FETCHED docs from /docs/ that are tutorials"
  → kurt content list --with-status FETCHED --include "*/docs/*" --with-content-type tutorial

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())
