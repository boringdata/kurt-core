# Technology Stack

**Project:** Kurt Plugin/Skill System
**Researched:** 2026-02-09
**Confidence:** HIGH

## Recommended Stack

### Core Plugin Infrastructure

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **importlib.metadata** | stdlib (3.13+) | Entry point discovery | Standard library solution for plugin discovery. Native since Python 3.8, stable API since 3.10. Zero dependencies. Supports both installed packages and local file-based plugins. |
| **apluggy** | 1.1.2+ | Hook system with async support | Only mature hook system with native async/await support. Wraps pluggy (industry standard from pytest) while adding async hooks, context managers, and plugin factories. Essential for Kurt's async codebase. |
| **tomllib** | stdlib (3.11+) | Manifest parsing (TOML) | Standard library TOML parser since Python 3.11. Zero dependencies for reading SKILL.toml manifests. No need for external libraries. |
| **Pydantic** | 2.12.5+ | Manifest validation | Already in Kurt's stack. Type-safe validation of SKILL.toml manifests with excellent error messages. V2 offers 5-50x performance improvement over v1. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **PyYAML** | 6.0.3+ | Alternative manifest format | If supporting SKILL.yaml in addition to TOML. Production-stable, YAML 1.1 compliant. Optional - only add if users request YAML support. |
| **tomli-w** | 0.4.0+ | TOML writing | If implementing skill scaffolding commands (e.g., `kurt skill create`). tomllib is read-only. |
| **importlib.util** | stdlib | Dynamic module loading | Loading skill.py files from filesystem paths. Part of standard library, no installation needed. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest-asyncio** | Testing async plugins | Already in Kurt's stack. Essential for testing async hook implementations. |
| **pytest-mock** | Mock plugin loading | Already in Kurt's stack. Useful for testing plugin discovery without installing real plugins. |

## Installation

```bash
# Core (already in Kurt's dependencies)
pip install pydantic>=2.12.5

# Async plugin system
pip install apluggy>=1.1.2

# Optional: TOML writing for scaffolding
pip install tomli-w>=0.4.0

# Optional: YAML manifest support
pip install PyYAML>=6.0.3

# Dev dependencies (already in Kurt)
pip install pytest-asyncio pytest-mock
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Hook System | apluggy | pluggy | Pluggy 1.6.0 has no async support. Would require complex workarounds for Kurt's async code. apluggy wraps pluggy and adds async seamlessly. |
| Hook System | apluggy | simplug | Simplug 0.5.6 supports async but less mature (8 stars vs pluggy's thousands). apluggy benefits from pluggy's battle-tested foundation. |
| Hook System | apluggy | stevedore | Stevedore 5.6.0 is OpenStack-heavy, no async support, more complex than needed. Better for large enterprise apps. |
| Discovery | importlib.metadata | click-plugins | click-plugins 1.1.1.2 is unmaintained since 2025. Locked to entry points only. importlib.metadata is more flexible and standard. |
| Discovery | importlib.metadata | pkg_resources | pkg_resources is legacy (deprecated in setuptools). Slow imports, complex API. importlib.metadata is modern replacement. |
| Manifest | tomllib | toml | toml library is deprecated. tomllib is stdlib since Python 3.11 and is the official replacement. |
| Manifest | TOML | JSON | TOML is more human-friendly for configs. Supports comments. Better for user-authored files. |
| Validation | Pydantic | dataclasses | Pydantic offers validation, error messages, coercion. dataclasses are just type hints without validation. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **pkg_resources** | Deprecated by setuptools. Slow imports (scans all packages). Legacy API superseded by importlib.metadata in Python 3.8+. | importlib.metadata |
| **pluginbase (mitsuhiko)** | Abandoned since 2018. No async support. No Python 3.10+ testing. | apluggy + importlib.metadata |
| **click-plugins** | Marked "no longer actively maintained" as of 2025. Locks you into entry points only, can't do file-based discovery. | importlib.metadata + custom Click integration |
| **toml library** | Deprecated. Superseded by stdlib tomllib in Python 3.11. | tomllib (read) + tomli-w (write) |
| **ruamel.yaml** | Overkill for simple manifest parsing. 10x slower than PyYAML for basic use. Use only if you need round-trip YAML editing. | PyYAML |

## Stack Patterns by Discovery Mode

Kurt should support two plugin discovery modes:

### Mode 1: Installed Packages (Entry Points)

**When:** Plugins distributed via PyPI/pip

**Stack:**
```python
from importlib.metadata import entry_points
import apluggy

# Discover
eps = entry_points(group='kurt.skills')
for ep in eps:
    skill_module = ep.load()

