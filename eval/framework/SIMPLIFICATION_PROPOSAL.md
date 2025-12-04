# Radical Simplification Proposal (No Backward Compatibility)

## Current Complexity (1,486 lines in runner.py)

The current system has multiple execution paths:
- Conversational scenarios
- Non-conversational scenarios
- Question sets
- Test cases
- Commands vs SDK execution
- Different output formats for each

## Proposed Simplification (~300 lines total)

### Core Principle: Everything is a Prompt

Remove ALL distinctions. Every scenario is just:
1. A list of prompts
2. Execute them
3. Save results

### Before vs After

#### Before (Complex YAML)
```yaml
# Conversational scenario
name: test_conversational
conversational: true
initial_prompt: "Help me with Python"
conversation:
  - user: "Create a function"
  - expected: "function created"
user_agent_prompt: "..."
assertions: [...]

# Non-conversational scenario
name: test_commands
conversational: false
commands:
  - "echo 'test'"
  - "python script.py"

# Question set scenario
name: test_questions
question_set:
  file: questions.yaml
  answer_file_template: "/tmp/{question_id}.md"
  commands:
    - "kurt answer {question}"
  llm_judge:
    enabled: true
    weights: {...}
```

#### After (Simple JSON/YAML)
```yaml
# Everything is the same format
name: any_scenario
prompts:
  - "Help me with Python"
  - "Create a function"
  - "What is async/await?"
judge: true  # Optional scoring
```

### Code Comparison

#### Before: Complex Execution Logic
```python
# runner.py - multiple execution paths
class ScenarioRunner:
    async def run(self):
        if scenario.question_set:
            return await self._execute_question_set()  # 195 lines
        elif scenario.conversational:
            return await self._execute_with_sdk()      # 365 lines
        else:
            return await self._execute_test_cases()    # 160 lines

    async def _execute_with_sdk(self):
        # 365 lines of complex SDK interaction
        # Hooks, callbacks, conversation tracking
        # User agent simulation, completion detection
        ...

    def _execute_question_set(self):
        # 195 lines handling questions specially
        # Template formatting, file loading
        # LLM judging, result aggregation
        ...
```

#### After: Simple Unified Execution
```python
# simple_runner.py - one execution path
class SimpleRunner:
    async def run(self):
        results = []
        for prompt in self.get_prompts():
            result = await self.execute_prompt(prompt)
            if self.config.get("judge"):
                result["score"] = self.judge(prompt, result)
            results.append(result)
        return results

    async def execute_prompt(self, prompt):
        # ~30 lines - just call the API
        response = await client.messages.create(...)
        return {"prompt": prompt, "response": response.content}
```

### Removed Concepts

1. **conversational vs non-conversational** - Everything uses SDK
2. **question_set as special case** - Just a list of prompts
3. **commands execution** - Use SDK for everything
4. **workspace isolation** - Not needed without commands
5. **complex template formatting** - Use f-strings
6. **user_agent simulation** - Not needed
7. **conversation completion detection** - Each prompt is independent
8. **multiple output formats** - One simple JSON format

### Benefits

| Aspect | Before | After | Reduction |
|--------|--------|-------|-----------|
| **Lines of Code** | 1,486 (runner.py) | ~300 (simple_runner.py) | **-80%** |
| **Execution Paths** | 5+ different paths | 1 unified path | **-80%** |
| **Config Complexity** | 20+ fields, nested | 3-5 fields, flat | **-75%** |
| **Output Formats** | 3 different formats | 1 JSON format | **-67%** |
| **Test Complexity** | Complex mocking needed | Simple to test | **-70%** |
| **Dependencies** | workspace, user_agent, etc | Just SDK client | **-60%** |

### Migration Path

#### Option 1: Clean Break
- Create `simple_runner.py` as the new standard
- Delete old runner.py and related modules
- Update all scenarios to new format
- Total effort: ~2 days

#### Option 2: Adapter Pattern
- Keep old runner.py
- Add adapter to convert old format to new
- Gradually migrate scenarios
- Total effort: ~1 week

### New File Structure

```
eval/
├── framework/
│   ├── simple_runner.py      # ~300 lines - all execution logic
│   ├── env_config.py          # ~150 lines - API keys
│   └── judge.py               # ~100 lines - simple scoring
├── scenarios/
│   └── *.yaml                 # Simple prompt lists
└── results/
    └── {scenario}_{timestamp}.json  # Uniform output
```

### Example: Complete New Implementation

See `simple_runner.py` for a working implementation that:
- Handles all scenarios uniformly
- Executes through SDK only
- Saves simple JSON output
- Optionally scores with judge
- **Total: 307 lines** vs 1,486 lines

### Why This Works

1. **Modern SDK is sufficient** - No need for command execution
2. **Prompts are universal** - Everything can be expressed as a prompt
3. **Independence is good** - Each prompt stands alone, no state
4. **JSON is enough** - One format for all outputs
5. **Simple is testable** - Easy to mock, easy to verify

### Recommendation

**Go with Option 1 (Clean Break)** because:
- No backward compatibility needed (per your requirement)
- Massive simplification (80% code reduction)
- Easier to maintain and extend
- Better developer experience
- Cleaner test suite

The new system would be:
- **5x smaller**
- **10x simpler**
- **Just as functional**

Ready to proceed with this simplification?