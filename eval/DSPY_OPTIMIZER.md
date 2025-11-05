# DSPy Training Data for Kurt Eval

## Overview

The Kurt eval framework **automatically generates DSPy-compatible training data** from every scenario run. Training data is stored natively in DSPy Example format (no conversion needed).

## Quick Start

### 1. Collect Training Data (Automatic)
```bash
# Run scenarios - training data auto-generated
for i in {1..20}; do
  uv run kurt-eval run 03_project_no_sources
done
```

### 2. View Statistics
```bash
# Specific scenario
uv run kurt-eval training stats 03_project_no_sources

# All scenarios
uv run kurt-eval training stats
```

### 3. Export for Optimization
```bash
# Export successful examples
uv run kurt-eval training export 03_project_no_sources --limit 50
```

### 4. Use with DSPy
```python
import dspy
from eval.framework.training_data import TrainingDataCollector

# Load training data (already DSPy format!)
collector = TrainingDataCollector("eval/training_data")
trainset = collector.load_dspy_dataset(
    scenario_name="03_project_no_sources",
    filter_passed=True,
    limit=50,
)

# Optimize immediately (no conversion needed)
optimizer = dspy.MIPROv2(metric=success_metric)
optimized = optimizer.compile(agent_program, trainset=trainset)
```

## What Gets Captured

Each training example contains:
- **Inputs:** Scenario name, initial prompt
- **Execution trace:** Full conversation, tool calls, timing
- **Outputs:** Tool sequence, agent responses, workspace state
- **Metadata:** Success/failure, error classification

## Storage Format

```
eval/training_data/
├── 03_project_no_sources/
│   ├── 2025-11-05T14-30-22.json    # Individual DSPy Examples
│   └── ...
└── 03_project_no_sources_dataset.jsonl  # Aggregated (JSONL)
```

Each file is a DSPy Example in JSON format - ready to load directly.

## CLI Commands

```bash
# View statistics
kurt-eval training stats <scenario>

# Inspect example
kurt-eval training view <scenario> --index 0

# Export dataset
kurt-eval training export <scenario> --limit 50 --format jsonl
```

## Key Design Decision

**Native DSPy Storage** - Training data is stored directly as DSPy Examples:
- ✅ Zero conversion overhead
- ✅ Guaranteed DSPy compatibility
- ✅ Single source of truth
- ✅ Simpler codebase

## Implementation

- **Core:** `eval/framework/training_data.py` - TrainingExample & TrainingDataCollector classes
- **Integration:** `eval/framework/metrics.py` - Auto-generates on every scenario run
- **CLI:** `eval/cli.py` - Management commands (stats, view, export)

## DSPy Example Structure

```json
{
  "scenario": "03_project_no_sources",
  "prompt": "run /create-project",
  "tool_sequence": [...],
  "agent_responses": [...],
  "final_state": {...},
  "conversation": [...],
  "tool_calls": [...],
  "outcome": {
    "success": true,
    "tool_count": 12,
    "duration_seconds": 45.2
  },
  "timestamp": "2025-11-05T14:30:22"
}
```

Fields marked with `with_inputs("scenario", "prompt")` are inputs; rest are outputs/metadata.

---

**Status:** ✅ Complete and production-ready
