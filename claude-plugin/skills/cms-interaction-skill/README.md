# CMS Interaction Infrastructure

**This directory contains shared infrastructure for CMS interaction. For actual usage, see the CMS skills below.**

## Skills (Use These!)

CMS interaction is split into 4 focused skills:

| Skill | Purpose | Documentation |
|-------|---------|---------------|
| **[cms-search-skill](../cms-search-skill/SKILL.md)** | Search CMS content with queries and filters | [SKILL.md](../cms-search-skill/SKILL.md) |
| **[cms-fetch-skill](../cms-fetch-skill/SKILL.md)** | Download CMS content as markdown files | [SKILL.md](../cms-fetch-skill/SKILL.md) |
| **[cms-import-skill](../cms-import-skill/SKILL.md)** | Import CMS content to Kurt database | [SKILL.md](../cms-import-skill/SKILL.md) |
| **[cms-publish-skill](../cms-publish-skill/SKILL.md)** | Publish drafts back to CMS | [SKILL.md](../cms-publish-skill/SKILL.md) |

## Quick Start

**1. Install dependencies:**
```bash
pip install sanity pyyaml
```

**2. Configure CMS:**
```bash
cp .claude/skills/cms-interaction-skill/adapters/sanity/config.json.example \
   .claude/scripts/cms-config.json

# Edit cms-config.json with your credentials
```

**3. Test connection:**
```bash
python .claude/skills/cms-interaction-skill/scripts/cms_search.py \
  --cms sanity --test-connection
```

**4. Use the skills:**
```bash
# Invoke skills in Claude Code
Skill(cms-search-skill)
Skill(cms-fetch-skill)
Skill(cms-import-skill)
Skill(cms-publish-skill)
```

## Complete Workflow Example

```bash
# 1. Search for content
python .claude/skills/cms-interaction-skill/scripts/cms_search.py \
  --cms sanity --query "tutorial" --output json > results.json

# 2. Fetch content
cat results.json | \
python .claude/skills/cms-interaction-skill/scripts/cms_fetch.py \
  --cms sanity --from-stdin

# 3. Import to Kurt
python .claude/skills/cms-interaction-skill/scripts/cms_import.py \
  --cms sanity --source-dir sources/cms/sanity/

# 4. Create update project
/create-project

# 5. Create updated drafts
content-writing-skill draft my-project updated-content

# 6. Publish to CMS
python .claude/skills/cms-interaction-skill/scripts/cms_publish.py \
  --cms sanity \
  --file projects/my-project/assets/updated-content-draft.md \
  --document-id abc-123

# 7. Review and publish in CMS
```

## Infrastructure Contents

This directory provides shared infrastructure for all CMS skills:

### Adapters (`adapters/`)

CMS-specific implementations following a common interface:

- **`base.py`** - Base adapter interface (`CMSAdapter`, `CMSDocument`)
- **`sanity/`** - Sanity.io adapter (✅ fully implemented)
  - GROQ query support
  - Portable Text ↔ Markdown conversion
  - Draft system integration
- **`contentful/`** - Contentful adapter (🚧 coming soon)
- **`wordpress/`** - WordPress adapter (🚧 coming soon)

### Scripts (`scripts/`)

CLI tools used by all CMS skills:

- **`cms_search.py`** - Search CMS content
- **`cms_fetch.py`** - Download content as markdown
- **`cms_import.py`** - Import to Kurt database
- **`cms_publish.py`** - Publish drafts to CMS

All scripts accept `--help` for usage information.

### Configuration

**Location:** `.claude/scripts/cms-config.json` (gitignored)

**Format:**
```json
{
  "sanity": {
    "project_id": "your-project-id",
    "dataset": "production",
    "token": "read-token",
    "write_token": "write-token",
    "base_url": "https://yoursite.com"
  },
  "contentful": {
    ...
  }
}
```

**Security:** Configuration file is gitignored to protect credentials.

