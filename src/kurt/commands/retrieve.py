"""Retrieve command - Hybrid retrieval from knowledge graph and embeddings.

This module provides multi-level retrieval:
- `kurt retrieve <query>` - Full context retrieval (default, backward compatible)
- `kurt retrieve entities <query>` - Entity-level graph exploration
- `kurt retrieve claims <query>` - Claim-level retrieval for specific entities
"""

import json
from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command

console = Console()


# Create a group for retrieve subcommands
# We use a custom callback to handle the case where user passes a query directly
# vs using a subcommand like "entities" or "claims"
@click.group(invoke_without_command=True)
@click.option(
    "--query",
    "-q",
    type=str,
    default=None,
    help="Query string (alternative to positional argument)",
)
@click.option(
    "--mode",
    type=click.Choice(["rag", "cag"], case_sensitive=False),
    default="cag",
    help="Retrieval mode: cag (fast, entity-based) or rag (full pipeline)",
)
@click.option(
    "--type",
    "query_type",
    type=click.Choice(["hybrid", "graph", "semantic"], case_sensitive=False),
    default="hybrid",
    help="RAG retrieval type: hybrid (default), graph-only, or semantic-only",
)
@click.option(
    "--deep",
    is_flag=True,
    default=False,
    help="Enable deep mode for more thorough retrieval (RAG only)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["context", "json", "citations"], case_sensitive=False),
    default="context",
    help="Output format (default: context)",
)
@click.option(
    "--session-id",
    type=str,
    default=None,
    help="Session ID for multi-turn conversations",
)
@click.option(
    "--top-k",
    type=int,
    default=5,
    help="CAG: Number of entities to match per term (default: 5)",
)
@click.option(
    "--min-similarity",
    type=float,
    default=0.3,
    help="CAG: Minimum entity similarity threshold (default: 0.3)",
)
@click.pass_context
@track_command
def retrieve_cmd(
    ctx,
    query: str,
    mode: str,
    query_type: str,
    deep: bool,
    output_format: str,
    session_id: str,
    top_k: int,
    min_similarity: float,
):
    """
    Retrieve context from the knowledge graph for a query.

    \b
    SUBCOMMANDS:
      entities   Explore entity graph (similarity search + neighbors)
      claims     Get claims about specific entities

    \b
    DEFAULT BEHAVIOR (with -q/--query):
      Full context retrieval combining entities, claims, and sources.

    \b
    MODES:
      CAG (default): Fast, entity-based retrieval for agent sessions.
      RAG: Full pipeline with multiple search strategies.

    \b
    EXAMPLES:
        kurt retrieve -q "What integrations does Segment support?"
        kurt retrieve entities "file formats, Parquet"
        kurt retrieve claims "DuckDB, MotherDuck"
        kurt retrieve -q "pricing" --mode rag --deep
    """
    # If a subcommand was invoked, skip this handler
    if ctx.invoked_subcommand is not None:
        return

    # If no query provided, show help
    if query is None:
        click.echo(ctx.get_help())
        return

    # Run the original full retrieval (backward compatible)
    _run_full_retrieval(
        query=query,
        mode=mode,
        query_type=query_type,
        deep=deep,
        output_format=output_format,
        session_id=session_id,
        top_k=top_k,
        min_similarity=min_similarity,
    )


# ============================================================================
# Entities subcommand - Graph exploration
# ============================================================================


