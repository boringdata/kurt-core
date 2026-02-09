# Pitfalls Research: Python Plugin System for Kurt CLI

**Domain:** Python CLI extensibility via skill plugins
**Researched:** 2026-02-09
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Async/Sync Event Loop Collision

**What goes wrong:**
A plugin uses synchronous blocking code (e.g., `time.sleep()`, `requests.get()`, synchronous file I/O) while the core CLI is running an asyncio event loop. This freezes the entire event loop, preventing other async tasks from making progress and destroying the fundamental benefits of async architecture.

**Why it happens:**
Plugin authors don't understand the async boundary or assume they can freely mix sync/async code. Python doesn't prevent calling sync code from async contexts - it just fails silently by blocking everything.

**How to avoid:**
- **Enforce async-first interfaces**: All plugin entry points must be `async def` functions
- **Provide `run_in_executor()` helpers**: Offer utility functions that wrap sync code safely: `await kurt.execute_sync(blocking_function)`
- **Document the execution model explicitly**: Make it clear that plugins run in an async context
- **Detect blocking calls in dev mode**: Use event loop monitoring to detect when the loop is blocked > 100ms

**Warning signs:**
- CLI becomes unresponsive during plugin execution
- Rich progress displays freeze
- Multiple async workflows don't run concurrently
- `RuntimeWarning: coroutine was never awaited`

**Phase to address:**
Phase 1 (Core Interface Design) - Define async-first plugin interface. Phase 3 (Documentation & Examples) - Provide clear guidance and examples for both async and sync plugin code.

---

### Pitfall 2: Import-Time Heavy Dependencies

**What goes wrong:**
Plugins import heavy ML/data libraries (`pandas`, `numpy`, `transformers`, `torch`) at module level. Every CLI command suffers a 500ms-2s startup penalty even for commands that don't use those plugins.

**Why it happens:**
Natural Python pattern is top-level imports. Plugin authors don't think about import cost because they only test their specific workflow, not the overall CLI startup.

**How to avoid:**
- **Lazy import enforcement**: Require plugins to declare heavy dependencies and lazy-load them in function bodies
- **Provide lazy import helpers**: Offer `kurt.lazy_import("pandas", "pd")` wrapper
- **Separate plugin discovery from loading**: Use entry points for discovery, but only import plugin modules when invoked
- **Set startup time budget**: Fail CI if `kurt --help` takes > 200ms

**Warning signs:**
- `kurt --help` takes > 500ms
- Simple commands (`kurt config get`) have noticeable latency
- Import of unused workflow code paths
- User complaints about CLI "feeling slow"

**Phase to address:**
Phase 1 (Core Interface Design) - Design plugin loading strategy with lazy imports. Phase 2 (Plugin Discovery) - Implement discovery without import. Phase 4 (Testing & Validation) - Add startup time tests.

---

### Pitfall 3: Plugin Dependency Conflicts

**What goes wrong:**
Plugin A requires `pydantic==2.0` while Plugin B requires `pydantic==1.10`. pip installs only one version, causing one plugin to break with import errors or runtime type validation failures.

**Why it happens:**
Python's site-packages is a global namespace with no built-in isolation. Different plugins have different dependency requirements that can't coexist in a single environment.

**How to avoid:**
- **Document supported version ranges**: Core maintains compatibility matrix (e.g., "Kurt supports pydantic >=2.0,<3.0")
- **Use loose version pins**: Encourage plugins to use wide ranges (`pydantic>=2.0` not `pydantic==2.5.3`)
- **Fail early with clear errors**: Detect incompatible dependencies at plugin registration time
- **Consider plugin vendoring**: For truly isolated plugins, use PEX or zipapp with vendored deps

**Warning signs:**
- `ImportError` or `AttributeError` when loading specific plugins
- Type validation errors from Pydantic models
- Cryptic errors like "no attribute 'Field'" after installing a new plugin
- Bug reports that only occur with certain plugin combinations

**Phase to address:**
Phase 2 (Plugin Discovery) - Implement dependency checking at registration. Phase 3 (Documentation & Examples) - Document dependency guidelines. Phase 5 (Advanced Features) - Consider isolated plugin loading.

---

### Pitfall 4: Uncaught Plugin Exceptions Break Core

**What goes wrong:**
A plugin raises an unhandled exception (e.g., `KeyError` due to missing data, network timeout without retry). This crashes the entire CLI command or workflow, losing all progress.

**Why it happens:**
Plugins are third-party code with unpredictable failure modes. Kurt's async workflow system may not have proper exception boundaries around plugin execution.

