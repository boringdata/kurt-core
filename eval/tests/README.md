# Evaluation Framework Tests

Tests for the evaluation framework itself (not for Kurt agent behavior).

## What This Tests

These tests validate that the evaluation framework components work correctly:

- **Workspace isolation**: Temp directories, cleanup, isolation between tests
- **Kurt initialization**: Running `kurt init` successfully
- **Claude plugin installation**: Copying `.claude/` directory
- **Helper methods**: File checking, database queries, context gathering

## Running Tests

```bash
# Run all framework tests
python eval/tests/test_workspace.py

# Or run individual test files as they're added
python eval/tests/test_assertions.py
python eval/tests/test_metrics.py
```

## Test Files

- `test_workspace.py` - Tests for workspace isolation and setup
- (Future) `test_assertions.py` - Tests for assertion helpers
- (Future) `test_metrics.py` - Tests for metrics collection
- (Future) `test_conversation.py` - Tests for user agent simulation

## What's the Difference?

- **`eval/tests/`** - Tests the framework itself (does workspace setup work?)
- **`eval/scenarios/`** - Tests agent behavior using the framework (can agent use kurt correctly?)

## Adding New Tests

Create a new test file in this directory:

```python
def test_my_feature():
    """Test description."""
    # Setup
    # Execute
    # Assert
    print("✅ PASSED: My feature")

if __name__ == "__main__":
    test_my_feature()
```

Keep tests simple and focused on one aspect of functionality.
