"""Workflow execution engine.

Executes workflow steps, handles variable substitution, and manages execution context.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import dspy
from rich.console import Console

from kurt.workflows.parser import substitute_variables
from kurt.workflows.schema import ErrorAction, StepType, WorkflowDefinition, WorkflowStep

logger = logging.getLogger(__name__)
console = Console()


class WorkflowExecutionError(Exception):
    """Error during workflow execution."""

    pass


class WorkflowContext:
    """
    Execution context for a workflow.

    Stores variables, step outputs, and execution state.
    """

    def __init__(
        self, workflow: WorkflowDefinition, initial_variables: Optional[Dict[str, Any]] = None
    ):
        self.workflow = workflow
        self.variables: Dict[str, Any] = {}

        # Initialize with workflow default variables
        if workflow.variables:
            self.variables.update(workflow.variables)

        # Override with user-provided variables
        if initial_variables:
            self.variables.update(initial_variables)

        # Track completed steps
        self.completed_steps: set[str] = set()
        self.step_outputs: Dict[str, Any] = {}

    def set_variable(self, name: str, value: Any):
        """Set a variable in the context."""
        self.variables[name] = value

    def get_variable(self, name: str) -> Any:
        """Get a variable from the context."""
        return self.variables.get(name)

    def set_step_output(self, step_name: str, output: Any):
        """Store the output of a step."""
        self.step_outputs[step_name] = output

    def get_step_output(self, step_name: str) -> Any:
        """Get the output of a completed step."""
        return self.step_outputs.get(step_name)

    def mark_step_completed(self, step_name: str):
        """Mark a step as completed."""
        self.completed_steps.add(step_name)

    def is_step_completed(self, step_name: str) -> bool:
        """Check if a step has been completed."""
        return step_name in self.completed_steps


class WorkflowExecutor:
    """
    Executes workflow definitions.

    Handles step execution, variable substitution, error handling, and output management.
    """

    def __init__(self, workflow: WorkflowDefinition, variables: Optional[Dict[str, Any]] = None):
        self.workflow = workflow
        self.context = WorkflowContext(workflow, variables)

    def execute(self) -> Dict[str, Any]:
        """
        Execute the workflow.

        Returns:
            Dictionary containing workflow results and outputs

        Raises:
            WorkflowExecutionError: If workflow execution fails
        """
        console.print(f"\n[bold cyan]Starting workflow:[/bold cyan] {self.workflow.name}")
        if self.workflow.description:
            console.print(f"[dim]{self.workflow.description}[/dim]\n")

        try:
            for step in self.workflow.steps:
                self._execute_step(step)

            console.print("\n[bold green]✓ Workflow completed successfully[/bold green]\n")

            return {
                "status": "success",
                "outputs": self.context.step_outputs,
                "variables": self.context.variables,
            }

        except WorkflowExecutionError as e:
            console.print(f"\n[bold red]✗ Workflow failed:[/bold red] {e}\n")
            return {
                "status": "error",
                "error": str(e),
                "outputs": self.context.step_outputs,
                "completed_steps": list(self.context.completed_steps),
            }

    def _execute_step(self, step: WorkflowStep, retry_count: int = 0):
        """
        Execute a single workflow step.

        Args:
            step: Step to execute
            retry_count: Current retry attempt (for error handling)

        Raises:
            WorkflowExecutionError: If step execution fails
        """
        # Check condition
        if step.condition:
            if not self._evaluate_condition(step.condition):
                console.print(f"[dim]⊘ Skipping step '{step.name}' (condition not met)[/dim]")
                return

        console.print(f"[cyan]▶ Executing step:[/cyan] {step.name}")
        if step.description:
            console.print(f"[dim]  {step.description}[/dim]")

        try:
            # Execute based on step type
            if step.type == StepType.CLI:
                result = self._execute_cli_step(step)
            elif step.type == StepType.DSPY:
                result = self._execute_dspy_step(step)
            elif step.type == StepType.SCRIPT:
                result = self._execute_script_step(step)
            elif step.type == StepType.PARALLEL:
                result = self._execute_parallel_step(step)
            else:
                raise WorkflowExecutionError(f"Unknown step type: {step.type}")

            # Store output if specified
            if step.output:
                self.context.set_variable(step.output, result)
                self.context.set_step_output(step.name, result)

            self.context.mark_step_completed(step.name)
            console.print(f"[green]✓ Completed:[/green] {step.name}\n")

        except Exception as e:
            # Handle error based on error handling configuration
            if step.on_error:
                if step.on_error.action == ErrorAction.RETRY:
                    if retry_count < step.on_error.max_retries:
                        console.print(
                            f"[yellow]⚠ Retry attempt {retry_count + 1}/{step.on_error.max_retries}[/yellow]"
                        )
                        self._execute_step(step, retry_count + 1)
                        return
                    else:
                        console.print(f"[red]✗ Max retries exceeded for step '{step.name}'[/red]")

                elif step.on_error.action == ErrorAction.SKIP:
                    console.print(f"[yellow]⚠ Skipping failed step '{step.name}': {e}[/yellow]\n")
                    return

                elif step.on_error.action == ErrorAction.FALLBACK:
                    console.print(
                        f"[yellow]⚠ Running fallback step '{step.on_error.fallback_step}'[/yellow]"
                    )
                    fallback = self.workflow.get_step(step.on_error.fallback_step)
                    if fallback:
                        self._execute_step(fallback)
                        return
                    else:
                        raise WorkflowExecutionError(
                            f"Fallback step '{step.on_error.fallback_step}' not found"
                        )

            # Default: fail the workflow
            raise WorkflowExecutionError(f"Step '{step.name}' failed: {e}")

    def _execute_cli_step(self, step: WorkflowStep) -> Any:
        """Execute a CLI command step."""
        # Substitute variables in command and args
        command = substitute_variables(step.command, self.context.variables)
        args = substitute_variables(step.args or {}, self.context.variables)

        # Build full command
        full_command = ["kurt"] + command.split()

        # Add arguments
        for key, value in args.items():
            arg_name = f"--{key.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    full_command.append(arg_name)
            elif isinstance(value, list):
                for item in value:
                    full_command.extend([arg_name, str(item)])
            else:
                full_command.extend([arg_name, str(value)])

        console.print(f"[dim]  $ {' '.join(full_command)}[/dim]")

        # Execute command
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=True,
            )
            console.print(result.stdout)
            return {"stdout": result.stdout, "stderr": result.stderr, "returncode": 0}
        except subprocess.CalledProcessError as e:
            console.print(f"[red]{e.stderr}[/red]")
            raise WorkflowExecutionError(
                f"Command failed with exit code {e.returncode}: {e.stderr}"
            )

    def _execute_dspy_step(self, step: WorkflowStep) -> Any:
        """Execute a DSPy signature step."""
        # Substitute variables in inputs
        inputs = substitute_variables(step.inputs or {}, self.context.variables)

        # Load or create signature class
        try:
            if isinstance(step.signature, dict):
                # Inline signature definition
                signature_class = self._create_dynamic_signature(step.signature)
                console.print("[dim]  Using inline DSPy signature[/dim]")
            else:
                # Reference to existing signature class
                signature_class = self._load_dspy_signature(step.signature)
                console.print(f"[dim]  Using DSPy signature: {step.signature}[/dim]")
        except Exception as e:
            raise WorkflowExecutionError(f"Failed to load DSPy signature: {e}")

        # Create predictor
        predictor = dspy.Predict(signature_class)

        # Execute
        try:
            result = predictor(**inputs)

            # Convert result to dict
            if hasattr(result, "model_dump"):
                output = result.model_dump()
            elif hasattr(result, "dict"):
                output = result.dict()
            else:
                output = dict(result)

            return output

        except Exception as e:
            raise WorkflowExecutionError(f"DSPy signature execution failed: {e}")

    def _execute_script_step(self, step: WorkflowStep) -> Any:
        """Execute a Python script step."""
        # Substitute variables in code
        code = substitute_variables(step.code, self.context.variables)

        console.print("[dim]  Executing Python script[/dim]")

        # Create execution namespace with access to context variables
        namespace = {
            "__builtins__": __builtins__,
            "variables": self.context.variables,
            "step_outputs": self.context.step_outputs,
            # Common imports
            "json": __import__("json"),
            "Path": Path,
        }

        # Execute code
        try:
            exec(code, namespace)

            # Return any 'result' variable set by the script
            return namespace.get("result")

        except Exception as e:
            raise WorkflowExecutionError(f"Script execution failed: {e}")

    def _execute_parallel_step(self, step: WorkflowStep) -> Any:
        """Execute parallel sub-steps."""
        console.print(f"[dim]  Running {len(step.steps)} steps in parallel[/dim]")

        # For now, execute sequentially (true parallelism requires threading/multiprocessing)
        results = []
        for sub_step in step.steps:
            self._execute_step(sub_step)
            if sub_step.output:
                results.append(self.context.get_variable(sub_step.output))

        return results

    def _evaluate_condition(self, condition: str) -> bool:
        """
        Evaluate a condition expression.

        Args:
            condition: Python expression to evaluate

        Returns:
            Boolean result of condition
        """
        # Substitute variables
        condition_expr = substitute_variables(condition, self.context.variables)

        # Create safe evaluation namespace
        namespace = {
            "variables": self.context.variables,
            "step_outputs": self.context.step_outputs,
            "len": len,
        }

        try:
            result = eval(condition_expr, {"__builtins__": {}}, namespace)
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False

    def _create_dynamic_signature(self, signature_def: Dict[str, Any]) -> type[dspy.Signature]:
        """
        Create a DSPy signature class dynamically from inline definition.

        Args:
            signature_def: Dictionary containing inputs, outputs, and prompt

        Returns:
            Dynamically created DSPy Signature class
        """
        from kurt.workflows.schema import InlineSignature

        # Validate signature definition
        try:
            inline_sig = InlineSignature(**signature_def)
        except Exception as e:
            raise ValueError(f"Invalid inline signature definition: {e}")

        # Build class attributes
        class_attrs = {}

        # Add docstring from prompt
        class_attrs["__doc__"] = inline_sig.prompt

        # Add input fields
        for field in inline_sig.inputs:
            class_attrs[field.name] = dspy.InputField(desc=field.description)

        # Add output fields
        for field in inline_sig.outputs:
            class_attrs[field.name] = dspy.OutputField(desc=field.description)

        # Create dynamic class inheriting from dspy.Signature
        signature_class = type("DynamicSignature", (dspy.Signature,), class_attrs)

        return signature_class

    def _load_dspy_signature(self, signature_name: str) -> type[dspy.Signature]:
        """
        Load a DSPy signature class by name.

        Args:
            signature_name: Name of signature class (e.g., 'AnalyzeQuestions')

        Returns:
            DSPy Signature class
        """
        # Try to import from kurt.workflows.signatures
        try:
            from kurt.workflows import signatures

            signature_class = getattr(signatures, signature_name)
            if not issubclass(signature_class, dspy.Signature):
                raise ValueError(f"{signature_name} is not a DSPy Signature")
            return signature_class
        except AttributeError:
            raise ValueError(f"Signature '{signature_name}' not found in kurt.workflows.signatures")


__all__ = [
    "WorkflowExecutionError",
    "WorkflowContext",
    "WorkflowExecutor",
]
