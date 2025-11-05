# Extract Style Subskill

**Purpose:** Extract writing voice, tone, and style patterns from existing content
**Parent Skill:** writing-rules-skill
**Output:** Style guides in `rules/style/`

---

## Context Received from Parent Skill

The parent skill provides:
- `$PROJECT_NAME` - Project name (if in project context)
- `$PROJECT_PATH` - Full path to project directory (if applicable)
- `$PROJECT_BRIEF` - Path to project.md (if applicable)
- `$RULES_STYLE_DIR` - `rules/style/`
- `$EXISTING_RULES` - List of existing style guides
- `$SOURCES_STATUS` - fetched status (fetch includes indexing)
- `$ARGUMENTS` - Subskill arguments

---

## Prerequisites Check

Content must be **fetched** before extraction (fetching automatically includes metadata indexing).

**If $SOURCES_STATUS indicates not ready:**
```
⚠️ Content not ready for style extraction

Sources must be fetched (downloaded + indexed automatically).

Current status: <status>

Required action:
  kurt fetch --include <url>

Once complete, retry: writing-rules-skill style ...
```

If sources ready, proceed to Step 1.

---

## Step 1: Parse Subskill Arguments

Arguments received: $ARGUMENTS

**Expected arguments:**
- `--type <type>` - Style type to extract (corporate, technical-docs, blog, author, etc.)
- `--auto-discover` - Automatically discover relevant content
- `--author-name "<name>"` - For author-specific style extraction
- `with documents: <file-paths>` - Manual document selection
- `--overwrite` - Replace all existing styles (nuclear option)
- `--include <path>` - Add specific document to auto-discovery
- `--exclude <pattern>` - Exclude documents from auto-discovery

**Parse flags:**
- Extraction type (corporate, technical-docs, blog, author)
- Auto-discovery mode (true/false)
- Author name (if type=author)
- Manual document list (if provided)
- Overwrite mode (true/false)
- Include/exclude patterns

---

## Step 2: Determine Discovery Mode

**Option A: Auto-discover mode** (`--auto-discover` flag present)
- Ask user to confirm auto-discovery: "Auto-discover content for <type> style or manual selection?"
- If confirmed, proceed to Step 3 (Auto-Discovery)

**Option B: Manual selection** (`with documents:` provided)
- Use provided document paths
- Proceed to Step 5 (Analyze Documents)

**Option C: Hybrid** (`--auto-discover` + `--include`/`--exclude`)
- Auto-discover content
- Add included documents
- Remove excluded documents
- Proceed to Step 5 (Analyze Documents)

**If no mode specified:**
- Ask user: "How would you like to select content?"
  - a) Auto-discover by style type
  - b) Manual document selection
  - c) Hybrid (auto-discover + manual refinement)

---

## Step 3: Auto-Discovery by Style Type

### Corporate Voice (Priority 1 - Recommended First)

**Purpose:** Extract brand voice from company marketing pages

**Discovery process:**
```bash
# Homepage (always include)
homepage=$(kurt content list --url-prefix https://company.com/ | grep -E "^https://[^/]+/?$")

# Product/Feature pages (marketing copy)
products=$(kurt content list --url-contains /product --status FETCHED | head -5)
features=$(kurt content list --url-contains /features --status FETCHED | head -3)
solutions=$(kurt content list --url-contains /solutions --status FETCHED | head -3)

# About/Company pages
about=$(kurt content list --url-contains /about --status FETCHED)
company=$(kurt content list --url-contains /company --status FETCHED)

# Landing pages (marketing campaigns)
landing=$(kurt content list --url-contains /landing --status FETCHED | head -3)
```

**Show proposed list:**
```
Found corporate/marketing pages for brand voice extraction:

✓ Homepage: https://company.com/
✓ 5 product pages
✓ 3 feature pages
✓ 2 about pages
✓ 3 landing pages

Total: 14 pages

Would you like to:
a) Use these pages (recommended)
b) Add/remove specific pages
c) Start over with manual selection
```

### Technical Documentation Voice (Priority 2)

**Purpose:** Extract writing style from technical content

**Discovery process:**
```bash
# Documentation pages
docs=$(kurt content list --url-contains /docs/ --status FETCHED | head -5)
documentation=$(kurt content list --url-contains /documentation --status FETCHED | head -3)

# Guides and tutorials
guides=$(kurt content list --url-contains /guide --status FETCHED | head -3)
tutorials=$(kurt content list --url-contains /tutorial --status FETCHED | head -3)

# Reference docs
reference=$(kurt content list --url-contains /reference --status FETCHED | head -3)

# Sample diverse doc types for comprehensive style (5-10 total)
```

**Show proposed list:**
```
Found technical documentation for style extraction:

✓ 5 documentation pages
✓ 3 guides
✓ 3 tutorials
✓ 2 reference pages

Total: 13 pages (diverse technical sample)

Proceed with these documents?
```

