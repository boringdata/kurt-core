# Foreach Step - Parallel Iteration with DBOS

## Overview

The `foreach` step type enables **parallel processing** of arrays using **DBOS queues** for true concurrent execution with durability guarantees.

## Syntax

```yaml
- name: "process_items"
  type: "foreach"
  items: "${array_variable}"      # Array to iterate over
  concurrency: 10                  # Max concurrent tasks (default: 10)
  step:                            # Template step to execute for each item
    name: "process_item"
    type: "cli"  # or "dspy", "script"
    # ... step configuration ...
    # Use ${item} to reference current item
  output: "results"                # Array of results
```

## Key Features

✅ **True Parallelism** - Uses DBOS queues for concurrent execution
✅ **Durable** - Each item execution is checkpointed
✅ **Concurrency Control** - Limit parallel tasks with `concurrency`
✅ **Automatic Fallback** - Falls back to sequential if DBOS unavailable
✅ **Works with All Step Types** - CLI, DSPy, Script steps supported

## How It Works

### With DBOS (Production)

```
1. Parse items array from variables
2. Create DBOS queue with concurrency limit
3. For each item:
   - Create child workflow context with ${item} variable
   - Enqueue as separate DBOS workflow
4. Wait for all tasks to complete
5. Collect results into array
```

**Each item gets:**
- Separate DBOS workflow (durable, resumable)
- Access to all parent variables + `${item}`
- Independent error handling

### Without DBOS (Fallback)

Executes items **sequentially** with same semantics but no parallelism.

## Examples

### 1. Simple File Writing

```yaml
variables:
  pages:
    - slug: "intro"
      content: "Introduction..."
    - slug: "guide"
      content: "User guide..."

steps:
  - name: "save_all_pages"
    type: "foreach"
    items: "${pages}"
    concurrency: 5
    step:
      type: "cli"
      command: "workflows write"
      args:
        data: "${item.content}"
        output: "pages/${item.slug}.md"
```

### 2. Parallel DSPy Processing

```yaml
variables:
  questions:
    - "What is machine learning?"
    - "How do neural networks work?"
    - "What is deep learning?"

steps:
  - name: "answer_all_questions"
    type: "foreach"
    items: "${questions}"
    concurrency: 3
    step:
      type: "dspy"
      signature:
        inputs:
          - name: "question"
            type: "str"
            description: "Question to answer"
        outputs:
          - name: "answer"
            type: "str"
            description: "Detailed answer"
        prompt: |
          Provide a comprehensive answer to the question.
          Include examples and explanations.
      inputs:
        question: "${item}"  # ${item} is the current question string
      output: "answer"
    output: "all_answers"  # Array of all answers
```

### 3. Nested Processing

```yaml
variables:
  topics:
    - name: "AI"
      subtopics: ["ML", "NLP", "CV"]
    - name: "Web"
      subtopics: ["HTML", "CSS", "JS"]

steps:
  - name: "process_topics"
    type: "foreach"
    items: "${topics}"
    concurrency: 2
    step:
      type: "foreach"  # Nested foreach!
      items: "${item.subtopics}"
      concurrency: 3
      step:
        type: "cli"
        command: "content fetch"
        args:
          url: "https://example.com/${item}"  # Inner ${item} is subtopic
```

### 4. Complex Pipeline

```yaml
steps:
  # Step 1: Fetch data for each URL
  - name: "fetch_all"
    type: "foreach"
    items: "${urls}"
    concurrency: 10
    step:
      type: "cli"
      command: "content fetch"
      args:
        url: "${item}"
      output: "content"
    output: "all_content"

  # Step 2: Process each piece of content with AI
  - name: "analyze_all"
    type: "foreach"
    items: "${all_content}"
    concurrency: 5
    step:
      type: "dspy"
      signature: "AnalyzeContent"
      inputs:
        text: "${item.content}"
      output: "analysis"
    output: "all_analyses"
```

## Variable Scoping

Within a foreach step, you have access to:

- **`${item}`** - Current item being processed
- **`${item.field}`** - Access fields if item is an object
- **All parent variables** - From workflow and previous steps

```yaml
variables:
  prefix: "output"
  pages:
    - slug: "guide"
      title: "User Guide"

steps:
  - type: "foreach"
    items: "${pages}"
    step:
      type: "cli"
      args:
        # Access current item
        content: "${item.title}"
        # Access parent variables
        output: "${prefix}/${item.slug}.md"
```

