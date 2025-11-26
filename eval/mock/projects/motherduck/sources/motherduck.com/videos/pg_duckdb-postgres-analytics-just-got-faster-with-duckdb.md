---
title: pg_duckdb-postgres-analytics-just-got-faster-with-duckdb
content_type: tutorial
source_url: https://motherduck.com/videos/pg_duckdb-postgres-analytics-just-got-faster-with-duckdb
indexed_at: '2025-11-25T20:43:59.913529'
content_hash: b50a4fd2e72bc7ff
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

pg\_duckdb: Postgres analytics just got faster with DuckDB - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[pg\_duckdb: Postgres analytics just got faster with DuckDB](https://www.youtube.com/watch?v=j_83wjKiNyM)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

More videos

## More videos

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=j_83wjKiNyM&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 14:19

•Live

•

YouTubeIngestionSQLEcosystem

# pg\_duckdb: Postgres analytics just got faster with DuckDB

2024/10/25

PostgreSQL is on a roll. It was named [DBMS of the Year in 2023](https://db-engines.com/en/blog_post/101) and continues to be the [most popular database among developers](https://survey.stackoverflow.co/2023/#most-popular-technologies-database), according to the 2024 Stack Overflow survey. It's robust, reliable, and fantastic for transactional workloads (OLTP)—the bread and butter of most applications.

Many of us start our analytics journey right inside Postgres. Our application data is already there, so it's the easiest place to start asking questions. You might want to know, "How much revenue did we generate in a specific country last quarter?" or, "How many of our customers have names that rhyme with 'duck'?"

But as you ask more complex questions across larger datasets, you inevitably hit a wall. Postgres, a row-oriented database optimized for transactions, can become painfully slow for these analytical (OLAP) queries. The common solution involves setting up a separate data warehouse and a complex ETL pipeline to move data, which adds overhead and delays insights.

This is where DuckDB shines. As a fast, open-source, in-process OLAP database, it’s built from the ground up for analytics. Its popularity is growing exponentially for good reason.

So, here's the central question: **What if you could get the analytical power of DuckDB without ever leaving your favorite PostgreSQL client?**

Meet [`pg_duckdb`](https://github.com/hydradatabase/pg_duckdb), a new PostgreSQL extension that integrates DuckDB’s analytical engine directly into Postgres. It's an open-source project born from a partnership between Hydra and MotherDuck, designed to bring the best of both worlds together.

Today, you can. Let's get your `psql` client warmed up.

## Part 1: Accelerate Local Analytics by 500x

Instead of moving your data, `pg_duckdb` brings the query engine to your data, giving you a massive performance boost right where you work.

### Hands-On Demo: The 500x Performance Gain

Let's see it in action. The easiest way to get started is with the official Docker image, which comes with everything pre-configured.

```bash
Copy code

# Run the container with a permissive password setting for this demo
# In production, you should manage secrets properly!
docker run -d --name pgduckdb -e POSTGRES_HOST_AUTH_METHOD=trust ghcr.io/hydradatabase/pg_duckdb:main
```

Once the container is running, you can connect directly with `psql`:

```bash
Copy code

docker exec -it pgduckdb psql -U postgres
```

For this demo, we've pre-loaded a 1GB TPC-DS dataset, a standard benchmark for analytical systems. First, let's run a complex analytical query using the native PostgreSQL engine. We'll use `\timing` to measure how long it takes.

```sql
Copy code

-- psql
\timing
-- TPC-DS Query 1
SELECT
    c.c_customer_id AS customer_id,
    c.c_first_name AS customer_first_name,
    c.c_last_name AS customer_last_name,
    -- ... (rest of the complex query)
FROM
    customer c,
    customer_address ca,
    customer_demographics cd
WHERE
    ca.ca_city = 'Hopewell'
    -- ... (more joins and conditions)
GROUP BY
    c.c_customer_id,
    c.c_first_name,
    c.c_last_name;
```

Running this query on our instance took **1 minute and 29 seconds**.

```css
Copy code

Time: 89000.123 ms (01:29.000)
```

Now, let's unleash the duck. With `pg_duckdb`, all we have to do is enable the DuckDB engine with a simple `SET` command and run the _exact same query_.

```sql
Copy code

-- Enable the DuckDB engine for this session
SET pg_duckdb.enable = true;

-- Run the exact same TPC-DS query again
SELECT
    c.c_customer_id AS customer_id,
    -- ... (same query as before)
```

The result? **137 milliseconds.**

```css
Copy code

Time: 137.000 ms
```

That's not a typo. We went from nearly a minute and a half to just over a tenth of a second—a **~500x speedup**. This is the power of DuckDB's columnar engine, which is purpose-built for analytical queries, reading only the data it needs from each column. This incredible boost is achieved with zero changes to how your data is stored; it's still a regular PostgreSQL table, but you're swapping in a more efficient engine for the job.

## Part 2: Turn Postgres into a Data Lake Gateway

The power of `pg_duckdb` goes far beyond just speeding up queries on local tables. It brings the entire DuckDB extension ecosystem into PostgreSQL, turning your database into a true data hub. This allows you to query Parquet files on S3, read from Apache Iceberg tables, and more, all from within `psql`.

For instance, you can query Parquet files directly from your data lake. DuckDB's `read_parquet()` function works seamlessly, as shown in this query that reads a public dataset from S3 to find top TV shows.

```sql
Copy code

-- Remember to keep pg_duckdb.enable = true;
SELECT "Title", "Days In Top 10"
FROM read_parquet('s3://us-west-2.opendata.source.coop/netflix/daily_top_10/day=*/country_name=United States/*.parquet')
WHERE "Days In Top 10" > 200
ORDER BY "Days In Top 10" DESC;
```

You can even connect to modern table formats like Apache Iceberg by installing the necessary DuckDB extension on the fly.

```sql
Copy code

-- Install the Iceberg extension
SELECT duckdb_install('iceberg');
-- Load the extension for the current session
SELECT duckdb_load('iceberg');

-- Query an Iceberg table stored on S3
SELECT *
FROM iceberg_scan('s3://my-iceberg-bucket/warehouse/db/table')
LIMIT 10;
```

It's also a two-way street. You can use `pg_duckdb` to export data from PostgreSQL back to your data lake. The standard `COPY` command, when used with the DuckDB engine, can write to Parquet on S3.

```sql
Copy code

-- Export a Postgres table to Parquet on S3
COPY (SELECT * FROM my_postgres_table)
TO 's3://my-backup-bucket/my_table.parquet'
WITH (FORMAT 'parquet');
```

This opens up powerful new workflows, like backing up large tables, exporting data for your data team, or importing valuable datasets from the lake directly into Postgres to support your applications.

## Part 3: Scale Analytics in the Cloud with MotherDuck

Running large analytical queries, even with DuckDB's speed, can still consume significant CPU and memory. On a production PostgreSQL instance that's also handling application transactions, this can create resource contention that slows down your application.

This is where MotherDuck comes in. MotherDuck is a serverless analytics platform powered by DuckDB. With `pg_duckdb`, you can seamlessly offload heavy analytical workloads to MotherDuck's cloud compute, protecting your production database without ever leaving your Postgres environment.

### Connecting Postgres to MotherDuck

Connecting is simple. First, [sign up for a free MotherDuck account](https://motherduck.com/) and get a service token from the UI.

Next, you need to add this token to your `postgresql.conf` file.

```ini
Copy code

# postgresql.conf
# Add this line with your token
motherduck.token = 'md_my_super_secret_token'
```

After adding the token, restart your PostgreSQL instance.

> **Security Best Practice:** Hardcoding secrets is not ideal. For a more secure setup, `pg_duckdb` also supports reading the token from an environment variable. You can set `motherduck_token` in your environment and use this line in `postgresql.conf` instead:
> `motherduck.token = '${motherduck_token}'`

### Hybrid Queries: The Best of Both Worlds

Once connected, you can query MotherDuck directly from `psql`. MotherDuck includes a shared database, `sample_data`, which you can query immediately. Let's count the mentions of "DuckDB" in Hacker News titles from 2022.

```sql
Copy code

-- This query runs on MotherDuck's cloud infrastructure
SELECT
    date_trunc('month', "timestamp") AS month,
    count(*) AS mentions
FROM sample_data.hacker_news.stories_2022
WHERE
    lower(title) LIKE '%duckdb%'
GROUP BY 1
ORDER BY 1;
```

The true power lies in moving data effortlessly between your local Postgres instance and MotherDuck.

**1\. Pulling analytical results from MotherDuck into a local PostgreSQL table:**

```sql
Copy code

-- Create a local Postgres table from a MotherDuck query result
CREATE TABLE local_duckdb_mentions AS
SELECT
    date_trunc('month', "timestamp") AS month,
    count(*) AS mentions
FROM sample_data.hacker_news.stories_2022
WHERE
    lower(title) LIKE '%duckdb%'
GROUP BY 1;
```

**2\. Pushing a local PostgreSQL table up to MotherDuck:**

```sql
Copy code

-- Create a table in MotherDuck from a local Postgres table
CREATE TABLE my_motherduck_backup.public.customer_archive
USING duckdb AS
SELECT * FROM public.customer;
```

This seamless, bi-directional data movement gives you ultimate flexibility, all without leaving the comfort of your `psql` prompt.

## Conclusion: The Best of Both Worlds

With `pg_duckdb`, you truly get the power of the duck in the elephant's hands. You can accelerate local analytics by orders of magnitude without changing your data storage, query your data lake (S3, Iceberg) directly from your operational database, and seamlessly scale your analytics by offloading heavy work to MotherDuck's serverless platform.

`pg_duckdb` is currently in Beta, and we're excited about what comes next. The success of DuckDB is all about simplicity, and we're thrilled to bring that simplicity directly to PostgreSQL users in their existing database.

### Get Started Today

- **Try it now:** The fastest way to start is with the [Docker container](https://github.com/hydradatabase/pg_duckdb).
- **Check out the code:** The project is open source on [GitHub](https://github.com/hydradatabase/pg_duckdb).
- **Share your feedback:** We're actively developing the roadmap. Please open an issue with feature requests or feedback!

In the meantime, keep quacking and keep coding.

...SHOW MORE

## Related Videos

[!["What can Postgres learn from DuckDB? (PGConf.dev 2025)" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_06_13_at_3_52_19_PM_470b0f71b1.png&w=3840&q=75)\\
\\
20:44](https://motherduck.com/videos/what-can-postgres-learn-from-duckdb-pgconfdev-2025/)

[2025-06-13](https://motherduck.com/videos/what-can-postgres-learn-from-duckdb-pgconfdev-2025/)

### [What can Postgres learn from DuckDB? (PGConf.dev 2025)](https://motherduck.com/videos/what-can-postgres-learn-from-duckdb-pgconfdev-2025)

DuckDB an open source SQL analytics engine that is quickly growing in popularity. This begs the question: What can Postgres learn from DuckDB?

YouTube

Ecosystem

Talk

[!["Instant SQL Mode - Real Time Feedback to Make SQL Data Exploration Fly" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FG_Se_B_Sox_AW_Fg_HD_f4fddaa9ab.jpg&w=3840&q=75)](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly/)

[2025-04-23](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly/)

### [Instant SQL Mode - Real Time Feedback to Make SQL Data Exploration Fly](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly)

Hamilton Ulmer shares insights from MotherDuck's Instant SQL Mode, exploring how real-time query result previews eliminate the traditional write-run-debug cycle through client-side parsing and DuckDB-WASM caching.

SQL

Talk

MotherDuck Features

[!["Using SQL in Your Data Lake with DuckDB, Iceberg, dbt, and MotherDuck" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_06_12_at_8_43_42_PM_24441d4ac8.png&w=3840&q=75)\\
\\
24:42](https://motherduck.com/videos/using-sql-in-your-data-lake-with-duckdb-iceberg-dbt-and-motherduck/)

[2025-01-17](https://motherduck.com/videos/using-sql-in-your-data-lake-with-duckdb-iceberg-dbt-and-motherduck/)

### [Using SQL in Your Data Lake with DuckDB, Iceberg, dbt, and MotherDuck](https://motherduck.com/videos/using-sql-in-your-data-lake-with-duckdb-iceberg-dbt-and-motherduck)

In this talk at our MotherDuck Seattle meetup, Jacob, developer advocate at MotherDuck, talked about why we should use more SQL and go hands-on with some practical examples of how to read from Iceberg using dbt, DuckDB, and MotherDuck.

dbt

Meetup

SQL

[View all](https://motherduck.com/videos/)

Authorization Response