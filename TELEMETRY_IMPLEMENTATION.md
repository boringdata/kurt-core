# Telemetry Implementation - Summary

This document summarizes the telemetry implementation for Kurt CLI and provides next steps for deployment.

## ✅ What Was Implemented

### 1. Core Infrastructure

- **PostHog Integration**: Full integration with PostHog Python SDK
- **Privacy-First Design**: Multiple opt-out methods, no PII collection
- **Non-Blocking**: All tracking happens in background threads
- **Graceful Degradation**: Works offline, handles errors silently

### 2. Module Structure

Created `src/kurt/telemetry/` module with:

- `config.py`: Configuration management, opt-out logic, machine ID generation
- `tracker.py`: PostHog client, event tracking, system properties
- `decorators.py`: `@track_command` decorator for easy integration
- `__init__.py`: Public API

### 3. CLI Commands

Added `kurt telemetry` command group:

```bash
kurt telemetry enable   # Enable telemetry
kurt telemetry disable  # Disable telemetry
kurt telemetry status   # Show telemetry status and what's collected
```

### 4. Event Tracking

Three core events:

1. `command_started` - When command begins
2. `command_completed` - When command succeeds (with duration)
3. `command_failed` - When command errors (with error type)

Properties tracked:
- Command name (e.g., "kurt content add")
- Execution time (milliseconds)
- OS, Python version, Kurt version
- Success/failure status
- Error type (if failed)

### 5. Privacy Features

- Multiple opt-out methods:
  - `DO_NOT_TRACK` environment variable
  - `KURT_TELEMETRY_DISABLED` environment variable
  - `kurt telemetry disable` command
  - Config file (`~/.kurt/telemetry.json`)

- No PII collected:
  - No file paths or URLs
  - No command arguments
  - No user names or emails
  - Anonymous machine ID only

### 6. Documentation

- Updated README with telemetry section
- Created TELEMETRY.md developer guide
- Inline code documentation

### 7. Tests

Created test suite:
- `tests/telemetry/test_config.py`: Configuration and opt-out tests
- `tests/telemetry/test_tracker.py`: Event tracking tests

## 📋 Next Steps (Before Production)

### 1. Get PostHog API Key (REQUIRED)

**You need to replace the placeholder API key with a real one:**

1. Sign up for PostHog: https://posthog.com/signup
2. Choose "Cloud" hosting (free tier: 1M events/month)
3. Create a new project or use existing
4. Copy your Project API Key
5. Update `src/kurt/telemetry/config.py`:

```python
# Replace this line:
POSTHOG_API_KEY = "phc_your_api_key_here"  # ← CHANGE THIS

# With your actual key:
POSTHOG_API_KEY = "phc_abc123..."  # ← Your real key
```

### 2. Install Dependencies

Update your environment:

```bash
cd /Users/davidkrevitt/code/kurt-core
uv sync  # Install PostHog dependency
```

### 3. Test the Implementation

```bash
# Test basic tracking
python -c "from kurt.telemetry.tracker import track_event; track_event('test_event')"

# Test CLI commands
kurt telemetry status
kurt telemetry disable
kurt telemetry enable

# Test with a tracked command
kurt init --help

# Check PostHog dashboard
# Events should appear at: https://app.posthog.com/
```

### 4. Add Tracking to More Commands (Optional)

The `@track_command` decorator is currently only applied to `kurt init`.

To track other commands, add the decorator:

```python
from kurt.telemetry.decorators import track_command

@click.command()
@track_command  # Add this decorator
def my_command():
    # command implementation
    pass
```

**Recommended commands to track:**
- All commands in `content.py` (add, fetch, index, etc.)
- All commands in `cms.py`
- All commands in `research.py`
- All commands in `project.py`

### 5. Run Tests

```bash
# Install dev dependencies
uv sync --group dev

# Run telemetry tests
uv run pytest tests/telemetry/ -v

# Run all tests
uv run pytest tests/ -v
```

### 6. Environment Configuration

Set up environment variables for your deployment:

```bash
# Optional: Disable telemetry for development
export KURT_TELEMETRY_DISABLED=1

# Optional: Enable debug mode
export KURT_TELEMETRY_DEBUG=true
```

### 7. Privacy Policy (Recommended)

Consider adding a privacy policy to your repository:

- Document what data is collected
- Explain how it's used
- Link from README
- Comply with relevant regulations (GDPR, CCPA, etc.)

## 🔍 Verification Checklist

Before deploying to production:

- [ ] PostHog API key updated in `config.py`
- [ ] Dependencies installed (`uv sync`)
- [ ] Tests passing (`pytest tests/telemetry/`)
- [ ] Telemetry commands work (`kurt telemetry status`)
- [ ] Events appear in PostHog dashboard
- [ ] Opt-out works (`DO_NOT_TRACK=1 kurt ...`)
- [ ] Documentation reviewed (README, TELEMETRY.md)
- [ ] Privacy policy created (optional but recommended)

## 📊 PostHog Dashboard Setup

Once you have real data flowing:

1. **Create Insights**:
   - Most used commands
   - Command success/failure rates
   - Average execution times
   - Error breakdown by type

2. **Set Up Dashboards**:
   - Overall usage dashboard
   - Performance monitoring dashboard
   - Error tracking dashboard

3. **Configure Alerts** (optional):
   - Alert on high error rates
   - Alert on performance degradation

## 🚀 Usage Examples

### For End Users

```bash
# Check telemetry status
kurt telemetry status

# Disable telemetry
kurt telemetry disable

# Or use environment variable
export DO_NOT_TRACK=1
```

### For Developers

```python
# Add tracking to a command
from kurt.telemetry.decorators import track_command

@click.command()
@track_command
def my_command():
    pass

# Track custom events
from kurt.telemetry.tracker import track_event

track_event("custom_event", properties={"key": "value"})
```

## 🔧 Troubleshooting

### Events not appearing in PostHog

1. Check API key is correct
2. Verify telemetry is enabled: `kurt telemetry status`
3. Enable debug mode: `KURT_TELEMETRY_DEBUG=true kurt ...`
4. Check internet connectivity
5. Wait a few minutes (PostHog has ~1-2 min delay)

### Telemetry always disabled

1. Check `DO_NOT_TRACK` env var
2. Check `KURT_TELEMETRY_DISABLED` env var
3. Check `~/.kurt/telemetry.json`
4. Run `kurt telemetry status` to see why

## 📚 Additional Resources

- **PostHog Docs**: https://posthog.com/docs
- **PostHog Python SDK**: https://posthog.com/docs/libraries/python
- **CLI Telemetry Best Practices**: https://marcon.me/articles/cli-telemetry-best-practices/
- **TELEMETRY.md**: Detailed developer guide in this repository

## 💡 Future Enhancements

Consider these improvements:

1. **Batch Events**: Reduce API calls by batching events
2. **Offline Queue**: Store events when offline, send when connected
3. **Feature Flags**: Use PostHog for A/B testing and feature rollout
4. **Session Tracking**: Group related commands into sessions
5. **User Surveys**: Collect feedback via PostHog surveys
6. **Cohort Analysis**: Segment users by behavior patterns

## 🎉 Summary

You now have a complete, privacy-respecting telemetry system for Kurt CLI that:

- ✅ Tracks command usage, timing, and errors
- ✅ Respects user privacy (no PII, easy opt-out)
- ✅ Never blocks or slows down commands
- ✅ Handles errors gracefully
- ✅ Provides transparency (clear documentation)
- ✅ Uses PostHog free tier (1M events/month)

**Next immediate step**: Get your PostHog API key and update `config.py`!

Good luck! 🚀
