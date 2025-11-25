# Kurt Evaluation Mock Projects

This directory contains complete Kurt project dumps for evaluation scenarios. Each project includes database dumps and source files organized by project.

## Structure

Each project follows this structure:

```
project-name/
├── database/           # Database table dumps (JSONL)
│   ├── documents.jsonl
│   ├── entities.jsonl
│   ├── document_entities.jsonl
│   └── entity_relationships.jsonl
├── sources/           # Original content files (markdown, etc.)
│   └── *.md
├── integrations/      # Mock integration data (optional)
│   ├── cms/          # CMS API responses
│   ├── analytics/    # Analytics data
│   └── research/     # Research API data
└── README.md         # Project documentation
```

## Available Projects

### acme-docs
Sample documentation project with 7 indexed documents, 15 entities, and full source files. Includes mock integration data for testing CMS, analytics, and research APIs.

**Contents:**
- 7 documents (API docs, guides, troubleshooting)
- 15 entities (topics, technologies, concepts)
- 11 entity relationships
- Full source markdown files
- Mock CMS (Sanity) data
- Mock analytics data
- Mock research data (Perplexity, Reddit, HackerNews)

### motherduck
Real-world dump from kurt-demo containing MotherDuck documentation and content.

**Contents:**
- 874 documents (MotherDuck docs and articles)
- 371 entities (DuckDB, MotherDuck, SQL features)
- 1,667 document-entity links
- 126 entity relationships

## Usage

### Load a Project Dump

```bash
# Initialize a new Kurt project
KURT_TELEMETRY_DISABLED=1 uv run kurt init

# Load a project dump
python eval/mock/generators/load_dump.py acme-docs
```

### Create a New Project Dump

```bash
# From an existing Kurt project
cd /path/to/your/kurt/project
python /path/to/kurt-core/eval/mock/generators/create_dump.py . my-project-name
```

This will create:
- `eval/mock/projects/my-project-name/database/` with JSONL table dumps
- `eval/mock/projects/my-project-name/sources/` with content files (if they exist)

### Use in Eval Scenarios

In your scenario YAML:

```yaml
setup_commands:
  - KURT_TELEMETRY_DISABLED=1 uv run kurt init
  - python eval/mock/generators/load_dump.py acme-docs
```

## Benefits

- **Reproducible**: Same data across all test runs
- **Version Control Friendly**: JSONL + markdown files
- **Fast**: No need to re-fetch or re-index for each test
- **Realistic**: Real project data with actual entities and relationships
- **Complete**: Includes both database state and source files
