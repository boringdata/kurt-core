# Answer Command Testing Summary

## ✅ Implementation Complete

### What Was Built

1. **Answer Command** (`kurt answer "question"`)
   - GraphRAG-based local search retrieval
   - Entity embedding similarity search
   - 1-hop relationship traversal
   - Document retrieval and ranking
   - LLM answer generation with DSPy
   - Citations, confidence scores, sources

2. **Configuration**
   - Added `ANSWER_LLM_MODEL` config (default: `openai/gpt-4o`)
   - Separate from indexing LLM for flexibility

3. **Evaluation Framework**
   - 6 comprehensive scenarios (07-12)
   - 40 total assertions across scenarios
   - 16 setup commands for pre-populating KGs
   - Complete documentation

## 📊 Validation Results

### Scenario Configuration
✅ **All 12 scenarios registered** (6 existing + 6 new answer scenarios)
✅ **YAML syntax valid** - No parsing errors
✅ **All assertions properly defined** - 40 total for answer scenarios
✅ **Setup commands configured** - Pre-existing project setups working
✅ **Mock data exists** - 13 mock files ready (7 docs + 6 blog posts)

### Scenario Breakdown

| Scenario | Assertions | Setup Cmds | Tests |
|----------|-----------|------------|-------|
| 07_answer_basic | 10 | 3 | Core functionality, KG population, output format |
| 08_answer_verbose | 8 | 3 | Verbose flag, retrieval stats display |
| 09_answer_multi_question | 7 | 3 | Multiple questions, KG consistency |
| 10_answer_max_docs | 4 | 3 | Document limiting with --max-docs |
| 11_answer_comparison | 7 | 4 | Multi-source synthesis, rich KG |
| 12_answer_empty_kg | 4 | 0 | Graceful error handling |

### Mock Data Quality
✅ **acme-docs** (7 files): Technical documentation
   - getting-started.md, api-reference.md, authentication guide, etc.
   - Rich content with code examples, prerequisites, tutorials

✅ **acme-corp** (6 files): Company blog
   - Home, about, pricing, 3 blog posts
   - Marketing and product content

✅ **Sitemaps included** for both sites
✅ **No network calls needed** - All HTTP mocked

## 🚀 Running the Tests

### Prerequisites

You need API keys for the eval framework to run:

```bash
# Required: Anthropic API (for Claude Agent SDK)
export ANTHROPIC_API_KEY="sk-ant-..."

# Required: OpenAI API (for answer generation and indexing)
export OPENAI_API_KEY="sk-..."
```

Or create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your keys
```

### Run Individual Scenarios

```bash
# Basic answer test with pre-populated KG
uv run eval/cli.py run 7

# Verbose mode test
uv run eval/cli.py run 8

# Multiple questions test
uv run eval/cli.py run 9

# Max docs control
uv run eval/cli.py run 10

# Comparison across sources
uv run eval/cli.py run 11

# Empty KG handling
uv run eval/cli.py run 12
```

### Run All Answer Scenarios

```bash
for i in 7 8 9 10 11 12; do
  echo "Running scenario $i..."
  uv run eval/cli.py run $i
done
```

### Debug Mode

Keep workspace to inspect database and files:
```bash
uv run eval/cli.py run 7 --no-cleanup
# Workspace location will be shown: /tmp/kurt_eval_<uuid>/
```

### What Happens During Test

Each scenario:
1. **Setup Phase** (if setup_commands defined):
   - Creates isolated temp workspace
   - Runs `kurt init`
   - Maps URLs: `kurt content map url http://docs.acme-corp.com`
   - Fetches content: `kurt content fetch`
   - Indexes to build KG: `kurt content index`
   - HTTP requests are mocked - no network calls!

2. **Execution Phase**:
   - Agent receives initial prompt
   - Invokes `kurt answer "question"` command
   - Answer command:
     - Generates query embedding
     - Searches similar entities (vector similarity)
     - Traverses relationships (1-hop)
     - Retrieves connected documents
     - Synthesizes answer with LLM
     - Returns: Answer + Confidence + Entities + Sources

