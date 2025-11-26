# Answer Command Evaluation Scenarios

This document describes the evaluation scenarios for the new `kurt answer` GraphRAG-based question answering command.

## Overview

The answer command uses a local search GraphRAG strategy to answer questions from indexed content:
1. **Query Embedding**: Generates embedding for the question
2. **Entity Search**: Finds similar entities using vector similarity
3. **Graph Traversal**: Expands context by following relationships (1-hop)
4. **Document Retrieval**: Gets documents connected to entities
5. **Answer Generation**: LLM synthesizes answer with citations and confidence

## Scenarios

### 07: Basic Question with Pre-populated KG
**Purpose**: Test basic functionality with indexed ACME documentation

**Setup**:
- Fetches ACME docs (mock data)
- Indexes content to build knowledge graph
- Pre-populates entities, relationships, documents

**Tests**:
- Knowledge graph population (entities, docs, relationships)
- Answer command execution
- Output includes: Answer, Confidence, Key Entities, Sources
- ACME-related content in answer

**Run**:
```bash
uv run kurt-eval run 07_answer_basic
```

### 08: Verbose Mode
**Purpose**: Test --verbose flag for retrieval statistics

**Setup**: Same as scenario 07 (ACME docs indexed)

**Tests**:
- Verbose output includes retrieval stats
- Shows: Entities found, Documents found, Entity similarity scores
- All standard answer components present

**Run**:
```bash
uv run kurt-eval run 08_answer_verbose
```

### 09: Multiple Questions
**Purpose**: Test handling multiple sequential questions

**Setup**: ACME docs indexed

**Tests**:
- Multiple answer command invocations in one conversation
- Knowledge graph consistency across questions
- Different question types (factual, how-to, integration)
- Confidence scores for each answer

**Run**:
```bash
uv run kurt-eval run 09_answer_multi_question
```

### 10: Max Documents Control
**Purpose**: Test --max-docs flag for retrieval control

**Setup**: ACME docs indexed

**Tests**:
- Document retrieval limiting works
- Answer quality with limited docs
- Flag parsing and application

**Run**:
```bash
uv run kurt-eval run 10_answer_max_docs
```

### 11: Comparison Questions
**Purpose**: Test synthesis across multiple sources

**Setup**:
- Fetches both ACME Corp blog and ACME documentation
- Richer knowledge graph with more entities and relationships

**Tests**:
- Multiple sources indexed
- Entity extraction from diverse content
- Relationship building across sources
- Answer synthesis from multiple documents
- Comparison/synthesis question handling

**Run**:
```bash
uv run kurt-eval run 11_answer_comparison
```

### 12: Empty Knowledge Graph
**Purpose**: Test graceful handling with no indexed content

**Setup**: No setup - empty knowledge graph

**Tests**:
- Graceful error handling
- Helpful message to user
- No crash or exception
- Conversation completes successfully

**Run**:
```bash
uv run kurt-eval run 12_answer_empty_kg
```

## Key Features Tested

### Pre-existing Project Setup
All scenarios (except #12) use `setup_commands` to pre-populate the knowledge graph:

```yaml
setup_commands:
  - uv run kurt content map url http://docs.acme-corp.com
  - uv run kurt content fetch
  - uv run kurt content index
```

This demonstrates the opt-in feature for pre-existing Kurt project setups as starting points.

### Mock Data Leverage
All scenarios use mock HTTP data from `eval/mock/websites/`:
- **acme-docs/** (6 pages): Technical documentation
- **acme-corp/** (6 pages): Company blog

No real network calls - fast, reproducible, no API costs!

### Comprehensive Assertions
Each scenario includes assertions for:
- **Database state**: Entity counts, document counts, relationship counts
- **Output format**: Answer components, confidence, citations
- **Content accuracy**: ACME-related content, entity relevance
- **Completion**: Successful conversation ending

## Running Scenarios

### List all scenarios
```bash
uv run kurt-eval list
```

### Run specific scenario
```bash
# By number
uv run kurt-eval run 7

# By name
uv run kurt-eval run 07_answer_basic
```

### Keep workspace for debugging
```bash
uv run kurt-eval run 7 --no-cleanup
```

### Use different LLM provider
```bash
# Default: OpenAI gpt-4o-mini
uv run kurt-eval run 7

# Use Anthropic claude-3-5-haiku
uv run kurt-eval run 7 --llm-provider anthropic
```

### Adjust limits
```bash
uv run kurt-eval run 7 --max-tool-calls 100 --max-duration 600
```

## Results

After running, results are saved to `eval/results/`:
- `{scenario_name}_{timestamp}.json` - Metrics, assertions, pass/fail
- `{scenario_name}_{timestamp}.md` - Full conversation transcript

## Metrics Collected

For each scenario, the framework collects:
- **Conversation metrics**: Turns, tool calls, duration, completion
- **File operations**: Files created, read, written
- **Database state**: Entities, documents, relationships
- **Tool usage**: Which tools were called, how often
- **Skills/Commands**: Which skills and slash commands were invoked

## Troubleshooting

### Scenario fails with "No entities found"
- Check that `kurt content index` ran successfully in setup_commands
- Verify mock data is present in `eval/mock/websites/`
- Check that indexing LLM is configured (OPENAI_API_KEY)

### Scenario times out
- Increase timeout: `--max-duration 900` (15 minutes)
- Check LLM API availability
- Review transcript to see where it's stuck

### Assertions fail
- Use `--no-cleanup` to keep workspace
- Inspect database: `sqlite3 .kurt/kurt.sqlite`
- Review transcript in results/
- Check logs for indexing errors

## Adding New Scenarios

To add new answer evaluation scenarios:

1. **Add to scenarios.yaml**:
```yaml
- name: 13_answer_new_test
  description: Test new feature

  setup_commands:
    - uv run kurt content map url http://docs.acme-corp.com
    - uv run kurt content fetch
    - uv run kurt content index

  initial_prompt: |
    Test the new feature...

  assertions:
    - type: SQLQueryAssertion
      query: SELECT COUNT(*) >= 5 FROM entities
    # Add more assertions...
```

2. **Run the scenario**:
```bash
uv run kurt-eval run 13
```

3. **Review results** and iterate

## Related Files

- **Scenarios**: `eval/scenarios/scenarios.yaml`
- **Mock data**: `eval/mock/websites/`
- **Framework**: `eval/framework/`
- **Answer implementation**:
  - `src/kurt/commands/answer.py` (CLI)
  - `src/kurt/content/answer.py` (GraphRAG logic)
- **Config**: `src/kurt/config/base.py` (ANSWER_LLM_MODEL)

## References

- GraphRAG Research: [BYOKG-RAG (EMNLP 2025)](https://aclanthology.org/2025.emnlp-main.1417/)
- Microsoft GraphRAG: [https://microsoft.github.io/graphrag/](https://microsoft.github.io/graphrag/)
- Eval Framework: `eval/framework/README.md`
- Mock Data: `eval/mock/README.md`
