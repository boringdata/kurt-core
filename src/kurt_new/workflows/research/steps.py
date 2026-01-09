"""Research workflow steps."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dbos import DBOS

from kurt_new.db import ensure_tables, managed_session
from kurt_new.integrations.research import ResearchResult
from kurt_new.integrations.research.config import get_source_config
from kurt_new.integrations.research.perplexity import PerplexityAdapter

from .config import ResearchConfig
from .models import ResearchDocument, ResearchStatus


def serialize_result(result: ResearchResult) -> dict[str, Any]:
    """Serialize ResearchResult for DBOS step return."""
    data = result.to_dict()
    # Ensure datetime is ISO string
    if isinstance(data.get("timestamp"), datetime):
        data["timestamp"] = data["timestamp"].isoformat()
    return data


@DBOS.step(name="research_search")
def research_search_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Execute research query via Perplexity (pure, no persistence).

    Args:
        config_dict: ResearchConfig as dict

    Returns:
        Dict with result data including query, answer, citations
    """
    config = ResearchConfig.model_validate(config_dict)

    # Get adapter config
    source_config = get_source_config(config.source)

    # Create adapter
    if config.source == "perplexity":
        adapter = PerplexityAdapter(source_config)
    else:
        raise ValueError(f"Unknown research source: {config.source}")

    # Execute search
    result = adapter.search(
        query=config.query,
        recency=config.recency,
        model=config.model,
    )

    # Stream progress
    DBOS.set_event("stage_total", 1)
    DBOS.set_event("stage_current", 1)
    DBOS.write_stream(
        "progress",
        {
            "step": "research_search",
            "query": config.query,
            "citations_count": len(result.citations),
            "response_time": result.response_time_seconds,
            "timestamp": time.time(),
        },
    )

    return {
        "result": serialize_result(result),
        "dry_run": config.dry_run,
        "save": config.save,
    }


@DBOS.transaction()
def persist_research_result(
    result_dict: dict[str, Any],
    save_to_file: bool = False,
    output_dir: str = "sources/research",
) -> dict[str, Any]:
    """
    Persist research result to database and optionally filesystem.

    Args:
        result_dict: Serialized ResearchResult
        save_to_file: Whether to save markdown to sources/research/

    Returns:
        Dict with persistence info
    """
    with managed_session() as session:
        ensure_tables([ResearchDocument], session=session)

        # Create ResearchDocument
        doc = ResearchDocument(
            id=result_dict["id"],
            query=result_dict["query"],
            answer=result_dict["answer"],
            source=result_dict["source"],
            model=result_dict.get("model"),
            citations_json=result_dict.get("citations", []),
            response_time_seconds=result_dict.get("response_time_seconds"),
            status=ResearchStatus.SUCCESS.value,
        )

        # Save to file if requested
        content_path = None
        if save_to_file:
            # Reconstruct markdown
            timestamp_str = result_dict.get("timestamp", datetime.utcnow().isoformat())
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = timestamp_str

            # Build markdown content
            markdown = _build_research_markdown(result_dict, timestamp)

            # Save to configured output directory
            date_str = timestamp.strftime("%Y%m%d")
            filename = f"{date_str}-{result_dict['id']}.md"
            research_dir = Path(output_dir)
            research_dir.mkdir(parents=True, exist_ok=True)

            content_path = str(research_dir / filename)
            with open(content_path, "w") as f:
                f.write(markdown)

            doc.content_path = content_path

        # Check for existing
        existing = session.get(ResearchDocument, result_dict["id"])
        if existing:
            # Update existing
            existing.answer = doc.answer
            existing.citations_json = doc.citations_json
            existing.response_time_seconds = doc.response_time_seconds
            existing.content_path = doc.content_path
            return {"document_id": doc.id, "updated": True, "content_path": content_path}
        else:
            session.add(doc)
            return {"document_id": doc.id, "created": True, "content_path": content_path}


def _build_research_markdown(result_dict: dict[str, Any], timestamp: datetime) -> str:
    """Build markdown content from result dict."""
    lines = [
        "---",
        f"research_id: {result_dict['id']}",
        f'research_query: "{result_dict["query"]}"',
        f"research_source: {result_dict['source']}",
    ]

    if result_dict.get("model"):
        lines.append(f"research_model: {result_dict['model']}")

    lines.append(f"research_date: {timestamp.isoformat()}")

    if result_dict.get("response_time_seconds"):
        lines.append(f"response_time_seconds: {result_dict['response_time_seconds']:.1f}")

    citations = result_dict.get("citations", [])
    lines.append(f"sources_count: {len(citations)}")

    if citations:
        lines.append("citations:")
        for citation in citations:
            lines.append(f'  - title: "{citation.get("title", "")}"')
            lines.append(f"    url: {citation.get('url', '')}")

    lines.append("---")
    lines.append("")
    lines.append(f"# {result_dict['query']}")
    lines.append("")
    lines.append(result_dict["answer"])
    lines.append("")
    lines.append("## Sources")
    lines.append("")

    for i, citation in enumerate(citations, 1):
        lines.append(f"[{i}] {citation.get('title', 'Source')} - {citation.get('url', '')}")

    return "\n".join(lines)
