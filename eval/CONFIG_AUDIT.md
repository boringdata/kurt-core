# Config Parameter Audit

## Parameters in config.yaml

### ✅ USED AND PROPERLY CONFIGURED

| Parameter | Location | Used In | Status |
|-----------|----------|---------|--------|
| `guardrails.max_tool_calls` | config.yaml:12 | runner.py:108 | ✅ Used via config property |
| `guardrails.max_duration_seconds` | config.yaml:15 | runner.py:111 | ✅ Used via config property |
| `guardrails.max_tokens` | config.yaml:18 | runner.py:115 | ✅ Used via config property |
| `guardrails.max_conversation_turns` | config.yaml:21 | runner.py:119 | ✅ FIXED - now used via config property |
| `workspace.preserve_on_error` | config.yaml:30 | runner.py:101 | ✅ Used via config property |
| `workspace.preserve_on_success` | config.yaml:33 | runner.py:103 | ✅ Used via config property |
| `workspace.init_kurt` | config.yaml:36 | workspace.py | ✅ Used via config property |
| `workspace.install_claude_plugin` | config.yaml:39 | workspace.py | ✅ Used via config property |
| `workspace.claude_plugin_path` | config.yaml:44 | workspace.py | ✅ Used via config property |
| `user_agent.llm_provider` | config.yaml:55 | runner.py:121 | ✅ Used via config property |
| `output.verbose` | config.yaml:95 | runner.py:106 | ✅ Used via config property |
| `output.results_dir` | config.yaml:101 | Used in results | ✅ Property exists |
| `sdk.allowed_tools` | config.yaml:70-78 | runner.py SDK | ✅ Used via config property |
| `sdk.permission_mode` | config.yaml:81 | runner.py SDK | ✅ Used via config property |
| `sdk.setting_sources` | config.yaml:84-86 | runner.py SDK | ✅ Used via config property |

### ⚠️ PARTIALLY USED (defined but hardcoded elsewhere)

| Parameter | Location | Issue | Action Needed |
|-----------|----------|-------|---------------|
| `scenarios.scenarios_file` | config.yaml:113 | Hardcoded in cli.py:158 as "scenarios/scenarios.yaml" | Use config |
| `scenarios.scenarios_dir` | config.yaml:116 | Hardcoded in cli.py:54,159 as "scenarios" | Use config |

### ❌ DEFINED BUT NEVER USED

| Parameter | Location | Has Property? | Used Anywhere? | Action |
|-----------|----------|---------------|----------------|--------|
| `user_agent.fallback_to_regex` | config.yaml:58 | ❌ No | ❌ No | Remove from YAML |
| `user_agent.default_response` | config.yaml:61 | ❌ No | ⚠️ Hardcoded in yaml_loader.py | Keep, needs property |
| `output.save_transcript` | config.yaml:98 | ✅ Yes | ❌ No | Remove from YAML or implement |
| `output.use_colors` | config.yaml:104 | ❌ No | ❌ No | Remove from YAML |
| `scenarios.yaml_extensions` | config.yaml:119-121 | ❌ No | ⚠️ Hardcoded in runner.py | Keep, use config |
| `performance.parallel_scenarios` | config.yaml:131 | ❌ No | ❌ No | Remove (not implemented) |
| `performance.tool_timeout` | config.yaml:134 | ❌ No | ❌ No | Remove (not implemented) |
| `performance.max_tool_output` | config.yaml:137 | ❌ No | ❌ No | Remove (not implemented) |
| `assertions.fail_fast` | config.yaml:163 | ❌ No | ❌ No | Remove (not implemented) |
| `assertions.verbose_errors` | config.yaml:166 | ❌ No | ❌ No | Remove (not implemented) |

### 📝 DOCUMENTATION ONLY

| Parameter | Location | Purpose |
|-----------|----------|---------|
| `api_keys.*` | config.yaml:145-154 | Documentation only |
| `metadata.*` | config.yaml:172-177 | Documentation only |

## Recommendations

1. **Remove unused parameters** from config.yaml:
   - `user_agent.fallback_to_regex`
   - `output.use_colors`
   - `performance.*` (entire section - not implemented)
   - `assertions.*` (entire section - not implemented)
   - `output.save_transcript` (or implement it)

2. **Use config instead of hardcoded values**:
   - cli.py should use `config.get('scenarios.scenarios_file')`
   - cli.py should use `config.get('scenarios.scenarios_dir')`
   - runner.py should use `config.get('scenarios.yaml_extensions')`

3. **Add missing properties** for actually-used values:
   - `default_response` - used in yaml_loader.py but no property

4. **Keep documentation sections**:
   - `api_keys` - useful documentation
   - `metadata` - useful documentation