### Blog Voice (Priority 2)

**Purpose:** Extract writing style from blog content

**Discovery process:**
```bash
# Blog posts (exclude blog homepage)
blog_posts=$(kurt content list --url-contains /blog/ --status FETCHED | grep -v "/blog/?$")

# Sample recent posts (5-10 for general blog voice)
recent_posts=$(echo "$blog_posts" | head -10)
```

**Show proposed list:**
```
Found blog posts for style extraction:

✓ 10 recent blog posts
Date range: <earliest> to <latest>

Proceed with these posts?
```

### Individual Author Voice (Optional)

**Purpose:** Extract personal writing style of specific author

**Discovery process:**
```bash
# Requires --author-name flag
# Search by author in metadata or URL
author_posts=$(kurt content list --author "$AUTHOR_NAME" --status FETCHED)

# Or by URL pattern if author has dedicated path
author_posts=$(kurt content list --url-contains "/blog/$author_slug/" --status FETCHED)
author_posts=$(kurt content list --url-contains "/author/$author_slug/" --status FETCHED)
```

**Show proposed list:**
```
Found blog posts by <Author Name>:

✓ 12 posts
Date range: <earliest> to <latest>
Topics: <topic list>

How many to use?
a) Use all 12 (comprehensive)
b) Use 6 most recent (current voice)
c) Custom selection
```

---

## Step 4: Get User Approval

Display proposed documents and ask for confirmation:

```
Review proposed documents for style extraction:

<List of documents with titles and URLs>

Total: <count> documents

Options:
a) Proceed with these documents
b) Add specific documents (provide paths/URLs)
c) Remove specific documents (provide paths/URLs)
d) Start over with manual selection
```

**Handle user response:**
- If (a): Proceed to Step 5
- If (b): Add documents, show updated list, ask again
- If (c): Remove documents, show updated list, ask again
- If (d): Go to manual selection mode

---

## Step 5: Analyze Documents for Style Patterns

### Load Document Content

For each document in final list:
1. Read file from `/sources/`
2. Extract text content (ignore frontmatter, code blocks, etc.)
3. Build corpus for analysis

### Analyze Style Characteristics

**Voice & Tone:**
- Conversational, authoritative, technical, friendly, casual, professional
- Analyze sentence patterns, transitions, expressions
- Identify consistent voice across documents

**Sentence Structure:**
- Average length and complexity
- Active vs passive voice ratio
- Sentence variety patterns
- Paragraph length patterns

**Word Choice:**
- Technical terminology level
- Jargon usage patterns
- Formality level
- Common vocabulary themes

**Common Patterns:**
- Recurring phrases and expressions
- Transition patterns
- Opening and closing patterns
- Stylistic devices used

### Detect Style Patterns

Analyze if documents share:
- Consistent voice and tone
- Similar sentence structures
- Common word choice patterns
- Recurring stylistic elements

**If single consistent style found:**
- Create one style guide
- Name based on content type + tone (e.g., "technical-documentation-style.md")

**If multiple distinct styles found:**
- Create multiple style guides
- Name each based on its characteristics
- Report: "Created 2 new style guides: <name1>.md, <name2>.md"

---

## Step 6: Check Against Existing Styles

**Load existing styles from $RULES_STYLE_DIR:**
```bash
ls -la rules/style/
```

**For each detected style pattern:**
1. Compare with existing style guides
2. Check if pattern already captured
3. Determine if new or duplicate

**Incremental Mode (default):**
- If pattern distinct from existing → Create new style guide
- If pattern similar to existing → Report "No new styles detected"
- Keep all existing style guides

**Overwrite Mode (`--overwrite` flag):**
- Delete all files in `rules/style/`
- Create fresh style guides from analysis
- Report all created guides

---

## Step 7: Create Style Guide Files

For each new/distinct style pattern:

### Generate Auto-Name

Based on analysis:
- **Content type:** blog, landing-page, technical-doc, tutorial, support
- **Tone:** conversational, formal, authoritative, casual, friendly
- **Audience:** executive, developer, customer, general

**Example names:**
- `conversational-marketing.md`
- `technical-documentation.md`
- `executive-blog-posts.md`
- `friendly-support-content.md`
- `jane-smith-blog-voice.md` (for author styles)

### Create File: rules/style/<name>.md

