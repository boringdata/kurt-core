# LLM Judge Evaluation Setup

## Overview

This document describes the complete LLM-as-judge evaluation pipeline for comparing GraphRAG (WITH KG) vs Vector-only (WITHOUT KG) approaches to answering MotherDuck questions.

## Architecture

The evaluation pipeline has three phases:

### Phase 1: Answer Generation
Each scenario runs and generates an answer file (`_answer.md`):
- **WITH KG scenarios**: Use `kurt answer` command (GraphRAG approach)
- **WITHOUT KG scenarios**: Use Claude Code SDK conversational sessions (vector search only)

### Phase 2: LLM Judge Evaluation (Per Scenario)
Each scenario's `post_scenario_commands` runs:
1. Copy answer file to timestamped results directory
2. Run LLM judge to evaluate the answer against canonical answer

### Phase 3: Comparison Report
After all scenarios complete, run comparison script to aggregate judge results and compare approaches.

## Files

### Judge Script
**Location**: `eval/mock/generators/judge_answer.py`

**Purpose**: Evaluates a generated answer against a canonical/expected answer using gpt-4o.

**Usage**:
```bash
python eval/mock/generators/judge_answer.py \
  --answer-file /tmp/answer_with_kg_1.md \
  --question-num 1
```

**Inputs**:
- `--answer-file`: Path to generated answer markdown file
- `--question-num`: Question number (1-10)
- Canonical answers from: `eval/scenarios/questions_motherduck.yaml`

**Outputs**:
Writes evaluation metrics to the latest timestamped JSON file in:
- `eval/results/answer_motherduck_with_kg_q{N}/YYYYMMDD_HHMMSS.json`
- `eval/results/answer_motherduck_without_kg_q{N}/YYYYMMDD_HHMMSS.json`

**Evaluation Metrics**:
- **Accuracy** (0-100): Correctness of information
- **Completeness** (0-100): Coverage of key points from canonical answer
- **Clarity** (0-100): Structure and readability
- **Overall** (0-100): Weighted average + summary

**Requirements**:
- `OPENAI_API_KEY` environment variable must be set
- Uses DSPy with gpt-4o model

### Scenario Files

#### WITH KG Scenarios
**Location**: `eval/scenarios/scenarios_answer_motherduck_with_kg.yaml`

**Characteristics**:
- 10 scenarios (q1-q10) - one per question
- Non-conversational (direct command execution)
- Uses `kurt answer` command with full knowledge graph

**Example scenario structure**:
```yaml
- name: answer_motherduck_with_kg_q1
  description: Answer Q1 using GraphRAG (WITH knowledge graph)
  project: motherduck
  conversational: false
  setup_commands:
    - KURT_TELEMETRY_DISABLED=1 uv run kurt answer "What file formats..." --output /tmp/answer_with_kg_1.md
  assertions:
    - type: FileExists
      path: /tmp/answer_with_kg_1.md
  post_scenario_commands:
    # 1. Copy answer to timestamped results directory
    - mkdir -p .../eval/results/answer_motherduck_with_kg_q1
      && cp /tmp/answer_with_kg_1.md .../eval/results/answer_motherduck_with_kg_q1/$(date +%Y%m%d_%H%M%S)_answer.md
    # 2. Run LLM judge evaluation
    - python eval/mock/generators/judge_answer.py --answer-file /tmp/answer_with_kg_1.md --question-num 1
```

#### WITHOUT KG Scenarios
**Location**: `eval/scenarios/scenarios_answer_motherduck_without_kg.yaml`

**Characteristics**:
- 10 scenarios (q1-q10) - one per question
- Conversational (Claude Code SDK sessions)
- Uses vector search only (no knowledge graph)

**Example scenario structure**:
```yaml
- name: answer_motherduck_without_kg_q1
  description: Answer Q1 about file formats via conversational mode
  conversational: true
  setup_commands:
    - uv run python .../load_dump.py motherduck --skip-entities
  initial_prompt: |
    Search through the .kurt/sources/ directory to answer this question:

    What file formats are most efficient for loading data into MotherDuck?

    Please:
    1. Search for relevant markdown files in .kurt/sources/
    2. Read the most relevant files
    3. Write a comprehensive answer in markdown format to: /tmp/answer_without_kg_1.md
    4. Include a "Sources" section listing the files you used
  assertions:
    - type: FileExists
      path: /tmp/answer_without_kg_1.md
    - type: FileContains
      path: /tmp/answer_without_kg_1.md
      content: Parquet
  post_scenario_commands:
    # 1. Copy answer to timestamped results directory
    - mkdir -p .../eval/results/answer_motherduck_without_kg_q1
      && cp /tmp/answer_without_kg_1.md .../eval/results/answer_motherduck_without_kg_q1/$(date +%Y%m%d_%H%M%S)_answer.md
    # 2. Run LLM judge evaluation
    - python eval/mock/generators/judge_answer.py --answer-file /tmp/answer_without_kg_1.md --question-num 1
```

### Canonical Answers
**Location**: `eval/scenarios/questions_motherduck.yaml`

**Purpose**: Contains expected/reference answers for all 10 questions.

