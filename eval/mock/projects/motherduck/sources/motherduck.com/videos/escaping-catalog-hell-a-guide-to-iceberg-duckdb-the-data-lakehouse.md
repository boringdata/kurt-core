---
title: escaping-catalog-hell-a-guide-to-iceberg-duckdb-the-data-lakehouse
content_type: tutorial
source_url: https://motherduck.com/videos/escaping-catalog-hell-a-guide-to-iceberg-duckdb-the-data-lakehouse
indexed_at: '2025-11-25T20:45:10.500358'
content_hash: 29d6c87380841f35
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Iceberg, Multi-Engine Data Stack and Catalog Hell - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Iceberg, Multi-Engine Data Stack and Catalog Hell](https://www.youtube.com/watch?v=iiZNv_xpJTg)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=iiZNv_xpJTg&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 46:27

•Live

•

MotherDuck Features

# Escaping Catalog Hell: A Guide to Iceberg, DuckDB & the Data Lakehouse

2025/06/12

Building a modern data stack often feels like a choice between two extremes. You can go "full-SaaS" with a platform like Snowflake or Databricks, which gets you moving fast but risks vendor lock-in and spiraling costs. Or, you can build it all yourself with open-source tools, giving you ultimate flexibility but often requiring months of complex infrastructure work before you can deliver a single insight.

This is what [Julien Hurault](https://www.linkedin.com/in/julienhuraultanalytics/) calls the **"cold start problem"**. "There is no middle ground," he notes in a recent conversation with MotherDuck's [Mehdi Ouazza](https://motherduck.com/authors/mehdi-ouazza/). Every data team, from startups to large enterprises, faces this tension.

So, how do you find that middle ground? Open table formats like [Apache Iceberg](https://iceberg.apache.org/) are the map, promising a future where data is decoupled from compute. But the catalog—the system that tracks the state of your tables—is the tricky terrain you must navigate.

In this article, we'll explore this terrain through the expert eyes of Julien, who has guided many companies on this journey. We'll break down the promise and the pain of the modern data stack, demystify the catalog, and walk through a hands-on tutorial to get you started with Iceberg and [DuckDB](https://duckdb.org/) in minutes, no cloud account required.

* * *

## The Promise and the Pain of the Modern Data Stack

The dream of the modern data stack is flexibility. You want to use the best tool for the job without being locked into a single vendor's ecosystem. This is where open table formats like [Apache Iceberg](https://iceberg.apache.org/), [Delta Lake](https://delta.io/), and [Hudi](https://hudi.apache.org/) come in. They allow you to store your data in a vendor-neutral format in your own object storage (like AWS S3 or Google Cloud Storage).

### The Multi-Engine Lakehouse Vision

Once your data is in an open format, you can bring different query engines to it. This "multi-engine" approach is the future of data architecture.

As Julien puts it, "People are just going to start by dumping their data in Iceberg... and then just plug a warehouse on top of it". This turns the traditional data warehouse on its head. Instead of being the single source of truth for storage and compute, it becomes just one of many specialized tools you can use.

> 🎙️ **Julien's Insight:** Think of a powerful data warehouse like a **"serverless function"**. You can spin it up to perform a compute-intensive task on your Iceberg data and then write the results back to the lakehouse. Nothing is permanently stored or locked inside the warehouse.

This model gives you incredible power:

- **Use DuckDB** 🦆 for fast, local analytical queries and development.
- **Use** [**Spark**](https://spark.apache.org/) ✨ for large-scale ETL and batch processing.
- **Use Snowflake or BigQuery** ❄️ for massive, ad-hoc interactive queries when you need the horsepower.

Your data remains in an open, accessible format, and you avoid getting locked into any single compute vendor. But there's a catch.

* * *

## The Hidden Hurdle: Understanding the Apache Iceberg Catalog

Adopting Iceberg isn't just about writing [Parquet](https://motherduck.com/learn-more/why-choose-parquet-table-file-format/) files with a specific structure. It's about managing the state of your tables—what data is in the table, what the schema looks like, and how it has changed over time. This is the job of the **catalog**.

While powerful, the catalog is also what holds many teams back from adopting Iceberg. According to Julien, the main barriers are:

1. **Poor User Experience:** The APIs and tooling can be complex, especially for developers outside the JVM ecosystem (e.g., Python and Node.js users).
2. **Table Maintenance:** Suddenly, tasks like compaction, cleaning up old snapshots, and optimizing file layouts become _your_ responsibility, not the warehouse's.
3. **The Catalog Itself:** It's another critical piece of infrastructure you have to choose, deploy, and manage. This is often the biggest source of complexity and frustration—what we call **"catalog hell."**

### The Iceberg Catalog Landscape: REST, Serverless & More

The world of Iceberg catalogs can be confusing. Here's a quick breakdown of the main options discussed:

- **Managed REST Catalogs:** These are dedicated catalog services. The most common are **AWS Glue Catalog**, **Databricks Unity Catalog**, and the open-source **Project Nessie**. They provide a central endpoint to manage table state and handle concurrent writes, but they are yet another service to pay for and manage.
- **"Serverless" Catalogs:** A new wave of services tightly integrates the catalog with the storage layer. **Amazon S3 Tables** and **Cloudflare R2 Tables** are prime examples. As Julien highlights, these are a "great innovation because they bundle the catalog _with the storage_, simplifying setup and maintenance". You don't manage a separate catalog service; it's part of your storage bucket.
- **File-Based Catalogs:** At its core, a REST catalog is often just "a fancy service to point to a metadata file," as Julien notes. This complexity is what led to simpler, file-based approaches, which are perfect for local development and getting started.

This last approach is the key to escaping catalog hell and getting your hands dirty with Iceberg and DuckDB.

* * *

## A Practical, Hands-On Approach with boring-catalog and DuckDB

To demonstrate just how simple an Iceberg setup can be, Julien created an open-source tool called [`boring-catalog`](https://github.com/boringdata/boring-catalog). It implements a lightweight, file-based catalog using a single JSON file. It's the perfect way to learn how Iceberg works without needing a cloud account or a complex distributed setup.

Let's walk through it. 🚀

### Goal: Go from zero to querying an Iceberg table with DuckDB in 5 minutes.

#### Step 1: Installation & Setup

First, install `boring-catalog` using pip.

```bash
Copy code

pip install boringcatalog
```

Next, initialize your catalog. This is similar to running `git init`.

```bash
Copy code

ice init
```

This simple command does two things:

1. Creates a `warehouse/` directory to store your Iceberg table data.
2. Creates a `.ice/index` file that points to your catalog file, which is `warehouse/catalog/catalog_boring.json`.

This `catalog_boring.json` file _is_ your catalog. It's just a simple JSON file that will keep track of your tables and point to their latest metadata files. This elegantly demonstrates Julien's point: you don't always need a complex REST service to manage state.

#### Step 2: Committing Data to an Iceberg Table

Now, let's get some sample data and commit it to a new Iceberg table.

```bash
Copy code

# Get some sample data (NYC taxi trips)
curl -L -o yellow_tripdata.parquet https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet

# Commit the Parquet file to a new Iceberg table called 'trips'
ice commit trips --source yellow_tripdata.parquet
```

That's it! You've just created a new Iceberg table and committed your first snapshot. The workflow is intentionally `git`-like. You can even view the history of your table.

```bash
Copy code

ice log trips
```

You'll see output like this, showing the complete history of operations, which enables powerful features like time-travel queries.

```yaml
Copy code

commit 5917812165563990664
  Table: ice_default.trips
  Date: 2025-07-09 19:55:00 UTC
  Operation: append
  Summary:
  added-data-files      : 1
  total-data-files      : 1
  added-records         : 20000
  total-records         : 20000
```

#### Step 3: Querying with DuckDB

Now for the fun part. How do you query this table? `boring-catalog` comes with a handy command to fire up a DuckDB shell that's pre-configured to read your Iceberg catalog.

```bash
Copy code

ice duck
```

This drops you right into a DuckDB CLI. You can now query your Iceberg table directly with SQL!

```sql
Copy code

-- The 'ice duck' command automatically creates a view for your table

USE ice_default;

SELECT passenger_count, count(*)
FROM trips
GROUP BY 1
ORDER BY 2 DESC;

+------------------+---------------+
| passenger_count  | count_star()  |
|     double       |     int64     |
+------------------+---------------+
|              1.0 |         14545 |
|              2.0 |          2997 |
|              3.0 |           883 |
|              0.0 |           585 |
|              4.0 |           424 |
|              5.0 |           335 |
|              6.0 |           221 |
|            NULL  |             7 |
|              7.0 |             2 |
|              9.0 |             1 |
+------------------+---------------+
```

You've successfully built a local, multi-engine data lakehouse. You used `boring-catalog` to manage the table format (Iceberg) and DuckDB as your query engine.

* * *

## The Bigger Picture: Iceberg vs. DuckLake

This hands-on example helps clarify the philosophical differences between Iceberg and [DuckLake](https://ducklake.select/).

The conversation between Mehdi and Julien shed light on this key distinction:

- **Iceberg's Catalog:** As we saw with `boring-catalog`, the catalog is a lightweight **pointer** to metadata files. Its primary job is to provide a central place for atomic commits, ensuring that concurrent writers don't corrupt the table. The metadata _about_ the files (like Parquet file statistics) lives in separate `metadata.json` files on disk.

- **DuckLake's Catalog:** In the DuckLake approach, the catalog isn't just a pointer; it **contains the actual metadata itself**, typically within a SQL database. This removes the need for separate metadata files on disk and gives the catalog more responsibility, which can simplify the overall architecture and user experience.


As Julien perfectly summarized, the ideal future would be a marriage of these two worlds: **"Iceberg's broad engine interoperability combined with DuckLake's simple, elegant user experience"**. That's the dream many data engineers share today.

## Conclusion: Your Next Steps

The catalog is the central nervous system of an open data lakehouse. While historically a source of complexity, a new wave of tools and managed services is making the power of Iceberg more accessible than ever. For the modern data professional, understanding how catalogs work—and how to choose the right one for the job—is a crucial skill.

- **Try it yourself:** The best way to learn is by doing. We highly encourage you to try out Julien's [`boring-catalog`](https://github.com/boringdata/boring-catalog) on your own machine.
- **Go deeper:** To learn more from Julien, check out his [**Boring Data**](https://boringdata.io/) newsletter and data stack templates.
- **Explore the DuckDB approach:** Want to dive deeper into how DuckDB and MotherDuck are innovating to solve the catalog problem? [**Get started with MotherDuck and DuckLake today**](https://motherduck.com/blog/announcing-ducklake-support-motherduck-preview/).

Happy building! 🦆

...SHOW MORE

## Related Videos

[!["Instant SQL Mode - Real Time Feedback to Make SQL Data Exploration Fly" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FG_Se_B_Sox_AW_Fg_HD_f4fddaa9ab.jpg&w=3840&q=75)](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly/)

[2025-04-23](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly/)

### [Instant SQL Mode - Real Time Feedback to Make SQL Data Exploration Fly](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly)

Hamilton Ulmer shares insights from MotherDuck's Instant SQL Mode, exploring how real-time query result previews eliminate the traditional write-run-debug cycle through client-side parsing and DuckDB-WASM caching.

SQL

Talk

MotherDuck Features

[!["DuckDB: Run dbt build with sub-second execution times" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_03_26_at_3_40_16_PM_c6e3a8096f.png&w=3840&q=75)\\
\\
24:06](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times/)

[2025-03-13](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times/)

### [DuckDB: Run dbt build with sub-second execution times](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times)

Whether you're new to DuckDB or looking to optimize your workflows, this session will provide practical insights to help you leverage its full potential.

YouTube

Data Pipelines

dbt

MotherDuck Features

[!["What's new in DuckDB & MotherDuck 🦆" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fvideo_t_r_Lb_Kmld7g_a6056e49e6.jpg&w=3840&q=75)\\
\\
0:33:54](https://motherduck.com/videos/whats-new-in-duckdb-motherduck/)

[2024-07-11](https://motherduck.com/videos/whats-new-in-duckdb-motherduck/)

### [What's new in DuckDB & MotherDuck 🦆](https://motherduck.com/videos/whats-new-in-duckdb-motherduck)

Join Mehdi Ouazza for a fun session to discuss all the new things in DuckDB and MotherDuck as of July 2024. He's flying solo this time for a special episode; he will quack but code too, so get ready!

YouTube

Quack & Code

MotherDuck Features

[View all](https://motherduck.com/videos/)

Authorization Response