# Execute with hooks
pm = apluggy.PluginManager('kurt')
pm.add_hookspecs(skill_module)
await pm.ahook.extract_content(url=url)
```

**Why:** Standard Python packaging. Users `pip install kurt-skill-example`. Works with virtual environments, dependency management.

### Mode 2: Local Filesystem (SKILL.md + skill.py)

**When:** Users drop folder into `~/.kurt/skills/` or project directory

**Stack:**
```python
import tomllib
from pathlib import Path
import importlib.util
import apluggy
from pydantic import BaseModel

class SkillManifest(BaseModel):
    name: str
    version: str
    description: str
    async_hooks: list[str]

# Discover
skills_dir = Path.home() / '.kurt' / 'skills'
for skill_path in skills_dir.iterdir():
    manifest_file = skill_path / 'SKILL.toml'

    # Parse manifest
    with open(manifest_file, 'rb') as f:
        manifest_data = tomllib.load(f)
    manifest = SkillManifest.model_validate(manifest_data)

    # Load skill.py
    skill_file = skill_path / 'skill.py'
    spec = importlib.util.spec_from_file_location(manifest.name, skill_file)
    skill_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skill_module)

    # Register with apluggy
    pm.register(skill_module, name=manifest.name)
```

**Why:** Zero-friction for users. No packaging required. "Drop folder and go" experience. Ideal for custom/private skills.

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| apluggy 1.1.2 | Python 3.9+ | Requires pluggy (auto-installed). Tested with asyncio. |
| Pydantic 2.12.5 | Python 3.9+ | Breaking changes from v1. Check CLAUDE.md migration notes if upgrading. |
| tomllib | Python 3.11+ | Stdlib only. For Python <3.11, use tomli backport. |
| PyYAML 6.0.3 | Python 3.8+ | Safe loading default since 5.1. Always use `yaml.safe_load()`. |

## Architecture Decision: Async-First

**Why apluggy is essential:**

Kurt's existing tools are async:
```python
# From CLAUDE.md examples
async def fetch_workflow(config_dict: dict) -> dict:
    # Existing engine dispatchers are async
    await engine.extract(url)
```

Plugin hooks must integrate with this:
```python
# With apluggy - works seamlessly
@apluggy.hookimpl
async def extract_content(url: str) -> dict:
    # Native async, no wrappers needed
    return await my_async_extraction(url)

pm = apluggy.PluginManager('kurt')
result = await pm.ahook.extract_content(url=url)
```

**Without async support (using regular pluggy):**
```python
# Forced to wrap everything - messy
@pluggy.hookimpl
def extract_content(url: str) -> dict:
    # Have to run event loop manually
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(my_async_extraction(url))
```

**Verdict:** apluggy's async support is not optional - it's required for clean integration with Kurt's async architecture.

## Confidence Assessment

| Technology | Confidence | Rationale |
|------------|------------|-----------|
| importlib.metadata | **HIGH** | Python stdlib since 3.8, stable API since 3.10. Official Python Packaging Guide recommends it. Verified in Python 3.13 docs. |
| apluggy | **HIGH** | Latest release Nov 20, 2025. Active maintenance. Only mature async hook system. Wraps battle-tested pluggy. Verified on PyPI and GitHub. |
| tomllib | **HIGH** | Python stdlib since 3.11 (PEP 680). Official replacement for toml library. Verified in Python 3.13 docs. |
| Pydantic | **HIGH** | Already in Kurt's stack. Current version 2.12.5 (Nov 26, 2025). Production-stable, widely adopted. |
| PyYAML | **MEDIUM** | Production-stable but optional. Only needed if users request YAML support. TOML is sufficient for MVP. |

## Sources

### High Confidence (Official Documentation)
- [importlib.metadata — Python 3.13 Documentation](https://docs.python.org/3.13/library/importlib.metadata.html)
- [tomllib — Python 3.13 Documentation](https://docs.python.org/3/library/tomllib.html)
- [Entry Points Specification — Python Packaging Guide](https://packaging.python.org/specifications/entry-points/)
- [Pydantic 2.12.5 — PyPI](https://pypi.org/project/pydantic/)
- [pluggy 1.6.0 — PyPI](https://pypi.org/project/pluggy/)

### High Confidence (Verified Packages)
- [apluggy 1.1.2 — GitHub](https://github.com/simonsobs/apluggy) (Nov 20, 2025)
- [PyYAML 6.0.3 — PyPI](https://pypi.org/project/PyYAML/) (Sep 25, 2025)

### Medium Confidence (Community Resources)
- [How to Build Plugin Systems in Python](https://oneuptime.com/blog/post/2026-01-30-python-plugin-systems/view) (Jan 30, 2026)
- [Creating and discovering plugins — Python Packaging Guide](https://packaging.python.org/guides/creating-and-discovering-plugins/)
- [simplug — GitHub](https://github.com/pwwang/simplug) (Alternative async system for comparison)

---
*Stack research for: Python CLI Plugin/Skill System (Kurt)*
*Researched: 2026-02-09*
*Researcher: GSD Project Researcher*
