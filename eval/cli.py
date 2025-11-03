#!/usr/bin/env python3
"""Kurt Evaluation CLI - Run evaluation scenarios for Kurt agent behavior."""

import sys
from pathlib import Path

import click

# Add eval and project root to path
eval_dir = Path(__file__).parent.resolve()
project_root = eval_dir.parent
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(project_root))

# Import from framework (works for both direct execution and module import)
try:
    from .framework.runner import run_scenario_by_name  # Module import
except ImportError:
    from framework.runner import run_scenario_by_name  # Direct execution


@click.group()
def main():
    """Kurt Evaluation Framework - Test agent behavior with automated scenarios."""
    pass


@main.command()
@click.argument("scenario", type=str)
@click.option("--no-cleanup", is_flag=True, help="Preserve workspace after completion")
@click.option("--max-tool-calls", type=int, default=50, help="Maximum tool calls allowed")
@click.option("--max-duration", type=int, default=300, help="Maximum duration in seconds")
@click.option("--max-tokens", type=int, default=100000, help="Maximum tokens to use")
@click.option(
    "--llm-provider",
    type=click.Choice(["openai", "anthropic"]),
    default="openai",
    help="LLM provider for user agent",
)
def run(scenario, no_cleanup, max_tool_calls, max_duration, max_tokens, llm_provider):
    """Run a single evaluation scenario.

    SCENARIO can be:
    - Scenario number (e.g., "3")
    - Scenario ID (e.g., "03_interactive_project")
    - Scenario name (e.g., "03_project_no_sources")

    Examples:
      kurt-eval run 3
      kurt-eval run 03_interactive_project
      kurt-eval run 3 --no-cleanup
      kurt-eval run 3 --llm-provider anthropic
    """
    scenarios_dir = eval_dir / "scenarios"

    # Convert scenario number to ID if needed
    if scenario.isdigit():
        # Pad to 2 digits
        scenario_id = f"{int(scenario):02d}"
        # Find matching scenario in scenarios.yaml
        scenarios_yaml = scenarios_dir / "scenarios.yaml"
        if scenarios_yaml.exists():
            import yaml

            with open(scenarios_yaml) as f:
                data = yaml.safe_load(f)
                for s in data.get("scenarios", []):
                    if s["name"].startswith(scenario_id):
                        scenario = s["name"]
                        break

    click.echo(f"Running scenario [{scenario}]: {scenario}\n")

    try:
        results = run_scenario_by_name(
            scenario_name=scenario,
            scenarios_dir=scenarios_dir,
            max_tool_calls=max_tool_calls,
            max_duration_seconds=max_duration,
            max_tokens=max_tokens,
            preserve_workspace=no_cleanup,
            llm_provider=llm_provider,
        )

        if results["passed"]:
            click.secho("\n✅ Scenario PASSED", fg="green", bold=True)
            sys.exit(0)
        else:
            click.secho(
                f"\n❌ Scenario FAILED: {results.get('error', 'Unknown error')}",
                fg="red",
                bold=True,
            )
            sys.exit(1)

    except Exception as e:
        click.secho(f"\n❌ Error: {e}", fg="red", bold=True)
        sys.exit(1)


@main.command()
@click.option("--filter", type=str, help="Filter scenarios by name pattern")
def list(filter):
    """List all available evaluation scenarios."""
    scenarios_yaml = eval_dir / "scenarios" / "scenarios.yaml"

    if not scenarios_yaml.exists():
        click.secho("❌ No scenarios.yaml found", fg="red")
        sys.exit(1)

    import yaml

    with open(scenarios_yaml) as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])

    if filter:
        scenarios = [
            s
            for s in scenarios
            if filter.lower() in s["name"].lower()
            or filter.lower() in s.get("description", "").lower()
        ]

    click.echo(f"\n📋 Available Scenarios ({len(scenarios)}):\n")

    for i, scenario in enumerate(scenarios, 1):
        name = scenario["name"]
        desc = scenario.get("description", "No description")

        # Extract scenario number from name (e.g., "03" from "03_interactive_project")
        scenario_num = name.split("_")[0] if "_" in name else str(i)

        click.echo(f"  {scenario_num}. {click.style(name, fg='cyan', bold=True)}")
        click.echo(f"     {desc}")

        if "notes" in scenario:
            notes = scenario["notes"].strip().split("\n")[0]  # First line only
            click.echo(f"     {click.style(notes, dim=True)}")

        click.echo()


@main.command()
@click.option("--filter", type=str, help="Filter scenarios by name pattern")
@click.option("--stop-on-failure", is_flag=True, help="Stop running on first failure")
@click.option("--max-tool-calls", type=int, default=50, help="Maximum tool calls allowed")
@click.option("--max-duration", type=int, default=300, help="Maximum duration in seconds")
@click.option(
    "--llm-provider",
    type=click.Choice(["openai", "anthropic"]),
    default="openai",
    help="LLM provider for user agent",
)
def run_all(filter, stop_on_failure, max_tool_calls, max_duration, llm_provider):
    """Run all evaluation scenarios."""
    scenarios_yaml = eval_dir / "scenarios" / "scenarios.yaml"
    scenarios_dir = eval_dir / "scenarios"

    if not scenarios_yaml.exists():
        click.secho("❌ No scenarios.yaml found", fg="red")
        sys.exit(1)

    import yaml

    with open(scenarios_yaml) as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])

    if filter:
        scenarios = [s for s in scenarios if filter.lower() in s["name"].lower()]

    click.echo(f"\n🚀 Running {len(scenarios)} scenarios...\n")

    passed = 0
    failed = 0
    failed_scenarios = []

    for scenario in scenarios:
        name = scenario["name"]
        click.echo(f"{'━'*70}")
        click.echo(f"Running: {name}")
        click.echo(f"{'━'*70}\n")

        try:
            results = run_scenario_by_name(
                scenario_name=name,
                scenarios_dir=scenarios_dir,
                max_tool_calls=max_tool_calls,
                max_duration_seconds=max_duration,
                max_tokens=100000,
                preserve_workspace=False,
                llm_provider=llm_provider,
            )

            if results["passed"]:
                passed += 1
                click.secho(f"✅ {name} PASSED\n", fg="green")
            else:
                failed += 1
                failed_scenarios.append(name)
                click.secho(
                    f"❌ {name} FAILED: {results.get('error', 'Unknown error')}\n", fg="red"
                )

                if stop_on_failure:
                    break

        except Exception as e:
            failed += 1
            failed_scenarios.append(name)
            click.secho(f"❌ {name} ERROR: {e}\n", fg="red")

            if stop_on_failure:
                break

    # Summary
    click.echo(f"\n{'='*70}")
    click.echo("📊 Summary:")
    click.echo(f"{'='*70}")
    click.secho(f"  ✅ Passed: {passed}", fg="green")
    click.secho(f"  ❌ Failed: {failed}", fg="red" if failed > 0 else "white")
    click.echo(f"  📝 Total:  {passed + failed}")

    if failed_scenarios:
        click.echo("\nFailed scenarios:")
        for name in failed_scenarios:
            click.secho(f"  - {name}", fg="red")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
