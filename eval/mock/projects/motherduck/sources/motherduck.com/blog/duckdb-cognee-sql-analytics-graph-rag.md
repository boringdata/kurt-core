---
title: duckdb-cognee-sql-analytics-graph-rag
content_type: tutorial
source_url: https://motherduck.com/blog/duckdb-cognee-sql-analytics-graph-rag
indexed_at: '2025-11-25T19:56:34.792020'
content_hash: 3fccade97fb18575
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# DuckDB × cognee: Run SQL Analytics Right Beside Your Graph-Native RAG

2025/08/29 - 5 min read

BY

[Vasilije Markovic](https://motherduck.com/authors/vasilije-markovic/)

_TL;DR: [cognee](https://www.cognee.ai/)’s DuckDB integration uplevels AI memory by combining local OLAP processing and cognee’s KG modelling rather than forcing you to choose between fast analytics and one-off RAG retrievals. This makes AI-first data lakes more analytical, cost-effective, and easier to build and use._

## Search _or_ Analytics ❌ -> Search _&_ Analytics ✅

We’ve written before about how [DuckDB, dlt, and Cognee can streamline RAG systems](https://motherduck.com/blog/streamlining-ai-agents-duckdb-rag-solutions/). This new post goes a step further: not just preparing and structuring data, but running SQL analytics directly beside your graph-native retrieval.

Traditional AI memory systems force a trade-off: fast semantic search (embeddings) or powerful SQL analytics. These rarely both work well together—vector databases excel at similarity search but struggle with complex analytical queries; SQL databases handle analytics beautifully but can’t do semantic retrieval without costly, complex integrations.

Meanwhile, DuckDB can crunch through gigabytes of data in seconds, run complex aggregations, and handle analytical workloads that would choke traditional databases — all while being embeddable and requiring zero infrastructure.

At the same time, AI memory frameworks produce rich, evolving models that users want to query with natural language (e.g., “What are the trending topics this quarter?” or “Who all is involved in Project X?”). Traditional vector stores don’t handle these workloads efficiently.

**The solution:** bring DuckDB's analytical power directly into cognee’s AI memory graph layer. Enriched with Kuzu as the knowledge graph store, the **DuckDB vector store** integration creates a synergy of semantic knowledge analytics and cognee’s retrieval capabilities.

## How cognee Works (the ECL Path)

cognee is built around a modular **Extract, Cognify, Load (ECL)** pipeline.

- **Extract**: ingestion of raw content from APIs, databases, or documents.
- **cognify**: splitting the content into chunks, generating embeddings, identifying key entities, and mapping their relationships.
- **Load**: writing of vector representations and graph connections to the memory backends.

This produces a semantic layer that can represent time, entities, and objects, and establish meaningful relationships between them.

## DuckDB Adapter (Literal Schema & Writes)

Starting with cognee's latest release, DuckDB integration is available for both local analytics and cloud-scale processing (parallel, async), so you can run analytical queries directly alongside your knowledge graph queries.

This integration means **knowledge graph embeddings** are stored in DuckDB’s columnar format and uses vectorized execution for fast SQL analytics. It sits next to cognee’s graph-native retrieval, so you can analyze embeddings with SQL while cognee connects those embeddings to the knowledge graph.

### Under the Hood: Vectors, Graphs, and Provenance

cognee combines three complementary storage systems. Each plays a distinct role, and together they make your data both **searchable** and **connected**.

- **Relational store** — Tracks documents, their chunks, and provenance (i.e., where each piece of data came from and how it’s linked to the source).
- **Vector store** — Holds **knowledge graph embeddings** (numerical representations that let cognee find conceptually related text, even if the wording is different) for semantic similarity and columnar SQL analytics.
- **Graph store** — Captures entities and relationships in a knowledge graph (i.e., nodes and edges that let cognee understand structure and navigate connections).

The DuckDB adapter is the **vector store adapter**. Behind the scenes, the wrapper creates a DuckDB table for each collection:

```sql
Copy code

CREATE TABLE IF NOT EXISTS {collection_name} (
    id VARCHAR PRIMARY KEY,
    text TEXT,
    vector FLOAT[{vector_dimension}],
    payload JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

```python
Copy code

create_data_points_query = f"""
INSERT OR REPLACE INTO {collection_name} (id, text, vector, payload) VALUES ($1, $2, $3, $4)
"""
await self._execute_transaction(
    [(create_data_points_query, [\
        str(data_point.id),\
        DataPoint.get_embeddable_data(data_point),\
        data_vectors[i],\
        json.dumps(serialize_for_json(data_point.model_dump()))\
    ]) for i, data_point in enumerate(data_points)]
)
```

The data is then loaded from cognee’s **DataPoint** objects—Pydantic models used as standardized input/output schemas for tasks. DataPoints:

- Define the shape of data passing between tasks.
- Provide validation and consistent typing.
- Make pipelines more robust and maintainable by catching schema errors early.

So, cognee’s pipeline processes the data; **DuckDB (knowledge graph embeddings)** and **Kuzu (knowledge graphs)** store it. Simple.

Let’s try it out.

## Getting Started

Before running queries, you first need to configure cognee to use **DuckDB as the vector store**. The example below shows a minimal setup: pruning any previous data, adding new content, running the ECL pipeline (`cognify`), and then searching against the stored embeddings.

```python
Copy code

import os
import asyncio
from cognee import config, prune, add, cognify, search, SearchType

# Import the register module to enable DuckDB support
from cognee_community_hybrid_adapter_duckdb import register

async def main():
    # Configure DuckDB as vector database
    config.set_vector_db_config({
        "vector_db_provider": "duckdb",
        "vector_db_url": "my_database.db",  # File path or None for in-memory
    })

    # Optional: Clean previous data
    await prune.prune_data()
    await prune.prune_system()

    # Add your content
    await add("""
    Natural language processing (NLP) is an interdisciplinary
    subfield of computer science and information retrieval.
    """)

    # Process with cognee
    await cognify()

    # Search (use vector-based search types)
    search_results = await search(
        query_type=SearchType.CHUNKS,
        query_text="Tell me about NLP"
    )

    for result in search_results:
        print("Search result:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

### Running SQL Analytics in DuckDB

After storing embeddings in DuckDB through cognee, you can also issue direct SQL queries against the same database. This allows you to take advantage of DuckDB’s columnar execution engine for lightweight analytics alongside retrieval.

```sql
Copy code

CREATE TABLE ducks AS SELECT 3 AS age, 'mandarin' AS breed;
SELECT * FROM ducks;
```

The same workflow applies to tables populated with embeddings: you can run SQL queries over them to perform analytics while cognee handles retrieval against the connected knowledge graph.

What makes this integration special is that it eliminates the trade-off between analytics and retrieval. With cognee’s ECL pipeline building a rich knowledge graph and DuckDB storing embeddings in a columnar format, you get the best of both worlds:

- Fast, SQL-native analytics over your embeddings, entities, and metadata.
- Graph-native retrieval that keeps relationships and context intact.
- No ETL overhead — everything stays in sync inside cognee, so you can query and analyze without extra pipelines.

Instead of stitching together vector stores and SQL engines, you get one integrated layer where analytics and search reinforce each other.

🚀 Want to see it in action? Try out the DuckDB cognee adapter and start running SQL queries right beside your knowledge graph memory.

🎥 And if you’d like to go deeper, join Mehdi Ouazza (MotherDuck) and Vasile (Cognee) for a live session breaking this down at lu.ma/6s0goctt.

### TABLE OF CONTENTS

[Search \_or\_ Analytics ❌ -> Search \_&\_ Analytics ✅](https://motherduck.com/blog/duckdb-cognee-sql-analytics-graph-rag/#search-or-analytics-search-analytics)

[How cognee Works](https://motherduck.com/blog/duckdb-cognee-sql-analytics-graph-rag/#how-cognee-works)

[DuckDB Adapter](https://motherduck.com/blog/duckdb-cognee-sql-analytics-graph-rag/#duckdb-adapter)

[Getting Started](https://motherduck.com/blog/duckdb-cognee-sql-analytics-graph-rag/#getting-started)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Announcing Pg_duckdb Version 1.0](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpg_duckdb_0ba60b727d.png&w=3840&q=75)](https://motherduck.com/blog/pg-duckdb-release/)

[2025/09/03 - Jelte Fennema-Nio, Jacob Matson](https://motherduck.com/blog/pg-duckdb-release/)

### [Announcing Pg\_duckdb Version 1.0](https://motherduck.com/blog/pg-duckdb-release)

PostgreSQL gets a DuckDB-flavored power-up for faster analytical queries without ever leaving Postgres.

[![DuckDB Ecosystem: September 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_3_72ab709f58.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

[2025/09/09 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

### [DuckDB Ecosystem: September 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025)

DuckDB Monthly #33: DuckDB 58× faster spatial joins, pg\_duckdb 1.0, and 79% Snowflake cost savings

[View all](https://motherduck.com/blog/)

Authorization Response