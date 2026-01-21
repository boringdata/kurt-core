"""Agent tool CLI commands for workflow data operations.

Provides CLI commands that agents can call to interact with
workflow tables, LLM steps, and embeddings. All commands output
JSON for agent parsing.

Commands:
    kurt agent tool save-to-db --table=<table> --data=<json>
    kurt agent tool llm --prompt=<template> --data=<json>
    kurt agent tool embedding --texts=<json> --output=<file>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click

from kurt.admin.telemetry.decorators import track_command


def _output_json(data: dict[str, Any], success: bool = True) -> None:
    """Output JSON result to stdout for agent parsing."""
    result = {"success": success, **data}
    click.echo(json.dumps(result, indent=2, default=str))


def _output_error(message: str, details: dict[str, Any] | None = None) -> None:
    """Output error JSON and exit with code 1."""
    result: dict[str, Any] = {"success": False, "error": message}
    if details:
        result["details"] = details
    click.echo(json.dumps(result, indent=2, default=str))
    sys.exit(1)


@click.group(name="tool")
def tool():
    """
    Agent tools for workflow data operations.

    \\b
    These commands are designed to be called by agents during
    workflow execution. All commands output JSON for parsing.

    \\b
    Commands:
      save-to-db   Save data to a workflow table
      llm          Run LLM batch processing
      embedding    Generate embeddings for texts
    """
    pass


@tool.command("save-to-db")
@click.option(
    "--table",
    required=True,
    help="Table name (from workflow's models.py)",
)
@click.option(
    "--data",
    required=True,
    help="JSON data to save (single object or array of objects)",
)
@click.option(
    "--workflow-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to workflow directory containing models.py",
)
@track_command
def save_to_db(table: str, data: str, workflow_dir: Path | None) -> None:
    """
    Save data to a workflow table via SaveStep.

    The table must be defined in the workflow's models.py file.
    Data can be a single JSON object or an array of objects.

    \\b
    Examples:
        kurt agent tool save-to-db --table=entities --data='{"name": "Test"}'
        kurt agent tool save-to-db --table=results --data='[{"a": 1}, {"a": 2}]'
    """
    from kurt.core import SaveStep, get_model_by_table_name

    # Parse JSON data
    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError as e:
        _output_error(f"Invalid JSON data: {e}")
        return

    # Normalize to list
    if isinstance(parsed_data, dict):
        rows = [parsed_data]
    elif isinstance(parsed_data, list):
        rows = parsed_data
    else:
        _output_error("Data must be a JSON object or array of objects")
        return

    # Find the model by table name
    try:
        model = get_model_by_table_name(table, workflow_dir=workflow_dir)
    except ImportError as e:
        _output_error(f"Failed to load models.py: {e}")
        return
    except ValueError as e:
        _output_error(str(e))
        return

    if model is None:
        _output_error(
            f"Table '{table}' not found in models.py",
            details={"hint": "Ensure models.py exists and defines a SQLModel with this __tablename__"},
        )
        return

    # Create SaveStep and run
    try:
        save_step = SaveStep(name=f"save_{table}", model=model)
        result = save_step.run(rows)

        _output_json(
            {
                "table": result["table"],
                "saved": result["saved"],
                "errors": result["errors"],
                "total_rows": len(rows),
            }
        )
    except Exception as e:
        _output_error(f"Failed to save data: {e}")


@tool.command("llm")
@click.option(
    "--prompt",
    required=True,
    help="Prompt template with {field} placeholders",
)
@click.option(
    "--data",
    required=True,
    help="JSON array of objects to process",
)
@click.option(
    "--output-schema",
    "output_schema_name",
    default=None,
    help="Name of Pydantic model from workflow's models.py for output validation",
)
@click.option(
    "--model",
    "llm_model",
    default=None,
    help="LLM model to use (default: from config)",
)
@click.option(
    "--concurrency",
    default=3,
    help="Number of concurrent LLM calls",
)
@click.option(
    "--workflow-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Path to workflow directory containing models.py",
)
@track_command
def llm_cmd(
    prompt: str,
    data: str,
    output_schema_name: str | None,
    llm_model: str | None,
    concurrency: int,
    workflow_dir: Path | None,
) -> None:
    """
    Run LLM batch processing on data.

    Processes each row through the LLM with the given prompt template.
    Fields in data are available as {field_name} in the prompt.

    \\b
    Examples:
        kurt agent tool llm --prompt="Summarize: {text}" --data='[{"text": "Hello"}]'
        kurt agent tool llm --prompt="Extract from: {content}" --data='[...]' --model=gpt-4
    """
    try:
        import pandas as pd
    except ImportError:
        _output_error("pandas is required. Install with: pip install kurt-core[workflows]")
        return

    # Parse JSON data
    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError as e:
        _output_error(f"Invalid JSON data: {e}")
        return

    if not isinstance(parsed_data, list):
        _output_error("Data must be a JSON array of objects")
        return

    if not parsed_data:
        _output_json({"results": [], "total": 0, "successful": 0, "errors": []})
        return

    # Detect input columns from prompt template
    import re

    input_columns = list(set(re.findall(r"\{(\w+)\}", prompt)))
    if not input_columns:
        _output_error(
            "Prompt template must contain at least one {field} placeholder",
            details={"prompt": prompt},
        )
        return

    # Resolve output schema
    output_schema = None
    if output_schema_name:
        try:
            from kurt.core.model_utils import _load_module_from_path

            models_path = (workflow_dir or Path.cwd()) / "models.py"
            if models_path.exists():
                module = _load_module_from_path(models_path)
                if module and hasattr(module, output_schema_name):
                    output_schema = getattr(module, output_schema_name)
        except Exception as e:
            _output_error(f"Failed to load output schema '{output_schema_name}': {e}")
            return

    # Create a simple output schema if none provided
    if output_schema is None:
        from pydantic import BaseModel

        class DefaultOutput(BaseModel):
            response: str = ""

        output_schema = DefaultOutput

    # Set up LLM function
    try:
        from kurt.config import resolve_model_settings

        settings = resolve_model_settings(model_category="LLM")
        model_to_use = llm_model or settings.model

        import litellm

        def llm_fn(prompt_text: str):
            response = litellm.completion(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt_text}],
            )
            content = response.choices[0].message.content or ""

            # Try to parse as JSON if output schema has multiple fields
            if len(output_schema.model_fields) > 1:
                try:
                    parsed = json.loads(content)
                    return output_schema(**parsed)
                except (json.JSONDecodeError, Exception):
                    pass

            # Return simple response
            return output_schema(response=content)

    except ImportError:
        _output_error("litellm is required. Install with: pip install kurt-core[workflows]")
        return
    except Exception as e:
        _output_error(f"Failed to configure LLM: {e}")
        return

    # Create LLMStep and run
    try:
        from kurt.core import LLMStep

        step = LLMStep(
            name="agent_llm",
            input_columns=input_columns,
            prompt_template=prompt,
            output_schema=output_schema,
            llm_fn=llm_fn,
            concurrency=concurrency,
        )

        df = pd.DataFrame(parsed_data)
        result_df = step.run(df)

        # Convert results to JSON-serializable format
        results = result_df.to_dict(orient="records")

        # Count successes and errors
        status_col = "agent_llm_status"
        successful = sum(1 for r in results if r.get(status_col) == "success")
        errors = [r for r in results if r.get(status_col) == "error"]

        _output_json(
            {
                "results": results,
                "total": len(results),
                "successful": successful,
                "errors": [r.get("error", "unknown") for r in errors],
            }
        )
    except Exception as e:
        _output_error(f"LLM processing failed: {e}")


@tool.command("embedding")
@click.option(
    "--texts",
    required=True,
    help="JSON array of texts to embed",
)
@click.option(
    "--output",
    "output_file",
    required=True,
    type=click.Path(path_type=Path),
    help="Output file path for embeddings (JSON format)",
)
@click.option(
    "--model",
    "embedding_model",
    default=None,
    help="Embedding model to use (default: from config)",
)
@click.option(
    "--max-chars",
    default=1000,
    help="Maximum characters per text (default: 1000)",
)
@track_command
def embedding_cmd(
    texts: str,
    output_file: Path,
    embedding_model: str | None,
    max_chars: int,
) -> None:
    """
    Generate embeddings for a list of texts.

    Outputs embeddings to a JSON file with format:
    {"embeddings": [[0.1, 0.2, ...], ...], "count": N}

    \\b
    Examples:
        kurt agent tool embedding --texts='["Hello", "World"]' --output=embeddings.json
        kurt agent tool embedding --texts='[...]' --output=out.json --model=text-embedding-3-small
    """
    # Parse JSON texts
    try:
        parsed_texts = json.loads(texts)
    except json.JSONDecodeError as e:
        _output_error(f"Invalid JSON texts: {e}")
        return

    if not isinstance(parsed_texts, list):
        _output_error("Texts must be a JSON array of strings")
        return

    if not all(isinstance(t, str) for t in parsed_texts):
        _output_error("All items in texts array must be strings")
        return

    if not parsed_texts:
        # Write empty result
        output_file.write_text(json.dumps({"embeddings": [], "count": 0}))
        _output_json({"output_file": str(output_file), "count": 0})
        return

    # Truncate texts to max_chars
    truncated_texts = [t[:max_chars] if len(t) > max_chars else t for t in parsed_texts]

    # Generate embeddings
    try:
        from kurt.core import generate_embeddings

        embeddings = generate_embeddings(
            truncated_texts,
            model=embedding_model,
            record_trace=True,
        )

        # Write to output file
        output_data = {
            "embeddings": embeddings,
            "count": len(embeddings),
            "model": embedding_model or "default",
        }
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(output_data))

        _output_json(
            {
                "output_file": str(output_file),
                "count": len(embeddings),
                "dimensions": len(embeddings[0]) if embeddings else 0,
            }
        )
    except ImportError as e:
        _output_error(f"Missing dependency: {e}")
    except Exception as e:
        _output_error(f"Embedding generation failed: {e}")