## Supported CMSs

| CMS | Status | Adapter | Documentation |
|-----|--------|---------|---------------|
| Sanity | ✅ Implemented | `adapters/sanity/` | [README](adapters/sanity/README.md) |
| Contentful | 🚧 Coming Soon | `adapters/contentful/` | - |
| WordPress | 🚧 Coming Soon | `adapters/wordpress/` | - |

## Adding New CMSs

To add a new CMS:

### 1. Create Adapter

```bash
mkdir -p adapters/your-cms
```

Create `adapters/your-cms/adapter.py`:

```python
from ..base import CMSAdapter, CMSDocument

class YourCMSAdapter(CMSAdapter):
    def __init__(self, config):
        # Initialize CMS client
        pass

    def search(self, query=None, filters=None, content_type=None, limit=100):
        # Return list of CMSDocument objects
        pass

    def fetch(self, document_id):
        # Return CMSDocument with full content
        pass

    def fetch_batch(self, document_ids):
        # Return list of CMSDocument objects
        pass

    def create_draft(self, content, title, content_type, metadata=None, document_id=None):
        # Return {'draft_id': ..., 'draft_url': ...}
        pass

    def get_content_types(self):
        # Return list of content type definitions
        pass

    def test_connection(self):
        # Return True if connection successful
        pass
```

### 2. Add Configuration Template

Create `adapters/your-cms/config.json.example`:

```json
{
  "your-cms": {
    "api_key": "your-api-key",
    "base_url": "https://api.yourcms.com"
  }
}
```

### 3. Create Documentation

Create `adapters/your-cms/README.md` with:
- Setup instructions
- API credentials
- CMS-specific features
- Troubleshooting

### 4. Update Scripts

Add your CMS to the choice list in all 4 scripts:

```python
parser.add_argument(
    '--cms',
    choices=['sanity', 'contentful', 'wordpress', 'your-cms']
)
```

Add adapter loading:

```python
def get_adapter(cms_name, config):
    if cms_name == 'your-cms':
        from your_cms.adapter import YourCMSAdapter
        return YourCMSAdapter(config)
    # ... other CMSs
```

### 5. Test

```bash
python scripts/cms_search.py --cms your-cms --test-connection
```

See [Sanity adapter](adapters/sanity/) as reference implementation.

## Architecture

### Design Pattern: Adapter

Each CMS implements the `CMSAdapter` interface defined in `base.py`:

```python
class CMSAdapter(ABC):
    @abstractmethod
    def search(...) -> List[CMSDocument]: pass

    @abstractmethod
    def fetch(document_id) -> CMSDocument: pass

    @abstractmethod
    def fetch_batch(document_ids) -> List[CMSDocument]: pass

    @abstractmethod
    def create_draft(...) -> Dict[str, str]: pass

    @abstractmethod
    def get_content_types() -> List[Dict]: pass

    @abstractmethod
    def test_connection() -> bool: pass
```

### Unified Document Model

All CMSs return `CMSDocument` objects:

```python
@dataclass
class CMSDocument:
    id: str
    title: str
    content: str  # Markdown
    content_type: str
    status: str  # draft/published
    url: Optional[str]
    author: Optional[str]
    published_date: Optional[str]
    last_modified: Optional[str]
    metadata: Optional[Dict[str, Any]]
```

### Benefits

- **Consistent interface** across all CMSs
- **Easy to add** new CMSs
- **Type-safe** with dataclasses
- **CMS-agnostic** scripts and skills

## File Organization

### Recommended Structure

```
sources/
└── cms/
    ├── sanity/
    │   ├── article/
    │   │   ├── quickstart-guide.md
    │   │   └── advanced-tutorial.md
    │   ├── page/
    │   │   └── about.md
    │   └── post/
    │       └── blog-post-1.md
    ├── contentful/
    │   └── ...
    └── wordpress/
        └── ...

projects/
└── tutorial-refresh/
    ├── project.md
    ├── sources/
    │   └── (symlinks to sources/cms/sanity/article/)
    └── assets/
        ├── quickstart-v2-outline.md
        └── quickstart-v2-draft.md
```