@retrieve_cmd.command("entities")
@click.argument("query", type=str)
@click.option(
    "--top-k",
    type=int,
    default=5,
    help="Number of similar entities to find per term (default: 5)",
)
@click.option(
    "--min-similarity",
    type=float,
    default=0.3,
    help="Minimum similarity threshold (default: 0.3)",
)
@click.option(
    "--neighbors",
    is_flag=True,
    default=False,
    help="Include 1-hop neighbors in results",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format (default: table)",
)
@track_command
def entities_cmd(
    query: str,
    top_k: int,
    min_similarity: float,
    neighbors: bool,
    output_format: str,
):
    """
    Explore entity graph via similarity search.

    Query can be comma-separated for multi-term search:
    - "file formats" - single term search
    - "Parquet, CSV, JSON" - multi-term search

    \b
    OPERATIONS:
      1. Embed query terms
      2. Find similar entity nodes (vector similarity)
      3. Optionally expand to 1-hop neighbors
      4. Show node degree (connectivity = importance)

    \b
    EXAMPLES:
        kurt retrieve entities "file formats"
        kurt retrieve entities "Parquet, CSV, MotherDuck" --neighbors
        kurt retrieve entities "DuckDB" --top-k 10 --format json
    """
    from kurt.db.database import get_session
    from kurt.db.models import DocumentEntity, Entity, EntityRelationship
    from kurt.db.sqlite import SQLiteClient
    from kurt.utils.embeddings import embedding_to_bytes, generate_embeddings

    console.print()
    console.print(f"[dim]Entity search for:[/dim] [bold]{query}[/bold]")

    # Parse comma-separated terms
    if "," in query:
        search_terms = [t.strip() for t in query.split(",") if t.strip()]
    else:
        search_terms = [query]

    console.print(f"[dim]Terms: {search_terms}[/dim]")
    console.print()

    # Generate embeddings for all terms
    term_embeddings = generate_embeddings(search_terms)

    # Search for similar entities
    client = SQLiteClient()
    entity_scores: dict[str, tuple] = {}  # entity_id -> (entity, similarity, matched_term)

    for term, term_embedding in zip(search_terms, term_embeddings):
        emb_bytes = embedding_to_bytes(term_embedding)
        results = client.search_similar_entities(
            emb_bytes, limit=top_k, min_similarity=min_similarity
        )

        for entity_id, sim in results:
            if entity_id not in entity_scores or sim > entity_scores[entity_id][1]:
                entity_scores[entity_id] = (None, sim, term)  # Entity loaded later

    if not entity_scores:
        console.print("[yellow]No matching entities found[/yellow]")
        return

    # Load entity details and compute degrees
    session = get_session()
    entities_data = []

    for entity_id, (_, sim, matched_term) in entity_scores.items():
        entity = session.get(Entity, UUID(entity_id))
        if not entity:
            continue

        # Count relationships (degree)
        outgoing = (
            session.query(EntityRelationship)
            .filter(EntityRelationship.source_entity_id == entity.id)
            .count()
        )
        incoming = (
            session.query(EntityRelationship)
            .filter(EntityRelationship.target_entity_id == entity.id)
            .count()
        )
        degree = outgoing + incoming

        # Count document mentions
        doc_count = (
            session.query(DocumentEntity).filter(DocumentEntity.entity_id == entity.id).count()
        )

        entities_data.append(
            {
                "id": str(entity.id),
                "name": entity.name,
                "type": entity.entity_type,
                "description": (entity.description or "")[:100],
                "aliases": entity.aliases or [],
                "similarity": sim,
                "matched_term": matched_term,
                "degree": degree,
                "doc_mentions": doc_count,
            }
        )

    # Sort by similarity
    entities_data.sort(key=lambda x: x["similarity"], reverse=True)

    # Optionally expand to neighbors
    neighbor_entities = []
    if neighbors and entities_data:
        matched_ids = {e["id"] for e in entities_data}

        for entity_data in entities_data[:5]:  # Expand top 5 only
            entity_id = UUID(entity_data["id"])

            # Get outgoing relationships
            out_rels = (
                session.query(EntityRelationship, Entity)
                .join(Entity, EntityRelationship.target_entity_id == Entity.id)
                .filter(EntityRelationship.source_entity_id == entity_id)
                .limit(5)
                .all()
            )

            for rel, target in out_rels:
                if str(target.id) not in matched_ids:
                    neighbor_entities.append(
                        {
                            "id": str(target.id),
                            "name": target.name,
                            "type": target.entity_type,
                            "description": (target.description or "")[:100],
                            "relationship": f"{entity_data['name']} → {rel.relationship_type} → {target.name}",
                            "from_entity": entity_data["name"],
                        }
                    )
                    matched_ids.add(str(target.id))

    session.close()

    # Output
    if output_format == "json":
        output = {
            "query": query,
            "terms": search_terms,
            "matched_entities": entities_data,
            "neighbor_entities": neighbor_entities if neighbors else [],
        }
        print(json.dumps(output, indent=2))
    else:
        # Table output
        table = Table(title="Matched Entities", show_header=True, header_style="bold cyan")
        table.add_column("Entity", style="bold", min_width=15)
        table.add_column("Type", style="dim", width=10)
        table.add_column("Description", style="white", no_wrap=False)
        table.add_column("Sim", style="green", justify="right", width=4)
        table.add_column("Deg", style="yellow", justify="right", width=3)

        for e in entities_data:
            desc = e["description"][:80] if e["description"] else "-"
            table.add_row(
                e["name"],
                e["type"],
                desc,
                f"{e['similarity']:.2f}",
                str(e["degree"]),
            )

        console.print(table)

        if neighbors and neighbor_entities:
            console.print()
            neighbor_table = Table(
                title="Neighbor Entities (1-hop)", show_header=True, header_style="bold yellow"
            )
            neighbor_table.add_column("Entity", style="bold")
            neighbor_table.add_column("Type", style="dim")
            neighbor_table.add_column("Relationship", style="cyan")

            for n in neighbor_entities[:10]:  # Show top 10 neighbors
                neighbor_table.add_row(n["name"], n["type"], n["relationship"])

            console.print(neighbor_table)

        console.print()
        console.print(f"[dim]Found {len(entities_data)} matched entities[/dim]")
        if neighbors:
            console.print(f"[dim]Found {len(neighbor_entities)} neighbor entities[/dim]")


