# Kurt Core

Document intelligence system for managing web content and extracting structured knowledge.

## Kurt-Core

CLI for fetching and managing web content with metadata extraction.

**Quick Start:**
```bash
uv sync
uv run kurt init
uv run kurt ingest map https://example.com
uv run kurt ingest fetch --url-prefix https://example.com/
```

[Full documentation](src/kurt/README.md)

## Kurt-Eval

Test Kurt agent behavior using Claude agent sessions via Anthropic SDK.

**Install:**
```bash
uv sync --extra eval
cp eval/.env.example eval/.env
# Edit eval/.env and add your ANTHROPIC_API_KEY
```

**List scenarios:**
```bash
uv run kurt-eval list
```

**Run scenarios:**
```bash
# Run by number or name
uv run kurt-eval run 1
uv run kurt-eval run 01_basic_init

# Run all scenarios
uv run kurt-eval run-all

# View results
cat eval/results/01_basic_init_*.json
cat eval/results/01_basic_init_*.md
```

**Available scenarios:**
- `01_basic_init` - Initialize a Kurt project
- `02_add_url` - Initialize and add content from a URL
- `03_interactive_project` - Multi-turn conversation with user agent
- `04_with_claude_plugin` - Test with Claude plugin integration

See [eval/scenarios/](eval/scenarios/) for scenario definitions.

## License

MIT
