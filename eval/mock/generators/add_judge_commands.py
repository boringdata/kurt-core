#!/usr/bin/env python3
"""Add LLM judge commands to post_scenario_commands for all scenarios.

This script updates both WITH KG and WITHOUT KG scenario files to add
judge evaluation as a second post_scenario_command.
"""

import yaml
from pathlib import Path


def add_judge_to_scenarios(scenario_file: Path, approach: str):
    """Add judge command to all scenarios in a file.

    Args:
        scenario_file: Path to scenario YAML file
        approach: Either 'with_kg' or 'without_kg'
    """
    with open(scenario_file) as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])
    updated = 0

    for scenario in scenarios:
        name = scenario.get("name", "")

        # Skip aggregate scenarios
        if "aggregate" in name:
            continue

        # Extract question number from scenario name
        # e.g., answer_motherduck_with_kg_q1 -> 1
        if not name.endswith(tuple(f"_q{i}" for i in range(1, 11))):
            continue

        q_num = int(name.split("_q")[-1])

        # Get absolute path to kurt-core directory and results directory
        kurt_core_dir = Path(__file__).parent.parent.parent.parent.absolute()
        results_dir = kurt_core_dir / "eval" / "results" / f"answer_motherduck_{approach}_q{q_num}"

        # Build new post_scenario_commands that:
        # 1. Find the latest JSON file and extract its timestamp
        # 2. Copy answer file with SAME timestamp
        # 3. Run judge with the same timestamp prefix (all in one command to share TIMESTAMP variable)
        post_cmds = [
            f"LATEST_JSON=$(ls -t {results_dir}/*.json 2>/dev/null | grep -v '_answer.json' | head -1) && "
            f"TIMESTAMP=$(basename \"$LATEST_JSON\" .json) && "
            f"mkdir -p {results_dir} && "
            f"cp /tmp/answer_{approach}_{q_num}.md {results_dir}/${{TIMESTAMP}}_answer.md && "
            f"uv run python {kurt_core_dir}/eval/mock/generators/judge_answer.py "
            f"--results-dir {results_dir} "
            f"--question-num {q_num} "
            f"--prefix $TIMESTAMP"
        ]

        scenario["post_scenario_commands"] = post_cmds

        updated += 1
        print(f"   ✓ {name}: updated with timestamp-matching copy command")

    # Write updated scenarios
    with open(scenario_file, "w") as f:
        # Write header comment
        if "with_kg" in str(scenario_file):
            header = """---
# Kurt Evaluation Scenarios - MotherDuck Question Answering (WITH Knowledge Graph)
#
# Tests the answer command with full knowledge graph (GraphRAG approach)
# Each question runs in a separate non-conversational scenario for parallel execution

"""
        else:
            header = """---
# Kurt Evaluation Scenarios - MotherDuck Question Answering (WITHOUT Knowledge Graph)
#
# Tests the baseline approach without knowledge graph (pure vector search)
# Each question runs in a separate conversational scenario

"""
        f.write(header)
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return updated


def main():
    print("🔧 Adding LLM judge commands to scenario files...")

    # Update WITH KG scenarios
    with_kg_file = Path("eval/scenarios/scenarios_answer_motherduck_with_kg.yaml")
    print(f"\n📝 Updating {with_kg_file}:")
    with_kg_updated = add_judge_to_scenarios(with_kg_file, "with_kg")

    # Update WITHOUT KG scenarios
    without_kg_file = Path("eval/scenarios/scenarios_answer_motherduck_without_kg.yaml")
    print(f"\n📝 Updating {without_kg_file}:")
    without_kg_updated = add_judge_to_scenarios(without_kg_file, "without_kg")

    print(f"\n✅ Done! Updated {with_kg_updated + without_kg_updated} scenarios total")
    print(f"   - WITH KG:    {with_kg_updated} scenarios")
    print(f"   - WITHOUT KG: {without_kg_updated} scenarios")


if __name__ == "__main__":
    main()
