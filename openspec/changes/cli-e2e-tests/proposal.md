# CLI E2E Test Coverage

## Problem

Current CLI tests have significant gaps:

1. **Internal Mocking**: Most tests mock internal functions (`resolve_documents`, `_get_status_data`) rather than testing real data flow
2. **Missing Commands**: Several commands have no tests (research, signals, analytics, workflow subcommands, sync, connect, cloud)
3. **Option Coverage**: Many command options are only tested for parsing, not actual behavior
4. **Database Verification**: Tests don't verify actual database state changes

## Solution

Add comprehensive E2E tests for all CLI commands that:

1. Use `tmp_project` fixture (real Dolt database on unique port per test)
2. Mock ONLY external provider API calls (httpx, Apify, Perplexity, etc.)
3. Verify database state after command execution
4. Check filesystem artifacts where applicable
5. Test all command options including edge cases

## Scope

### Commands to Test

| Group | Commands | Current Coverage | Target |
|-------|----------|-----------------|--------|
| Core | init, status, doctor, repair, serve | Partial | Full |
| tool map | URL, folder, CMS sources | Partial | Full |
| tool fetch | All engines, all options | Partial | Full |
| tool research | search | None | Full |
| tool signals | reddit, hackernews, feeds | None | Full |
| tool analytics | sync | None | Full |
| docs | list, get, delete | Good | Complete |
| workflow | run, status, logs, cancel, test, list, show, validate, history, init, create | None | Full |
| sync | branch, commit, merge, pull, push | Partial | Full |
| connect | cms, analytics, research | None | Full |
| cloud | login, status, logout | None | Full |

### Test Structure

```
src/kurt/
├── testing/                          # NEW: Shared test utilities
│   ├── __init__.py
│   ├── mocks.py                      # External provider mock factories
│   ├── assertions.py                 # Database assertion helpers
│   └── fixtures.py                   # Additional E2E fixtures
├── cli/tests/
│   ├── test_init_e2e.py             # NEW
│   ├── test_status_e2e.py           # NEW
│   ├── test_doctor_e2e.py           # NEW
│   ├── test_repair_e2e.py           # NEW
│   └── test_global_options_e2e.py   # NEW
├── tools/
│   ├── map/tests/test_cli_e2e.py    # NEW
│   ├── fetch/tests/test_cli_e2e.py  # NEW
│   ├── research/tests/test_cli_e2e.py # NEW
│   ├── signals/tests/test_cli_e2e.py  # NEW
│   └── analytics/tests/test_cli_e2e.py # NEW
├── documents/tests/test_cli_e2e.py  # EXTEND
├── workflows/toml/tests/test_cli_e2e.py # NEW
├── db/isolation/tests/test_sync_cli_e2e.py # NEW
├── integrations/tests/
│   ├── test_connect_cms_e2e.py      # NEW
│   └── test_connect_analytics_e2e.py # NEW
├── cloud/tests/test_cli_e2e.py      # NEW
└── web/tests/test_serve_e2e.py      # NEW
```

## Test Principles

1. **Real Database**: Use `tmp_project` fixture with actual Dolt server
2. **External Mocks Only**: Mock httpx, trafilatura, feedparser, etc. - NOT internal functions
3. **Verify State**: Query database after commands to verify changes
4. **Full Option Coverage**: Test every CLI option explicitly
5. **Edge Cases**: Test error conditions and unusual inputs
6. **JSON Output**: Verify --format json returns valid, complete JSON

## Estimated Scope

- **New test files**: 15
- **New test functions**: ~200
- **Stories**: 42

## Dependencies

- Dolt CLI installed for test execution
- pytest-timeout for server tests
- API keys for optional integration tests (skipped without keys)

## Success Criteria

- [ ] All CLI commands have E2E tests
- [ ] All command options are tested
- [ ] Tests pass in CI (with Dolt installed)
- [ ] Code coverage for CLI modules > 80%
- [ ] No internal mocking in E2E tests
