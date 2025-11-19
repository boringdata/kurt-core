# Kurt Workflows

Define multi-step content workflows in YAML that combine CLI commands with DSPy-powered AI operations.

## Overview

Workflows enable you to automate complex content operations like:
- AEO (AI Engine Optimization) campaigns
- Content clustering and classification
- FAQ generation with schema markup
- Multi-source content aggregation and analysis

## Workflow Structure

A workflow YAML file defines:
1. **Steps**: Sequential operations to execute
2. **Step Types**:
   - `cli`: Execute a Kurt CLI command
   - `dspy`: Run a DSPy signature for AI-powered processing
   - `script`: Run custom Python code
3. **Variables**: Pass data between steps
4. **Conditions**: Control flow based on results

## Example Workflows

### AEO FAQ Schema Workflow

Generate FAQ pages with JSON-LD schema from community questions:

```yaml
# workflows/aeo_faq_schema.yaml
name: "AEO FAQ Schema Generator"
description: "Mine questions, generate FAQ content, and deploy with schema markup"
version: "1.0"

variables:
  target_domain: "example.com"
  num_questions: 50
  output_path: "content/faqs"

steps:
  - name: "fetch_reddit_questions"
    type: "cli"
    command: "kurt integrations research reddit"
    args:
      subreddit: "${target_domain}"
      limit: "${num_questions}"
      filter: "questions"
    output: "reddit_questions"

  - name: "analyze_questions"
    type: "dspy"
    signature: "AnalyzeQuestions"
    inputs:
      questions: "${reddit_questions}"
    output: "question_clusters"

  - name: "generate_faq_content"
    type: "dspy"
    signature: "GenerateFAQContent"
    inputs:
      clusters: "${question_clusters}"
      domain: "${target_domain}"
    output: "faq_pages"

  - name: "generate_schema_markup"
    type: "dspy"
    signature: "GenerateJSONLD"
    inputs:
      faq_pages: "${faq_pages}"
      schema_type: "FAQPage"
    output: "schema_markup"

  - name: "save_content"
    type: "script"
    code: |
      import json
      from pathlib import Path

      output_dir = Path("${output_path}")
      output_dir.mkdir(parents=True, exist_ok=True)

      for page in faq_pages:
          file_path = output_dir / f"{page['slug']}.md"
          with open(file_path, 'w') as f:
              f.write(page['content'])

          schema_path = output_dir / f"{page['slug']}.schema.json"
          with open(schema_path, 'w') as f:
              json.dump(page['schema'], f, indent=2)

  - name: "validate_schema"
    type: "cli"
    command: "kurt content validate-schema"
    args:
      path: "${output_path}"
```

### Content Clustering Workflow

```yaml
# workflows/cluster_content.yaml
name: "Content Clustering"
description: "Analyze and cluster content by topic"
version: "1.0"

variables:
  source_url: ""
  max_depth: 2

steps:
  - name: "fetch_content"
    type: "cli"
    command: "kurt content fetch"
    args:
      url: "${source_url}"
      max_docs: 100
      discover: true
    output: "fetched_docs"

  - name: "cluster_topics"
    type: "cli"
    command: "kurt content cluster"
    args:
      source_url: "${source_url}"
    output: "clusters"

  - name: "analyze_clusters"
    type: "dspy"
    signature: "AnalyzeClusterQuality"
    inputs:
      clusters: "${clusters}"
    output: "cluster_analysis"

  - name: "generate_report"
    type: "dspy"
    signature: "GenerateClusterReport"
    inputs:
      clusters: "${clusters}"
      analysis: "${cluster_analysis}"
    output: "report"
```

## Running Workflows

```bash
# Run a workflow
kurt workflows run workflows/aeo_faq_schema.yaml

# Run with custom variables
kurt workflows run workflows/aeo_faq_schema.yaml --var target_domain=mysite.com --var num_questions=100

# Run in background (DBOS)
kurt workflows run workflows/aeo_faq_schema.yaml --background

# List available workflow templates
kurt workflows list-templates

# Validate a workflow file
kurt workflows validate workflows/my_workflow.yaml
```

## Directory Structure

```
workflows/
├── README.md                    # This file
├── templates/                   # Built-in workflow templates
│   ├── aeo_faq_schema.yaml
│   ├── cluster_content.yaml
│   └── citation_tracking.yaml
└── custom/                      # Your custom workflows
    └── my_workflow.yaml
```

## DSPy Signatures

Custom DSPy signatures can be defined in `src/kurt/workflows/signatures/`:

```python
# src/kurt/workflows/signatures/aeo.py
import dspy
from pydantic import BaseModel, Field

class Question(BaseModel):
    question: str
    context: str
    frequency: int

class QuestionCluster(BaseModel):
    topic: str
    questions: list[Question]

class AnalyzeQuestions(dspy.Signature):
    """Cluster related questions by topic."""
    questions: list[Question] = dspy.InputField()
    clusters: list[QuestionCluster] = dspy.OutputField()

class FAQPage(BaseModel):
    slug: str
    title: str
    content: str
    questions: list[Question]

class GenerateFAQContent(dspy.Signature):
    """Generate FAQ page content from question clusters."""
    clusters: list[QuestionCluster] = dspy.InputField()
    domain: str = dspy.InputField()
    pages: list[FAQPage] = dspy.OutputField()

class GenerateJSONLD(dspy.Signature):
    """Generate JSON-LD schema markup for FAQ pages."""
    faq_pages: list[FAQPage] = dspy.InputField()
    schema_type: str = dspy.InputField()
    schema_markup: dict = dspy.OutputField()
```

## Advanced Features

### Conditional Execution

```yaml
steps:
  - name: "check_content_exists"
    type: "cli"
    command: "kurt content list"
    args:
      url_prefix: "${source_url}"
    output: "existing_content"

  - name: "fetch_new_content"
    type: "cli"
    command: "kurt content fetch"
    condition: "len(existing_content) == 0"
    args:
      url: "${source_url}"
```

### Parallel Execution

```yaml
steps:
  - name: "parallel_fetch"
    type: "parallel"
    steps:
      - name: "fetch_blog"
        type: "cli"
        command: "kurt content fetch"
        args:
          url: "${blog_url}"

      - name: "fetch_docs"
        type: "cli"
        command: "kurt content fetch"
        args:
          url: "${docs_url}"
```

### Error Handling

```yaml
steps:
  - name: "fetch_content"
    type: "cli"
    command: "kurt content fetch"
    args:
      url: "${source_url}"
    on_error:
      action: "retry"
      max_retries: 3
      fallback_step: "use_cached_content"
```
