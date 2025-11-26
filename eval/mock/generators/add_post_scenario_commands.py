#!/usr/bin/env python3
"""Add post_scenario_commands to copy answer files to results directory.

This script modifies both WITHOUT KG and WITH KG scenario files to add
post-scenario commands that copy answer files from /tmp/ to the results
directory with timestamped filenames.
"""

import yaml
from pathlib import Path


def add_post_commands_to_scenarios(scenario_file: Path, output_prefix: str):
    """Add post_scenario_commands to all scenarios in a file.

    Args:
        scenario_file: Path to YAML file with scenarios
        output_prefix: Prefix for answer files (e.g., 'answer_without_kg' or 'answer_with_kg')
    """
    # Load scenarios
    with open(scenario_file) as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])

    # Add post_scenario_commands to each scenario
    for i, scenario in enumerate(scenarios, start=1):
        scenario_name = scenario["name"]

        # Extract question number from scenario name (e.g., 'q1' -> 1)
        q_num = i

        # Source file in /tmp/
        src_file = f"/tmp/{output_prefix}_{q_num}.md"

        # Destination directory
        dest_dir = f"eval/results/{scenario_name}"

        # Post-scenario command to copy file with timestamp
        post_cmd = f"mkdir -p {dest_dir} && cp {src_file} {dest_dir}/$(date +%Y%m%d_%H%M%S)_answer.md"

        # Add post_scenario_commands field
        scenario["post_scenario_commands"] = [post_cmd]

        print(f"✓ Added post_scenario_commands to {scenario_name}")

    # Write back to file
    # Preserve the header comments by reading the original file first
    with open(scenario_file) as f:
        original_content = f.read()

    # Extract header comments (lines starting with # before the YAML starts)
    lines = original_content.split('\n')
    header_lines = []
    yaml_start_idx = 0

    for idx, line in enumerate(lines):
        if line.strip().startswith('---'):
            yaml_start_idx = idx
            continue
        if yaml_start_idx == 0 or (line.strip().startswith('#') or line.strip() == ''):
            header_lines.append(line)
        else:
            break

    # Write header + new YAML
    with open(scenario_file, 'w') as f:
        if header_lines:
            f.write('\n'.join(header_lines))
            f.write('\n')
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"✓ Updated {scenario_file}")


def main():
    """Main entry point."""

    # Process WITHOUT KG scenarios
    without_kg_file = Path("eval/scenarios/scenarios_answer_motherduck_without_kg.yaml")
    print("\n" + "="*80)
    print("Processing WITHOUT KG scenarios...")
    print("="*80)
    add_post_commands_to_scenarios(without_kg_file, "answer_without_kg")

    print()

    # Process WITH KG scenarios
    with_kg_file = Path("eval/scenarios/scenarios_answer_motherduck_with_kg.yaml")
    print("="*80)
    print("Processing WITH KG scenarios...")
    print("="*80)
    add_post_commands_to_scenarios(with_kg_file, "answer_with_kg")

    print("\n" + "="*80)
    print("✅ Complete!")
    print("="*80)
    print("\nAnswer files will now be copied to results directories with timestamps:")
    print("  WITHOUT KG: eval/results/answer_motherduck_without_kg_q{1-10}/<timestamp>_answer.md")
    print("  WITH KG:    eval/results/answer_motherduck_with_kg_q{1-10}/<timestamp>_answer.md")


if __name__ == "__main__":
    main()
