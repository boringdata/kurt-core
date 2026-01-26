"""
Direct tool CLI commands.

Provides CLI commands for invoking tools directly from the command line:
- kurt map <url|file> [--depth=N] [--source=url|file|cms]
- kurt fetch <input.jsonl> [--engine=trafilatura] [--concurrency=5]
- kurt llm <input.jsonl> --prompt-template='...' [--model=gpt-4o-mini]
- kurt embed <input.jsonl> --text-field=content [--model=text-embedding-3-small]
- kurt tool write-to-db <input.jsonl> --table=<name> [--mode=upsert] [--key=url]
- kurt sql '<query>' [--params='{}']
- kurt research search '<query>' [--recency=day]
- kurt signals reddit -s <subreddit> [--timeframe=day]

Each command:
- Parses CLI args into tool config
- Loads ToolContext
- Calls execute_tool()
- Outputs results as JSONL to stdout
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Iterator, TextIO

import click

from kurt.tools import (
    EmbedConfig,
    FetchConfig,
    LLMConfig,
    SQLConfig,
    WriteConfig,
    execute_tool,
    load_tool_context,
)
from kurt.tools.base import SubstepEvent

# ============================================================================
# Progress Display
# ============================================================================


class ProgressMode:
    """Progress display modes."""

    QUIET = "quiet"
    PROGRESS = "progress"
    JSON_PROGRESS = "json_progress"


def _emit_progress(event: SubstepEvent, mode: str) -> None:
    """Emit progress to stderr based on mode."""
    if mode == ProgressMode.QUIET:
        return

    if mode == ProgressMode.JSON_PROGRESS:
        # Emit JSON progress event to stderr
        print(json.dumps(event.to_dict()), file=sys.stderr)
    else:
        # Human-readable progress
        if event.current is not None and event.total is not None:
            pct = (event.current / event.total * 100) if event.total > 0 else 0
            msg = f"[{event.substep}] {event.current}/{event.total} ({pct:.0f}%)"
        else:
            msg = f"[{event.substep}] {event.status}"

        if event.message:
            msg += f" - {event.message}"

        print(msg, file=sys.stderr, end="\r" if event.status == "progress" else "\n")


def _get_progress_mode(quiet: bool, progress: bool, json_progress: bool) -> str:
    """Determine progress mode from flags."""
    if quiet:
        return ProgressMode.QUIET
    if json_progress:
        return ProgressMode.JSON_PROGRESS
    if progress or sys.stderr.isatty():
        return ProgressMode.PROGRESS
    return ProgressMode.QUIET


# ============================================================================
# Input/Output Helpers
# ============================================================================


def _read_jsonl(input_file: str | TextIO) -> Iterator[dict[str, Any]]:
    """
    Read JSONL from file path or stdin.

    Args:
        input_file: File path, '-' for stdin, or file-like object

    Yields:
        Parsed JSON objects
    """
    if input_file == "-":
        # Read from stdin
        for line in sys.stdin:
            line = line.strip()
            if line:
                yield json.loads(line)
    elif hasattr(input_file, "read"):
        # File-like object
        for line in input_file:
            line = line.strip()
            if line:
                yield json.loads(line)
    else:
        # File path
        with open(input_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)


def _write_jsonl(data: list[dict[str, Any]]) -> None:
    """Write data as JSONL to stdout using click.echo for proper test capturing."""
    for item in data:
        click.echo(json.dumps(item, default=str))


def _determine_exit_code(result: Any) -> int:
    """
    Determine exit code based on result.

    Returns:
        0 = success
        1 = partial failure (some items failed)
        2 = total failure (all items failed)
    """
    if not hasattr(result, "success"):
        return 0

    if result.success:
        return 0

    if not result.data:
        return 2

    # Count errors
    error_count = len(result.errors)
    total_count = len(result.data)

    if error_count >= total_count:
        return 2  # Total failure
    return 1  # Partial failure


# ============================================================================
# Shared Progress Options
# ============================================================================


def add_progress_options():
    """Decorator to add progress display options."""

    def decorator(f):
        f = click.option(
            "--quiet",
            "-q",
            is_flag=True,
            help="No progress, only output",
        )(f)
        f = click.option(
            "--progress",
            "-p",
            is_flag=True,
            help="Show progress bar to stderr (default if tty)",
        )(f)
        f = click.option(
            "--json-progress",
            is_flag=True,
            help="Emit progress events as JSON to stderr",
        )(f)
        return f

    return decorator


# ============================================================================
# map command
# ============================================================================


@click.command("map")
@click.argument("target", required=True)
@click.option(
    "--depth",
    "-d",
    type=int,
    default=1,
    help="Maximum crawl depth for URL discovery (0-10)",
)
@click.option(
    "--source",
    "-s",
    type=click.Choice(["url", "file", "cms"]),
    default=None,
    help="Source type (auto-detected if not specified)",
)
@click.option(
    "--max-pages",
    type=int,
    default=1000,
    help="Maximum pages/files to discover",
)
@click.option(
    "--include",
    "include_patterns",
    multiple=True,
    help="Glob patterns to include (can be specified multiple times)",
)
@click.option(
    "--exclude",
    "exclude_patterns",
    multiple=True,
    help="Glob patterns to exclude (can be specified multiple times)",
)
@click.option(
    "--discovery-method",
    type=click.Choice(["auto", "sitemap", "crawl"]),
    default="auto",
    help="URL discovery method",
)
@add_progress_options()
def map_cmd(
    target: str,
    depth: int,
    source: str | None,
    max_pages: int,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
    discovery_method: str,
    quiet: bool,
    progress: bool,
    json_progress: bool,
) -> None:
    """
    Discover content sources from URLs, files, or CMS.

    TARGET: URL to crawl, folder path, or CMS base URL.

    Examples:
        kurt map https://example.com
        kurt map https://example.com --depth=2
        kurt map ./docs --source=file
        kurt map https://example.com --include='*.html' --exclude='/admin/*'

    Piping:
        kurt map https://example.com | kurt fetch
    """
    progress_mode = _get_progress_mode(quiet, progress, json_progress)

    # Auto-detect source type
    if source is None:
        if target.startswith(("http://", "https://")):
            source = "url"
        elif Path(target).exists() and Path(target).is_dir():
            source = "file"
        else:
            # Default to URL for non-existent paths (could be a URL to crawl)
            source = "url"

    # Build params
    params: dict[str, Any] = {
        "source": source,
        "depth": depth,
        "max_pages": max_pages,
        "include_patterns": list(include_patterns),
        "exclude_patterns": list(exclude_patterns),
        "discovery_method": discovery_method,
    }

    # Set source-specific fields
    if source == "url":
        params["url"] = target
    elif source == "file":
        params["path"] = target
    elif source == "cms":
        params["base_url"] = target

    def on_progress(event: SubstepEvent) -> None:
        _emit_progress(event, progress_mode)

    # Load context and execute
    context = load_tool_context(init_db=False, init_http=True, init_llm=False)

    result = asyncio.run(
        execute_tool("map", params, context=context, on_progress=on_progress)
    )

    # Output results as JSONL
    _write_jsonl(result.data)

    sys.exit(_determine_exit_code(result))


# ============================================================================
# fetch command
# ============================================================================


@click.command("fetch")
@click.argument("input_file", required=False, default="-")
@click.option(
    "--engine",
    "-e",
    type=click.Choice(["trafilatura", "httpx", "tavily", "firecrawl"]),
    default="trafilatura",
    help="Fetch engine to use",
)
@click.option(
    "--concurrency",
    "-c",
    type=int,
    default=5,
    help="Maximum parallel fetches (1-20)",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=30000,
    help="Request timeout in milliseconds",
)
@click.option(
    "--retries",
    type=int,
    default=3,
    help="Maximum retry attempts",
)
@click.option(
    "--content-dir",
    help="Directory to save content",
)
@add_progress_options()
def fetch_cmd(
    input_file: str,
    engine: str,
    concurrency: int,
    timeout: int,
    retries: int,
    content_dir: str | None,
    quiet: bool,
    progress: bool,
    json_progress: bool,
) -> None:
    """
    Fetch content from URLs.

    INPUT_FILE: JSONL file with URLs, or '-' for stdin (default).

    Each line should have a "url" field:
        {"url": "https://example.com/page1"}
        {"url": "https://example.com/page2"}

    Examples:
        kurt fetch urls.jsonl
        echo '{"url": "https://example.com"}' | kurt fetch
        kurt map https://example.com | kurt fetch --engine=trafilatura

    Piping:
        kurt fetch urls.jsonl | kurt llm --prompt-template='Summarize: {content}'
    """
    progress_mode = _get_progress_mode(quiet, progress, json_progress)

    # Read inputs
    inputs: list[dict[str, Any]] = []
    for row in _read_jsonl(input_file):
        url = row.get("url", "")
        if url:
            inputs.append({"url": url})

    if not inputs:
        click.echo("Error: No URLs found in input", err=True)
        sys.exit(2)

    # Build config
    config = FetchConfig(
        engine=engine,
        concurrency=concurrency,
        timeout_ms=timeout,
        retries=retries,
        content_dir=content_dir,
    )

    params = {
        "inputs": inputs,
        "config": config.model_dump(),
    }

    def on_progress(event: SubstepEvent) -> None:
        _emit_progress(event, progress_mode)

    # Load context and execute
    context = load_tool_context(init_db=False, init_http=True, init_llm=False)

    result = asyncio.run(
        execute_tool("fetch", params, context=context, on_progress=on_progress)
    )

    # Output results as JSONL
    _write_jsonl(result.data)

    sys.exit(_determine_exit_code(result))


# ============================================================================
# llm command
# ============================================================================


@click.command("llm")
@click.argument("input_file", required=False, default="-")
@click.option(
    "--prompt-template",
    required=True,
    help="Prompt template with {field} placeholders",
)
@click.option(
    "--output-schema",
    help="Pydantic model name for structured output",
)
@click.option(
    "--model",
    "-m",
    default="gpt-4o-mini",
    help="Model identifier (e.g., gpt-4o-mini, claude-3-haiku-20240307)",
)
@click.option(
    "--provider",
    type=click.Choice(["openai", "anthropic"]),
    default="openai",
    help="LLM provider",
)
@click.option(
    "--concurrency",
    "-c",
    type=int,
    default=3,
    help="Maximum parallel LLM calls (1-20)",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=60000,
    help="Request timeout in milliseconds",
)
@click.option(
    "--temperature",
    type=float,
    default=0.0,
    help="Sampling temperature (0.0 = deterministic)",
)
@click.option(
    "--max-tokens",
    type=int,
    default=4096,
    help="Maximum tokens in response",
)
@add_progress_options()
def llm_cmd(
    input_file: str,
    prompt_template: str,
    output_schema: str | None,
    model: str,
    provider: str,
    concurrency: int,
    timeout: int,
    temperature: float,
    max_tokens: int,
    quiet: bool,
    progress: bool,
    json_progress: bool,
) -> None:
    """
    Process rows through an LLM.

    INPUT_FILE: JSONL file with row data, or '-' for stdin (default).

    Each line is a JSON object with fields for template substitution:
        {"content": "Hello world", "title": "Greeting"}

    Examples:
        kurt llm data.jsonl --prompt-template='Summarize: {content}'
        cat data.jsonl | kurt llm --prompt-template='Extract entities from: {text}'
        kurt fetch urls.jsonl | kurt llm -p 'Summarize: {content}' --model=gpt-4o

    Piping:
        kurt tool map url | kurt tool fetch | kurt tool llm -p 'Extract: {content}' | kurt tool write-to-db --table=extracted
    """
    progress_mode = _get_progress_mode(quiet, progress, json_progress)

    # Read inputs - each row becomes an LLM input
    inputs: list[dict[str, Any]] = []
    for row in _read_jsonl(input_file):
        inputs.append({"row": row})

    if not inputs:
        click.echo("Error: No rows found in input", err=True)
        sys.exit(2)

    # Build config
    config = LLMConfig(
        prompt_template=prompt_template,
        output_schema=output_schema,
        model=model,
        provider=provider,
        concurrency=concurrency,
        timeout_ms=timeout,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    params = {
        "inputs": inputs,
        "config": config.model_dump(),
    }

    def on_progress(event: SubstepEvent) -> None:
        _emit_progress(event, progress_mode)

    # Load context and execute
    context = load_tool_context(init_db=False, init_http=False, init_llm=True)

    result = asyncio.run(
        execute_tool("llm", params, context=context, on_progress=on_progress)
    )

    # Output results as JSONL
    _write_jsonl(result.data)

    sys.exit(_determine_exit_code(result))


# ============================================================================
# embed command
# ============================================================================


@click.command("embed")
@click.argument("input_file", required=False, default="-")
@click.option(
    "--text-field",
    "-f",
    default="content",
    help="Field name containing text to embed",
)
@click.option(
    "--model",
    "-m",
    default="text-embedding-3-small",
    help="Embedding model name",
)
@click.option(
    "--provider",
    type=click.Choice(["openai", "cohere", "voyage"]),
    default="openai",
    help="Embedding provider",
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Number of texts per API batch",
)
@click.option(
    "--concurrency",
    "-c",
    type=int,
    default=2,
    help="Maximum parallel API calls (1-10)",
)
@click.option(
    "--max-chars",
    type=int,
    default=8000,
    help="Maximum characters per text (truncated if exceeded)",
)
@add_progress_options()
def embed_cmd(
    input_file: str,
    text_field: str,
    model: str,
    provider: str,
    batch_size: int,
    concurrency: int,
    max_chars: int,
    quiet: bool,
    progress: bool,
    json_progress: bool,
) -> None:
    """
    Generate vector embeddings for text content.

    INPUT_FILE: JSONL file with text data, or '-' for stdin (default).

    Each line should have the text field (default: 'content'):
        {"content": "Some text to embed", "id": "1"}

    Examples:
        kurt embed docs.jsonl --text-field=content
        cat docs.jsonl | kurt embed --model=text-embedding-3-large
        kurt fetch urls.jsonl | kurt embed

    Note: Embeddings are returned as base64-encoded bytes in the 'embedding' field.
    """
    progress_mode = _get_progress_mode(quiet, progress, json_progress)

    # Read inputs - each row is passed through
    inputs: list[dict[str, Any]] = list(_read_jsonl(input_file))

    if not inputs:
        click.echo("Error: No rows found in input", err=True)
        sys.exit(2)

    # Build config
    config = EmbedConfig(
        text_field=text_field,
        model=model,
        provider=provider,
        batch_size=batch_size,
        concurrency=concurrency,
        max_chars=max_chars,
    )

    params = {
        "inputs": inputs,
        "config": config.model_dump(),
    }

    def on_progress(event: SubstepEvent) -> None:
        _emit_progress(event, progress_mode)

    # Load context and execute
    context = load_tool_context(init_db=False, init_http=False, init_llm=True)

    result = asyncio.run(
        execute_tool("embed", params, context=context, on_progress=on_progress)
    )

    # Convert bytes embeddings to base64 for JSON serialization
    import base64

    for item in result.data:
        if item.get("embedding") and isinstance(item["embedding"], bytes):
            item["embedding"] = base64.b64encode(item["embedding"]).decode("ascii")

    # Output results as JSONL
    _write_jsonl(result.data)

    sys.exit(_determine_exit_code(result))


# ============================================================================
# write-to-db command (formerly write, then save)
# ============================================================================


@click.command("write-to-db")
@click.argument("input_file", required=False, default="-")
@click.option(
    "--table",
    "-t",
    required=True,
    help="Target table name",
)
@click.option(
    "--mode",
    type=click.Choice(["insert", "upsert", "replace"]),
    default="insert",
    help="Write mode",
)
@click.option(
    "--key",
    "-k",
    help="Column(s) for upsert/replace (comma-separated for composite)",
)
@click.option(
    "--continue-on-error",
    is_flag=True,
    help="Continue processing after individual row errors",
)
@add_progress_options()
def write_to_db_cmd(
    input_file: str,
    table: str,
    mode: str,
    key: str | None,
    continue_on_error: bool,
    quiet: bool,
    progress: bool,
    json_progress: bool,
) -> None:
    """
    Write data to a database table.

    INPUT_FILE: JSONL file with row data, or '-' for stdin (default).

    Each line is a JSON object representing a row:
        {"url": "https://...", "title": "Page Title", "content": "..."}

    Examples:
        kurt tool write-to-db data.jsonl --table=documents
        cat data.jsonl | kurt tool write-to-db --table=documents --mode=upsert --key=url
        kurt tool fetch urls.jsonl | kurt tool write-to-db --table=fetched --mode=upsert --key=url

    Piping:
        kurt tool map url | kurt tool fetch | kurt tool write-to-db --table=content --key=url
    """
    progress_mode = _get_progress_mode(quiet, progress, json_progress)

    # Read inputs
    inputs: list[dict[str, Any]] = []
    for row in _read_jsonl(input_file):
        inputs.append({"row": row})

    if not inputs:
        click.echo("Error: No rows found in input", err=True)
        sys.exit(2)

    # Parse key columns
    key_cols: str | list[str] | None = None
    if key:
        if "," in key:
            key_cols = [k.strip() for k in key.split(",")]
        else:
            key_cols = key

    # Build config
    config = WriteConfig(
        table=table,
        mode=mode,
        key=key_cols,
        continue_on_error=continue_on_error,
    )

    params = {
        "inputs": inputs,
        "config": config.model_dump(),
    }

    def on_progress(event: SubstepEvent) -> None:
        _emit_progress(event, progress_mode)

    # Load context and execute
    context = load_tool_context(init_db=True, init_http=False, init_llm=False)

    result = asyncio.run(
        execute_tool("write", params, context=context, on_progress=on_progress)
    )

    # Output results as JSONL
    _write_jsonl(result.data)

    sys.exit(_determine_exit_code(result))


# ============================================================================
# sql command
# ============================================================================


@click.command("sql")
@click.argument("query", required=True)
@click.option(
    "--params",
    help="Named parameters as JSON object (e.g., '{\"url\": \"...\"}'})",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=30000,
    help="Query timeout in milliseconds",
)
@add_progress_options()
def sql_cmd(
    query: str,
    params: str | None,
    timeout: int,
    quiet: bool,
    progress: bool,
    json_progress: bool,
) -> None:
    """
    Execute a read-only SQL query.

    QUERY: SQL SELECT query (only SELECT is allowed).

    Use :name syntax for parameters to prevent SQL injection:
        kurt sql 'SELECT * FROM docs WHERE url = :url' --params='{"url": "..."}'

    Examples:
        kurt sql 'SELECT * FROM documents LIMIT 10'
        kurt sql 'SELECT COUNT(*) FROM documents'
        kurt sql 'SELECT * FROM docs WHERE status = :status' -p '{"status": "active"}'

    Output is JSONL, one row per line.
    """
    progress_mode = _get_progress_mode(quiet, progress, json_progress)

    # Parse params
    params_dict: dict[str, Any] | None = None
    if params:
        try:
            params_dict = json.loads(params)
        except json.JSONDecodeError as e:
            click.echo(f"Error parsing --params JSON: {e}", err=True)
            sys.exit(2)

    # Build config
    config = SQLConfig(
        query=query,
        params=params_dict,
        timeout_ms=timeout,
    )

    tool_params = {
        "config": config.model_dump(),
    }

    def on_progress(event: SubstepEvent) -> None:
        _emit_progress(event, progress_mode)

    # Load context and execute
    context = load_tool_context(init_db=True, init_http=False, init_llm=False)

    result = asyncio.run(
        execute_tool("sql", tool_params, context=context, on_progress=on_progress)
    )

    # Output results as JSONL
    _write_jsonl(result.data)

    sys.exit(_determine_exit_code(result))


# ============================================================================
# Tools group (for grouped access: kurt tool <x>)
# ============================================================================


@click.group()
def tools_group() -> None:
    """
    Direct tool invocation commands.

    \b
    Commands:
      map          Discover content sources (URLs, folders, CMS)
      fetch        Fetch and index documents
      llm          Process rows through an LLM
      embed        Generate vector embeddings
      write-to-db  Write data to a database table
      sql          Execute read-only SQL queries
      research     Execute research queries
      signals      Monitor social signals
    """
    pass


# Import the full-featured map/fetch CLI commands from their new location
from kurt.tools.fetch.cli import fetch_cmd as fetch_tool_cmd  # noqa: E402
from kurt.tools.map.cli import map_cmd as map_tool_cmd  # noqa: E402
from kurt.tools.research.cli import research_group  # noqa: E402
from kurt.tools.signals.cli import signals_group  # noqa: E402

tools_group.add_command(map_tool_cmd, name="map")
tools_group.add_command(fetch_tool_cmd, name="fetch")
tools_group.add_command(llm_cmd, name="llm")
tools_group.add_command(embed_cmd, name="embed")
tools_group.add_command(write_to_db_cmd, name="write-to-db")
tools_group.add_command(sql_cmd, name="sql")
tools_group.add_command(research_group, name="research")
tools_group.add_command(signals_group, name="signals")
