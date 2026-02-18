# DSPy Training Plan for Indexing Pipeline

## Overview

This plan outlines the process to create training data and optimize the DSPy modules in Kurt's indexing pipeline using DSPy optimizers.

## Phase 1: Training Data Collection

### 1.1 Create Kurt Training Project

**Location**: `/kurt-training/` (new directory at project root)

```bash
mkdir kurt-training
cd kurt-training
uv run kurt init
```

### 1.2 Training URLs (50 pages from 10 providers)

Select 5 pages per provider covering different content types:
- Landing page
- Feature/product page
- Documentation/reference page
- Tutorial/guide
- Integration/comparison page

**Selected Developer Tool Providers:**

| Provider | Domain | Focus |
|----------|--------|-------|
| Stripe | stripe.com/docs | Payment APIs |
| Vercel | vercel.com/docs | Deployment platform |
| Supabase | supabase.com/docs | Backend-as-a-service |
| Cloudflare | developers.cloudflare.com | Edge computing |
| Datadog | docs.datadoghq.com | Monitoring |
| Tailwind CSS | tailwindcss.com/docs | CSS framework |
| Next.js | nextjs.org/docs | React framework |
| Prisma | prisma.io/docs | Database ORM |
| PlanetScale | planetscale.com/docs | Serverless MySQL |
| Resend | resend.com/docs | Email API |

### 1.3 Fetch Training URLs via Kurt

```bash
cd kurt-training

# Add each provider's URLs
uv run kurt url add https://stripe.com/docs/payments
uv run kurt url add https://stripe.com/docs/api
# ... (all 50 URLs)

# Fetch content
uv run kurt url fetch
```

---

## Phase 2: Training Data Structure

### 2.1 Directory Structure

```
eval/training/dataset/
├── kurt-training-dump/          # Kurt project dump
│   ├── database/
│   │   ├── documents.jsonl
│   │   ├── entities.jsonl
│   │   └── ...
│   └── sources/                 # Markdown content files
│
├── extraction/                  # IndexDocument signature training
│   ├── train.jsonl             # ~50 training examples
│   ├── dev.jsonl               # ~10 dev examples
│   └── test.jsonl              # ~10 test examples
│
├── entity_resolution/           # ResolveEntityGroup signature training
│   ├── train.jsonl
│   ├── dev.jsonl
│   └── test.jsonl
│
├── claim_resolution/            # Future claim resolution signature
│   ├── train.jsonl
│   ├── dev.jsonl
│   └── test.jsonl
│
└── README.md                    # Dataset documentation
```

### 2.2 DSPy Example Format for Each Step

#### IndexDocument (Extraction)

```python
dspy.Example(
    # Inputs
    document_content="...",  # First 5000 chars of markdown
    existing_entities="[]",  # JSON list of existing entities

    # Outputs (gold standard - manually created)
    metadata={
        "content_type": "REFERENCE",
        "has_code_examples": True,
        "has_step_by_step_procedures": False,
        "has_narrative_structure": False
    },
    entities=[
        {
            "name": "Stripe",
            "entity_type": "Company",
            "description": "Payment processing platform",
            "aliases": ["Stripe Inc"],
            "confidence": 0.95,
            "resolution_status": "NEW",
            "quote": "Stripe is a technology company..."
        },
        # ... more entities
    ],
    relationships=[
        {
            "source_entity": "Stripe API",
            "target_entity": "Stripe",
            "relationship_type": "part_of",
            "context": "The Stripe API is part of Stripe's core offering",
            "confidence": 0.9
        },
        # ... more relationships
    ],
    claims=[
        {
            "statement": "Stripe supports over 135 currencies",
            "claim_type": "capability",
            "entity_indices": [0],  # References Stripe
            "source_quote": "Accept payments in over 135 currencies...",
            "quote_start_offset": 1234,
            "quote_end_offset": 1290,
            "confidence": 0.95
        },
        # ... more claims
    ]
).with_inputs("document_content", "existing_entities")
```

#### ResolveEntityGroup (Entity Resolution)