# ============================================================================
# Claims subcommand - Claim-level retrieval
# ============================================================================


@retrieve_cmd.command("claims")
@click.argument("query", type=str)
@click.option(
    "--top-k",
    type=int,
    default=5,
    help="Number of entities to match per term (default: 5)",
)
@click.option(
    "--max-claims",
    type=int,
    default=20,
    help="Maximum claims to return (default: 20)",
)
@click.option(
    "--min-similarity",
    type=float,
    default=0.3,
    help="Minimum entity similarity threshold (default: 0.3)",
)
@click.option(
    "--claim-type",
    type=str,
    default=None,
    help="Filter by claim type (e.g., CAPABILITY, LIMITATION, FACT)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    help="Output format (default: markdown)",
)
@track_command
def claims_cmd(
    query: str,
    top_k: int,
    max_claims: int,
    min_similarity: float,
    claim_type: str,
    output_format: str,
):
    """
    Get claims about specific entities.

    Query can be comma-separated for multi-entity search:
    - "DuckDB" - claims about DuckDB
    - "Parquet, CSV, JSON" - claims about file formats

    Claims that reference multiple matched entities are prioritized
    (cross-entity knowledge).

    \b
    OPERATIONS:
      1. Embed query terms → find entity nodes
      2. Get claims attached to matched entities
      3. Prioritize cross-entity claims
      4. Return claims with source document refs

    \b
    EXAMPLES:
        kurt retrieve claims "DuckDB, MotherDuck"
        kurt retrieve claims "Parquet" --claim-type CAPABILITY
        kurt retrieve claims "pricing, cost" --max-claims 30 --format json
    """
    from sqlalchemy import func

    from kurt.db.claim_models import Claim, ClaimEntity
    from kurt.db.database import get_session
    from kurt.db.models import Document, Entity
    from kurt.db.sqlite import SQLiteClient
    from kurt.utils.embeddings import embedding_to_bytes, generate_embeddings

    console.print()
    console.print(f"[dim]Claims search for:[/dim] [bold]{query}[/bold]")

    # Parse comma-separated terms
    if "," in query:
        search_terms = [t.strip() for t in query.split(",") if t.strip()]
    else:
        search_terms = [query]

    console.print(f"[dim]Terms: {search_terms}[/dim]")
    console.print()

    # Generate embeddings and find entities
    term_embeddings = generate_embeddings(search_terms)
    client = SQLiteClient()
    matched_entity_ids = set()

    for term, term_embedding in zip(search_terms, term_embeddings):
        emb_bytes = embedding_to_bytes(term_embedding)
        results = client.search_similar_entities(
            emb_bytes, limit=top_k, min_similarity=min_similarity
        )
        for entity_id, _ in results:
            matched_entity_ids.add(UUID(entity_id))

    if not matched_entity_ids:
        console.print("[yellow]No matching entities found[/yellow]")
        return

    session = get_session()

    # Get entity names for display
    entity_names = {}
    for eid in matched_entity_ids:
        entity = session.get(Entity, eid)
        if entity:
            entity_names[eid] = entity.name

    console.print(f"[dim]Matched entities: {', '.join(entity_names.values())}[/dim]")
    console.print()

    # Step 1: Find cross-entity claims (claims referencing multiple matched entities)
    claims_data = []
    seen_claim_ids = set()

    if len(matched_entity_ids) >= 2:
        # Find claims that appear multiple times in ClaimEntity for our matched entities
        cross_entity_claim_ids = (
            session.query(ClaimEntity.claim_id)
            .filter(ClaimEntity.entity_id.in_(matched_entity_ids))
            .group_by(ClaimEntity.claim_id)
            .having(func.count(ClaimEntity.entity_id) >= 2)
            .limit(max_claims // 2)
            .all()
        )
        cross_claim_ids = [c.claim_id for c in cross_entity_claim_ids]

        if cross_claim_ids:
            query_obj = (
                session.query(Claim, Entity, Document)
                .join(Entity, Claim.subject_entity_id == Entity.id)
                .join(Document, Claim.source_document_id == Document.id)
                .filter(Claim.id.in_(cross_claim_ids))
            )
            if claim_type:
                query_obj = query_obj.filter(Claim.claim_type == claim_type)
            query_obj = query_obj.order_by(Claim.overall_confidence.desc())

            for claim, entity, doc in query_obj.all():
                if claim.id not in seen_claim_ids:
                    claims_data.append(
                        {
                            "statement": claim.statement,
                            "type": (
                                claim.claim_type.value
                                if hasattr(claim.claim_type, "value")
                                else str(claim.claim_type)
                            ),
                            "confidence": claim.overall_confidence,
                            "entity": entity.name,
                            "source_doc_id": str(doc.id)[:8],
                            "source_doc_title": doc.title or "Untitled",
                            "is_cross_entity": True,
                        }
                    )
                    seen_claim_ids.add(claim.id)

    # Step 2: Add claims about matched entities (subject is a matched entity)
    if len(claims_data) < max_claims:
        remaining = max_claims - len(claims_data)
        query_obj = (
            session.query(Claim, Entity, Document)
            .join(Entity, Claim.subject_entity_id == Entity.id)
            .join(Document, Claim.source_document_id == Document.id)
            .filter(Claim.subject_entity_id.in_(matched_entity_ids))
        )
        if claim_type:
            query_obj = query_obj.filter(Claim.claim_type == claim_type)
        query_obj = query_obj.order_by(Claim.overall_confidence.desc()).limit(
            remaining + len(seen_claim_ids)
        )

        for claim, entity, doc in query_obj.all():
            if claim.id not in seen_claim_ids and len(claims_data) < max_claims:
                claims_data.append(
                    {
                        "statement": claim.statement,
                        "type": (
                            claim.claim_type.value
                            if hasattr(claim.claim_type, "value")
                            else str(claim.claim_type)
                        ),
                        "confidence": claim.overall_confidence,
                        "entity": entity.name,
                        "source_doc_id": str(doc.id)[:8],
                        "source_doc_title": doc.title or "Untitled",
                        "is_cross_entity": False,
                    }
                )
                seen_claim_ids.add(claim.id)

    session.close()

    if not claims_data:
        console.print("[yellow]No claims found for matched entities[/yellow]")
        return

    # Output
    if output_format == "json":
        output = {
            "query": query,
            "terms": search_terms,
            "matched_entities": list(entity_names.values()),
            "claims": claims_data,
            "total_claims": len(claims_data),
        }
        print(json.dumps(output, indent=2))
    else:
        # Markdown output
        cross_entity_claims = [c for c in claims_data if c.get("is_cross_entity")]
        single_entity_claims = [c for c in claims_data if not c.get("is_cross_entity")]

        lines = []

        if cross_entity_claims:
            lines.append("## Cross-Entity Claims")
            lines.append("")
            for c in cross_entity_claims:
                lines.append(
                    f"- **[{c['entity']}]** {c['statement']} "
                    f"[{c['type']}] [{c['source_doc_id']}]"
                )
            lines.append("")

        if single_entity_claims:
            # Group by entity
            claims_by_entity: dict[str, list] = {}
            for c in single_entity_claims:
                ent = c["entity"]
                if ent not in claims_by_entity:
                    claims_by_entity[ent] = []
                claims_by_entity[ent].append(c)

            for entity, entity_claims in claims_by_entity.items():
                lines.append(f"## {entity}")
                lines.append("")
                for c in entity_claims:
                    lines.append(f"- {c['statement']} [{c['type']}] [{c['source_doc_id']}]")
                lines.append("")

        console.print(
            Panel(
                "\n".join(lines),
                title=f"[bold cyan]Claims ({len(claims_data)} total)[/bold cyan]",
                border_style="cyan",
            )
        )

        console.print()
        console.print(f"[dim]Cross-entity claims: {len(cross_entity_claims)}[/dim]")
        console.print(f"[dim]Single-entity claims: {len(single_entity_claims)}[/dim]")


# ============================================================================
# Full retrieval (original behavior, backward compatible)
# ============================================================================


def _run_full_retrieval(
    query: str,
    mode: str,
    query_type: str,
    deep: bool,
    output_format: str,
    session_id: str,
    top_k: int,
    min_similarity: float,
):
    """Run full context retrieval (original behavior)."""
    console.print()
    console.print(f"[dim]Retrieving context for:[/dim] [bold]{query}[/bold]")

    if mode == "cag":
        # CAG mode: fast, entity-based retrieval using workflow runner
        from kurt.models.staging.retrieval.step_cag import CAGConfig
        from kurt.utils.filtering import DocumentFilters
        from kurt.workflows.cli_helpers import dbos_cleanup_context, run_pipeline_simple

        console.print(f"[dim]Mode: CAG (top_k={top_k}, min_sim={min_similarity})[/dim]")
        console.print("[dim]Using unified retrieval.cag step[/dim]")
        console.print()

        with dbos_cleanup_context():
            try:
                # Build config for the model
                config = CAGConfig(
                    top_k_per_term=top_k,
                    min_similarity=min_similarity,
                )

                # Run via workflow runner
                workflow_result = run_pipeline_simple(
                    target="retrieval.cag",
                    filters=DocumentFilters(),
                    model_configs={"retrieval.cag": config},
                    metadata={"query": query},
                )

                # Read result from the table
                from sqlalchemy import text

                from kurt.db.database import get_session

                with get_session() as session:
                    row = session.execute(
                        text(
                            "SELECT query, matched_entities, topics, context_markdown, "
                            "token_estimate, sources, telemetry "
                            "FROM retrieval_cag_context WHERE query_id = :wf_id"
                        ),
                        {"wf_id": workflow_result.get("workflow_id")},
                    ).fetchone()

                if not row:
                    console.print("[yellow]No results found[/yellow]")
                    return

                # Parse JSON fields
                matched_entities = json.loads(row.matched_entities)
                topics = json.loads(row.topics)
                sources = json.loads(row.sources)
                telemetry = json.loads(row.telemetry)

            except Exception as e:
                console.print(f"[red]Error during CAG retrieval:[/red] {e}")
                raise click.Abort()

        # Output based on format
        if output_format == "json":
            output = {
                "query": query,
                "mode": "cag",
                "topics": topics,
                "matched_entities": matched_entities,
                "context_markdown": row.context_markdown,
                "token_estimate": row.token_estimate,
                "sources": sources,
                "telemetry": telemetry,
            }
            print(json.dumps(output, indent=2))

        elif output_format == "citations":
            if not sources:
                console.print("[yellow]No sources found[/yellow]")
                return

            console.print("[bold cyan]Sources[/bold cyan]")
            console.print()

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("#", style="yellow", width=4, justify="right")
            table.add_column("Title", style="bold")
            table.add_column("URL", style="dim")

            for i, src in enumerate(sources, 1):
                title = src.get("title", "Untitled")
                if len(title) > 50:
                    title = title[:47] + "..."
                url = src.get("url", "N/A")
                if len(url) > 40:
                    url = url[:37] + "..."
                table.add_row(str(i), title, url)

            console.print(table)
            console.print()
            console.print(f"[dim]Total: {len(sources)} sources[/dim]")

        else:  # context (default)
            console.print(
                Panel(
                    row.context_markdown,
                    title="[bold cyan]Agent Context (CAG)[/bold cyan]",
                    border_style="cyan",
                )
            )

            # Show stats
            console.print()
            console.print("[dim]Stats:[/dim]")
            console.print(f"  Topics: {', '.join(topics) if topics else 'None'}")
            console.print(f"  Matched entities: {', '.join(matched_entities[:5])}")
            console.print(f"  Token estimate: {row.token_estimate}")
            if telemetry:
                console.print(f"  Claims loaded: {telemetry.get('claims_loaded', 0)}")
                console.print(f"  Sources: {telemetry.get('sources_loaded', 0)}")

        return

    # RAG mode: unified multi-signal retrieval using workflow runner
    from kurt.models.staging.retrieval.step_rag import RAGConfig
    from kurt.utils.filtering import DocumentFilters
    from kurt.workflows.cli_helpers import dbos_cleanup_context, run_pipeline_simple

    console.print(f"[dim]Mode: RAG ({query_type})" + (" (deep)" if deep else "") + "[/dim]")
    console.print("[dim]Using unified retrieval.rag step[/dim]")
    console.print()

    with dbos_cleanup_context():
        try:
            # Build config for the model
            config = RAGConfig()

            # Run via workflow runner
            workflow_result = run_pipeline_simple(
                target="retrieval.rag",
                filters=DocumentFilters(),
                model_configs={"retrieval.rag": config},
                metadata={
                    "query": query,
                    "query_type": query_type,
                    "deep_mode": deep,
                },
            )

            # Read result from the table
            from sqlalchemy import text

            from kurt.db.database import get_session

            with get_session() as session:
                row = session.execute(
                    text(
                        "SELECT query, context_text, doc_ids, entities, claims, "
                        "citations, telemetry "
                        "FROM retrieval_rag_context WHERE query_id = :wf_id"
                    ),
                    {"wf_id": workflow_result.get("workflow_id")},
                ).fetchone()

            if not row:
                console.print("[yellow]No results found[/yellow]")
                return

            # Parse JSON fields
            citations = json.loads(row.citations)
            telemetry = json.loads(row.telemetry)
            entities = json.loads(row.entities)

        except Exception as e:
            console.print(f"[red]Error during RAG retrieval:[/red] {e}")
            raise click.Abort()

    # Output based on format
    if output_format == "json":
        output = {
            "query": query,
            "query_type": query_type,
            "deep_mode": deep,
            "context_text": row.context_text,
            "citations": citations,
            "entities": entities,
            "telemetry": telemetry,
        }
        print(json.dumps(output, indent=2))

    elif output_format == "citations":
        if not citations:
            console.print("[yellow]No citations found[/yellow]")
            return

        console.print("[bold cyan]Citations[/bold cyan]")
        console.print()

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Rank", style="yellow", width=6, justify="right")
        table.add_column("Title", style="bold")
        table.add_column("Score", style="green", width=8, justify="right")
        table.add_column("URL", style="dim")

        for i, citation in enumerate(citations, 1):
            title = citation.get("title") or "Untitled"
            if len(title) > 50:
                title = title[:47] + "..."
            url = citation.get("url") or "N/A"
            if len(url) > 40:
                url = url[:37] + "..."

            table.add_row(
                str(i),
                title,
                f"{citation.get('score', 0):.1%}",
                url,
            )

        console.print(table)
        console.print()
        console.print(f"[dim]Total: {len(citations)} citations[/dim]")

    else:  # context (default)
        # Show context in a panel
        console.print(
            Panel(
                row.context_text,
                title="[bold cyan]Retrieved Context[/bold cyan]",
                border_style="cyan",
            )
        )

        # Show summary stats
        console.print()
        console.print("[dim]Stats:[/dim]")
        if "graph_results" in telemetry:
            console.print(f"  Graph results: {telemetry['graph_results']}")
        if "semantic_results" in telemetry:
            console.print(f"  Semantic results: {telemetry['semantic_results']}")
        if "entities" in telemetry:
            console.print(f"  Entities: {telemetry['entities']}")
        if citations:
            console.print(f"  Citations: {len(citations)}")