### Path Convention

- CMS content: `sources/cms/{cms-name}/{content-type}/{slug-or-id}.md`
- Each file has YAML frontmatter with all metadata
- Markdown content converted from CMS format

## Integration with Kurt

### Document Records

CMS content in Kurt database:

```
ID: abc-123
URL: sanity://abc-123
Content Path: cms/sanity/article/quickstart.md
Status: FETCHED
Title: Quickstart Tutorial
Author: Jane Doe
Topics: ["getting started", "tutorials"]
Tools: ["platform", "api"]
```

### Querying

```bash
# List CMS content
kurt content list --url-prefix sanity://

# Query by metadata
kurt content list --content-type tutorial
kurt content list --tool postgres
```

### Lineage Tracking

Content-writing-skill automatically tracks CMS sources:

```yaml
# In draft frontmatter
sources:
  - path: sources/cms/sanity/article/quickstart.md
    sections: [Introduction, Setup, Configuration]
    cms_id: abc-123
    cms_url: https://yoursite.com/quickstart
```

## Troubleshooting

### Connection Issues

```bash
# Test connection
python scripts/cms_search.py --cms sanity --test-connection

# Check config
cat .claude/scripts/cms-config.json

# Verify tokens
# - Read token: Viewer role minimum
# - Write token: Editor role for drafts
```

### Script Issues

```bash
# Check Python dependencies
pip list | grep -E "(sanity|yaml)"

# Make scripts executable
chmod +x scripts/*.py

# Test script directly
python scripts/cms_search.py --help
```

### Import Issues

```bash
# Verify Kurt installed
which kurt
kurt --version

# Check import script exists
ls -la .claude/scripts/import_markdown.py

# Test import manually
python .claude/scripts/import_markdown.py --help
```

## Best Practices

### Security

1. **Never commit** `cms-config.json` (use `.gitignore`)
2. **Use read-only tokens** for search/fetch
3. **Separate tokens** for read vs write
4. **Rotate tokens** regularly
5. **Test on staging** before production

### Workflow

1. **Search → Fetch → Import** for new content
2. **Dry run** before bulk operations
3. **Review drafts** before publishing
4. **Track in version control** all fetched/created content
5. **Document conventions** in project.md

### Performance

1. **Use batch operations** when possible
2. **Limit search results** appropriately
3. **Cache search results** before fetching
4. **Parallel operations** via stdin piping

## Development

### Running Tests

```bash
# Test Sanity adapter
python -c "
from adapters.sanity.adapter import SanityAdapter
import json

with open('.claude/scripts/cms-config.json') as f:
    config = json.load(f)

adapter = SanityAdapter(config['sanity'])
print('✓ Connection:', adapter.test_connection())

results = adapter.search(limit=5)
print(f'✓ Search: Found {len(results)} documents')
"
```

### Debugging

```bash
# Enable verbose output
export DEBUG=1

# Run script with python -v
python -v scripts/cms_search.py --cms sanity --test-connection

# Check logs (CMS-specific)
# Sanity: No built-in logs
# Check CMS dashboard for API usage
```

## Related Documentation

- **[Sanity Adapter](adapters/sanity/README.md)** - Sanity-specific docs
- **Skills:**
  - [cms-search-skill](../cms-search-skill/SKILL.md)
  - [cms-fetch-skill](../cms-fetch-skill/SKILL.md)
  - [cms-import-skill](../cms-import-skill/SKILL.md)
  - [cms-publish-skill](../cms-publish-skill/SKILL.md)

## Support

For CMS-specific questions, see adapter README files.

For skill usage questions, see individual SKILL.md files.

For bugs or feature requests, create an issue.
