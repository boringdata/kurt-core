# Workflow Templates

This directory contains example YAML workflow templates demonstrating Kurt's workflow capabilities.

## Directory Structure

```
templates/
├── aeo/              # Answer Engine Optimization workflows
├── content/          # Content generation and optimization
└── examples/         # Feature demonstration examples
```

## Templates by Category

### AEO (Answer Engine Optimization)

- **[aeo/aeo_faq_schema.yaml](aeo/aeo_faq_schema.yaml)** - Generate FAQ content with JSON-LD schema markup
  - Mines questions from community sources (Reddit)
  - Clusters questions by topic
  - Generates comprehensive FAQ answers
  - Creates structured schema markup for AI search engines

- **[aeo/aeo_inline_dspy.yaml](aeo/aeo_inline_dspy.yaml)** - AEO workflow with inline DSPy signatures
  - Demonstrates inline signature definitions
  - Shows DSPy integration patterns
  - Advanced prompt engineering

### Content Generation & Optimization

- **[content/linkedin_simple.yaml](content/linkedin_simple.yaml)** - Simple LinkedIn post generation
  - Quick single-step content generation
  - Good starting point for custom workflows

- **[content/linkedin_content_workflow.yaml](content/linkedin_content_workflow.yaml)** - Multi-step LinkedIn content
  - Complex workflow with research, drafting, and optimization
  - Demonstrates multi-step orchestration
  - Shows context management between steps

- **[content/citation_optimization.yaml](content/citation_optimization.yaml)** - Improve content citations
  - Enhances existing content with better source attribution
  - Uses Kurt's knowledge graph for context

- **[content/content_analysis.yaml](content/content_analysis.yaml)** - Analyze content quality
  - Evaluates content structure and effectiveness
  - Provides actionable improvement suggestions

### Examples & Feature Demos

- **[examples/aeo_foreach_example.yaml](examples/aeo_foreach_example.yaml)** - Parallel batch processing
  - Demonstrates `foreach` step type
  - Shows DBOS queue-based parallel execution
  - Batch processing patterns

## Usage

### List Available Templates

```bash
kurt workflows list
```

### Run a Template

```bash
kurt workflows run workflows/templates/content/linkedin_simple.yaml
```

### Validate Template Syntax

```bash
kurt workflows validate workflows/templates/aeo/aeo_faq_schema.yaml
```

### Use as Starting Point

Copy a template and customize it:

```bash
cp workflows/templates/content/linkedin_simple.yaml my_workflow.yaml
# Edit my_workflow.yaml with your variables and steps
kurt workflows run my_workflow.yaml
```

## Template Features

All templates demonstrate:

- **Variables**: Define reusable parameters
- **Steps**: Chain operations with dependencies
- **Outputs**: Pass data between steps
- **Conditions**: Conditional execution
- **Error Handling**: Graceful failure management
- **DBOS Integration**: Durable, resumable workflows

## See Also

- [Workflow Architecture](../ARCHITECTURE.md)
- [Foreach Documentation](../FOREACH.md)
- [Inline Signatures Guide](../INLINE_SIGNATURES.md)
- [Main Workflow README](../README.md)
