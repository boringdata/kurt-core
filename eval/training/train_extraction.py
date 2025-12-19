#!/usr/bin/env python3
"""
DSPy Training Script for IndexDocument Extraction

Usage:
    # Train with default settings
    python eval/training/train_extraction.py

    # Train with specific model
    python eval/training/train_extraction.py --model claude-3-5-sonnet-latest

    # Quick test run (fewer examples)
    python eval/training/train_extraction.py --quick

    # Use MIPROv2 optimizer (better quality, slower)
    python eval/training/train_extraction.py --optimizer mipro

How DSPy Training Works:
========================
1. Load training examples (document -> entities, relationships, claims)
2. Define a metric function to score predictions
3. Use an optimizer (BootstrapFewShot) that:
   - Runs the signature on training examples
   - Collects successful demonstrations
   - Creates few-shot examples for the prompt
4. Save the optimized program with tuned prompts

The optimized program contains:
- Few-shot demonstrations selected from training data
- Potentially modified instructions (with MIPROv2)
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import dspy
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")

# ============================================================================
# Data Loading
# ============================================================================


def load_training_data(split_ratio: tuple = (0.8, 0.1, 0.1), quick: bool = False):
    """Load and split training data into train/dev/test sets."""
    data_file = Path(__file__).parent / "dataset" / "extraction" / "train.jsonl"

    examples = []
    with open(data_file) as f:
        for line in f:
            data = json.loads(line)

            # Read the source document content
            source_file = data.get("_source_file", "")
            doc_path = (
                Path(__file__).parent / "dataset" / "kurt-training-dump" / "sources" / source_file
            )

            if doc_path.exists():
                document_content = doc_path.read_text()[:5000]  # First 5000 chars like pipeline
            else:
                continue

            # Create DSPy Example
            example = dspy.Example(
                # Inputs
                document_content=document_content,
                existing_entities="[]",
                # Expected outputs (gold standard)
                gold_metadata=data.get("metadata", {}),
                gold_entities=data.get("entities", []),
                gold_relationships=data.get("relationships", []),
                gold_claims=data.get("claims", []),
            ).with_inputs("document_content", "existing_entities")

            examples.append(example)

    # Shuffle
    random.seed(42)
    random.shuffle(examples)

    if quick:
        examples = examples[:15]  # Just 15 for quick test

    # Split
    n = len(examples)
    train_end = int(n * split_ratio[0])
    dev_end = train_end + int(n * split_ratio[1])

    train_set = examples[:train_end]
    dev_set = examples[train_end:dev_end]
    test_set = examples[dev_end:]

    print(f"Loaded {n} examples: train={len(train_set)}, dev={len(dev_set)}, test={len(test_set)}")

    return train_set, dev_set, test_set


# ============================================================================
# DSPy Signature (simplified for training)
# ============================================================================


class ExtractKnowledge(dspy.Signature):
    """Extract structured knowledge from technical documentation.

    Extract:
    1. ENTITIES: Named concepts (Products, Features, Technologies, Topics, Companies)
    2. RELATIONSHIPS: How entities connect (part_of, integrates_with, enables, etc.)
    3. CLAIMS: Factual statements with source quotes

    Be thorough - extract 5-15 entities, 5-10 relationships, 10-20 claims.
    """

    document_content: str = dspy.InputField(desc="Markdown document content")
    existing_entities: str = dspy.InputField(default="[]", desc="Known entities JSON")

    entities: str = dspy.OutputField(desc="JSON array of extracted entities")
    relationships: str = dspy.OutputField(desc="JSON array of entity relationships")
    claims: str = dspy.OutputField(desc="JSON array of factual claims with quotes")


# ============================================================================
# Metrics
# ============================================================================


def extraction_metric(example, prediction, trace=None) -> float:
    """
    Score extraction quality.

    Compares:
    - Entity coverage (recall): how many gold entities were found
    - Claim coverage: how many claims were extracted
    - Relationship coverage: how many relationships were found

    Returns score 0.0 - 1.0
    """
    score = 0.0
    total_weight = 0.0

    # Parse prediction outputs (they're JSON strings)
    try:
        pred_entities = (
            json.loads(prediction.entities)
            if isinstance(prediction.entities, str)
            else prediction.entities
        )
    except (json.JSONDecodeError, TypeError):
        pred_entities = []

    try:
        pred_claims = (
            json.loads(prediction.claims)
            if isinstance(prediction.claims, str)
            else prediction.claims
        )
    except (json.JSONDecodeError, TypeError):
        pred_claims = []

    try:
        pred_relationships = (
            json.loads(prediction.relationships)
            if isinstance(prediction.relationships, str)
            else prediction.relationships
        )
    except (json.JSONDecodeError, TypeError):
        pred_relationships = []

    # Get gold data
    gold_entities = example.gold_entities or []
    gold_claims = example.gold_claims or []
    gold_relationships = example.gold_relationships or []

    # 1. Entity recall (weight: 0.4)
    if gold_entities:
        gold_entity_names = {e.get("name", "").lower() for e in gold_entities}
        pred_entity_names = {
            e.get("name", "").lower() if isinstance(e, dict) else "" for e in pred_entities
        }

        if gold_entity_names:
            entity_recall = len(gold_entity_names & pred_entity_names) / len(gold_entity_names)
            score += 0.4 * entity_recall
        total_weight += 0.4

    # 2. Claim count similarity (weight: 0.3)
    if gold_claims:
        gold_claim_count = len(gold_claims)
        pred_claim_count = len(pred_claims)

        # Score based on how close the counts are (prefer more claims up to gold count)
        if gold_claim_count > 0:
            claim_ratio = min(pred_claim_count / gold_claim_count, 1.5)  # Cap at 1.5x
            claim_score = min(claim_ratio, 1.0)  # Perfect if within range
            score += 0.3 * claim_score
        total_weight += 0.3

    # 3. Relationship count (weight: 0.2)
    if gold_relationships:
        gold_rel_count = len(gold_relationships)
        pred_rel_count = len(pred_relationships)

        if gold_rel_count > 0:
            rel_ratio = min(pred_rel_count / gold_rel_count, 1.5)
            rel_score = min(rel_ratio, 1.0)
            score += 0.2 * rel_score
        total_weight += 0.2

    # 4. Valid JSON output bonus (weight: 0.1)
    if pred_entities and pred_claims:
        score += 0.1
    total_weight += 0.1

    return score / total_weight if total_weight > 0 else 0.0


# ============================================================================
# Training
# ============================================================================


def train(
    model: str = "claude-3-5-haiku-latest", quick: bool = False, optimizer_type: str = "bootstrap"
):
    """Run DSPy training optimization."""

    print("=" * 60)
    print("DSPy Training for IndexDocument Extraction")
    print("=" * 60)

    # Configure LM
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    lm = dspy.LM(f"anthropic/{model}", api_key=api_key)
    dspy.configure(lm=lm)
    print(f"Using model: {model}")
    print(f"Using optimizer: {optimizer_type}")

    # Load data
    train_set, dev_set, test_set = load_training_data(quick=quick)

    # Create predictor
    predictor = dspy.Predict(ExtractKnowledge)

    # Configure optimizer based on type
    print("\nStarting optimization...")

    if optimizer_type == "mipro":
        from dspy.teleprompt import MIPROv2

        print("MIPROv2 will:")
        print("  1. Generate candidate instructions")
        print("  2. Optimize both instructions AND demos")
        print("  3. Search for best combination")
        print()

        optimizer = MIPROv2(
            metric=extraction_metric,
            auto="light",  # light/medium/heavy - controls optimization intensity
            max_bootstrapped_demos=3,
            max_labeled_demos=3,
        )

        # MIPROv2 needs both trainset and valset
        optimized = optimizer.compile(
            predictor,
            trainset=train_set,
            valset=dev_set,
        )

    elif optimizer_type == "random":
        from dspy.teleprompt import BootstrapFewShotWithRandomSearch

        print("BootstrapFewShotWithRandomSearch will:")
        print("  1. Run extraction on training examples")
        print("  2. Try multiple demo combinations")
        print("  3. Select best performing set")
        print()

        optimizer = BootstrapFewShotWithRandomSearch(
            metric=extraction_metric,
            max_bootstrapped_demos=4,
            num_candidate_programs=8,  # Try 8 different combinations
        )

        optimized = optimizer.compile(
            predictor,
            trainset=train_set,
            valset=dev_set,
        )

    else:  # default: bootstrap
        from dspy.teleprompt import BootstrapFewShot

        print("BootstrapFewShot will:")
        print("  1. Run extraction on training examples")
        print("  2. Collect successful demonstrations")
        print("  3. Create few-shot prompts")
        print()

        optimizer = BootstrapFewShot(
            metric=extraction_metric,
            max_bootstrapped_demos=3,
            max_labeled_demos=3,
            max_rounds=1,
        )

        optimized = optimizer.compile(
            predictor,
            trainset=train_set,
        )

    # Evaluate on dev set
    print("\n" + "=" * 60)
    print("Evaluation on dev set")
    print("=" * 60)

    total_score = 0.0
    for example in dev_set:
        try:
            pred = optimized(
                document_content=example.document_content,
                existing_entities=example.existing_entities,
            )
            score = extraction_metric(example, pred)
            total_score += score
        except Exception as e:
            print(f"  Error: {e}")

    avg_score = total_score / len(dev_set) if dev_set else 0
    print(f"\nAverage dev score: {avg_score:.3f}")

    # Save optimized program
    output_dir = Path(__file__).parent / "optimized"
    output_dir.mkdir(exist_ok=True)

    # Use optimizer type in filename
    version = f"extraction_{optimizer_type}_v1"
    output_file = output_dir / f"{version}.json"
    optimized.save(str(output_file))
    print(f"\nSaved optimized program to: {output_file}")

    # Also save as readable format
    readable_file = output_dir / f"{version}_readable.json"
    with open(readable_file, "w") as f:
        # Extract the demos from the optimized predictor
        state = optimized.dump_state()
        json.dump(state, f, indent=2, default=str)
    print(f"Saved readable state to: {readable_file}")

    return optimized


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DSPy extraction model")
    parser.add_argument("--model", default="claude-3-5-haiku-latest", help="Model to use")
    parser.add_argument("--quick", action="store_true", help="Quick test with fewer examples")
    parser.add_argument(
        "--optimizer",
        choices=["bootstrap", "random", "mipro"],
        default="bootstrap",
        help="Optimizer: bootstrap (fast), random (better demos), mipro (best, rewrites instructions)",
    )
    args = parser.parse_args()

    train(model=args.model, quick=args.quick, optimizer_type=args.optimizer)
