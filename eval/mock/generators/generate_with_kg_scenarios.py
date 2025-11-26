#!/usr/bin/env python3
"""Generate individual WITH KG scenarios from questions file.

This script creates scenarios_answer_motherduck_with_kg.yaml with 10 individual
non-conversational scenarios (one per question) that can be run in parallel.

Since the eval framework doesn't support test_cases, we put the command
in setup_commands instead.
"""

import sys
import yaml
from pathlib import Path

def main():
    # Load questions
    questions_file = Path("eval/scenarios/questions_motherduck.yaml")
    with open(questions_file) as f:
        data = yaml.safe_load(f)

    questions = data["questions"]

    # Generate scenarios
    scenarios = []

    for i, q_data in enumerate(questions, start=1):
        question = q_data["question"]

        scenario = {
            "name": f"answer_motherduck_with_kg_q{i}",
            "description": f"Answer Q{i} using GraphRAG (WITH knowledge graph)",
            "project": "motherduck",
            "conversational": False,  # Non-conversational for fast execution
            "setup_commands": [
                # Run kurt answer command (database is already loaded from dump)
                f'KURT_TELEMETRY_DISABLED=1 uv run kurt answer "{question}" --output /tmp/answer_with_kg_{i}.md'
            ],
            "assertions": [
                {
                    "type": "FileExists",
                    "path": f"/tmp/answer_with_kg_{i}.md"
                }
            ],
            "post_scenario_commands": [
                f"mkdir -p /Users/julien/Documents/wik/wikumeo/projects/kurt-core/eval/results/answer_motherduck_with_kg_q{i} && cp /tmp/answer_with_kg_{i}.md /Users/julien/Documents/wik/wikumeo/projects/kurt-core/eval/results/answer_motherduck_with_kg_q{i}/$(date +%Y%m%d_%H%M%S)_answer.md"
            ]
        }

        scenarios.append(scenario)

    # Create output YAML
    output = {
        "scenarios": scenarios
    }

    output_file = Path("eval/scenarios/scenarios_answer_motherduck_with_kg.yaml")

    # Write header comment
    with open(output_file, "w") as f:
        f.write("""---
# Kurt Evaluation Scenarios - MotherDuck Question Answering (WITH Knowledge Graph)
#
# Tests the answer command with full knowledge graph (GraphRAG approach)
# Each question runs in a separate non-conversational scenario for parallel execution

""")
        yaml.dump(output, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"✓ Generated {len(scenarios)} WITH KG scenarios (non-conversational)")
    print(f"✓ Written to: {output_file}")


if __name__ == "__main__":
    main()
