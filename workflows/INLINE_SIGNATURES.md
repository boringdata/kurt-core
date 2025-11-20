# Inline DSPy Signatures

## Overview

Kurt workflows support defining DSPy signatures **inline** in YAML files, eliminating the need to create separate Python files for signatures. This makes workflows more self-contained and easier to share.

## Syntax

```yaml
steps:
  - name: "step_name"
    type: "dspy"
    signature:
      inputs:
        - name: "input_field_name"
          type: "str"  # str, int, float, bool, list, dict
          description: "Description for the LLM"
      outputs:
        - name: "output_field_name"
          type: "str"
          description: "Description of expected output"
      prompt: |
        System prompt/instructions for the LLM.
        This guides the model on how to process inputs and generate outputs.
    inputs:
      input_field_name: "${variable_or_value}"
    output: "result_variable"
```

## Field Definitions

### Input/Output Fields

Each field requires:
- **name**: The field name (used when calling the signature)
- **type**: Data type (`str`, `int`, `float`, `bool`, `list`, `dict`)
- **description**: Human-readable description that guides the LLM

### Prompt

The `prompt` field contains instructions for the LLM. This is equivalent to the docstring in a Python DSPy signature class.

## Examples

### Simple Q&A

```yaml
name: "Question Answering"
steps:
  - name: "answer_question"
    type: "dspy"
    signature:
      inputs:
        - name: "question"
          type: "str"
          description: "The question to answer"
        - name: "context"
          type: "str"
          description: "Context information"
      outputs:
        - name: "answer"
          type: "str"
          description: "Concise answer to the question"
      prompt: |
        You are a helpful assistant that answers questions using provided context.
        Provide accurate, concise answers based on the context.
    inputs:
      question: "${user_question}"
      context: "${retrieved_context}"
    output: "answer"
```

### Multi-Field Analysis

```yaml
name: "Content Analysis"
steps:
  - name: "analyze_content"
    type: "dspy"
    signature:
      inputs:
        - name: "text"
          type: "str"
          description: "Text to analyze"
        - name: "domain"
          type: "str"
          description: "Domain/industry context"
      outputs:
        - name: "topics"
          type: "str"
          description: "Key topics (JSON array)"
        - name: "sentiment"
          type: "str"
          description: "Overall sentiment (positive/negative/neutral)"
        - name: "entities"
          type: "str"
          description: "Named entities (JSON array)"
      prompt: |
        Analyze the provided text and extract:
        1. Main topics and themes
        2. Overall sentiment
        3. Named entities (people, organizations, locations)

        Return structured JSON for topics and entities.
    inputs:
      text: "${article_text}"
      domain: "${industry}"
    output: "analysis"
```

## Comparison: Inline vs. Python Files

### Before (Python File Required)

**File: `src/kurt/workflows/signatures/aeo.py`**
```python
import dspy

class AnalyzeQuestions(dspy.Signature):
    """Cluster related questions by topic"""
    questions: str = dspy.InputField(desc="List of questions (JSON format)")
    domain: str = dspy.InputField(desc="Domain/industry context")
    clusters: str = dspy.OutputField(desc="Question clusters (JSON format)")
```

**File: `workflows/workflow.yaml`**
```yaml
steps:
  - name: "cluster_questions"
    type: "dspy"
    signature: "AnalyzeQuestions"  # Reference to Python class
    inputs:
      questions: "${reddit_questions}"
      domain: "${target_domain}"
    output: "question_clusters"
```

### After (Inline Definition)

**File: `workflows/workflow.yaml`** (Self-contained)
```yaml
steps:
  - name: "cluster_questions"
    type: "dspy"
    signature:
      inputs:
        - name: "questions"
          type: "str"
          description: "List of questions (JSON format)"
        - name: "domain"
          type: "str"
          description: "Domain/industry context"
      outputs:
        - name: "clusters"
          type: "str"
          description: "Question clusters grouped by topic"
      prompt: |
        Cluster related questions by topic.
        Identify common themes and group similar questions together.
    inputs:
      questions: "${reddit_questions}"
      domain: "${target_domain}"
    output: "question_clusters"
```

## Benefits

1. **Self-Contained**: Workflows are fully defined in a single YAML file
2. **Shareable**: No need to distribute Python signature files
3. **Readable**: Everything needed to understand the workflow is in one place
4. **Flexible**: Easy to experiment with different prompts and field definitions
5. **Version Controlled**: Changes to signatures are tracked with the workflow

## Mixed Usage

You can use **both** inline signatures and Python class references in the same workflow:

```yaml
steps:
  # Inline signature
  - name: "preprocess"
    type: "dspy"
    signature:
      inputs: [...]
      outputs: [...]
      prompt: "..."

  # Reference to Python class (for complex/reusable signatures)
  - name: "advanced_processing"
    type: "dspy"
    signature: "ComplexSignatureClass"
```

## Implementation Details

Inline signatures are dynamically converted to DSPy Signature classes at runtime:

1. YAML is parsed and validated using Pydantic models
2. Executor detects `signature` is a dict (not a string reference)
3. Dynamic class is created: `type("DynamicSignature", (dspy.Signature,), attrs)`
4. Input/output fields are added as `dspy.InputField()` and `dspy.OutputField()`
5. Prompt becomes the class docstring
6. Signature is executed like any other DSPy signature

This approach provides the same functionality as Python-defined signatures while keeping workflows self-contained.
