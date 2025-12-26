"""Context formatting utilities for retrieval."""

from kurt.utils.retrieval.context_loading import TopicContextData


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 chars per token).

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    return len(text) // 4


def format_agent_context(query: str, data: TopicContextData) -> str:
    """Format context data as markdown for agent system prompt.

    Claims-centric format: each entity with claims shows its relationships
    and claims together, giving a complete picture.

    Args:
        query: Original user query
        data: Context data

    Returns:
        Markdown-formatted context string
    """
    # Build entity info lookup: name -> {type, matched}
    entity_info: dict[str, dict] = {}
    for e in data.entities:
        entity_info[e["name"]] = {"type": e["type"], "matched": e.get("matched", False)}

    # Build relationships by source entity: source -> list of (type, target)
    rels_by_source: dict[str, list[tuple[str, str]]] = {}
    for r in data.relationships:
        # Skip self-referential relationships
        if r["source"] == r["target"]:
            continue
        source = r["source"]
        if source not in rels_by_source:
            rels_by_source[source] = []
        rels_by_source[source].append((r["type"], r["target"]))

    # Group claims by entity
    claims_by_entity: dict[str, list] = {}
    for claim in data.claims:
        entity = claim["entity"]
        if entity not in claims_by_entity:
            claims_by_entity[entity] = []
        claims_by_entity[entity].append(claim)

    # Header
    topics_str = ", ".join(data.topics) if data.topics else "None"
    lines = [
        f"# Context: {query}",
        f"Topic: {topics_str} | {len(data.sources)} source(s), {len(data.claims)} claims",
        "",
    ]

    # Knowledge section - entities with their relationships and claims together
    if claims_by_entity:
        lines.append("## Knowledge")
        lines.append("")

        # Sort: matched entities first, then by query relevance (name appears in query)
        query_lower = query.lower()

        def entity_sort_key(e: str) -> tuple:
            is_matched = entity_info.get(e, {}).get("matched", False)
            # Check if entity name appears in query (case-insensitive)
            name_in_query = e.lower() in query_lower
            # Secondary sort by claim count (more claims = more relevant)
            claim_count = len(claims_by_entity.get(e, []))
            return (not is_matched, not name_in_query, -claim_count, e)

        sorted_entities = sorted(claims_by_entity.keys(), key=entity_sort_key)

        for i, entity in enumerate(sorted_entities):
            entity_claims = claims_by_entity[entity]
            info = entity_info.get(entity, {"type": "Unknown", "matched": False})
            entity_type = info["type"]

            # Entity header with type
            if info["matched"]:
                lines.append(f"### **{entity}** ({entity_type})")
            else:
                lines.append(f"### {entity} ({entity_type})")

            # Relationships for this entity (with types)
            if entity in rels_by_source:
                rels = rels_by_source[entity][:6]  # Limit to 6
                more = len(rels_by_source[entity]) - 6
                rel_parts = [f"*{rel_type}* → {target}" for rel_type, target in rels]
                if more > 0:
                    rel_parts.append(f"(+{more})")
                lines.append(f"→ {', '.join(rel_parts)}")

            # Smart claim limit: more claims for query-relevant entities
            # First entity (most relevant) gets 8, second gets 6, rest get 4
            name_in_query = entity.lower() in query_lower
            if name_in_query or i == 0:
                max_claims = 8
            elif i == 1:
                max_claims = 6
            else:
                max_claims = 4

            # Claims with source doc_id refs
            total_claims = len(entity_claims)
            shown_claims = min(total_claims, max_claims)
            if total_claims > shown_claims:
                lines.append(f"*{shown_claims}/{total_claims} claims:*")

            for claim in entity_claims[:max_claims]:
                src_ref = ""
                if claim.get("source_doc_id"):
                    # Use short doc_id (first 8 chars)
                    short_id = claim["source_doc_id"][:8]
                    src_ref = f" [{short_id}]"
                lines.append(f"• {claim['statement']}{src_ref}")

            lines.append("")

    # Sources section removed - claims already include source_doc_id refs
    # which can be resolved via API if needed

    return "\n".join(lines)