```python
dspy.Example(
    # Inputs
    group_entities=[
        {"name": "Next.js", "type": "Technology", "description": "React framework", "aliases": [], "confidence": 0.9},
        {"name": "NextJS", "type": "Technology", "description": "Framework for React", "aliases": [], "confidence": 0.85}
    ],
    existing_candidates=[
        {"id": "abc123", "name": "Next.js", "type": "Technology", "description": "The React Framework for Production", "aliases": ["NextJS"]}
    ],

    # Outputs (gold standard)
    resolutions={
        "resolutions": [
            {
                "entity_index": 0,
                "decision_type": "LINK_TO_EXISTING",
                "target_index": 0,
                "canonical_name": "Next.js",
                "aliases": ["NextJS"],
                "reasoning": "Exact match with existing entity"
            },
            {
                "entity_index": 1,
                "decision_type": "MERGE_WITH_PEER",
                "target_index": 0,
                "canonical_name": "Next.js",
                "aliases": ["NextJS"],
                "reasoning": "Same technology, different casing"
            }
        ]
    }
).with_inputs("group_entities", "existing_candidates")
```

---

## Phase 3: Manual Training Data Creation

### 3.1 Process for Each Document

For each of the 50 fetched documents:

1. **Read the document content** (first 5000 chars)
2. **Identify content type** (REFERENCE, TUTORIAL, GUIDE, etc.)
3. **Extract entities manually**:
   - Products (Stripe, Vercel, etc.)
   - Features (Payment Links, Edge Functions)
   - Technologies (Node.js, TypeScript)
   - Topics (API authentication, webhooks)
   - Companies (parent companies, partners)
   - Integrations (with other services)
4. **Define relationships** between entities
5. **Extract claims** with exact quotes and offsets
6. **Write DSPy Example** to JSONL file

### 3.2 Quality Guidelines

**Entities:**
- Only extract entities prominently discussed (not just mentioned)
- Provide clear descriptions (1-2 sentences)
- Include common aliases
- Set appropriate confidence (0.7-1.0)

**Relationships:**
- Use correct RelationshipType from enum
- Provide context snippet showing the relationship
- Set confidence based on explicitness

**Claims:**
- Extract factual, verifiable statements
- Include exact source quotes (50-500 chars)
- Calculate accurate character offsets
- Link to relevant entities via indices
- Cover all ClaimTypes: capability, limitation, definition, feature, instruction, etc.

---

## Phase 4: DSPy Training Utilities

### 4.1 Create Training Data Loader

```python
# eval/training/loader.py

from pathlib import Path
import json
import dspy

def load_extraction_dataset(split: str = "train") -> list[dspy.Example]:
    """Load IndexDocument training examples."""
    dataset_path = Path(__file__).parent / "dataset" / "extraction" / f"{split}.jsonl"

    examples = []
    with open(dataset_path) as f:
        for line in f:
            data = json.loads(line)
            example = dspy.Example(**data).with_inputs("document_content", "existing_entities")
            examples.append(example)

    return examples

def load_entity_resolution_dataset(split: str = "train") -> list[dspy.Example]:
    """Load ResolveEntityGroup training examples."""
    dataset_path = Path(__file__).parent / "dataset" / "entity_resolution" / f"{split}.jsonl"

    examples = []
    with open(dataset_path) as f:
        for line in f:
            data = json.loads(line)
            example = dspy.Example(**data).with_inputs("group_entities", "existing_candidates")
            examples.append(example)

    return examples
```

### 4.2 Dump Kurt Project to Dataset

```bash
# After fetching all URLs in kurt-training
python eval/framework/dumps/creator.py ../kurt-training kurt-training-dump
```

---

## Phase 5: Training Script

### 5.1 Training Approach

Use **BootstrapFewShotWithRandomSearch** for ~50 examples:
- Generates demonstrations from training data
- Tests multiple candidate programs
- Selects best performing configuration

### 5.2 Training Script Structure