**How to avoid:**
- **Isolate plugin execution**: Wrap all plugin calls in try/except with explicit error handling
- **Provide error context**: Capture plugin name, version, inputs when exceptions occur
- **Continue on plugin failure**: Design workflows to gracefully degrade if a plugin fails
- **Return Result types**: Use `Result[T, Error]` pattern instead of raising exceptions

**Warning signs:**
- Full CLI crashes from plugin errors
- Stack traces showing plugin code as the source
- Loss of partial workflow results
- No way to identify which plugin caused the failure

**Phase to address:**
Phase 1 (Core Interface Design) - Define error handling boundaries. Phase 4 (Testing & Validation) - Test failure scenarios. Phase 5 (Advanced Features) - Implement graceful degradation.

---

### Pitfall 5: Plugin Security - Arbitrary Code Execution

**What goes wrong:**
Users install malicious skill files from untrusted sources. The plugin executes at import time or during runtime with full filesystem/network access, stealing credentials, modifying data, or installing backdoors.

**Why it happens:**
Python's import system executes code immediately. Dynamic imports using `importlib` provide no sandboxing. Users trust plugins like they trust packages, but skill files are user-generated content.

**How to avoid:**
- **Explicit opt-in for third-party plugins**: Warn before loading plugins from outside known directories
- **Sandboxing for untrusted plugins**: Use `RestrictedPython` or subprocess isolation for community plugins
- **Code signing**: Verify signatures for official plugins
- **Audit imports at registration**: Scan for dangerous patterns (`eval`, `exec`, `__import__`, subprocess)
- **Restrict filesystem access**: Plugins should only write to designated directories

**Warning signs:**
- Network calls during plugin import
- File writes outside project directory
- Environment variable access during import
- Suspicious imports: `socket`, `subprocess`, `os.system`, `eval`

**Phase to address:**
Phase 2 (Plugin Discovery) - Implement registration-time validation. Phase 3 (Documentation & Examples) - Security guidelines. Phase 5 (Advanced Features) - Sandboxing for untrusted plugins.

---

### Pitfall 6: Plugin API Versioning Chaos

**What goes wrong:**
Core Kurt CLI updates break existing plugins because the plugin API changed without versioning. Users upgrade Kurt and all their custom skills stop working with `AttributeError: 'SkillContext' has no attribute 'workflow_id'`.

**Why it happens:**
No explicit versioning of the plugin interface. Breaking changes ship without deprecation warnings or migration guides. Plugins don't declare which API version they target.

**How to avoid:**
- **Semantic versioning for plugin API**: Use separate version from Kurt package version
- **Declare API version in plugin metadata**: `skill_api_version = "1.0"`
- **Maintain backwards compatibility**: Support old API versions with deprecation warnings
- **Version detection at load time**: Reject plugins that target unsupported API versions

**Warning signs:**
- Plugins break after Kurt upgrades
- No way to know which Kurt version a plugin was built for
- Users afraid to upgrade Kurt due to plugin breakage
- GitHub issues: "Plugin X stopped working after update"

**Phase to address:**
Phase 1 (Core Interface Design) - Define versioned plugin API. Phase 2 (Plugin Discovery) - Check version compatibility at load. Phase 4 (Testing & Validation) - Test cross-version compatibility.

---

### Pitfall 7: Plugin State Leakage Between Invocations

**What goes wrong:**
A plugin stores state in module-level variables (e.g., a cache, configuration, or connection pool). When the plugin is called multiple times or from concurrent workflows, state bleeds between invocations causing race conditions or stale data.

**Why it happens:**
Python modules are singletons - imported once and reused. Plugin authors write stateful code assuming each invocation is isolated. Kurt's workflow system may execute plugins concurrently.

**How to avoid:**
- **Design stateless plugin interface**: Pass all context as function parameters
- **Provide plugin instance lifecycle hooks**: `on_load()`, `on_invoke()`, `on_cleanup()`
- **Thread-local storage for plugin context**: Use `threading.local()` for per-invocation state
- **Document concurrency model**: Make it explicit that plugins may be called concurrently

**Warning signs:**
- Race conditions in plugin tests
- Intermittent failures that disappear with sequential execution
- Data corruption when running parallel workflows
- Connection pool exhaustion

**Phase to address:**
Phase 1 (Core Interface Design) - Define stateless interface. Phase 4 (Testing & Validation) - Test concurrent plugin execution. Phase 5 (Advanced Features) - Add lifecycle hooks if needed.

---

### Pitfall 8: Entry Point Discovery Namespace Pollution

