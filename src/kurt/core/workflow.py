"""
Generic DBOS workflow runner for dbt-like pipelines.

Any pipeline can use this - just define a PipelineConfig and call run_workflow().

For CLI integration, use run_pipeline_workflow() which accepts:
- Namespace string (e.g., "indexing") - auto-discovers models
- Model name (e.g., "indexing.document_sections") - runs single model
- Python file/folder path - imports and discovers models
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dbos import DBOS

from kurt.utils.filtering import DocumentFilters

from .dbos_events import emit_batch_status
from .model_runner import ModelContext, run_pipeline
from .pipeline import PipelineConfig, get_pipeline
from .registry import ModelRegistry

logger = logging.getLogger(__name__)


@DBOS.workflow()
async def run_workflow(
    pipeline: PipelineConfig,
    filters: DocumentFilters,
    incremental_mode: str = "full",
    reprocess_unchanged: bool = False,
    workflow_id: Optional[str] = None,
    model_configs: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generic DBOS workflow for any dbt-like pipeline.

    dbt-like execution:
    1. Store workflow context (filters, mode)
    2. Run pipeline models in sequence (each reads from upstream tables)
    3. Emit status events for monitoring

    Args:
        pipeline: PipelineConfig defining which models to run
        filters: Document filters to apply
        incremental_mode: Processing mode ("full" or "delta")
        reprocess_unchanged: If True, reprocess docs even if content unchanged.
                            Default False means unchanged docs are skipped.
        workflow_id: Optional workflow ID (defaults to DBOS.workflow_id)
        metadata: Optional dict with additional context (e.g., {"verbose": True})

    Returns:
        Dict containing model results and workflow metadata

    Example:
        from kurt.core import run_workflow, PipelineConfig

        MY_PIPELINE = PipelineConfig(
            name="my_pipeline",
            models=["my.first_model", "my.second_model"],
        )

        result = await run_workflow(
            pipeline=MY_PIPELINE,
            filters=DocumentFilters(ids="doc1,doc2"),
            incremental_mode="full",
            reprocess_unchanged=True,  # Force reprocess all docs
        )
    """
    workflow_id = workflow_id or DBOS.workflow_id

    logger.info(
        "Workflow '%s' started (mode=%s, reprocess_unchanged=%s, workflow_id=%s)",
        pipeline.name,
        incremental_mode,
        reprocess_unchanged,
        workflow_id,
    )

    await emit_batch_status(
        {
            "batch_status": "processing",
            "workflow_id": workflow_id,
            "pipeline": pipeline.name,
        }
    )

    # Run pipeline - models read from tables via sources={}
    # Merge model_configs into metadata (metadata takes precedence for verbose, etc.)
    combined_metadata = {"model_configs": model_configs or {}}
    if metadata:
        combined_metadata.update(metadata)
    ctx = ModelContext(
        filters=filters,
        incremental_mode=incremental_mode,
        reprocess_unchanged=reprocess_unchanged,
        workflow_id=workflow_id,
        metadata=combined_metadata,
    )
    pipeline_result = await run_pipeline(pipeline, ctx)

    # Get document stats from first model result (if available)
    # First model (document_sections) returns: documents, sections, skipped
    first_model = pipeline.models[0] if pipeline.models else None
    first_result = pipeline_result["results"].get(first_model, {}) if first_model else {}
    processed_docs = first_result.get("documents", 0)
    skipped_docs = first_result.get("skipped", 0)
    total_docs = processed_docs + skipped_docs

    await emit_batch_status(
        {
            "batch_total": total_docs,
            "batch_status": "complete",
            "active_docs": processed_docs,
            "skipped_docs": skipped_docs,
            "workflow_done": True,
            "pipeline": pipeline.name,
        }
    )

    return {
        "workflow_id": workflow_id,
        "pipeline": pipeline.name,
        "total_documents": total_docs,
        "documents_processed": processed_docs,
        "skipped_docs": skipped_docs,
        "models_executed": pipeline_result["models_executed"],
        "errors": pipeline_result["errors"],
        **pipeline_result["results"],
    }


