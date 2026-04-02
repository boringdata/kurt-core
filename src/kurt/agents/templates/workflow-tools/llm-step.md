# LLMStep: Batch LLM Processing

LLMStep processes data through an LLM with templated prompts.
It supports concurrent processing, structured output, and automatic retries.

## CLI Usage

```bash
# Basic usage with inline data
kurt agent tool llm \
  --prompt="Summarize this text: {content}" \
  --data='[{"content": "Long article text here..."}]'

# With output schema for structured responses
kurt agent tool llm \
  --prompt="Extract entities from: {text}" \
  --data='[{"text": "Apple announced new iPhone"}]' \
  --output-schema=ExtractOutput

# With custom model and concurrency
kurt agent tool llm \
  --prompt="Analyze: {description}" \
  --data='[{"description": "..."}]' \
  --model=gpt-4 \
  --concurrency=5

# From file (for large datasets)
kurt agent tool llm \
  --prompt="Categorize: {title}" \
  --data="$(cat items.json)"
```

## Output Format

```json
{
  "success": true,
  "results": [
    {
      "content": "Original text...",
      "agent_llm_result": {"response": "Summary here..."},
      "agent_llm_status": "success"
    }
  ],
  "total": 1,
  "successful": 1,
  "errors": []
}
```

## Prompt Template Syntax

Use `{field_name}` placeholders that match keys in your data:

```python
# Data
[{"title": "Breaking News", "body": "Article content..."}]

# Prompt - both fields available
"Summarize this article:\nTitle: {title}\nBody: {body}"
```

## Output Schema (Optional)

Define a Pydantic model in `models.py` for structured output:

```python
# models.py
from pydantic import BaseModel

class ExtractOutput(BaseModel):
    entities: list[str] = []
    sentiment: str = "neutral"
    confidence: float = 0.0
```

Then use it:
```bash
kurt agent tool llm \
  --prompt="Extract entities and sentiment: {text}" \
  --data='[{"text": "Apple stock rose 5%"}]' \
  --output-schema=ExtractOutput
```

Response:
```json
{
  "results": [{
    "text": "Apple stock rose 5%",
    "agent_llm_result": {
      "entities": ["Apple"],
      "sentiment": "positive",
      "confidence": 0.9
    },
    "agent_llm_status": "success"
  }]
}
```

## Prompt Best Practices

1. **Be specific about output format**
```
Extract entities from: {text}

Return JSON with:
- entities: list of entity names
- sentiment: "positive", "negative", or "neutral"
```

2. **Include examples in prompt**
```
Categorize the product: {description}

Categories: Electronics, Clothing, Food, Other

Example: "iPhone 15 Pro" -> Electronics
```

3. **Handle edge cases**
```
If the text is empty or unclear, return:
{"entities": [], "sentiment": "neutral", "confidence": 0.0}
```

## Concurrency

Default concurrency is 3. Increase for large batches:

```bash
# Process 100 items with 10 concurrent calls
kurt agent tool llm \
  --prompt="Process: {item}" \
  --data='[...]' \
  --concurrency=10
```

## Error Handling

Errors are captured per-row:
```json
{
  "results": [
    {"agent_llm_status": "success", ...},
    {"agent_llm_status": "error", "error": "Rate limit exceeded"}
  ],
  "successful": 1,
  "errors": ["Rate limit exceeded"]
}
```

## Workflow Integration

In `workflow.toml`, use type=llm step for declarative LLM processing:

```toml
[steps.enrich]
type = "llm"
depends_on = ["fetch"]
prompt_template = """
Analyze this content:
Title: {title}
Content: {content}

Return JSON with: summary, keywords, sentiment
"""
output_schema = "EnrichmentOutput"
```

Or use CLI in agent prompts for dynamic processing:
```toml
[steps.analyze]
type = "agent"
prompt = """
Process the fetched items using:
\`\`\`bash
kurt agent tool llm --prompt="Summarize: {text}" --data='[...]'
\`\`\`
"""
```

## Model Selection

| Model | Best For |
|-------|----------|
| `gpt-4` | Complex reasoning, high accuracy |
| `gpt-3.5-turbo` | Fast, cost-effective |
| `claude-3-haiku` | Fast, good for simple extraction |
| `claude-3-sonnet` | Balanced speed/quality |