**What goes wrong:**
Multiple plugins register entry points in the same namespace (e.g., `kurt.skills`). Entry point names collide, causing plugins to silently override each other. Users install "skill-summarize" and "skill-summary" which both register as `summarize`, and only one works.

**Why it happens:**
setuptools entry points don't enforce uniqueness. Plugin authors choose obvious names that collide. Kurt doesn't validate for conflicts at registration time.

**How to avoid:**
- **Use fully qualified names**: Encourage `author.skill_name` pattern (e.g., `kurt.summarize`, `custom.summarize`)
- **Detect conflicts at discovery**: Fail with clear error if two plugins claim the same name
- **Provide plugin namespace**: Kurt core reserves `kurt.*`, community plugins use their own prefix
- **Allow explicit override**: Let users choose which plugin wins via config

**Warning signs:**
- Plugin commands mysteriously not working
- Installing a new plugin breaks an existing one
- No error message, just silent failure
- `kurt skills list` shows only one of two installed plugins

**Phase to address:**
Phase 2 (Plugin Discovery) - Implement conflict detection. Phase 3 (Documentation & Examples) - Document naming conventions.

---

## Moderate Pitfalls

### Pitfall 9: Plugin Testing Without Core Integration

**What goes wrong:**
Plugin authors test their skill in isolation using mocks. It works in their tests but fails when integrated with Kurt because of incorrect assumptions about data formats, execution context, or API behavior.

**Prevention:**
- Provide `kurt-plugin-test` test harness that simulates real execution
- Ship example plugins with comprehensive tests
- Document plugin testing best practices
- Offer pytest fixtures for common testing scenarios

---

### Pitfall 10: Implicit Dependency on Core Internals

**What goes wrong:**
Plugins import from `kurt.db.dolt` or `kurt.core.models` instead of using the public plugin API. Core refactors break plugins because they're coupled to internal implementation details.

**Prevention:**
- Define clear public API in `kurt.plugin.*` namespace
- Mark internal modules as private (leading underscore)
- Use `__all__` to explicitly export public API
- Static analysis to detect plugins importing private modules

---

### Pitfall 11: Plugin Documentation Drift

**What goes wrong:**
SKILL.md metadata diverges from actual skill.py implementation. Title, parameters, or behavior documented in the YAML frontmatter doesn't match the Python code.

**Prevention:**
- Generate documentation from code where possible
- Validation at registration time: verify declared parameters match function signature
- Provide `kurt skill validate` command
- CI checks for skill documentation consistency

---

### Pitfall 12: Platform-Specific Plugin Code

**What goes wrong:**
Plugin works on macOS/Linux but fails on Windows due to path separators, shell commands, or missing dependencies. Users report "skill works for me but not for others."

**Prevention:**
- Provide cross-platform utilities in plugin API: `kurt.plugin.paths`, `kurt.plugin.run_command`
- Test plugins on multiple platforms in CI
- Document platform requirements in SKILL.md
- Detect platform-specific patterns during validation

---

## Minor Pitfalls

### Pitfall 13: Plugin Logging Interferes with CLI Output

**What goes wrong:**
Plugin uses `print()` or `logging.info()` which pollutes Kurt's structured CLI output. JSON output becomes unparseable.

**Prevention:**
- Provide plugin logging API: `context.log()`, `context.warn()`, `context.error()`
- Redirect stdout/stderr during plugin execution
- Document that plugins should use structured logging, not print

---

### Pitfall 14: Resource Leaks in Long-Running Plugins

**What goes wrong:**
Plugin opens files, database connections, or HTTP sessions without closing them. Over time this exhausts file descriptors or connection pools.

**Prevention:**
- Encourage context manager usage in examples
- Provide resource management helpers
- Implement timeout for plugin execution
- Monitor resource usage and warn on leaks

---

### Pitfall 15: Plugin Startup Validation Missing

**What goes wrong:**
Plugin needs external dependencies (API keys, CLI tools, data files) but only fails at runtime, wasting user time.

