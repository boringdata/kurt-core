# Commands Folder - Final Review

## ✅ Framework Migration Status

### Fully Migrated Commands
- ✅ **`map.py`**: Uses `run_pipeline_simple()` with `landing.discovery` model
  - All three subcommands (url, folder, cms) use new pipeline
  - `dry_run` support added to `DiscoveryConfig`
  - No direct DBOS calls
  - No old `kurt.content.map` imports (except clustering utility)

- ✅ **`fetch.py`**: Uses `run_pipeline_simple()` with `landing.fetch` and `staging` models
  - Uses workflows module for execution
  - Config passed via `model_configs` parameter
  - No direct DBOS calls

- ✅ **`index.py`**: Uses `run_pipeline_simple()` with `staging` model
  - Uses shared filter options (`@add_filter_options`)
  - Uses `resolve_filters()` helper
  - No direct DBOS calls

### Remaining Dependencies

#### `kurt.content.cluster` (OK - Utility, not workflow)
- Used in: `map.py`, `cluster.py`
- **Status**: ✅ This is a utility function for clustering, not part of old workflow system
- **Action**: Keep as-is

## 🧹 Code Quality

### Shared Patterns
- ✅ All commands use `run_pipeline_simple()` from `kurt.workflows.cli_helpers`
- ✅ All commands use `DocumentFilters` from `kurt.utils.filtering`
- ✅ Config passed via `model_configs` parameter (proper config module usage)
- ✅ Display handled automatically by framework decorator

### Deprecated Flags (Handled with warnings)
- `--url`, `--file` in `fetch.py` → merged into positional identifier
- `--force` in `fetch.py`, `delete.py` → shows deprecation warning

### Helper Files
- ✅ `_shared_options.py`: Shared filter options decorator
- ✅ `_fetch_helpers.py`: Utility functions (no workflow logic)

## 📊 Summary

### Framework Usage
- **100%** of workflow execution uses new framework (`run_pipeline_simple`)
- **0** direct DBOS imports in workflow execution paths
- **0** old `kurt.content.map` imports (only clustering utility remains)

### Dead Code
- **None found** - all imports are used
- Deprecated flags are handled with warnings (intentional)

### Recommendations
1. ✅ All commands fully use new framework
2. ✅ No dead code found
3. ✅ Clustering utility (`kurt.content.cluster`) is separate from workflow system - keep as-is

## 🎯 Conclusion

**All commands are fully migrated to the new framework!**

- All workflow execution goes through `kurt.workflows.cli_helpers`
- All config uses proper `ModelConfig` pattern
- All display handled by framework
- No dead code or unused imports

The only remaining `kurt.content` import is `kurt.content.cluster`, which is a utility function (not a workflow) and should remain.