def format_context_structured(query: str, data: TopicContextData) -> str:
    """Format context with clear structure: entities → claims → sources.

    Optimized for "What is X?" style queries.

    Args:
        query: Original user query
        data: Context data

    Returns:
        Markdown-formatted context string
    """
    # Build source index
    source_index = {src["doc_id"]: i for i, src in enumerate(data.sources, 1)}

    # Build entity info lookup
    entity_info = {e["name"]: e for e in data.entities}

    # Build relationships by source (deduplicated, no self-references)
    rels_by_source: dict[str, set[str]] = {}
    for r in data.relationships:
        # Skip self-referential relationships
        if r["source"] == r["target"]:
            continue
        if r["source"] not in rels_by_source:
            rels_by_source[r["source"]] = set()
        rels_by_source[r["source"]].add(r["target"])

    # Group claims by entity
    claims_by_entity: dict[str, list] = {}
    for claim in data.claims:
        entity = claim["entity"]
        if entity not in claims_by_entity:
            claims_by_entity[entity] = []
        claims_by_entity[entity].append(claim)

    lines = [
        f"# {query}",
        "",
    ]

    # Relationships section - show the knowledge graph connections
    if data.relationships:
        # Deduplicate relationships (source, target) pairs
        unique_rels: dict[tuple[str, str], str] = {}
        for r in data.relationships:
            if r["source"] == r["target"]:
                continue
            key = (r["source"], r["target"])
            if key not in unique_rels:
                unique_rels[key] = r["type"]

        if unique_rels:
            lines.append("## Relationships")
            for (source, target), rel_type in list(unique_rels.items())[:15]:
                lines.append(f"• {source} → *{rel_type}* → {target}")
            lines.append("")

    # Sort entities: matched first, then by claim count
    sorted_entities = sorted(
        claims_by_entity.keys(),
        key=lambda e: (
            not entity_info.get(e, {}).get("matched", False),
            -len(claims_by_entity.get(e, [])),
        ),
    )

    for entity in sorted_entities:
        info = entity_info.get(entity, {"type": "Unknown", "description": ""})
        entity_claims = claims_by_entity[entity]

        # Entity header
        lines.append(f"## {entity}")
        if info.get("description"):
            lines.append(f"*{info['type']}* — {info['description'][:150]}")
        else:
            lines.append(f"*{info['type']}*")

        lines.append("")

        # Claims for this entity
        for claim in entity_claims[:7]:  # Max 7 claims per entity
            src_ref = ""
            if claim.get("source_doc_id") in source_index:
                src_ref = f" [{source_index[claim['source_doc_id']]}]"
            lines.append(f"• {claim['statement']}{src_ref}")

        lines.append("")

    # Sources
    if data.sources:
        lines.append("---")
        lines.append("**Sources:**")
        for i, src in enumerate(data.sources, 1):
            title = src["title"][:50] + "..." if len(src["title"]) > 50 else src["title"]
            url = src.get("url", "")
            if url:
                lines.append(f"[{i}] {title} — {url}")
            else:
                lines.append(f"[{i}] {title}")

    return "\n".join(lines)