**Prevention:**
- Provide `validate()` hook called at registration
- Offer `--validate` flag to check plugin health
- Clear error messages with remediation steps
- Fail fast with actionable errors

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Allow sync plugins with auto-wrapping | Easy adoption, no async learning curve | Event loop blocking, poor perf, hard to debug | Never - async must be explicit |
| Skip dependency conflict checking | Simple implementation, works in single-plugin case | Users hit cryptic errors with multiple plugins | Only in MVP if clearly documented as limitation |
| Use exec() for plugin loading | Simple, flexible, no entry points needed | Security nightmare, debugging impossible | Never - use importlib.import_module |
| Module-level plugin state | Natural Python pattern | Race conditions, memory leaks, test pollution | Only for truly immutable config |
| No API versioning | Fast iteration, no compatibility burden | Breaking changes break all plugins | Only pre-1.0 if community warned |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Async plugins | Forgetting `await` when calling async plugin functions | Enforce `async def` signature, use type hints, fail on coroutine objects |
| Plugin discovery | Importing all plugins to discover them (slow startup) | Use importlib.metadata to read entry points without import |
| Error handling | Letting plugin exceptions propagate | Wrap plugin calls in try/except, return Result type |
| Testing | Mocking plugin interface in tests | Use real plugin loading with test plugins, verify contract |
| Documentation | Separate docs from code | Use Pydantic models for parameters, generate docs from types |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Import-time heavy deps | CLI startup > 1s | Lazy imports, separate discovery from loading | First plugin with ML libs installed |
| Loading all plugins upfront | Help command slow | Load plugins on-demand when invoked | > 5 plugins installed |
| No plugin caching | Re-parsing SKILL.md every invocation | Cache parsed metadata, invalidate on file change | > 20 plugins, high-frequency commands |
| Synchronous plugin in async workflow | Event loop blocking, poor concurrency | Enforce async interface, detect blocking calls | First sync plugin used |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Execute plugin code at import | Malicious code runs during discovery | Use AST parsing for metadata, defer execution |
| Unrestricted filesystem access | Plugin deletes user data or system files | Sandbox plugins, restrict writes to designated dirs |
| No input validation | Plugin crashes on malformed input | Validate inputs against schema before invoking plugin |
| Eval/exec user input | Remote code execution | Never use eval/exec, use ast.literal_eval for data |
| Network access during import | Data exfiltration, slow startup | Block network during discovery, allow only at runtime with user consent |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent plugin load failures | User invokes skill, nothing happens, no error | Show clear error with plugin name, failure reason, remediation |
| Plugin errors crash entire workflow | Loss of partial work | Isolate plugin failures, continue workflow, report errors at end |
| No plugin discovery feedback | User installs plugin, doesn't know if it worked | `kurt plugins list`, `kurt plugins validate` commands |
| Unclear plugin requirements | Plugin fails with "module not found" | Declare dependencies in SKILL.md, check at registration, helpful errors |
| Version incompatibility silent | Plugin breaks after Kurt upgrade | Check API version, show deprecation warnings, migration guides |

---

## "Looks Done But Isn't" Checklist

- [ ] **Plugin error isolation:** Verify plugin exceptions don't crash core CLI - test with deliberately broken plugin
- [ ] **Async enforcement:** Check that sync plugins are rejected or properly wrapped - test with blocking `time.sleep()` plugin
- [ ] **Entry point conflicts:** Test installing two plugins with same name - verify clear error message
- [ ] **Import performance:** Measure `kurt --help` time with 10+ plugins - should be < 300ms
- [ ] **Dependency conflicts:** Install two plugins with conflicting dependencies - fails gracefully with clear error
- [ ] **Security scanning:** Verify dangerous imports are detected - test with plugin using `eval()`, `exec()`, `__import__`
- [ ] **API versioning:** Install plugin targeting old API version - clear error message with migration guide
- [ ] **Concurrent execution:** Run same plugin from 5 parallel workflows - no race conditions or state leakage
- [ ] **Cross-platform:** Test plugins on Linux, macOS, Windows - path handling, shell commands work everywhere
- [ ] **Documentation validation:** SKILL.md parameters must match skill.py function signature - automated check

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Async/sync collision | LOW | Detect in dev, add async wrapper or reject sync plugin |
| Import-time dependencies | LOW | Refactor to lazy imports, update examples |
| Dependency conflicts | MEDIUM | Adjust version ranges, document compatibility, consider vendoring |
| Plugin exceptions crashing core | LOW | Add exception boundaries, implement error handling |
| Security vulnerability | HIGH | Audit all plugins, implement sandboxing, notify users |
| API versioning missing | HIGH | Retrofit versioning, support migration, maintain old APIs |
| State leakage | MEDIUM | Refactor to stateless design, add concurrency tests |
| Entry point conflicts | LOW | Add conflict detection, namespace conventions |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Async/sync collision | Phase 1: Interface Design | Test plugin with `time.sleep()`, verify event loop not blocked |
| Import-time dependencies | Phase 1: Interface Design, Phase 2: Discovery | Measure `kurt --help` < 300ms with 10 plugins |
| Dependency conflicts | Phase 2: Plugin Discovery | Install conflicting plugins, verify clear error |
| Uncaught exceptions | Phase 1: Interface Design | Inject plugin that raises KeyError, verify graceful handling |
| Security - code execution | Phase 2: Plugin Discovery, Phase 5: Sandboxing | Test plugin with `eval()`, verify rejected or sandboxed |
| API versioning | Phase 1: Interface Design | Load plugin with incompatible API version, verify error |
| State leakage | Phase 1: Interface Design | Run 10 concurrent plugin invocations, verify isolation |
| Entry point conflicts | Phase 2: Plugin Discovery | Install two plugins with same name, verify conflict detection |
| Testing isolation | Phase 3: Documentation | Ship test harness, verify plugins can run integration tests |
| Internal API coupling | Phase 1: Interface Design | Static analysis detects private imports |
| Documentation drift | Phase 2: Plugin Discovery | Validate SKILL.md matches skill.py signature |
| Platform-specific code | Phase 3: Documentation | Test plugins on Linux, macOS, Windows |
| Logging pollution | Phase 1: Interface Design | Verify `kurt skill run --json` output is valid JSON |
| Resource leaks | Phase 4: Testing | Run plugin 100 times, verify file descriptors stable |
| Missing validation | Phase 2: Plugin Discovery | Call plugin without required deps, verify clear error |