def _import_models_from_path(path: Path) -> str:
    """Import models from a Python file or directory.

    Args:
        path: Path to .py file or directory containing model files

    Returns:
        Namespace detected from imported models

    Raises:
        ValueError: If path doesn't exist or no models found
    """
    if not path.exists():
        raise ValueError(f"Path does not exist: {path}")

    # Track models before/after import to detect new ones
    models_before = set(ModelRegistry.list_all())

    if path.is_file() and path.suffix == ".py":
        # Import single file
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[path.stem] = module
            spec.loader.exec_module(module)
            logger.info(f"Imported models from {path}")
    elif path.is_dir():
        # Import all .py files in directory (excluding tests, __pycache__)
        for py_file in path.glob("*.py"):
            if py_file.name.startswith("_") or "test" in py_file.name.lower():
                continue
            spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[py_file.stem] = module
                try:
                    spec.loader.exec_module(module)
                    logger.debug(f"Imported {py_file}")
                except Exception as e:
                    logger.warning(f"Failed to import {py_file}: {e}")
        logger.info(f"Imported models from directory {path}")
    else:
        raise ValueError(f"Path must be a .py file or directory: {path}")

    # Detect namespace from new models
    models_after = set(ModelRegistry.list_all())
    new_models = models_after - models_before

    if not new_models:
        raise ValueError(f"No models found in {path}")

    # Extract namespace from first model name (e.g., "indexing.document_sections" -> "indexing")
    namespaces = set()
    for model_name in new_models:
        if "." in model_name:
            namespaces.add(model_name.split(".")[0])

    if len(namespaces) == 1:
        return namespaces.pop()
    elif len(namespaces) > 1:
        logger.warning(f"Multiple namespaces found: {namespaces}, using first")
        return sorted(namespaces)[0]
    else:
        # No namespace prefix, use path stem
        return path.stem


def resolve_pipeline(target: str) -> PipelineConfig:
    """Resolve a target string to a PipelineConfig.

    Accepts:
    - Namespace (e.g., "indexing") - discovers all models with that prefix
    - Model name (e.g., "indexing.document_sections") - runs single model
    - File path (e.g., "./models/step_extract.py") - imports and discovers
    - Directory path (e.g., "./models/") - imports all and discovers

    Args:
        target: Namespace, model name, or path

    Returns:
        PipelineConfig ready for execution
    """
    # Check if it's a file/directory path
    path = Path(target)
    if path.exists() or target.endswith(".py") or "/" in target or "\\" in target:
        if not path.exists():
            raise ValueError(f"Path does not exist: {target}")
        namespace = _import_models_from_path(path)
        return get_pipeline(namespace)

    # Check if it's a specific model name
    if ModelRegistry.get(target):
        logger.info(f"Running single model: {target}")
        return PipelineConfig(name=target, models=[target])

    # Try importing known model packages for the namespace
    namespace = target
    try:
        # Import models from kurt.models package (new location)
        # Map namespace aliases to model packages
        namespace_to_package = {
            "landing": "kurt.models.landing",
            "staging": "kurt.models.staging",
            "indexing": "kurt.models.staging",  # Alias: indexing -> staging
        }

        if namespace in namespace_to_package:
            try:
                importlib.import_module(namespace_to_package[namespace])
                logger.debug(f"Imported {namespace_to_package[namespace]}")
            except ImportError as e:
                logger.debug(f"Could not import {namespace_to_package[namespace]}: {e}")
    except Exception as e:
        logger.debug(f"Could not auto-import models for namespace {namespace}: {e}")

    # Discover pipeline from namespace
    pipeline = get_pipeline(namespace)
    if not pipeline.models:
        raise ValueError(
            f"No models found for '{target}'. "
            f"Provide a namespace (e.g., 'indexing'), model name (e.g., 'indexing.document_sections'), "
            f"or path to model files."
        )

    return pipeline


@DBOS.workflow()
async def run_pipeline_workflow(
    target: str,
    filters: DocumentFilters,
    incremental_mode: str = "full",
    reprocess_unchanged: bool = False,
    workflow_id: Optional[str] = None,
    model_configs: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generic workflow that resolves target and runs pipeline.

    This is the main entry point for CLI integration. It accepts flexible
    target specifications and auto-discovers models.

    Args:
        target: One of:
            - Namespace (e.g., "indexing") - discovers all models
            - Model name (e.g., "indexing.document_sections") - single model
            - File path (e.g., "./my_models.py") - imports and runs
            - Directory path (e.g., "./models/") - imports all and runs
        filters: Document filters to apply
        incremental_mode: Processing mode ("full" or "delta")
        reprocess_unchanged: If True, reprocess unchanged documents
        workflow_id: Optional workflow ID
        metadata: Optional dict with additional context (e.g., {"verbose": True})

    Returns:
        Dict with workflow results

    Example CLI usage:
        # Run all indexing models
        kurt index --pipeline indexing

        # Run single model
        kurt index --pipeline indexing.document_sections

        # Run models from custom path
        kurt index --pipeline ./my_pipeline/models/
    """
    pipeline = resolve_pipeline(target)
    return await run_workflow(
        pipeline=pipeline,
        filters=filters,
        incremental_mode=incremental_mode,
        reprocess_unchanged=reprocess_unchanged,
        workflow_id=workflow_id,
        model_configs=model_configs,
        metadata=metadata,
    )
