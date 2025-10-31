# Kurt Architecture

## Layered Architecture

Kurt follows a clean three-layer architecture with clear separation of concerns.

```
┌─────────────────────────────────────────┐
│  Commands Layer (CLI)                   │
│  src/kurt/commands/                     │
│  - Parse CLI arguments                  │
│  - Display output (Rich Console)        │
│  - Handle user input/errors             │
│  - NO business logic or DB queries      │
└──────────────┬──────────────────────────┘
               │ calls
               ▼
┌─────────────────────────────────────────┐
│  Services Layer (Business Logic)        │
│  src/kurt/services/                     │
│  src/kurt/document.py                   │
│  src/kurt/ingestion/                    │
│  - Business logic                       │
│  - Database queries                     │
│  - Data transformations                 │
│  - NO UI/console code                   │
└──────────────┬──────────────────────────┘
               │ uses
               ▼
┌─────────────────────────────────────────┐
│  Data Layer                             │
│  src/kurt/db/                           │
│  src/kurt/utils/                        │
│  - Database models & migrations         │
│  - Pure utility functions               │
│  - NO side effects in utils             │
└─────────────────────────────────────────┘
```

## Directory Structure

```
src/kurt/
├── commands/              # CLI layer - thin wrappers
│   ├── cluster_urls.py   # → calls clustering_service
│   ├── status.py         # → calls status_service
│   ├── content.py        # → calls document service
│   ├── project.py        # → calls project_utils
│   ├── map.py           # → calls ingestion/map
│   ├── fetch.py         # → calls ingestion/fetch
│   └── ...
│
├── services/             # Business logic layer
│   ├── clustering_service.py
│   └── status_service.py
│
├── ingestion/            # Content ingestion logic
│   ├── fetch.py         # Fetch & download
│   ├── map.py           # Content discovery
│   ├── cluster.py       # Topic clustering
│   └── index.py         # LLM indexing
│
├── document.py           # Document CRUD operations
├── db/                   # Database layer
│   ├── models.py        # SQLAlchemy models
│   ├── database.py      # Session management
│   └── migrations/      # Database migrations
│
└── utils/               # Pure utility functions
    ├── project_utils.py
    ├── file_utils.py
    └── url_utils.py
```

## Key Principles

### 1. Commands Layer (CLI)
**What it does:**
- Parse Click options and arguments
- Call service layer functions
- Format and display results using Rich
- Handle user confirmations and errors

**What it does NOT do:**
- Query the database directly
- Implement business logic
- Parse data formats (delegate to utils)

### 2. Services Layer (Business Logic)
**What it does:**
- Implement business logic
- Query and update database
- Aggregate and transform data
- Return data structures (dicts, lists, models)

**What it does NOT do:**
- Import Click or Rich (UI-agnostic)
- Handle CLI arguments
- Print to console

### 3. Data Layer
**What it does:**
- Define database models (SQLAlchemy)
- Manage database sessions
- Provide pure utility functions
- Handle migrations

**What it does NOT do:**
- Implement business logic
- Access UI components

## Design Patterns

### Service Functions
All service functions follow this pattern:

```python
def get_something(filters: dict) -> dict:
    """
    Business logic description.

    Args:
        filters: Description

    Returns:
        dict with keys: ...

    Example:
        >>> result = get_something({"filter": "value"})
    """
    session = get_session()
    # Query database
    # Transform data
    return result
```

### Command Functions
All commands follow this pattern:

```python
@click.command()
@click.option("--filter", help="Description")
def my_command(filter: str):
    """CLI command description."""
    try:
        # Parse/validate CLI inputs
        result = service_function(filter)

        # Format and display output
        console.print(f"[green]Success: {result['count']}[/green]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
```

## Example Flow

**User runs:** `kurt cluster-urls --include "*/docs/*"`

```
1. CLI Layer (commands/cluster_urls.py)
   └─> Parses --include option
   └─> Calls clustering_service.get_existing_clusters_summary()

2. Service Layer (services/clustering_service.py)
   └─> Queries database via get_session()
   └─> Returns {"count": 5, "clusters": [...]}

3. CLI Layer (commands/cluster_urls.py)
   └─> Formats data with Rich tables
   └─> Displays to user
```

## Testing Strategy

- **Unit tests**: Test service functions independently
- **Integration tests**: Test command flows end-to-end
- **Mock database**: Use in-memory SQLite for tests

## Adding New Features

**To add a new command:**

1. Create service function in appropriate service module
2. Add command in `commands/` that calls the service
3. Register command in `cli.py`
4. Write tests for both layers

**Example:**

```python
# 1. Service (services/my_service.py)
def get_statistics() -> dict:
    session = get_session()
    return {"total": session.query(Document).count()}

# 2. Command (commands/stats.py)
@click.command()
def stats_cmd():
    result = get_statistics()
    console.print(f"Total: {result['total']}")

# 3. Register (cli.py)
cli.add_command(stats_cmd, name="stats")
```

## Migration Notes

Recent refactoring (2025) moved business logic out of commands:
- Created `services/` directory for business logic
- Moved DB queries from commands to services
- Commands now only handle CLI concerns

See git history for detailed migration patterns.