---

## Sources

**Web Search - Python Plugin Patterns:**
- [Plugin Architecture in Python - DEV Community](https://dev.to/charlesw001/plugin-architecture-in-python-jla)
- [Implementing a Plugin Architecture in a Python Application - Siv Scripts](https://alysivji.com/simple-plugin-system.html)
- [Python Packaging User Guide - Creating and discovering plugins](https://packaging.python.org/guides/creating-and-discovering-plugins/)

**Web Search - Async Compatibility:**
- [Python Asyncio Part 5 – Mixing Synchronous and Asynchronous Code | cloudfit-public-docs](https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-5.html)
- [Python & Async Simplified - Aeracode](https://www.aeracode.org/2018/02/19/python-async-simplified/)
- [Running async code from sync code in Python - death and gravity](https://death.andgravity.com/asyncio-bridge)

**Web Search - Security Risks:**
- [Python Security Vulnerabilities | Top Issues](https://www.aikido.dev/blog/python-security-vulnerabilities)
- [The dangers of Python import and how enterprises can be safe | TheServerSide](https://www.theserverside.com/tip/The-dangers-of-Python-import-and-how-enterprises-can-be-safe)
- [Code Injection in Python | Semgrep](https://semgrep.dev/docs/cheat-sheets/python-code-injection)

**Web Search - Dependency Conflicts:**
- [ModuleGuard: Understanding and Detecting Module Conflicts in Python Ecosystem](https://arxiv.org/html/2401.02090v1)
- [Python Package Management: A Guide to Avoid Dependency Conflicts | by Hugo Perrier | MAIF Data Design Tech etc. | Medium](https://medium.com/maif-data-design-tech-etc/python-package-management-a-guide-to-avoid-dependency-conflicts-0f0fe292f766)

**Web Search - Lazy Loading:**
- [PEP 810 – Explicit lazy imports | peps.python.org](https://peps.python.org/pep-0810/)
- [Python Lazy Imports: Speed Up Startup with PEP 810 | byteiota](https://byteiota.com/python-lazy-imports-speed-up-startup-with-pep-810/)
- [Scientific Python - SPEC 1 — Lazy Loading of Submodules and Functions](https://scientific-python.org/specs/spec-0001/)

**Web Search - Entry Points:**
- [Entry Points - setuptools documentation](https://setuptools.pypa.io/en/latest/userguide/entry_point.html)
- [Python Packaging User Guide - Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)

**Web Search - Error Handling:**
- [API Error Handling & Retry Strategies: Python Guide 2026](https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide)
- [Building a Self-Healing Data Pipeline That Fixes Its Own Python Errors | Towards Data Science](https://towardsdatascience.com/building-a-self-healing-data-pipeline-that-fixes-its-own-python-errors/)

**Web Search - API Versioning:**
- [C API Stability — Python documentation](https://docs.python.org/3/c-api/stable.html)
- [API Versioning Best Practices for Backward Compatibility | Endgrate](https://endgrate.com/blog/api-versioning-best-practices-for-backward-compatibility)

---

*Pitfalls research for: Python CLI plugin system (SKILL.md + skill.py extensibility)*
*Researched: 2026-02-09*