**File structure:**
```markdown
---
type: style-guide
content_type: <type>
tone_type: <tone>
audience: <audience>
voice_characteristics: [list]
complexity_level: <level>
documents_analyzed: <count>
extracted_date: <date>
extraction_method: <auto-discover|manual>
source_documents:
  - <path1>
  - <path2>
  ...
---

# <Style Guide Name>

## Overview
<Brief description of this writing style>

## When to Use
<Content types and contexts where this style applies>

## Voice & Tone
<Core writing personality and emotional quality>

**Voice Characteristics:**
- <characteristic 1>
- <characteristic 2>
- <characteristic 3>

**Tone:**
- <tone description>
- <when it shifts>

## Sentence Structure

**Length & Complexity:**
- <average sentence length>
- <complexity level>

**Patterns:**
- <active vs passive voice>
- <sentence variety description>

**Paragraph Structure:**
- <typical paragraph length>
- <organization patterns>

## Word Choice

**Vocabulary Level:**
- <technical vs general>
- <formality level>

**Common Terms:**
- <key terminology>
- <industry jargon usage>

**Words/Phrases to Favor:**
- <list>

**Words/Phrases to Avoid:**
- <list>

## Common Patterns

**Recurring Expressions:**
- "<example 1>"
- "<example 2>"

**Transitions:**
- <typical transition words/phrases>

**Opening Patterns:**
- <how content typically begins>

**Closing Patterns:**
- <how content typically ends>

## Example Sentences

<5-10 representative sentences from analyzed content>

1. "<example sentence 1>" (from: <source>)
2. "<example sentence 2>" (from: <source>)
...

## Usage Notes

**Best for:**
- <content type 1>
- <content type 2>

**Not suitable for:**
- <content type 1>
- <content type 2>

**Key Guidelines:**
1. <guideline 1>
2. <guideline 2>
3. <guideline 3>

## Rule Application

When applying this style guide:
- Maintain voice consistency throughout content
- Match sentence complexity to audience expectations
- Use common patterns naturally, not mechanically
- Adapt examples to your specific content needs

---

*Extracted on <date> from <count> documents using <method>*
```

### Save File

Write file to `rules/style/<name>.md`

---

## Step 8: Report Results

**If styles created:**
```
✅ Style extraction complete

📊 Analysis:
   - <count> documents analyzed
   - <count> distinct style pattern(s) identified

📝 Style guide(s) created:
   - rules/style/<name1>.md
   - rules/style/<name2>.md (if multiple)

🔍 Style characteristics:
   <Style 1>:
   - Voice: <voice description>
   - Tone: <tone description>
   - Complexity: <level>
   - Typical use: <content types>

   <Style 2>: (if multiple)
   ...

Next steps:
  1. Review style guide(s) to understand voice and tone
  2. Extract other rule types (structure, persona, publisher)
  3. Use in content creation: content-writing-skill outline/draft <project> <asset>
```

**If no new styles detected:**
```
ℹ️ No new style patterns detected

Analyzed <count> documents and found patterns already captured in:
  - rules/style/<existing-guide-1>.md
  - rules/style/<existing-guide-2>.md

Options:
  1. Review existing guides - may already have what you need
  2. Try different content types for distinct patterns
  3. Use --overwrite to refresh existing styles
```

**If overwrite mode used:**
```
✅ Style library refreshed (overwrite mode)

🗑️ Deleted <count> existing style guide(s)
📝 Created <count> new style guide(s) from fresh analysis

Updated style library:
  - rules/style/<name1>.md
  - rules/style/<name2>.md
  ...
```

---

## Style Extraction Philosophy

**Layered Approach:**

1. **Corporate Voice (Priority 1)** - The company's brand voice
   - Most important to extract first
   - Used on marketing pages, product pages
   - Represents official brand communication

2. **Content Type Voices (Priority 2)** - Distinct voices for different content
   - Technical documentation voice
   - Blog post voice (may be more casual)
   - Support/help content voice

3. **Individual Author Voices (Optional)** - Personal voices of specific authors
   - Blog posts by individual authors
   - Only extract if project requires matching individual style

**Recommendation:** Always extract corporate voice first, then content-type voices, then individual voices if needed.

---

## Validation

**Minimum Document Check:**
- Requires at least 3 substantial documents
- Warns if insufficient content provided
- Prompts to add more sources or proceed with caveat

**Quality Indicators:**
- More documents = more reliable patterns
- Consistent authorship = clearer style voice
- Same content type = more focused style guide

---

## Directory Management

**Automatic Directory Creation:**
- Creates `rules/style/` if it doesn't exist
- No manual setup required
- Works on first use

---

## Error Handling

**If insufficient documents:**
```
⚠️ Warning: Only <count> documents provided

Reliable style extraction requires minimum 3-5 substantial documents.

Options:
a) Add more documents (recommended)
b) Proceed with caveat (patterns may be less reliable)
c) Cancel and try later
```

**If no content found in auto-discovery:**
```
⚠️ No content found for style type: <type>

Searched for: <URL patterns>

Options:
a) Check if content is fetched: kurt content list --url-contains <pattern>
b) Fetch content (includes indexing): kurt fetch --include <url>
c) Try different style type
d) Use manual document selection
```

---

*This subskill is invoked by writing-rules-skill and requires content to be fetched before extraction (fetching includes automatic indexing).*
