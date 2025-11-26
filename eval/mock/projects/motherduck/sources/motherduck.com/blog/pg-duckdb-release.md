---
title: pg-duckdb-release
content_type: blog
source_url: https://motherduck.com/blog/pg-duckdb-release
indexed_at: '2025-11-25T19:56:35.744715'
content_hash: e0f53688470bfdc5
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Announcing Pg\_duckdb Version 1.0

2025/09/03 - 6 min read

BY

[Jelte Fennema-Nio](https://motherduck.com/authors/jelte-fennema-nio/)
,
[Jacob Matson](https://motherduck.com/authors/jacob-matson/)

We're excited to share the 1.0 release of pg\_duckdb, an open-source PostgreSQL extension that brings DuckDB's vectorized analytical engine directly inside PostgreSQL. You can think of it as adding a turbo engine to your PostgreSQL database–ready to run efficient, ad hoc queries while PostgreSQL continues doing what it does best: transactional workloads for your production app.

Pg\_duckdb embeds a DuckDB instance directly into your existing PostgreSQL process. While pg\_duckdb won’t turn your PostgreSQL database into a full-fledged data warehouse, it offers PostgreSQL users a path for speedy analytical queries.

Version 1.0 brings enhanced MotherDuck integration, support for more data types, greater stability, and performance improvements including parallel table scanning–read the [full pg\_duckdb release notes](https://github.com/duckdb/pg_duckdb/releases/tag/v1.0.0) for all of the details.

Let’s dive into the performance use cases.

## DuckDB speed in elephant mode

First, let’s look at pg\_duckdb’s performance. As always, performance depends greatly on your workload. In short, the queries that will benefit the most from pg\_duckdb are cases where indexes cannot be used efficiently. Certain queries that time out with PostgreSQL alone now become possible with pg\_duckdb!

We ran a TPCH-like benchmark suite to test pg\_duckdb in two ways: with all PostgreSQL indexes created, and compared to PostgreSQL with only primary keys. Against PostgreSQL with all indexes, speed-ups are nice but not astounding–up to ~4x faster. But against the PostgreSQL engine with only primary keys, pg\_duckdb is much faster. **Queries that time out within the 10 minute window on PostgreSQL alone now complete in less than 10 seconds with pg\_duckdb!**

For more details on the benchmark setup, head over to the [pg\_duckdb repo](https://github.com/duckdb/pg_duckdb/blob/main/scripts/tpch/README.md#results).

## Analytics on PostgreSQL with ducks

Traditionally, scaling analytics workloads in PostgreSQL means maintaining a fleet of replicas. Each replica receives data from the primary instance WAL and applies changes while staying available for analytical queries. Adding indexes to your replicas will improve performance for analytical queries, but here’s the problem: the indexes must be maintained on the **primary** in order to read on the **replicas**. Updating indexes leads to a constant negotiation between the team maintaining the primary database and the team using replicas for analytical workloads.

Thankfully, the pg\_duckdb extension adds DuckDB to the mix which can read directly from PostgreSQL storage format and quickly return datasets without having to replicate it into yet another storage format or add indexes. When used appropriately, this can massively accelerate queries, up to 1000x in some cases (less if indexes already exist).

It's important to note that when querying PostgreSQL tables directly with pg\_duckdb, you're still working with PostgreSQL's row-oriented storage—you don't get DuckDB's columnar storage benefits or compression advantages. The performance gains come from DuckDB's vectorized execution engine, which is optimized for analytical workloads even when operating on row-oriented data.

Already a PostgreSQL expert? You can run pg\_duckdb directly by using a Docker image:

```shell
Copy code

docker run -d -e POSTGRES_PASSWORD=duckdb pgduckdb/pgduckdb:16-main
```

Then, query a PostgreSQL table directly–or, query an external Parquet file like our open dataset containing Netflix top 10 program data:

```sql
Copy code

-- Use DuckDB engine to query a Postgres table directly
SET duckdb.force_execution = true; SELECT count(*) FROM your_pg_table WHERE status = 'active';

-- Use DuckDB engine to query an external Parquet file accessible from the PG server
SELECT COUNT(*) FROM read_parquet('s3://us-prd-motherduck-open-datasets/netflix/netflix_daily_top_10.parquet');
```

Keep in mind: PostgreSQL requires that extensions on primary and replicas are identical, so the pg\_duckdb extension must also be installed on the primary. Since DuckDB can be very resource-hungry, you’ll want controls in place to prevent use on the primary. Additionally, each connection to PostgreSQL gets its own DuckDB instance–DuckDB should be appropriately configured with resource limits that match the size of the replica.

## PostgreSQL as a data lake engine

Since DuckDB has a great abstraction for Data Lakes–a unified SQL interface that works across cloud providers and file formats–we can also extend that to PostgreSQL with pg\_duckdb. This extension brings powerful capabilities to PostgreSQL: secure access to cloud storage (S3, GCP, Azure), the ability to directly query remote files in various formats (CSV, JSON, Parquet, Iceberg, Delta), and an analytics engine that serves BI tools and applications using familiar PostgreSQL SQL.

The result is 'in-database ETL'–you can now handle data transformations that traditionally required external tools directly within SQL queries.

This architecture enables something particularly powerful: joining PostgreSQL data with remote data lake files in a single query. For example, you could enrich a local customers table with user behavior data from a 10-billion-row Parquet file stored on S3–all in one SQL query.

```sql
Copy code

-- enrich customers table with event data from S3

SELECT
   date_trunc('month', c.signup_date) as signup_month,
   avg(b['page_views']) as avg_page_views,
   avg(b['session_duration']) as avg_session_duration,
   count(*) as customer_count
FROM customers c
JOIN read_parquet('s3://data-lake/user_behavior_10b_rows.parquet') b ON c.customer_id = b['customer_id']
WHERE b['last_active'] >= '2024-01-01'
GROUP BY date_trunc('month', c.signup_date)
ORDER BY signup_month;
```

## Serverless analytics power with MotherDuck

While PostgreSQL can benefit from DuckDB's analytical horsepower with pg\_duckdb, it wasn't architected to handle the spiky workloads from large analytical queries. The pg\_duckdb extension offers a MotherDuck integration that solves this by offloading demanding analytics to serverless cloud compute, allowing users to ship PostgreSQL data to MotherDuck using familiar SQL operations like `CREATE TABLE AS` statements or incremental inserts.

This hybrid approach provides several advantages. MotherDuck can leverage connections to cloud storage for faster data lake reads, and users gain flexibility in how they interact with their data—they can connect directly to MotherDuck for complex DuckDB analytics or stick with PostgreSQL for familiar operational queries.

Your analytical queries on data in MotherDuck will also be much faster than if the data is stored in regular PostgreSQL tables, because the DuckDB engine benefits greatly from the columnar storage that MotherDuck uses. Lastly, the architecture supports scaling through read replicas that automatically scale out to a fleet of Ducklings—MotherDuck compute instances—meaning your small, always-on PostgreSQL replica can instantly access massive serverless compute power when analytical workloads spike.

![Diagram showing analytics with PostgreSQL and MotherDuck.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpg_duckdb_diagram_eb1728e9d4.png&w=3840&q=75)

The tradeoff is network latency versus processing power. While storing data only in PostgreSQL minimizes data movement, replicating frequently accessed data to MotherDuck reduces the network bottleneck for analytical queries by keeping compute and storage co-located in the cloud.

## Getting started with pg\_duckdb

Ready to add DuckDB-powered analytics to your PostgreSQL workflow? Visit the [pg\_duckdb GitHub repo](https://github.com/duckdb/pg_duckdb) to get started, and check out these helpful resources along the way:

- [Pg\_duckdb Tutorial Video](https://motherduck.com/videos/124/pgduckdb-postgres-analytics-just-got-faster-with-duckdb/)
- [(Blog)PostgreSQL and Ducks: The Perfect Analytical Pairing](https://motherduck.com/blog/postgres-duckdb-options/)
- [MotherDuck Documentation](https://motherduck.com/docs/getting-started/)

### TABLE OF CONTENTS

[DuckDB speed in elephant mode](https://motherduck.com/blog/pg-duckdb-release/#duckdb-speed-in-elephant-mode)

[Analytics on PostgreSQL with ducks](https://motherduck.com/blog/pg-duckdb-release/#analytics-on-postgresql-with-ducks)

[PostgreSQL as a data lake engine](https://motherduck.com/blog/pg-duckdb-release/#postgresql-as-a-data-lake-engine)

[Serverless analytics power with MotherDuck](https://motherduck.com/blog/pg-duckdb-release/#serverless-analytics-power-with-motherduck)

[Getting started with pg\_duckdb](https://motherduck.com/blog/pg-duckdb-release/#getting-started-with-pgduckdb)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![When Spark Meets DuckLake: Tooling You Know, Simplicity You Need](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fspark_ducklake_3ae4e9cb61.png&w=3840&q=75)](https://motherduck.com/blog/spark-ducklake-getting-started/)

[2025/08/11 - Mehdi Ouazza](https://motherduck.com/blog/spark-ducklake-getting-started/)

### [When Spark Meets DuckLake: Tooling You Know, Simplicity You Need](https://motherduck.com/blog/spark-ducklake-getting-started)

Learn how to combine Apache Spark’s scale with DuckLake’s simplicity to build a lakehouse with ACID, time travel, and schema evolution

[![Why Semantic Layers Matter — and How to Build One with DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsem_picture_6d4261bdb7.png&w=3840&q=75)](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)

[2025/08/19 - Simon Späti](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)

### [Why Semantic Layers Matter — and How to Build One with DuckDB](https://motherduck.com/blog/semantic-layer-duckdb-tutorial)

Learn what a semantic layer is, why it matters, and how to build a simple one with DuckDB and Ibis using just YAML and Python

[View all](https://motherduck.com/blog/)

Authorization Response