```python
# eval/training/train_extraction.py

import dspy
from dspy.teleprompt import BootstrapFewShotWithRandomSearch

from kurt.content.indexing.step_extract_sections import IndexDocument
from eval.training.loader import load_extraction_dataset
from eval.training.metrics import extraction_accuracy

def train_extraction():
    # Load datasets
    train_set = load_extraction_dataset("train")
    dev_set = load_extraction_dataset("dev")

    # Configure LM
    lm = dspy.LM("anthropic/claude-3-5-sonnet-latest")
    dspy.configure(lm=lm)

    # Create module to optimize
    predictor = dspy.Predict(IndexDocument)

    # Configure optimizer
    optimizer = BootstrapFewShotWithRandomSearch(
        metric=extraction_accuracy,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
        num_candidate_programs=8,
        num_threads=4
    )

    # Run optimization
    optimized_predictor = optimizer.compile(
        predictor,
        trainset=train_set,
        valset=dev_set
    )

    # Save optimized program
    optimized_predictor.save("eval/training/optimized/extraction_v1.json")

    return optimized_predictor

if __name__ == "__main__":
    train_extraction()
```

### 5.3 Metrics Functions

```python
# eval/training/metrics.py

def extraction_accuracy(example, prediction, trace=None):
    """Compute accuracy for IndexDocument extraction."""
    score = 0.0
    total = 0.0

    # Check content_type accuracy
    total += 1.0
    if prediction.metadata.content_type == example.metadata["content_type"]:
        score += 1.0

    # Check entity recall (how many gold entities were found)
    gold_entity_names = {e["name"].lower() for e in example.entities}
    pred_entity_names = {e.name.lower() for e in prediction.entities}

    if gold_entity_names:
        total += 1.0
        entity_recall = len(gold_entity_names & pred_entity_names) / len(gold_entity_names)
        score += entity_recall

    # Check claim coverage
    gold_claim_count = len(example.claims)
    pred_claim_count = len(prediction.claims)

    if gold_claim_count > 0:
        total += 1.0
        claim_coverage = min(pred_claim_count / gold_claim_count, 1.0)
        score += claim_coverage

    return score / total if total > 0 else 0.0


def entity_resolution_accuracy(example, prediction, trace=None):
    """Compute accuracy for ResolveEntityGroup resolution."""
    gold_decisions = {r["entity_index"]: r["decision_type"] for r in example.resolutions["resolutions"]}
    pred_decisions = {r.entity_index: r.decision_type for r in prediction.resolutions.resolutions}

    if not gold_decisions:
        return 1.0

    correct = sum(1 for idx, dec in gold_decisions.items() if pred_decisions.get(idx) == dec)
    return correct / len(gold_decisions)
```

---

## Phase 6: Execution Plan

### Step 1: Setup (~1 hour)
- [ ] Create `kurt-training/` directory
- [ ] Initialize Kurt project
- [ ] Create `eval/training/dataset/` structure

### Step 2: URL Collection (~2 hours)
- [ ] Compile list of 50 URLs (5 per provider)
- [ ] Add URLs via `kurt url add`
- [ ] Fetch all content via `kurt url fetch`
- [ ] Dump project to `eval/training/dataset/kurt-training-dump/`

### Step 3: Training Data Creation (Main Effort)
- [ ] Create 50 IndexDocument training examples (manual extraction)
- [ ] Create 50 ResolveEntityGroup training examples (from real clustering scenarios)
- [ ] Split into train/dev/test (50/10/10)
- [ ] Create JSONL files

### Step 4: Training Infrastructure
- [ ] Create `eval/training/loader.py`
- [ ] Create `eval/training/metrics.py`
- [ ] Create `eval/training/train_extraction.py`
- [ ] Create `eval/training/train_entity_resolution.py`

### Step 5: Training Execution
- [ ] Run extraction training
- [ ] Run entity resolution training
- [ ] Evaluate on test set
- [ ] Save optimized models

### Step 6: Integration
- [ ] Load optimized prompts in production pipeline
- [ ] A/B test against baseline
- [ ] Document improvements

---

## Expected Outputs

1. **Training Dataset**:
   - `eval/training/dataset/extraction/` (70 examples)
   - `eval/training/dataset/entity_resolution/` (70 examples)

2. **Optimized Models**:
   - `eval/training/optimized/extraction_v1.json`
   - `eval/training/optimized/entity_resolution_v1.json`

3. **Documentation**:
   - Dataset README with annotation guidelines
   - Training results and metrics

---

## Notes

- Training budget estimate: $5-20 for BootstrapFewShotWithRandomSearch
- Time estimate: ~10 minutes per optimization run
- Can start with smaller dataset (20 examples) for faster iteration
