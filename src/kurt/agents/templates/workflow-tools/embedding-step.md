# EmbeddingStep: Vector Embeddings

Generate vector embeddings for text data. Embeddings are saved to a JSON file
for use in similarity search, clustering, or RAG applications.

## CLI Usage

```bash
# Basic usage
kurt agent tool embedding \
  --texts='["Hello world", "Goodbye world"]' \
  --output=embeddings.json

# With custom model
kurt agent tool embedding \
  --texts='["Text to embed"]' \
  --output=vectors.json \
  --model=text-embedding-3-large

# With max characters (default: 1000)
kurt agent tool embedding \
  --texts='["Very long text..."]' \
  --output=out.json \
  --max-chars=2000
```

## Output Format

CLI response:
```json
{
  "success": true,
  "output_file": "embeddings.json",
  "count": 2,
  "dimensions": 1536
}
```

Output file (`embeddings.json`):
```json
{
  "embeddings": [
    [0.0123, -0.0456, 0.0789, ...],
    [0.0111, -0.0222, 0.0333, ...]
  ],
  "count": 2,
  "model": "text-embedding-3-small"
}
```

## Embedding Models

| Model | Dimensions | Best For |
|-------|------------|----------|
| `text-embedding-3-small` | 1536 | Fast, cost-effective |
| `text-embedding-3-large` | 3072 | Higher quality |
| `text-embedding-ada-002` | 1536 | Legacy OpenAI |

## Text Truncation

Texts are truncated to `--max-chars` (default: 1000) to fit model limits:

```bash
# For longer documents, increase max-chars
kurt agent tool embedding \
  --texts='["Full article content here..."]' \
  --output=out.json \
  --max-chars=8000
```

## Workflow Use Cases

### 1. Semantic Search

```bash
# Generate query embedding
kurt agent tool embedding \
  --texts='["How do I reset my password?"]' \
  --output=query.json

# Compare with document embeddings using cosine similarity
```

### 2. Document Clustering

```bash
# Embed all documents
kurt agent tool embedding \
  --texts='["Doc 1...", "Doc 2...", "Doc 3..."]' \
  --output=docs.json

# Use embeddings for k-means clustering
```

### 3. Duplicate Detection

```bash
# Embed potential duplicates
kurt agent tool embedding \
  --texts='["Original text", "Slightly modified text"]' \
  --output=dupes.json

# Compare with cosine similarity (> 0.95 = likely duplicate)
```

## Agent Prompt Example

```toml
[steps.embed]
type = "agent"
depends_on = ["fetch"]
prompt = """
Generate embeddings for the fetched content.

1. Read the content from {outputs.fetch}
2. Extract text from each document
3. Generate embeddings:

\`\`\`bash
kurt agent tool embedding \
  --texts='["text1", "text2", ...]' \
  --output=content-embeddings.json
\`\`\`

4. Report the number of embeddings generated
"""
```

## Loading Embeddings

Python code to load and use embeddings:

```python
import json
import numpy as np
from numpy.linalg import norm

# Load embeddings
with open("embeddings.json") as f:
    data = json.load(f)
    embeddings = np.array(data["embeddings"])

# Cosine similarity function
def cosine_sim(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))

# Find most similar
query_embedding = embeddings[0]
similarities = [cosine_sim(query_embedding, e) for e in embeddings[1:]]
most_similar_idx = np.argmax(similarities)
```

## Best Practices

1. **Batch texts together** - One API call for multiple texts is cheaper
2. **Truncate appropriately** - Balance context vs. cost
3. **Store with metadata** - Save text IDs alongside embeddings
4. **Normalize if needed** - Some similarity metrics require unit vectors

## Error Handling

```json
{
  "success": false,
  "error": "Embedding generation failed: Rate limit exceeded"
}
```

Handle errors in agent prompt:
```markdown
Generate embeddings. If rate limited, wait 60 seconds and retry.
Check `success` field in response.
```