## Concurrency Control

```yaml
- type: "foreach"
  items: "${large_array}"
  concurrency: 5  # Max 5 items processed simultaneously
```

**Guidelines:**
- **I/O-bound tasks** (API calls, file operations): Higher concurrency (10-50)
- **CPU-bound tasks** (DSPy, heavy processing): Lower concurrency (2-5)
- **Rate-limited APIs**: Match concurrency to rate limits

## Error Handling

Errors in individual items don't stop the foreach:

```python
# Results array includes both successes and errors
[
  {"content": "..."},           # Success
  {"error": "...", "index": 1}, # Failed item
  {"content": "..."}            # Success
]
```

**Best Practice:**
```yaml
- type: "foreach"
  items: "${items}"
  step:
    type: "cli"
    command: "..."
    on_error:
      action: "skip"  # Continue processing other items
```

## Performance Characteristics

### With DBOS Queues

| Items | Concurrency | Sequential Time | Parallel Time | Speedup |
|-------|-------------|-----------------|---------------|---------|
| 10    | 5           | 50s             | ~10s          | 5x      |
| 100   | 10          | 500s            | ~50s          | 10x     |
| 1000  | 20          | 5000s           | ~250s         | 20x     |

**Actual speedup depends on:**
- Task duration
- I/O vs CPU bound
- DBOS worker availability
- Database performance

### Fallback (Sequential)

No speedup, but same semantics and error handling.

## DBOS Queue Details

When foreach creates a DBOS queue:

```python
queue = Queue(
    name=f"foreach_{step_name}_{unique_id}",
    worker_concurrency=concurrency  # Max concurrent workers
)
```

**Each item becomes a DBOS workflow:**
- Durable (survives crashes)
- Resumable (picks up where it left off)
- Traceable (workflow ID, status tracking)
- Isolated (independent execution)

## Comparison: Foreach vs Parallel

| Feature | `foreach` | `parallel` |
|---------|-----------|------------|
| **Input** | Array of items | Fixed list of steps |
| **Concurrency** | DBOS queues (true) | Sequential (TODO) |
| **Use Case** | Process N similar items | Run M different tasks |
| **Output** | Array of results | Array of step outputs |
| **Scaling** | Scales with data | Fixed by workflow |

**Use `foreach` when:**
- Processing lists/arrays (pages, users, files)
- Same operation on different data
- Need concurrency control

**Use `parallel` when:**
- Running different operations
- Independent tasks (fetch + analyze + save)
- Fixed set of steps

## Best Practices

1. **Keep Items Small** - Large items slow down serialization
   ```yaml
   # Bad: Huge objects
   items: "${large_documents}"

   # Good: IDs or references
   items: "${document_ids}"
   step:
     # Fetch document inside step
   ```

2. **Set Appropriate Concurrency**
   ```yaml
   # API with rate limit: 10 req/sec
   concurrency: 10

   # CPU-intensive DSPy
   concurrency: 2

   # Fast file operations
   concurrency: 50
   ```

3. **Handle Errors Gracefully**
   ```yaml
   step:
     on_error:
       action: "skip"  # Don't fail entire foreach
   ```

4. **Use Output for Results**
   ```yaml
   - type: "foreach"
     items: "${items}"
     step:
       output: "result"  # Collect this
     output: "all_results"  # Into this array
   ```

## Limitations

- Maximum concurrency: 100 (configurable in schema)
- Items must be JSON-serializable
- DBOS required for true parallelism
- No shared state between items (by design)

## Troubleshooting

**"DBOS not available, executing sequentially"**
- DBOS is not installed or failed to initialize
- Workflow runs sequentially (slower but functional)
- Check DBOS setup: `kurt workflows validate`

**"Foreach items must be a list"**
- The `items` variable is not an array
- Check variable substitution: `items: "${array_var}"`

**Tasks failing silently**
- Check error handling: Items may be skipped
- Review output array for `{"error": "..."}` entries

**Slow execution with DBOS**
- Check concurrency setting
- Monitor database performance
- Verify worker availability

## Internal Implementation

See [executor.py:317-442](../src/kurt/workflows/executor.py#L317-L442) for implementation details.

**Key methods:**
- `_execute_foreach_step()` - Entry point, checks DBOS availability
- `_execute_foreach_with_dbos()` - DBOS queue-based parallel execution
- `_execute_foreach_sequential()` - Fallback sequential execution
