# SaveStep: Database Persistence

SaveStep persists data to PostgreSQL/SQLite tables defined in `models.py`.
It validates data against SQLModel schemas and provides error feedback.

## CLI Usage

```bash
# Save single object
kurt agent tool save-to-db \
  --table=competitor_analysis \
  --data='{"company": "Acme", "score": 85, "products": ["widget", "gadget"]}'

# Save multiple objects
kurt agent tool save-to-db \
  --table=competitor_analysis \
  --data='[{"company": "Acme", "score": 85}, {"company": "Beta", "score": 72}]'

# Specify workflow directory (if models.py is not in cwd)
kurt agent tool save-to-db \
  --table=analysis \
  --data='{"key": "value"}' \
  --workflow-dir=/path/to/workflow
```

## Output Format

```json
{
  "success": true,
  "table": "competitor_analysis",
  "saved": 2,
  "errors": [],
  "total_rows": 2
}
```

On validation error:
```json
{
  "success": true,
  "table": "competitor_analysis",
  "saved": 1,
  "errors": [{"idx": 1, "errors": ["score must be >= 0"]}],
  "total_rows": 2
}
```

## Required: models.py

You MUST create a `models.py` file with SQLModel table definitions:

```python
"""SQLModel tables for my_workflow."""

from typing import Optional
from pydantic import Field
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class CompetitorAnalysis(SQLModel, table=True):
    """Competitor analysis results."""

    __tablename__ = "competitor_analysis"  # This is the --table value

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)
    company: str
    score: int = Field(ge=0, le=100)  # Validation: 0-100
    products: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    notes: Optional[str] = None
```

## Field Types

| Python Type | SQL Type | Notes |
|-------------|----------|-------|
| `str` | VARCHAR | Required string |
| `Optional[str]` | VARCHAR NULL | Optional string |
| `int` | INTEGER | Required integer |
| `float` | FLOAT | Required float |
| `bool` | BOOLEAN | Required boolean |
| `list[str]` | JSON | Use `sa_column=Column(JSON)` |
| `dict` | JSON | Use `sa_column=Column(JSON)` |
| `datetime` | TIMESTAMP | Use `from datetime import datetime` |

## Validation

SQLModel/Pydantic validation runs before insert:

```python
# Add constraints
score: int = Field(ge=0, le=100)           # Range: 0-100
email: str = Field(regex=r".*@.*\..*")     # Regex pattern
name: str = Field(min_length=1, max_length=100)  # Length limits
```

## Best Practices

1. **Always include workflow_id** - Links rows to parent workflow
2. **Use JSON columns for nested data** - lists, dicts
3. **Add indexes on query fields** - `Field(index=True)`
4. **Validate at model level** - Pydantic constraints catch bad data
5. **Handle errors gracefully** - Check `errors` array in response

## Error Handling in Agent Prompt

```markdown
Save analysis results:
\`\`\`bash
kurt agent tool save-to-db --table=competitor_analysis --data='{...}'
\`\`\`

If validation errors occur, fix the data and retry.
Check the `errors` array in the response for specific issues.
```

## Workflow Directory Structure

```
workflows/my_workflow/
├── workflow.toml    # Workflow definition
├── models.py        # SQLModel tables (required for save-to-db)
└── tools.py         # Step functions (for type=function steps)
```
