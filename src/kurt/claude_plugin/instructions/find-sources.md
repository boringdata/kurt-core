# FIND-SOURCES.md

## When to use this instruction
Discovering and retrieving existing content from Kurt's database.

Use this instruction when:
- User wants to find existing sources on a topic
- Need to discover related or prerequisite content
- Exploring what content exists before fetching new sources

---

## Discovery Methods

### 1. Semantic Search
Full-text search through fetched document content.

```bash
# Search all content
kurt content search "authentication"

# Filter by URL pattern
kurt content search "webhooks" --include "*/docs/*"

# Case-sensitive
kurt content search "OAuth" --case-sensitive
```

**Use when**: Finding documents by keyword, searching for specific concepts

**Requires**: ripgrep (`brew install ripgrep`)

---

### 2. Cluster-Based Discovery
Browse content organized by topic clusters.

```bash
# See all topic clusters
kurt content list-clusters

# List documents in a cluster
kurt content list --in-cluster "API Tutorials"

# Fetch all documents in a cluster
kurt content fetch --in-cluster "Getting Started" --priority 1
```

**Use when**: Exploring content by theme, large content collections

**Note**: Clusters created during mapping with `--cluster-urls` flag

---

### 3. Link-Based Discovery
Navigate document relationships through internal links.

```bash
# Show outbound links from a document
kurt content links <doc-id> --direction outbound

# Show inbound links to a document
kurt content links <doc-id> --direction inbound
```

**Use when**: Finding prerequisite reading, discovering related content, understanding dependencies

**How Claude interprets anchor text:**
- "Prerequisites", "Read this first", "Before you start" → prerequisite docs
- "See also", "Related", "Learn more about" → related content
- "Example", "Try this", "Sample" → example docs
- Other anchor text → general references

---

### 4. Direct Retrieval
Query documents by metadata, status, or properties.

```bash
# All documents
kurt content list

# Filter by URL pattern
kurt content list --url-contains "/docs/"
kurt content list --url-starts-with "https://example.com"

# Filter by status
kurt content list --with-status FETCHED
kurt content list --with-status NOT_FETCHED

# Filter by content type
kurt content list --with-content-type tutorial

# Filter by cluster
kurt content list --in-cluster "API Guides"

# Combine filters
kurt content list --with-status FETCHED --url-contains "/api/" --with-content-type reference

# Get specific document
kurt content get <doc-id>

# Content statistics
kurt content stats
kurt content stats --include "*docs.example.com*"
```

**Use when**: Need specific filtering by URL, status, type, or analytics

---

## Which Method to Use?

**I know the exact topic/keyword** → Semantic Search
- Example: "Find all docs mentioning webhooks"

**I want to explore by theme** → Cluster-Based Discovery
- Example: "Show me all tutorial content"

**I have a document and want related ones** → Link-Based Discovery
- Example: "Show me links from this doc" → Check anchor text for relationships

**I need specific filtering** → Direct Retrieval
- Example: "Show all FETCHED docs from /docs/ that are tutorials"
