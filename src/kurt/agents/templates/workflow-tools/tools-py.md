# tools.py: DBOS Step Functions

The `tools.py` file contains `@DBOS.step()` functions used by `type = "function"` steps.
These functions are durable, retriable, and observable.

## Basic Structure

```python
"""DBOS step functions for my_workflow."""

from dbos import DBOS


@DBOS.step()
def my_step(context: dict) -> dict:
    """Step description.

    Args:
        context: Workflow context with inputs and outputs

    Returns:
        Dict with step results
    """
    inputs = context.get("inputs", {})
    outputs = context.get("outputs", {})

    # Your logic here

    return {"result": "value"}
```

## Context Object

The context dict passed to each step contains:

```python
{
    "inputs": {...},           # From [inputs] section
    "outputs": {               # Results from previous steps
        "step_name": {...}
    },
    "workflow_id": "abc-123",  # Current workflow ID
}
```

## Step Types

### 1. Data Fetching Step

```python
@DBOS.step()
def fetch_data(context: dict) -> dict:
    """Fetch data from external sources."""
    inputs = context.get("inputs", {})
    urls = inputs.get("urls", [])

    import httpx

    results = []
    for url in urls:
        response = httpx.get(url, timeout=30)
        results.append({
            "url": url,
            "content": response.text[:10000],  # Truncate
            "status": response.status_code,
        })

    return {"pages": results, "count": len(results)}
```

### 2. Processing Step

```python
@DBOS.step()
def process_items(context: dict) -> dict:
    """Process items from previous step."""
    outputs = context.get("outputs", {})
    pages = outputs.get("fetch", {}).get("pages", [])

    processed = []
    for page in pages:
        processed.append({
            "url": page["url"],
            "word_count": len(page["content"].split()),
            "title": extract_title(page["content"]),
        })

    return {"items": processed, "count": len(processed)}


def extract_title(html: str) -> str:
    """Helper function (not a step)."""
    import re
    match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    return match.group(1) if match else "Untitled"
```

### 3. Report Generation Step

```python
@DBOS.step()
def generate_report(context: dict) -> dict:
    """Generate final report from analysis."""
    from sqlmodel import select
    from kurt.db import managed_session
    from .models import AnalysisResult

    workflow_id = context["workflow_id"]

    # Query results saved by agent step
    with managed_session() as session:
        results = session.exec(
            select(AnalysisResult)
            .where(AnalysisResult.workflow_id == workflow_id)
        ).all()

    report = f"# Analysis Report\n\nAnalyzed {len(results)} items.\n\n"
    for r in results:
        report += f"- {r.name}: {r.summary}\n"

    return {
        "report": report,
        "total_items": len(results),
        "status": "completed",
    }
```

## Using External APIs

```python
@DBOS.step()
def call_api(context: dict) -> dict:
    """Call external API with retry logic."""
    import httpx
    from tenacity import retry, stop_after_attempt, wait_exponential

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call(url: str) -> dict:
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        return response.json()

    inputs = context.get("inputs", {})
    api_url = inputs.get("api_url")

    try:
        data = _call(api_url)
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Progress Tracking

```python
@DBOS.step()
def process_batch(context: dict) -> dict:
    """Process batch with progress updates."""
    items = context.get("inputs", {}).get("items", [])
    total = len(items)

    DBOS.set_event("stage_total", total)

    results = []
    for idx, item in enumerate(items):
        result = process_item(item)
        results.append(result)
        DBOS.set_event("stage_current", idx + 1)

    return {"results": results, "processed": len(results)}
```

## Error Handling

```python
@DBOS.step()
def safe_step(context: dict) -> dict:
    """Step with error handling."""
    try:
        # Risky operation
        result = do_something()
        return {"success": True, "result": result}
    except ValueError as e:
        # Expected error - return error info
        return {"success": False, "error": str(e), "error_type": "validation"}
    except Exception as e:
        # Unexpected error - re-raise for DBOS retry
        raise
```

## Complete Example

```python
"""DBOS step functions for competitor_tracker workflow."""

from dbos import DBOS


@DBOS.step()
def fetch_pages(context: dict) -> dict:
    """Fetch competitor pages from URLs."""
    import httpx
    from trafilatura import extract

    inputs = context.get("inputs", {})
    urls = inputs.get("urls", [])

    pages = []
    for url in urls:
        try:
            response = httpx.get(url, timeout=30, follow_redirects=True)
            content = extract(response.text) or response.text[:10000]
            pages.append({
                "url": url,
                "content": content,
                "status": "success",
            })
        except Exception as e:
            pages.append({
                "url": url,
                "content": "",
                "status": "error",
                "error": str(e),
            })

    return {"pages": pages, "count": len(pages)}


@DBOS.step()
def generate_report(context: dict) -> dict:
    """Generate report from saved analysis."""
    from datetime import datetime
    from sqlmodel import select
    from kurt.db import managed_session
    from .models import CompetitorAnalysis

    workflow_id = context["workflow_id"]

    with managed_session() as session:
        analyses = session.exec(
            select(CompetitorAnalysis)
            .where(CompetitorAnalysis.workflow_id == workflow_id)
            .order_by(CompetitorAnalysis.company)
        ).all()

    report_lines = [
        f"# Competitor Analysis Report",
        f"Generated: {datetime.utcnow().isoformat()}",
        f"Total Competitors: {len(analyses)}",
        "",
    ]

    for a in analyses:
        report_lines.extend([
            f"## {a.company}",
            f"- Website: {a.website}",
            f"- Products: {', '.join(a.products)}",
            f"- Confidence: {a.confidence_score:.0%}",
            "",
        ])

    return {
        "report": "\n".join(report_lines),
        "competitor_count": len(analyses),
        "status": "completed",
    }
```

## Using in workflow.toml

```toml
[steps.fetch]
type = "function"
function = "fetch_pages"  # Calls fetch_pages() from tools.py

[steps.analyze]
type = "agent"
depends_on = ["fetch"]
prompt = "Analyze competitors from {outputs.fetch}..."

[steps.report]
type = "function"
depends_on = ["analyze"]
function = "generate_report"  # Calls generate_report() from tools.py
```

## Best Practices

1. **Keep steps focused** - One task per step
2. **Return serializable data** - Dicts with JSON-compatible values
3. **Use context for data flow** - Access inputs and previous outputs
4. **Handle errors gracefully** - Return error info or re-raise
5. **Track progress** - Use `DBOS.set_event()` for long operations
6. **Query saved data in report step** - Agent saves, function reads