def format_markdown_legacy(query: str, topics: list[str], context: dict) -> str:
    """Legacy format for backward compatibility with step_cag.py.

    Args:
        query: Original user query
        topics: List of topic names
        context: Dict with entities, relationships, claims, sources

    Returns:
        Markdown-formatted context string
    """
    lines = [
        "# Knowledge Context",
        "",
        f"**Query:** {query}",
        f"**Topics:** {', '.join(topics) if topics else 'None matched'}",
        "",
        f"*Retrieved: {len(context['entities'])} entities, "
        f"{len(context['relationships'])} relationships, "
        f"{len(context['claims'])} claims from {len(context['sources'])} documents*",
        "",
    ]

    # Entities section
    lines.append("## Knowledge Graph")
    lines.append("")
    lines.append("### Entities")

    matched = [e for e in context["entities"] if e.get("matched")]
    other = [e for e in context["entities"] if not e.get("matched")]

    if matched:
        lines.append("")
        lines.append("**Matched from query:**")
        for e in matched:
            desc = f": {e['description'][:100]}..." if e["description"] else ""
            lines.append(f"- **{e['name']}** ({e['type']}){desc}")

    if other:
        lines.append("")
        lines.append("**Related entities:**")
        for e in other[:20]:
            desc = f": {e['description'][:80]}..." if e["description"] else ""
            lines.append(f"- {e['name']} ({e['type']}){desc}")

    lines.append("")

    # Relationships
    if context["relationships"]:
        lines.append("### Relationships")
        for r in context["relationships"]:
            lines.append(f"- {r['source']} --[{r['type']}]--> {r['target']}")
        lines.append("")

    # Claims
    if context["claims"]:
        lines.append("## Claims")
        lines.append("")

        claims_by_entity: dict = {}
        for claim in context["claims"]:
            entity = claim["entity"]
            if entity not in claims_by_entity:
                claims_by_entity[entity] = []
            claims_by_entity[entity].append(claim)

        for entity, entity_claims in claims_by_entity.items():
            lines.append(f"### {entity}")
            for claim in entity_claims[:5]:
                conf = claim["confidence"]
                source = claim.get("source_doc_title", "")
                source_ref = f" → [{source}]" if source else ""
                lines.append(f"- {claim['statement']} [conf: {conf:.2f}]{source_ref}")
            lines.append("")

    # Sources
    if context["sources"]:
        lines.append("## Sources")
        lines.append("")
        for i, src in enumerate(context["sources"], 1):
            if src.get("url"):
                lines.append(f"[{i}] {src['title']} - {src['url']}")
            else:
                lines.append(f"[{i}] {src['title']}")

    return "\n".join(lines)


def format_rag_context(
    query: str,
    ranked_docs: list[tuple[str, float]],
    entities: list[str],
    relationships: list[dict],
    claims: list[dict],
    doc_metadata: dict,
) -> str:
    """Format RAG retrieved context as text.

    Args:
        query: Original query
        ranked_docs: List of (doc_id, score) tuples
        entities: List of entity names
        relationships: List of relationship dicts
        claims: List of claim dicts
        doc_metadata: Dict mapping doc_id to {title, url}

    Returns:
        Formatted context string
    """
    lines = [
        f"=== CONTEXT FOR: {query} ===",
        f"Retrieved: {len(ranked_docs)} documents, {len(claims)} claims",
        "",
    ]

    # Entities
    lines.append("## Entities")
    for entity in sorted(set(entities))[:30]:
        lines.append(f"- {entity}")
    lines.append("")

    # Relationships
    if relationships:
        lines.append("## Relationships")
        seen: set[tuple[str, str, str]] = set()
        for rel in relationships[:20]:
            if isinstance(rel, dict):
                key = (
                    rel.get("source_entity", ""),
                    rel.get("target_entity", ""),
                    rel.get("relationship_type", ""),
                )
                if key not in seen:
                    seen.add(key)
                    lines.append(f"- {key[0]} --[{key[2]}]--> {key[1]}")
        lines.append("")

    # Claims
    if claims:
        lines.append("## Claims")
        for claim in claims[:10]:
            entity = claim.get("entity", "")
            prefix = f"[{entity}] " if entity else ""
            lines.append(f"- {prefix}{claim['statement']} (confidence: {claim['confidence']:.2f})")
        lines.append("")

    # Citations
    lines.append("## Citations")
    for i, (doc_id, score) in enumerate(ranked_docs[:10]):
        meta = doc_metadata.get(doc_id, {})
        title = meta.get("title") or f"Document {doc_id[:8]}"
        url = meta.get("url", "")
        if url:
            lines.append(f"[{i + 1}] {title} ({url}) - score: {score:.3f}")
        else:
            lines.append(f"[{i + 1}] {title} - score: {score:.3f}")

    return "\n".join(lines)
