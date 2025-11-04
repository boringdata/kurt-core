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

## Telemetry

Kurt collects anonymous usage analytics to help us understand how the tool is used and improve it. We take privacy seriously.

### What We Collect

- **Command usage**: Which commands are run (e.g., `kurt content add`)
- **Execution metrics**: Timing and success/failure rates
- **Environment**: OS, Python version, Kurt version
- **Machine ID**: Anonymous identifier (UUID, not tied to personal info)

### What We DON'T Collect

- Personal information (names, emails, etc.)
- File paths or URLs
- Command arguments or user data
- Any sensitive information

### How to Opt-Out

Disable telemetry using any of these methods:

```bash
# 1. Use the CLI command
kurt telemetry disable

# 2. Set environment variable (universal)
export DO_NOT_TRACK=1

# 3. Set Kurt-specific environment variable
export KURT_TELEMETRY_DISABLED=1
```

Check telemetry status:

```bash
kurt telemetry status
```

### Privacy

All telemetry is:
- **Anonymous**: No personal information collected
- **Transparent**: Clearly documented what we collect
- **Optional**: Easy to opt-out
- **Non-blocking**: Never slows down CLI commands
- **Secure**: Uses PostHog cloud (SOC 2 compliant)

## License

MIT
