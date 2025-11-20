"""Tests for inline DSPy signature definitions."""

import pytest

from kurt.workflows import (
    InlineSignature,
    WorkflowDefinition,
    WorkflowExecutor,
    WorkflowStep,
)


def test_inline_signature_schema():
    """Test inline signature schema validation."""
    sig_def = {
        "inputs": [
            {"name": "question", "type": "str", "description": "The question to answer"},
        ],
        "outputs": [
            {"name": "answer", "type": "str", "description": "The answer"},
        ],
        "prompt": "You are a helpful assistant. Answer the question.",
    }

    sig = InlineSignature(**sig_def)
    assert len(sig.inputs) == 1
    assert sig.inputs[0].name == "question"
    assert len(sig.outputs) == 1
    assert sig.outputs[0].name == "answer"
    assert "helpful assistant" in sig.prompt


def test_inline_signature_missing_fields():
    """Test validation fails when required fields are missing."""
    sig_def = {
        "inputs": [{"name": "question", "type": "str", "description": "Question"}],
        # Missing outputs and prompt
    }

    with pytest.raises(Exception):
        InlineSignature(**sig_def)


def test_workflow_step_with_inline_signature():
    """Test workflow step accepts inline signature as dict."""
    step = WorkflowStep(
        name="test_step",
        type="dspy",
        signature={
            "inputs": [{"name": "text", "type": "str", "description": "Input text"}],
            "outputs": [{"name": "result", "type": "str", "description": "Output"}],
            "prompt": "Process the text",
        },
        inputs={"text": "test"},
        output="result",
    )

    assert isinstance(step.signature, dict)
    assert "inputs" in step.signature
    assert "outputs" in step.signature
    assert "prompt" in step.signature


def test_workflow_step_with_string_signature():
    """Test workflow step accepts signature as string reference."""
    step = WorkflowStep(
        name="test_step",
        type="dspy",
        signature="AnalyzeQuestions",
        inputs={"questions": "[]"},
        output="result",
    )

    assert isinstance(step.signature, str)
    assert step.signature == "AnalyzeQuestions"


def test_create_dynamic_signature():
    """Test dynamic signature creation from inline definition."""
    workflow = WorkflowDefinition(
        name="test",
        steps=[
            WorkflowStep(
                name="test_step",
                type="dspy",
                signature={
                    "inputs": [{"name": "question", "type": "str", "description": "The question"}],
                    "outputs": [{"name": "answer", "type": "str", "description": "The answer"}],
                    "prompt": "Answer the question concisely.",
                },
                inputs={"question": "What is 2+2?"},
                output="result",
            )
        ],
    )

    executor = WorkflowExecutor(workflow)

    # Test dynamic signature creation
    sig_class = executor._create_dynamic_signature(workflow.steps[0].signature)

    # Check it's a valid DSPy signature class
    import dspy

    assert issubclass(sig_class, dspy.Signature)
    assert sig_class.__doc__ == "Answer the question concisely."

    # Check it has the correct fields
    # Note: DSPy stores fields differently, we just verify the class was created
    assert sig_class is not None


def test_parse_workflow_with_inline_signatures():
    """Test parsing a complete workflow with inline signatures."""
    from kurt.workflows import load_workflow

    workflow_yaml = """
name: "Test Workflow"
version: "1.0"

variables:
  input_text: "Hello world"

steps:
  - name: "process_text"
    type: "dspy"
    signature:
      inputs:
        - name: "text"
          type: "str"
          description: "Text to process"
      outputs:
        - name: "result"
          type: "str"
          description: "Processed text"
      prompt: |
        Process the input text and return a result.
    inputs:
      text: "${input_text}"
    output: "processed"
"""

    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(workflow_yaml)
        temp_path = Path(f.name)

    try:
        workflow = load_workflow(temp_path)

        assert workflow.name == "Test Workflow"
        assert len(workflow.steps) == 1

        step = workflow.steps[0]
        assert step.type.value == "dspy"
        assert isinstance(step.signature, dict)
        assert "inputs" in step.signature
        assert len(step.signature["inputs"]) == 1
        assert step.signature["inputs"][0]["name"] == "text"

    finally:
        temp_path.unlink()