**Structure**:
```yaml
questions:
  - question: "What file formats are most efficient for loading data into MotherDuck?"
    expected_answer: |
      Parquet is the most efficient file format for loading data into MotherDuck.
      It's a columnar storage format optimized for analytical queries and well-supported by DuckDB.
      Other efficient formats include CSV for simple data and JSON for semi-structured data,
      but Parquet offers the best performance for large-scale analytics.
```

### Generator Scripts

#### `add_judge_commands.py`
**Location**: `eval/mock/generators/add_judge_commands.py`

**Purpose**: Utility script to add judge commands to all scenario files.

**Usage**:
```bash
uv run python eval/mock/generators/add_judge_commands.py
```

Automatically updates both WITH KG and WITHOUT KG scenario files to add the judge command as a second `post_scenario_command`.

#### `compare_approaches.py`
**Location**: `eval/mock/generators/compare_approaches.py`

**Purpose**: Generate comparison report between WITH KG and WITHOUT KG approaches.

**Status**: ✅ Complete - reads from `eval/results/` directories

**Features**:
- Finds latest timestamped JSON files in results directories
- Loads judge evaluation metrics from JSON files
- Calculates average scores across all questions
- Generates detailed markdown comparison report with per-question breakdown
- Outputs both markdown and JSON comparison files

**Usage**:
```bash
python eval/mock/generators/compare_approaches.py
```

All arguments have sensible defaults:
- `--results-dir eval/results`
- `--questions-file eval/scenarios/questions_motherduck.yaml`
- `--output eval/results/comparison_report.md`

## Running the Evaluation

### Step 1: Run WITH KG Scenarios
```bash
# Run all WITH KG scenarios in parallel
uv run python -m eval run answer_motherduck_with_kg_q1 answer_motherduck_with_kg_q2 ... --no-cleanup

# Or run individual scenarios
uv run python -m eval run answer_motherduck_with_kg_q1 --no-cleanup
```

### Step 2: Run WITHOUT KG Scenarios
```bash
# Run all WITHOUT KG scenarios in parallel
uv run python -m eval run answer_motherduck_without_kg_q1 answer_motherduck_without_kg_q2 ... --no-cleanup

# Or run individual scenarios
uv run python -m eval run answer_motherduck_without_kg_q1 --no-cleanup
```

### Step 3: Generate Comparison Report
```bash
python eval/mock/generators/compare_approaches.py
```

This will:
- Read latest timestamped JSON files from `eval/results/`
- Extract judge evaluations from both WITH KG and WITHOUT KG scenarios
- Generate `eval/results/comparison_report.md` with side-by-side comparison
- Generate `eval/results/comparison_report.json` with structured data

## Results Directory Structure

```
eval/results/
├── answer_motherduck_with_kg_q1/
│   ├── 20251126_202306.json          # Metrics + judge evaluation
│   ├── 20251126_202306.md            # Conversation transcript
│   └── 20251126_202306_answer.md     # Generated answer
├── answer_motherduck_with_kg_q2/
│   └── ...
├── answer_motherduck_without_kg_q1/
│   ├── 20251126_203015.json          # Metrics + judge evaluation
│   ├── 20251126_203015.md            # Conversation transcript
│   └── 20251126_203015_answer.md     # Generated answer
└── answer_motherduck_without_kg_q2/
    └── ...
```

## JSON Results Format

Each timestamped JSON file contains:

```json
{
  "scenario_name": "answer_motherduck_with_kg_q1",
  "passed": true,
  "duration_seconds": 45.2,
  "tool_calls": [...],
  "conversation": [...],
  "llm_judge_evaluation": {
    "accuracy": {
      "score": 95,
      "reasoning": "The answer correctly identifies Parquet as the most efficient format..."
    },
    "completeness": {
      "score": 90,
      "reasoning": "Covers all key points from the canonical answer..."
    },
    "clarity": {
      "score": 88,
      "reasoning": "Well-structured with clear sections..."
    },
    "overall": {
      "score": 91,
      "summary": "Excellent answer with accurate information and good coverage"
    },
    "timestamp": "2025-11-26T20:23:06.123456"
  }
}
```

## Environment Variables

The judge script requires:
- `OPENAI_API_KEY`: OpenAI API key for gpt-4o access

## Training Data

Training data generation has been **disabled** (commented out in `eval/framework/metrics.py` lines 240-255) to avoid cluttering the results directory.

If needed in the future, uncomment those lines to generate DSPy training examples.

## Completion Status

1. ✅ Judge script created and tested
2. ✅ All 20 scenarios updated with judge commands
3. ✅ Comparison script updated to read from results directories
4. ⏳ **Next:** Run all scenarios and collect judge evaluations
5. ⏳ **Next:** Generate final comparison report

## Quick Start

To run the complete evaluation pipeline:

```bash
# 1. Run all WITH KG scenarios
for i in {1..10}; do
  uv run python -m eval run answer_motherduck_with_kg_q$i --no-cleanup
done

# 2. Run all WITHOUT KG scenarios
for i in {1..10}; do
  uv run python -m eval run answer_motherduck_without_kg_q$i --no-cleanup
done

# 3. Generate comparison report
python eval/mock/generators/compare_approaches.py

# 4. View the report
cat eval/results/comparison_report.md
```
