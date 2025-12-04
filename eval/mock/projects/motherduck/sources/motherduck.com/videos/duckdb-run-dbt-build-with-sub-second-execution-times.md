---
title: duckdb-run-dbt-build-with-sub-second-execution-times
content_type: tutorial
source_url: https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times
indexed_at: '2025-11-25T20:44:21.929889'
content_hash: 9b4f2f73d41459ca
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

DuckDB: Run dbt build with sub-second execution times - YouTube

[Photo image of Hiflylabs](https://www.youtube.com/channel/UCYY3oUYe_V4ohlJAsXtmeNw?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

Hiflylabs

123 subscribers

[DuckDB: Run dbt build with sub-second execution times](https://www.youtube.com/watch?v=YoBLz1gjz4w)

Hiflylabs

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

[Watch on](https://www.youtube.com/watch?v=YoBLz1gjz4w&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 24:07

•Live

•

YouTubeData PipelinesdbtMotherDuck Features

# DuckDB: Run dbt build with sub-second execution times

2025/03/13

_This article is based on a tech talk by [Gabor Szarnyas](https://szarnyasg.org/), Developer Relations Advocate at [DuckDB Labs](https://duckdblabs.com/)._

## The Agony of a Slow Data Pipeline

I want to tell you a story. A few years ago, I inherited a project that involved generating large graph datasets. The original pipeline was built on Hadoop. It was slow and incredibly difficult to work with. We migrated it to Spark, hoping for an improvement. While it was a step up, it was still complex and, more painfully, expensive. We were spending **tens of thousands of euros** just running Spark jobs to generate this data \[13:51\].

The pipeline was so cumbersome that we decided to pre-generate all possible variations of the data. This led to a combinatorial explosion of files, growing to tens of terabytes that we had to store on archival tape. If you wanted to use the data, you had to request it, wait for it to be retrieved from tape, and then download it. As I said to my team, "this is obviously no way to live" \[13:58\].

This experience set me on a path to find a better way. What if we could take that massive, expensive cloud pipeline and run it on a laptop? What if we could do it in under a second? This is the story of how DuckDB and `dbt-core` make that possible. To see how this leap is possible, we first need to understand what makes DuckDB's architecture so different.

## What Makes DuckDB Different? The "In-Process" Revolution

When developers first encounter DuckDB, the immediate question is: what makes it different from other databases like PostgreSQL or Snowflake? The answer lies in its architecture. DuckDB is an **in-process** OLAP database.

Traditional databases use a client-server model. You have a database server running somewhere—on-prem or in the cloud—and your application connects to it over a network. This model works, but it has inherent friction. There is the operational overhead of setting up and managing a server, the hassle of configuring credentials, and the network itself, which is often the biggest bottleneck. Fetching a billion-row table from a remote server will always be slow and expensive \[01:54\].

DuckDB eliminates this entirely by running directly inside your application. There's no server to manage, making it a _truly_ serverless architecture—unlike cloud "serverless" options where a server is still running somewhere \[02:21\]. You just `import duckdb` in Python, and you have a full-powered analytical database at your fingertips.

We were heavily inspired by SQLite, which proved the power of a single-file, embedded database. We like to think of DuckDB's place in the ecosystem like this:

> "DuckDB has the form factor of SQLite... but it has the workload style of Snowflake." \[03:03\]

It gives you the simplicity and portability of an embedded library with the analytical power of a modern cloud data warehouse.

## How DuckDB Achieves Sub-Second Speed

How can a library running on a laptop outperform a distributed cluster for certain workloads? The magic is in three core design principles.

#### 1\. Columnar Storage and Compression

Unlike row-based databases (like SQLite or Postgres) that store all values for a given row together, DuckDB stores all values for a given _column_ together. This is a game-changer for analytics.

Imagine a table of railway data sorted by date \[03:47\]. In a columnar format, all the `date` values are contiguous on disk. If they are sorted, we can use simple Delta encoding to compress the entire column down to a starting value and a series of tiny integers \[04:03\]. If a `delay` column contains many zeros because the trains were on time, we can compress that entire block into a single constant value \[04:18\]. This leads to massive reductions in data size and I/O.

#### 2\. Vectorized Execution

When processing data, you could go "tuple-at-a-time," processing one row after another. This is slow and doesn't use modern CPUs efficiently \[04:38\]. The other extreme is "column-at-a-time," where you load an entire column into memory. This is why Pandas can famously run out of memory and crash \[04:58\].

DuckDB uses a vectorized execution model, which is a powerful middle ground. We process data in "vectors"—chunks of 2048 values at a time \[05:13\]. These chunks are small enough to fit comfortably within a CPU's L1 cache, the fastest memory available \[05:51\]. By operating on these cache-sized chunks, DuckDB avoids the main memory bottleneck and achieves incredible processing speed. Modern compilers can even auto-vectorize this code into SIMD (Single Instruction, Multiple Data) instructions, squeezing every drop of performance out of the hardware.

#### 3\. Lightweight "Pruning" Indexes

You might think that for fast queries, you need to add lots of indexes. For transactional systems, that's true. But for analytical workloads, heavy indexes can slow down data loading and updates without providing much benefit \[08:22\].

Instead, DuckDB uses lightweight metadata stored for each data block. For every column in every block, we store the minimum and maximum value in what's called a "zone map" \[08:51\]. When you run a query like `WHERE date BETWEEN '2024-06-01' AND '2024-08-31'`, DuckDB first checks these zone maps. It can instantly determine which data blocks _cannot possibly_ contain matching data and skips reading them entirely. This "pruning" dramatically reduces the amount of data we need to scan, and it works not just on DuckDB's native files but even on remote Parquet files over S3 \[10:19\].

## Hands-On: Migrating a Spark Pipeline to `dbt-duckdb`

Let's go back to my slow, expensive Spark pipeline. Here’s how we can replace it with a simple, elegant `dbt-duckdb` project that runs in under a second.

#### Step 1: Prepare and Optimize Your Source Data

My original problem started with large, unoptimized CSV files \[14:55\]. While Parquet is the standard for columnar analytics, we can optimize even further. I used DuckDB to convert the raw CSVs into highly compressed Parquet files using the ZSTD compression codec, which resulted in a 4x file size reduction over the original compressed CSVs.

You can do this with a simple `COPY` command in DuckDB:

```sql
Copy code

-- Gabor's optimization technique

COPY person TO 'person.csv'; -- 13MB

COPY person TO 'person-v1.parquet' (PARQUET_VERSION v1); -- 4.4MB

COPY person TO 'person-v2.parquet' (PARQUET_VERSION v2); -- 3.6MB

COPY person TO 'person-v2-zstd.parquet' (PARQUET_VERSION v2, COMPRESSION 'ZSTD'); -- 2.6MB
```

This single command reads your source data and writes it out to a new, highly optimized Parquet file.

#### Step 2: Build the dbt Model

Now, we set up our dbt project. The `dbt_project.yml` is straightforward; you just need to specify `dbt-duckdb` as your adapter.

The real power comes from the model itself. Instead of loading data into a database and then writing it out, we can use `materialized='external'` \[15:40\]. This tells DuckDB to execute the transformation and write the result directly to a file (like a CSV or another Parquet file) without ever storing it in the main database file.

Here's a simplified version of my dbt model that reads the optimized Parquet file and generates one of the required CSV layouts:

Input model:

```sql
Copy code

FROM 'input/person.parquet'
```

Output model:

```sql
Copy code

{{
  config(
    materialized='external',
    location='person-project-fk.csv'
  )
}}
SELECT
  creationDate, id, firstName, lastName, gender, birthday, locationIP, browserUsed
  -- some transformations here
FROM {{ ref('person_merged_fk') }}
```

#### Step 3: Run and Debug

With the model in place, you simply run:

```bash
Copy code

dbt build
```

The result? The entire pipeline, which used to take ages and cost a fortune on [Spark](https://spark.apache.org/), now completes in **less than half a second** on my laptop \[16:19\].

**Pro-Tip for Debugging:**
As I was building this, I discovered a fantastic debugging trick. `dbt-duckdb` creates a `dev.duckdb` file in your project directory during a run. You can connect to this file directly with the new [DuckDB UI](https://duckdb.org/docs/guides/ui/):

```bash
Copy code

duckdb dev.duckdb -c ".ui"
```

> "You can peek into the import and the export tables and just troubleshoot your queries, which is again much nicer than working with Spark." \[16:38\]

This local-first approach is incredibly powerful, but you might be wondering: what happens when I need to collaborate with a team or work with larger cloud datasets? This is where DuckDB's ecosystem comes into play.

## From Local Core to Cloud Scale: The Broader Ecosystem

DuckDB is a fully open-source project with a permissive MIT license. To guarantee it stays that way forever, we've moved the intellectual property into the non-profit DuckDB Foundation in the Netherlands \[17:43\]. This ensures the core project will always remain free and open, addressing a common concern in today's database landscape.

The core development happens at DuckDB Labs, a revenue-funded company (no VC!) that provides support and consulting. But what happens when your local project needs to scale? What if you need to collaborate with a team?

This is where our partner, **MotherDuck**, comes in.

MotherDuck takes the powerful local core of DuckDB and intelligently builds back the most useful components of the client-server model: collaboration, cloud storage, and easy data sharing \[18:47\]. It offers a serverless data warehouse based on DuckDB, but with a unique twist: **[hybrid query execution](https://motherduck.com/blog/announcing-motherduck-duckdb-in-the-cloud/)** \[18:51\].

Imagine you have sensitive PII data on your laptop that can't leave your machine, but you need to join it with a large public dataset in the cloud. MotherDuck allows you to write a single query where one part executes locally on your sensitive data, and the other part executes in the cloud, with the results seamlessly combined. It's the best of both worlds.

## Conclusion: A New Default for Your Data Stack

By pairing the lightning-fast, in-process power of DuckDB with the robust framework of dbt, we've solved the problems of speed, cost, and complexity for local data transformation. That monstrous pipeline that once cost tens of thousands of euros on Spark and lived on tape archives now runs on a laptop in the blink of an eye.

DuckDB is pushing the boundaries of what's possible on a single machine, making it the new default for interactive analysis and local development pipelines.

**Ready to try it yourself?**

1. **Get started:** Install `dbt-duckdb` and run through the tutorial.
2. **Explore:** Check out the official [DuckDB documentation](https://duckdb.org/docs/introduction) and the new [DuckDB UI](https://duckdb.org/docs/guides/ui/).
3. **Scale to the cloud:** See how you can take your local workflows to the next level with [MotherDuck](https://motherduck.com/).

...SHOW MORE

## Related Videos

[!["Escaping Catalog Hell: A Guide to Iceberg, DuckDB & the Data Lakehouse" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ficeberg_video_thumbnail_adfdabe3d6.jpg&w=3840&q=75)\\
\\
46:26](https://motherduck.com/videos/escaping-catalog-hell-a-guide-to-iceberg-duckdb-the-data-lakehouse/)

[2025-06-12](https://motherduck.com/videos/escaping-catalog-hell-a-guide-to-iceberg-duckdb-the-data-lakehouse/)

### [Escaping Catalog Hell: A Guide to Iceberg, DuckDB & the Data Lakehouse](https://motherduck.com/videos/escaping-catalog-hell-a-guide-to-iceberg-duckdb-the-data-lakehouse)

Building a data stack means choosing between easy SaaS and complex open-source. Apache Iceberg is a middle ground, but its catalog is a hurdle. New tools now simplify using Iceberg with DuckDB to create a flexible, local data lakehouse.

MotherDuck Features

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