3. **Validation Phase**:
   - Checks database state (entities, docs, relationships)
   - Verifies output format (Answer, Confidence, Sources)
   - Validates content accuracy (ACME-related content)
   - Confirms conversation completion

4. **Results**:
   - Saved to `eval/results/`
   - JSON file with metrics and assertions
   - Markdown transcript of full conversation

## 📈 Expected Results

### Scenario 07 (Basic)
- **KG Population**: ≥5 entities, ≥3 documents, ≥3 relationships
- **Output**: Contains "Answer:", "Confidence", "Key Entities", "Sources", "ACME"
- **Pass Criteria**: All 10 assertions pass

### Scenario 08 (Verbose)
- **Additional Output**: "Retrieval Stats", "Entities found", "Documents found"
- **Pass Criteria**: All 8 assertions pass

### Scenario 09 (Multi-question)
- **Multiple Invocations**: ≥3 tool calls
- **Multiple Turns**: ≥2 conversation turns
- **Pass Criteria**: All 7 assertions pass

### Scenario 10 (Max Docs)
- **Flag Usage**: --max-docs 3 respected
- **Pass Criteria**: All 4 assertions pass

### Scenario 11 (Comparison)
- **Rich KG**: ≥10 entities, ≥5 relationships
- **Multiple Sources**: Both acme-corp and acme-docs indexed
- **Pass Criteria**: All 7 assertions pass

### Scenario 12 (Empty KG)
- **Empty State**: 0 entities, 0 documents
- **Graceful Handling**: No crashes, helpful message
- **Pass Criteria**: All 4 assertions pass

## 🔍 Debugging Failed Tests

### Check Workspace
```bash
uv run eval/cli.py run 7 --no-cleanup
cd /tmp/kurt_eval_<uuid>/
sqlite3 .kurt/kurt.sqlite "SELECT COUNT(*) FROM entities;"
ls -la sources/
```

### Review Transcript
```bash
cat eval/results/07_answer_basic_<timestamp>.md
```

### Check Logs
```bash
# Check if indexing worked
grep "index" eval/results/07_answer_basic_<timestamp>.md

# Check if answer command ran
grep "kurt answer" eval/results/07_answer_basic_<timestamp>.md
```

### Common Issues

**No entities extracted**:
- Check OPENAI_API_KEY is set
- Verify indexing ran: `kurt content index`
- Check mock data loaded correctly

**Answer command not found**:
- Ensure kurt was installed in eval environment
- Check CLI registration in `src/kurt/cli.py`

**Timeout**:
- Increase duration: `--max-duration 900`
- Check API availability
- Reduce max-docs if needed

## 📝 Key Features Demonstrated

✅ **Pre-existing Project Setup** - `setup_commands` populates KG before agent starts
✅ **Mock HTTP Data** - No real network calls, fast & reproducible
✅ **Comprehensive Assertions** - DB state, output format, content accuracy
✅ **Multiple Test Scenarios** - Basic, verbose, multi-question, limiting, synthesis, error handling
✅ **Realistic Data** - Rich mock content with ACME API documentation and blog

## 🎯 Next Steps

1. **Get API Keys**: Set ANTHROPIC_API_KEY and OPENAI_API_KEY
2. **Run Tests**: Start with `uv run eval/cli.py run 7`
3. **Review Results**: Check `eval/results/` for transcripts
4. **Iterate**: Adjust scenarios based on results
5. **Add More**: Create new scenarios for edge cases

## 📚 Documentation

- **Scenario Definitions**: `eval/scenarios/scenarios.yaml`
- **Scenario Guide**: `eval/ANSWER_SCENARIOS.md`
- **Mock Data**: `eval/mock/websites/`
- **Framework Docs**: `eval/framework/`
- **Answer Implementation**:
  - `src/kurt/commands/answer.py` (CLI)
  - `src/kurt/content/answer.py` (GraphRAG logic)

## 🔗 References

- [BYOKG-RAG (EMNLP 2025)](https://aclanthology.org/2025.emnlp-main.1417/)
- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk)
- [DSPy Framework](https://github.com/stanfordnlp/dspy)

---

**Status**: ✅ Ready to test (requires API keys)
**Scenarios**: 6 configured and validated
**Mock Data**: 13 files ready
**Total Assertions**: 40
