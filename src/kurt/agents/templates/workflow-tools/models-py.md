# models.py: SQLModel Table Definitions

The `models.py` file defines database tables for your workflow.
These tables are used by:
- `kurt agent tool save-to-db` - for persisting data
- `kurt agent tool llm` - for output schemas
- `type = "function"` steps - for querying results

## Basic Structure

```python
"""SQLModel tables for my_workflow."""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


# Database table (table=True)
class MyResult(SQLModel, table=True):
    """Results from my workflow."""

    __tablename__ = "my_results"  # Table name for --table option

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)  # Link to parent workflow

    # Your fields here
    name: str
    score: int = Field(ge=0, le=100)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Pydantic model for LLM output schema (no table=True)
class ExtractOutput(BaseModel):
    """Output schema for LLM extraction."""

    entities: list[str] = []
    sentiment: str = "neutral"
    confidence: float = PydanticField(default=0.0, ge=0.0, le=1.0)
```

## Key Differences

| Type | Purpose | Has `table=True` |
|------|---------|------------------|
| SQLModel table | Database persistence | Yes |
| Pydantic model | LLM output schema | No |

## Field Types Reference

### Basic Types

```python
# Strings
name: str                           # Required
name: Optional[str] = None          # Optional
name: str = "default"               # With default
name: str = Field(min_length=1, max_length=100)  # With constraints

# Numbers
count: int                          # Required integer
count: int = 0                      # With default
score: float = Field(ge=0.0, le=1.0)  # Float with range

# Boolean
is_active: bool = True

# Datetime
created_at: datetime = Field(default_factory=datetime.utcnow)
updated_at: Optional[datetime] = None
```

### JSON/Complex Types

```python
from sqlalchemy import Column, JSON

# Lists
tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
scores: list[float] = Field(default_factory=list, sa_column=Column(JSON))

# Dicts
metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

# Nested objects (as JSON)
details: dict = Field(default_factory=dict, sa_column=Column(JSON))
```

### Indexes and Primary Keys

```python
# Auto-increment primary key
id: Optional[int] = Field(default=None, primary_key=True)

# Indexed field (for fast queries)
workflow_id: str = Field(index=True)
company: str = Field(index=True)

# Unique constraint
email: str = Field(unique=True)
```

## Validation

Pydantic validation runs before database insert:

```python
# Range constraints
score: int = Field(ge=0, le=100)           # 0 <= score <= 100
price: float = Field(gt=0)                 # price > 0

# String constraints
name: str = Field(min_length=1, max_length=255)
email: str = Field(regex=r"^[\w.-]+@[\w.-]+\.\w+$")

# List constraints
tags: list[str] = Field(min_length=1)      # At least 1 tag
```

## Complete Example

```python
"""SQLModel tables for competitor_tracker workflow."""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field as PydanticField
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class CompetitorAnalysis(SQLModel, table=True):
    """Competitor analysis results stored in database."""

    __tablename__ = "competitor_analysis"

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)

    # Company info
    company: str = Field(index=True)
    website: str
    industry: Optional[str] = None

    # Analysis results
    products: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    pricing: dict = Field(default_factory=dict, sa_column=Column(JSON))
    strengths: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    weaknesses: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    # Metadata
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class CompetitorExtract(BaseModel):
    """Output schema for LLM competitor extraction."""

    company_name: str
    products: list[str] = []
    pricing_model: str = "unknown"
    target_market: str = ""
    key_features: list[str] = []
    confidence: float = PydanticField(default=0.0, ge=0.0, le=1.0)
```

## Using in Workflow

### Save to Database

```bash
kurt agent tool save-to-db \
  --table=competitor_analysis \
  --data='{"workflow_id": "abc-123", "company": "Acme", "products": ["Widget"]}'
```

### LLM with Output Schema

```bash
kurt agent tool llm \
  --prompt="Extract competitor info: {text}" \
  --data='[{"text": "Acme sells widgets at $10/month"}]' \
  --output-schema=CompetitorExtract
```

### Query in tools.py

```python
from sqlmodel import select
from kurt.db import managed_session
from .models import CompetitorAnalysis

@DBOS.step()
def generate_report(context: dict) -> dict:
    workflow_id = context["workflow_id"]

    with managed_session() as session:
        results = session.exec(
            select(CompetitorAnalysis)
            .where(CompetitorAnalysis.workflow_id == workflow_id)
        ).all()

    return {"count": len(results), "companies": [r.company for r in results]}
```

## Best Practices

1. **Always include workflow_id** - Links data to parent workflow
2. **Use indexes on query fields** - `Field(index=True)` for filtering
3. **Validate at model level** - Catch bad data early
4. **Separate tables from schemas** - `table=True` only for persistence
5. **Use JSON for nested data** - Lists, dicts with `sa_column=Column(JSON)`
