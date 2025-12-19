#!/usr/bin/env python3
"""Collect extraction outputs from agents and save to JSONL training file."""

import json
import re
from pathlib import Path

TASKS_DIR = Path(
    "/tmp/claude/-Users-julien-Documents-wik-wikumeo-projects-kurt-core-dspy-training/tasks"
)
OUTPUT_DIR = Path(__file__).parent / "dataset" / "extraction"


def extract_json_from_output(content: str) -> dict | None:
    """Extract JSON from agent output."""
    # Find JSON block in markdown code fence
    json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError as e:
            print(f"  JSON parse error: {e}")
            return None

    # Try to find raw JSON object
    json_match = re.search(r'\{[\s\S]*"metadata"[\s\S]*"entities"[\s\S]*"claims"[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return None

    return None


def get_doc_path_from_output(content: str) -> str | None:
    """Extract document path from agent output."""
    # Look for the source file path in tool calls
    match = re.search(r'sources/([^"]+\.md)', content)
    if match:
        return match.group(1)
    return None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_files = list(TASKS_DIR.glob("*.output"))
    print(f"Found {len(output_files)} agent output files")

    examples = []
    errors = []

    for output_file in sorted(output_files):
        content = output_file.read_text()

        # Extract document path
        doc_path = get_doc_path_from_output(content)

        # Extract JSON
        extraction = extract_json_from_output(content)

        if extraction and doc_path:
            # Add document path to extraction
            extraction["_source_file"] = doc_path
            examples.append(extraction)
            print(f"✓ {doc_path}")
        else:
            errors.append(output_file.name)
            print(f"✗ {output_file.name} - {'no JSON' if not extraction else 'no path'}")

    # Save to JSONL
    train_file = OUTPUT_DIR / "train.jsonl"
    with open(train_file, "w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"\n{'='*60}")
    print(f"Saved {len(examples)} examples to {train_file}")
    print(f"Errors: {len(errors)}")

    # Print stats
    total_entities = sum(len(e.get("entities", [])) for e in examples)
    total_relationships = sum(len(e.get("relationships", [])) for e in examples)
    total_claims = sum(len(e.get("claims", [])) for e in examples)

    print("\nStats:")
    print(f"  Total entities: {total_entities} (avg {total_entities/len(examples):.1f}/doc)")
    print(
        f"  Total relationships: {total_relationships} (avg {total_relationships/len(examples):.1f}/doc)"
    )
    print(f"  Total claims: {total_claims} (avg {total_claims/len(examples):.1f}/doc)")


if __name__ == "__main__":
    main()
