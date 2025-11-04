# Kurt Telemetry - Developer Guide

This document provides detailed information about the telemetry implementation in Kurt CLI.

## Overview

Kurt uses [PostHog](https://posthog.com) for anonymous usage analytics to help improve the tool. The implementation follows CLI telemetry best practices with a focus on:

- **Privacy**: No PII or sensitive data collected
- **Transparency**: Clear documentation of what's collected
- **Opt-out**: Multiple easy ways to disable
- **Non-blocking**: Never impacts CLI performance
- **Graceful degradation**: Works offline, handles errors silently

## Architecture

### Module Structure

```
src/kurt/telemetry/
├── __init__.py          # Public API
├── config.py            # Configuration and opt-out logic
├── tracker.py           # PostHog integration
└── decorators.py        # Command tracking decorator
```

### Components

#### 1. Configuration (`config.py`)

Handles:
- Machine ID generation (UUID stored in `~/.kurt/machine_id`)
- Opt-out detection (DO_NOT_TRACK, config file)
- CI environment detection
- Telemetry status reporting

#### 2. Tracker (`tracker.py`)

Handles:
- PostHog client initialization (lazy loading)
- Event tracking with system properties
- Non-blocking event submission (threading)
- Error handling (silent failures)

#### 3. Decorators (`decorators.py`)

Provides:
- `@track_command` decorator for Click commands
- Automatic tracking of command start/completion/failure
- Duration measurement
- Error type capture

## Data Collected

### Events

1. **command_started**
   - When: Command begins execution
   - Properties: command path, system info

2. **command_completed**
   - When: Command succeeds
   - Properties: command path, duration_ms, exit_code=0, system info

3. **command_failed**
   - When: Command raises exception
   - Properties: command path, duration_ms, exit_code=1, error_type, system info

### Properties

**System Properties** (automatically added to all events):
- `os`: Operating system (e.g., "Darwin", "Linux", "Windows")
- `os_version`: OS version string
- `python_version`: Python version (e.g., "3.10.5")
- `kurt_version`: Kurt CLI version
- `is_ci`: Boolean indicating CI environment

**Event-Specific Properties**:
- `command`: Full command path (e.g., "kurt content add")
- `duration_ms`: Execution time in milliseconds
- `exit_code`: 0 for success, 1 for error
- `error_type`: Exception class name (only for failures)

### What We DON'T Collect

- User names, emails, or any PII
- File paths or URLs
- Command arguments or user-provided data
- API keys or credentials
- Project-specific information
- Any sensitive data

## Usage

### Adding Tracking to Commands

Use the `@track_command` decorator on Click commands:

```python
from kurt.telemetry.decorators import track_command
import click

@click.command()
@track_command
def my_command():
    """My command that will be tracked."""
    # Command implementation
    pass
```

### Manual Event Tracking

For custom events:

```python
from kurt.telemetry.tracker import track_event

track_event(
    "custom_event",
    properties={
        "feature": "my_feature",
        "value": 123,
    }
)
```

### Checking Telemetry Status

```python
from kurt.telemetry.config import is_telemetry_enabled, get_telemetry_status

if is_telemetry_enabled():
    # Track something
    pass

status = get_telemetry_status()
print(status)
```

## Configuration

### Environment Variables

- `DO_NOT_TRACK`: Universal opt-out (any value)
- `KURT_TELEMETRY_DISABLED`: Kurt-specific opt-out (any value)
- `KURT_TELEMETRY_DEBUG`: Enable debug logging (set to "true")

### Config File

Stored in `~/.kurt/telemetry.json`:

```json
{
  "enabled": false
}
```

### PostHog Configuration

In `config.py`:

```python
POSTHOG_API_KEY = "phc_your_api_key_here"
POSTHOG_HOST = "https://us.i.posthog.com"
```

**Important**: Replace `POSTHOG_API_KEY` with your actual PostHog project API key before deploying.

## Testing

### Running Tests

```bash
# Run telemetry tests
uv run pytest tests/telemetry/

# Run with coverage
uv run pytest tests/telemetry/ --cov=kurt.telemetry
```

### Testing with Telemetry Disabled

```bash
# Using DO_NOT_TRACK
DO_NOT_TRACK=1 kurt content add https://example.com

# Using Kurt-specific env var
KURT_TELEMETRY_DISABLED=1 kurt content add https://example.com
```

### Testing in Debug Mode

```bash
# Enable debug logging
KURT_TELEMETRY_DEBUG=true kurt content add https://example.com
```

## Best Practices

### 1. Non-Blocking Operation

All tracking happens in background threads. Never use `blocking=True` in production:

```python
# Good - non-blocking (default)
track_event("my_event")

# Bad - blocking
track_event("my_event", blocking=True)  # Only for testing
```

### 2. Error Handling

All telemetry code uses try/except to never break CLI:

```python
try:
    track_event("event")
except Exception:
    # Silently fail - telemetry should never break the CLI
    pass
```

### 3. Privacy

Never track user data:

```python
# Good
track_event("command_completed", {"command": "kurt content add"})

# Bad - don't do this
track_event("command_completed", {"url": user_provided_url})  # ❌
track_event("command_completed", {"email": user_email})       # ❌
```

### 4. Respect Opt-Out

Always check before tracking:

```python
from kurt.telemetry.config import is_telemetry_enabled

if is_telemetry_enabled():
    track_event("my_event")
```

## PostHog Dashboard

Once deployed with a real API key, you can view analytics at:

https://app.posthog.com/

### Useful Queries

**Command Usage**:
- Event: `command_completed`
- Breakdown by: `command` property

**Error Rates**:
- Event: `command_failed`
- Group by: `error_type` property

**Performance**:
- Event: `command_completed`
- Metric: Average `duration_ms`

## Migration from Snowplow

If migrating from Snowplow, key differences:

1. **Simpler SDK**: PostHog has cleaner Python API
2. **Cloud-hosted**: No self-hosting required (but optional)
3. **Free tier**: 1M events/month vs Snowplow's paid-only
4. **Built-in UI**: PostHog includes analytics dashboard
5. **Product-focused**: Better for CLI/product analytics vs Snowplow's data pipeline approach

## Security

- PostHog is SOC 2 Type II certified
- Data encrypted in transit (HTTPS)
- Data encrypted at rest
- No PII collected by design
- Machine IDs are random UUIDs, not tied to users
- Users can opt-out anytime

## Future Enhancements

Potential improvements:

1. **Batch events**: Reduce API calls by batching
2. **Offline queue**: Store events when offline, send later
3. **Feature flags**: Use PostHog for A/B testing
4. **Session tracking**: Group commands by session
5. **User properties**: Track usage patterns over time (anonymously)

## Troubleshooting

### Events not appearing in PostHog

1. Check API key is set correctly
2. Verify telemetry is enabled: `kurt telemetry status`
3. Enable debug mode: `KURT_TELEMETRY_DEBUG=true`
4. Check network connectivity
5. Verify PostHog project is active

### Telemetry always disabled

1. Check for `DO_NOT_TRACK` env var
2. Check for `KURT_TELEMETRY_DISABLED` env var
3. Check `~/.kurt/telemetry.json`
4. Verify no CLI option disabling it

## Support

For issues or questions about telemetry:

1. Check telemetry status: `kurt telemetry status`
2. Review logs with debug mode
3. Open issue on GitHub
4. See PostHog docs: https://posthog.com/docs

## License

Same as Kurt CLI (MIT)
