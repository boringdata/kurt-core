# Kurt Eval Project Dumps

Project dumps contain complete Kurt project data for use in evaluation scenarios.

## Structure

Each project dump contains:
- **Database tables** (JSONL format): documents, entities, document_entities, entity_relationships
- **Source files**: Content from `.kurt/sources/` directory

```
projects/
└── {project-name}/
    ├── documents.jsonl
    ├── entities.jsonl
    ├── document_entities.jsonl
    ├── entity_relationships.jsonl
    └── sources/
        └── (content files)
```

## Creating a Dump

Dump your Kurt project to use it in eval scenarios:

```bash
python eval/mock/generators/create_dump.py /path/to/your/kurt-project project-name
```

Example:
```bash
python eval/mock/generators/create_dump.py ~/my-kurt-demo my-demo
```

This creates `eval/mock/data/projects/my-demo/` with all data.

## Loading a Dump

Load a dump into a fresh Kurt project:

```bash
# Initialize new project
kurt init

# Load the dump
python eval/mock/generators/load_dump.py project-name
```

The load is **schema-adaptive** - it automatically filters columns to match your database schema, so dumps work across different schema versions.

## Using in Eval Scenarios

### Option 1: Simple Project Reference (Recommended)

```yaml
- name: my_test
  description: Test with pre-loaded project data
  project: acme-docs  # Simple reference to project dump

  initial_prompt: |
    Answer the question: "What is ACME?"
```

### Option 2: Manual Setup Commands

```yaml
- name: my_test
  description: Test with manual setup
  setup_commands:
    - KURT_TELEMETRY_DISABLED=1 uv run kurt init
    - python eval/mock/generators/load_dump.py acme-docs

  initial_prompt: |
    Answer the question: "What is ACME?"
```

**Note:** When using `project:`, Kurt init is automatically run first, so you don't need to include it in setup_commands.

## Available Dumps

- **acme-docs**: Technical documentation example (4 docs, 15 entities)
