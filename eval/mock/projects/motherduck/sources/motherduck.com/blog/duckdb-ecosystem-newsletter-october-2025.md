---
title: duckdb-ecosystem-newsletter-october-2025
content_type: event
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2025
indexed_at: '2025-11-25T19:57:02.223558'
content_hash: ce93596f836fe497
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# DuckDB Ecosystem: October 2025

2025/10/07 - 10 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

This month, we've got major updates, including DuckDB 1.4.0 LTS with database encryption and MERGE statements, impressive benchmarks showing 100x performance gains over Spark on modest hardware, and new tooling like an official Docker image and a lightweight geospatial feature server.

As a side note, we’re just a month away from [Small Data SF](https://www.smalldatasf.com/#speakers), organized by MotherDuck, with a great lineup including Joe Reis, Holden Karau, and Tristan Handy from dbt Labs!

\- [Simon](https://www.ssp.sh/)

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1741901839713.jpeg&w=3840&q=75)

### Hoyt Emerson

[Hoyt Emerson](https://www.linkedin.com/in/hoytemerson/) is a Senior Product Manager focused on Data and AI, with over a decade of experience across Fortune 25 companies and Silicon Valley startups.

He is the creator of _The Full Data Stack_ [Substack](https://thefulldatastack.substack.com/) and [YouTube channel](https://www.youtube.com/@thefulldatastack), where he explores modern data tools through hands-on videos and technical content.

Hoyt is passionate about the full analytics stack, from SQL and Python to Polars, Streamlit, and DuckDB.

Recently, he has shared deep-dive videos on [DuckDB](https://youtu.be/733cRt4sHwM?si=6d2Zjb1H5Sho32RW), [DuckLake](https://youtu.be/R_tgEBaEDf0?si=eoHJqB-8_7ny0zdf), and [MotherDuck](https://www.youtube.com/watch?v=TeKXwuYjAHs), highlighting their impact on the data ecosystem. Thanks for sharing your knowledge Hoyt!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [Docker Image for DuckDB](https://github.com/duckdb/duckdb-docker/)

**TL;DR**: The duckdb-docker repository provides a small Docker image that exposes the DuckDB CLI for interactive and non‑interactive use, supporting amd64 and arm64.

You can use this official Docker image by pulling it with docker pull duckdb/duckdb:latest or a specific tag, running interactively with docker run --rm -it -v "$(pwd):/workspace" -w /workspace duckdb/duckdb (Windows variants use %cd% or ${PWD}), and run one‑off commands like docker run --rm duckdb/duckdb duckdb --version .

Speedwise will probably be much better if you run it locally on your machine or on the server, as installation is simple due to its small footprint. But there's always a need for a Docker image, and if you had that, here it is now. The initial need might have come from a new [Linux Distro](https://github.com/basecamp/omarchy/pull/1518#issuecomment-3291643244).

### [Big Data on the Move: DuckDB on the Framework Laptop 13](https://duckdb.org/2025/09/08/duckdb-on-the-framework-laptop-13)

**TL;DR:** A 12‑core Framework Laptop 13 (AMD Ryzen AI 9 HX 370, 128 GB RAM, 8 TB NVMe) running DuckDB can load large CSVs at nearly 2 GB/s and execute TPC‑H at multi‑TB scale (SF3,000 and SF10,000) with acceptable runtimes, although thermal throttling and disk spill should be considered.

Gabor ran the DuckDB CLI installed DuckDB to measure CSV ingestion (20 GB loaded in 10.2s ≈ 1.96 GB/s). For TPC‑H he generated Parquet with tpchgen-rs and loaded ~4 TB Parquet into ~2.7 TB DuckDB storage for SF10,000 (observed disk spills up to 3.6 TB). Measured results: SF3,000 total 47.5 min (geomean 86.5 s) reduced to 30.8 min (geomean 58.2 s, 32% faster) when inserting cooling pauses; SF3,000 on battery ran 46.9 min and drained to ~30%; SF10,000 ran 4.2 h (geomean 6.6 min) and 3.8 h with cooling (14% speedup).

It shows once again that DuckDB is a viable, low‑cost platform for terabyte‑scale analytics with new powerful hardware options.

### [Announcing DuckDB 1.4.0 LTS](https://duckdb.org/2025/09/16/announcing-duckdb-140.html)

**TL;DR**: DuckDB 1.4.0 "Andium" brings database encryption with AES-256-GCM, the MERGE statement for upserts, Iceberg writes support, and significant performance improvements through k-way merge sorting and CTE materialization.

DuckDB 1.4.0 introduces several improvements, such as database encryption using industry-standard AES with 256-bit keys and GCM mode, encrypting the main database file, WAL, and temporary files via ATTACH 'encrypted.db' AS enc\_db (ENCRYPTION\_KEY 'quack\_quack'). The MERGE INTO statement now supports complex upsert operations without requiring primary keys, using custom merge conditions. For the data lake ecosystem, Iceberg writes are now supported through COPY FROM DATABASE duckdb\_db TO iceberg\_datalake, enabling bidirectional data movement between DuckDB and Iceberg tables. Performance improvements include complete rewrite of the sorting implementation using k-way merge sort with better thread scaling, and the change to materialize CTEs.

Besides that, the release establishes DuckDB's first Long Term Support (LTS) model with one year of community support.

### [A lightweight RESTful geospatial feature server based on DuckDB](https://github.com/tobilg/duckdb_featureserv)

**TL;DR**: duckdb\_featureserv provides an OGC API - Features compliant REST layer over DuckDB with duckdb-spatial, plus an optional DuckDB HTTP server for direct SQL (including CRUD), configurable via file or env vars and runnable via Docker.

Technically, the server supports standard and extended query params (limit, bbox, filter/CQL2 with spatial ops, sortby, crs, offset, properties, transform, precision, groupby) and returns JSON/GeoJSON. It relies on DuckDB Spatial for geometry processing and executes filters in DuckDB.  HTTP features include CORS, GZIP, and HTTPS.

Configuration can be supplied via TOML or environment variables.  An optional HTTP SQL endpoint is enabled via \[DuckDB\] EnableHttpServer = true. Example query: curl -X POST --header "X-API-Key: ..." -d "SELECT 'hello', version()" "http://localhost:9001/?default\_format=JSONCompact". This is especially helpful if you need a lightweight, geospatial service on DuckDB with optional mutable SQL access.

### [Honest review of MotherDuck](https://dataengineeringcentral.substack.com/p/honest-review-of-motherduck)

**TL;DR**: Daniel demonstrates the integrating MotherDuck into an Apache Airflow data pipeline to process S3 data, highlighting the seamless transition from local development to the cloud.

In his review, Daniel details building an Airflow DAG to query a 50GB CSV dataset stored in S3. He emphasizes the simplicity of shifting from a local DuckDB instance to the cloud-based MotherDuck service, noting the only significant code change is the connection string: con = duckdb.connect(f\\\"md:{MD\_DB}?motherduck\_token={MD\_TOKEN}\\\").

While not a formal benchmark, he observed that this data processing task completed in under two minutes within the Airflow pipeline. This gives you the most minimal friction required to scale a local DuckDB script to a cloud execution environment. [Code Snippet](https://github.com/danielbeach/MotherDuckwithApacheAirflow/tree/main)

### [DuckDB benchmarked against Spark](https://blog.dataexpert.io/p/duckdb-can-be-100x-faster-than-spark)

**TL;DR**: On a 16 GB RAM laptop, DuckDB consistently outperformed Spark by orders of magnitude on local Parquet scans up to ~23 GB (≈0.5B rows) using a simple count-distinct benchmark.

Matt and Zach generated seven synthetic Parquet datasets in DuckDB and benchmarked both engines by reading each file and computing COUNT(DISTINCT rand\_str) to force full-file scans. Results showed DuckDB was faster in every run, including the largest 23 GB dataset that exceeded the machine RAM.

Matt says he defaults to DuckDB for pipelines and only switches to Spark when datasets exceed ~20 GB on his 16 GB laptop. Code available at [spark vs duckdb/scratchpad.ipynb](https://github.com/mattmartin14/dream_machine/blob/main/substack/articles/2025.08.02%20-%20spark%20vs%20duckdb/scratchpad.ipynb)

### [DuckLake 0.3 with Iceberg Interoperability and Geometry Support](https://ducklake.select/2025/09/17/ducklake-03/)

**TL;DR:** DuckLake v0.3 (ducklake DuckDB extension in DuckDB v1.4.0) adds Iceberg interoperability, geometry types, MERGE/CHECKPOINT support, author commit metadata, and a per-thread output write option that reduced a 1B-row copy from ~4.5s to ~3.4s (~25% faster) in the provided benchmark.

The release enables deep and metadata-only copies between DuckLake and Iceberg via the Iceberg extension, allowing querying of previous Iceberg snapshots. SQL-level features now supported include MERGE INTO and a CHECKPOINT maintenance command (flush, expire snapshots, and compact/rewrite files), which are configurable. Guillermo and Gabor noted the focus on robustness, enabling high-bandwidth large writes, but beware small-file churn.

### [Turn Thousands of Messy JSON Files into One Parquet: DuckDB for Fast Data Warehouse Ingestion](https://www.dumky.net/posts/turn-thousands-of-messy-json-files-into-one-parquet-duckdb-for-fast-data-warehouse-ingestion/)

**TL;DR**: Using DuckDB to consolidate thousands of small, drifting JSON files into one/few Parquet artifacts with lineage, then load via connectors or query directly to reduce scans and stabilize schemas.

The core pattern is to read JSON files and transform them into Parquet format while capturing the filename for lineage. Schema drift is handled with UNION BY NAME across directories and selective extraction via json\_extract\* \+ try\_cast. Loading paths include connectors, warehouse COPY/LOAD from staged Parquet, or dbt-duckdb external sources.

Performance notes from the article are consolidation enables column pruning, predicate pushdown, and stats, often cutting execution time or credits "by half or more", staging small files to local SSD/NVMe before conversion can yield a 2–10× wall‑clock improvement versus direct S3 reads. Dumky said to retain raw JSON but serve Parquet as the hot analytical layer -> "only touch it once".

### [🔥 DuckDB in 100 Seconds - Fireship video](https://www.youtube.com/watch?v=uHm6FEb2Re4)

**TL;DR:** DuckDB earned a 100-second legendary video by Fireship.

Fireships states that it was developed in the Netherlands, written in C++, and first released in 2019. DuckDB is presented as “like SQLite, but for columnar data.” He continues that column-wise storage enables faster aggregations on high-volume time-series and similar analytical workloads than row-store engines. The engine processes data in vectorized batches in parallel and is multi-threaded by default.

There's not much news for us DuckDB users, but it's great to see our tech in big YouTube videos. Fireship praises its simplicity and capability for data wrangling, including support for JSON and HTML. He notes real-world adoption (e.g., Meta, Google, Airbnb).

### [New Query.Farm Extensions: Marisa Matching Algorithm & Textplot](https://query.farm/duckdb_extension_marisa.html)

**TL;DR**: Query.Farm released two community extensions—Marisa for space-efficient trie-based string operations and Textplot for ASCII/Unicode data visualization directly in SQL queries.

Query.Farm's Marisa extension brings MARISA (Matching Algorithm with Recursively Implemented StorAge) trie functionality to DuckDB, enabling efficient prefix searches and string lookups.

The extension provides four core functions: marisa\_trie() aggregates strings into a compact BLOB representation (e.g., 4160 bytes for 10 employee names), marisa\_lookup(trie, 'Alice') performs existence checks, marisa\_common\_prefix(trie, 'USA', 10) returns all trie strings that are prefixes of the input, and marisa\_predictive(trie, 'Me', 10) finds strings starting with a given prefix.

Meanwhile, their Textplot extension enables terminal-based visualizations with functions for progress indicators with threshold-based coloring. A simple progress bar looks like this:

\-\- Simple progress bar (50% filled)

SELECT tp\_bar(0.5);

┌──────────────────────┐

│     tp\_bar(0.5)      │

│       varchar        │

├──────────────────────┤

│ 🟥🟥🟥🟥🟥⬜⬜⬜⬜⬜ │

└──────────────────────┘

Both extensions install community extensions and are particularly useful for CLI analytics, data exploration in terminals, and embedding lightweight visualizations without external charting libraries.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Streaming Kafka Data into MotherDuck with Estuary Flow](https://luma.com/7vfyym4m?utm_source=eventspage)

**October 09 - Online : 9:00 PM PTD**

​In this session, MotherDuck & Estuary will show you how Estuary Flow bridges Kafka and MotherDuck with a simple, declarative approach to stream ingestion. You’ll see a live demo of streaming Kafka data into MotherDuck, evolving schemas on the fly, and querying fresh data in seconds.

### [Coalesce by dbt Labs](https://coalesce.getdbt.com/event/21662b38-2c17-4c10-9dd7-964fd652ab44/summary)

**October 13 - 🇺🇸 Las Vegas**

oin dbt Labs and thousands of data enthusiasts at Coalesce to rethink how the world does data. MotherDuck will be there sponsoring (booth #104)—and quackin’ our way through a breakout session you won’t want to miss

### [Simplifying the Transformation Layer](https://luma.com/7qk4df9q)

**October 14 - Online 11 AM CET**

​Join MotherDuck and Xebia to learn about the latest in architectures for the transformation layer and what companies are using in the real world.

### [Beyond BI: Building Data Apps and Customer-Facing Analytics](https://luma.com/3lw1nad1)

**October 15 - Online**

Join MotherDuck and Codecentric for a discussion all about data apps: when to build one, when not to, plus a hands-on example showing how to launch an internal data app without over-engineering by using MotherDuck.

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-october-2025/#upcoming-events)

Subscribe to DuckDB Newsletter

E-mail

Subscribe to other MotherDuck news

Submit

Subscribe

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![4 Senior Data Engineers Answer 10 Top Reddit Questions](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Foct_25_simon_blog_455f822c25.png&w=3840&q=75)](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions/)

[2025/10/30 - Simon Späti](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions/)

### [4 Senior Data Engineers Answer 10 Top Reddit Questions](https://motherduck.com/blog/data-engineers-answer-10-top-reddit-questions)

A great panel answering the most voted/commented data questions on Reddit

[![DuckDB Ecosystem: November 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_36d7966f34.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/)

[2025/11/12 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025/)

### [DuckDB Ecosystem: November 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-november-2025)

DuckDB Monthly #35: DuckDB extensions, DuckLake, DataFrame, and more!

[View all](https://motherduck.com/blog/)

Authorization Response