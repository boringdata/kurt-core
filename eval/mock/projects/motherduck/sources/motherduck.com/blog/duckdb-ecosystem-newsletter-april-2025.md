---
title: duckdb-ecosystem-newsletter-april-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2025
indexed_at: '2025-11-25T19:57:38.106616'
content_hash: 70949221e7e5c58c
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# DuckDB Ecosystem: April 2025

2025/04/05 - 9 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

I hope you're doing well. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB, delivered straight to your inbox.

In this April issue, I gathered 10 (actually 12, I squeezed in two more related) links highlighting the updates and news from the ecosystem of DuckDB. This time, we have SQLFlow turning DuckDB into a streaming engine, a new vector search database built on DuckDB, dramatic performance boosts with local caching, the exciting new DuckDB UI, AWS S3 Tables integration, security enhancements, and more. Check out this edition below.

If you have feedback, news, or any insights, they are always welcome. 👉🏻 [duckdbnews@motherduck.com](mailto:duckdbnews@motherduck.com).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1695655515395.jpeg&w=3840&q=75)

### Caleb Fahlgren

[**Caleb Fahlgren**](https://www.linkedin.com/in/calebfahlgren/) is a Product ML Engineer at Hugging Face. In his recent [community blog post](https://huggingface.co/blog/cfahlgren1/querying-datasets-with-duckdb-ui), he walks through how the new DuckDB Local UI makes it easy to explore Hugging Face datasets locally using the hf:// protocol. Not only is the integration between DuckDB and Hugging Face datasets smooth, but DuckDB also powers dataset discovery behind the scenes at Hugging Face.

Thanks to Caleb for his thoughtful contribution to the DuckDB community!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [DuckDB for Streaming Data](https://github.com/turbolytics/sql-flow)

**TL;DR:** SQLFlow is a stream processing engine built on DuckDB and Apache Arrow, enabling users to define data pipelines using SQL for high-performance data transformations and aggregations.

SQLFlow ingests data from sources like Kafka and WebSockets, processes it using DuckDB for SQL execution, and outputs it to destinations like PostgreSQL, Kafka, or cloud storage. Key to its architecture are input sources, handlers (SQL execution via DuckDB), and output sinks. It offers a range of use cases, including streaming data transformations (basic.agg.mem.yml), stream enrichment (enrich.yml), and real-time data aggregation, as well as integration with services like [Bluesky](https://github.com/turbolytics/sql-flow/blob/main/dev/config/examples/bluesky/bluesky.kafka.raw.yml) firehose and [Iceberg](https://github.com/turbolytics/sql-flow/blob/main/dev/config/examples/kafka.mem.iceberg.yml) catalogs. Takeaway: SQLFlow allows DuckDB users to leverage SQL for defining real-time data pipelines, offering a lightweight alternative to traditional stream processing engines.

### [Building a Hybrid Vector Search Database with Arrow and DuckDB](https://medium.com/@mcgeehan/building-a-hybrid-vector-search-database-with-arrow-and-duckdb-07ebc049bc1f)

**TL;DR:** Thomas introduces [Quiver](https://github.com/TFMV/quiver), a Go-powered hybrid vector database combining HNSW (Hierarchical Navigable Small World) for fast vector search, DuckDB for SQL-based metadata filtering, and Apache Arrow for efficient data movement.

Quiver is open-source and provides full SQL support and columnar storage optimized for analytical workloads powered by DuckDB, eliminating the need for a heavyweight external database. Thomas details the implementation of hybrid search, employing pre-filtering (SQL first, vector search later) and post-filtering (vector search first, SQL later), choosing the best approach based on query selectivity.

Further, the use of Apache Arrow, integrated via Arrow Database Connectivity (ADBC), ensures zero-copy data movement between components for more efficiency. If you are interested in this topic, I also recommend my recent deep dive into [Vector Technologies for AI: Extending Your Existing Data Stack](https://motherduck.com/blog/vector-technologies-ai-data-stack/).

### [No Bandwidth? No Problem: Why We Think Local Cache is Great for DuckDB](https://medium.com/@douenergy/no-bandwidth-no-problem-why-we-think-local-cache-is-great-for-duckdb-75b2958fd7f3)

**TL;DR:** The cache\_httpfs DuckDB extension accelerates data reads from object storage by leveraging local caching, offering significant performance improvements.

The cache\_httpfs community extension addresses bandwidth costs, latency, and reliability issues when querying data from object storage. It supports in-memory, on-disk, and no-cache modes, configurable via SET cache\_httpfs\_type='noop'. This can boost user experience with a query time reduction from 100 seconds to 40 seconds using the extension. The extension leverages DuckDB's optimizations, such as parquet bloom filters, to minimize data transfer from object storage. It supports parallel reads and provides profiling metrics while maintaining compatibility with DuckDB's httpfs. The extension extends its support to Hugging Face (hf://), Amazon S3 (S3://), and Cloudflare R2 (R2://).

Practical takeaway: Using cache\_httpfs allows users to reduce S3 costs and accelerate their DuckDB queries with minimal configuration changes. Check out the GitHub repo at [dentiny/duck-read-cache-fs](https://github.com/dentiny/duck-read-cache-fs).

### [DuckDB Local UI](https://duckdb.org/2025/03/12/duckdb-ui.html)

**TL;DR:** The recently announced DuckDB UI offers a user-friendly interface for local DuckDB instances, enhancing productivity with features like interactive notebooks and column exploration, making it easier to manage and analyze data.

You might have heard of the new DuckDB UI; a notebook-style ui extension, all available locally. This has been created with great collaboration between MotherDuck and the DuckDB Labs team. Starting with DuckDB v1.2.1, users can launch the UI via the command line using duckdb -ui or through a SQL command `CALL start_ui()`;. The UI features come with syntax highlights for SQL scripting and autocomplete. It also includes a column explorer for result analysis and supports local query execution, with optional MotherDuck integration for cloud data warehousing. The UI stores notebooks in a DuckDB database (ui.db) within the .duckdb directory. The UI extension embeds a localhost HTTP server for the browser application and uses server-sent events for real-time updates, ensuring a low-latency experience. Also, check out the [How-to YT-Video](https://www.youtube.com/watch?v=vCbO8CynO88). PS: The duckdb-ui is open-source on [GitHub](https://github.com/duckdb/duckdb-ui).

### [DuckDB: Crunching Data Anywhere, From Laptops to Servers](https://youtu.be/9Rdwh0rNaf0?si=4BOX6wMSpHvKw0on)

**TL;DR:** [Top-rated](https://www.techtalksweekly.io/p/100-most-watched-software-engineering) talk at FOSDEM 2024 showcased performance on large datasets and its potential to reduce cloud costs.

Gábor demonstrated in the 35 minutes DuckDB's ability to load 15 GB of CSV data in 11 seconds and execute complex queries in milliseconds on a standard laptop. He explains column-oriented storage, vectorized execution, and using zone maps for indexing. Gábor also highlighted DuckDB's portability, achieved through its C++11 codebase and minimal external dependencies, running on web browsers via WebAssembly.

### [Preview: Amazon S3 Tables in DuckDB](https://duckdb.org/2025/03/14/preview-amazon-s3-tables.html)

**TL;DR:** DuckDB now supports Apache Iceberg REST Catalogs, enabling seamless connections to [Amazon S3 Tables](https://aws.amazon.com/s3/features/tables/) and [SageMaker Lakehouse](https://aws.amazon.com/sagemaker/lakehouse/).

The new preview feature in the Iceberg extension allows attaching to Iceberg REST catalogs using the `ATTACH` command. This feature requires installing the "bleeding edge" versions of the extensions from the `core_nightly` repository. AWS credentials can be configured using the Secrets Manager with either `credential_chain` or manual key/secret/region specification. Connections to S3 Tables are established via the S3 Tables ARN value, e.g., `ATTACH 'arn:aws:s3tables:us-east-1:111122223333:bucket/bucket_name' AS s3_tables_db (TYPE iceberg, ENDPOINT_TYPE s3_tables);`.

An alternative connection method uses the Amazon SageMaker Lakehouse (AWS Glue Data Catalog) Iceberg REST Catalog endpoint: `ATTACH 'account_id:s3tablescatalog/namespace_name' AS (TYPE iceberg, ENDPOINT_TYPE glue);.` The extension also supports Iceberg's schema evolution, allowing users to follow changes in the table's schema.

### [Securing DuckDB, Improving Startup Time, and Working Offline](https://blog.colinbreck.com/securing-duckdb-improving-startup-time-and-working-offline/)

**TL;DR:** Statically compiling DuckDB enhances security, reduces startup time, and supports offline environments by embedding necessary extensions directly into the binary.

This article addresses challenges with loading extensions dynamically, especially without the internet, which can be challenging. By statically compiling DuckDB, as outlined by Colin, developers can include essential extensions, such as icu, parquet, and sqlite\_scanner, directly into the DuckDB binary, eliminating the need for runtime downloads. This is achieved using the build command: `DISABLE_EXTENSION_LOAD=1 CORE_EXTENSIONS='icu;parquet;sqlite_scanner' GEN=ninja make`. This approach ensures that extensions are loaded instantly, bypassing the typical delays seen with dynamic loading. Furthermore, the use of the `DISABLE_EXTENSION_LOAD` flag prevents the installation of unauthorized extensions.

### [DuckDB Tricks - Renaming fields in a SELECT \* across tables](https://rmoff.net/2025/02/27/duckdb-tricks-renaming-fields-in-a-select-across-tables/)

TL;DR: Quick tricks demonstrating how to rename fields in a `SELECT *` query across multiple tables in DuckDB, resolving ambiguity when identical field names exist.

Robin addresses the challenge of distinguishing fields from different tables after a JOIN operation, where a simple `SELECT *` can lead to unclear provenance. He explores using the `COLUMNS` expression in DuckDB to prefix column names, effectively aliasing them based on their source table. For example, `describe select columns(t1.*) as "t1_\0", columns(t2.*) as "t2_\0" from t1 inner join t2 on t1.X = t2.X;` prefixes the columns from tables t1 and t2 with t1\_ and t2\_, respectively. Takeaway: A handy productivity boost when working with complex joins that prevents the tedious task of manually aliasing each column.

### [Yazi plugin that uses DuckDB to preview data files](https://github.com/wylie102/duckdb.yazi)

**TL;DR:** duckdb.yazi is a [Yazi](https://github.com/sxyazi/yazi) plugin leveraging DuckDB for rapid data file preview and summarization, enhancing file exploration within the Yazi file manager in the terminal.

For example, with duckdb.yazi plugin, you can instant preview .csv, .json, .parquet, and .tsv files directly within the Yazi file manager. Yazi, in case you haven't heard, is a Ranger alternative, a fast terminal file manager written in Rust based on async I/O. It allows us to show images and now also data set files that we can explore immediately.

### [Mastering DuckDB When You’re Used to Pandas or Polars](https://labs.quansight.org/blog/duckdb-when-used-to-frames)

**TL;DR:** The article demonstrates how to perform common dataframe operations in DuckDB using SQL, offering a robust and standardized alternative to dataframe APIs.

Marco showcases translating pandas/Polars operations to DuckDB SQL, focusing on window functions for tasks like centering data `(a - MEAN(a) OVER () AS a_centered)`or resampling time series data by implementing date truncation and interval arithmetic `(DATE_TRUNC('week', date - INTERVAL 2 DAYS) + INTERVAL 2 DAYS AS week_start)`.  He also briefly touches on Python API alternatives like SQLFrame, DuckDB's Relational API, Narwhals, and Ibis, emphasizing their capabilities and limitations. Another related article that explores [DuckDB over Pandas/Polars](https://pgrs.net/2024/11/01/duckdb-over-pandas-polars/).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Practical Uses for AI in Your Data Workflows](https://lu.ma/gmsg4lcl)

**Tuesday, April 09 10:30 EST - Online**

​Join us for a live discussion where professionals from across the data landscape share how they're using AI in their everyday work.

​In this practical session, you'll learn:

- ​How Mehdi shortens his data engineering test-deploy cycles using MCP feedback loops

- ​Archie's Cursor configurations that boost productivity in data app development

- ​How Nate applies LLMs to SQL for smarter CRM data cleaning in analytics


### [Hold on, where's my context...?](https://www.meetup.com/pydata-nl/events/307025252/)

**Wednesday, April 16 - In-person \[NL - Amsterdam\]**

Much of AI-assisted tooling depends significantly on obtaining the appropriate context for the specific task. But how exactly do these AI tools retrieve and utilize this context? And how can you, as a user, effectively provide and work with this context? That's exactly what I'll be talking about

### [\[Data Council Workshop\] More than a vibe: AI-Driven SQL that actually works](https://www.datacouncil.ai/bay-2025)

**Tuesday, April 22 - In-person \[US - Oakland\]**

More than a vibe: AI-Driven SQL that actually works In this hands-on workshop, we will demonstrate how AI can empower you to "vibe code"—using AI to write accurate SQL, enabled only by the magic of MotherDuck & DuckDB

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-april-2025/#upcoming-events)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Prompting? That’s so 2024. Welcome to Quack-to-SQL.](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fquacktosql_blog_2cff2b4afe.png&w=3840&q=75)](https://motherduck.com/blog/quacktosql/)

[2025/04/01 - MotherDuck team](https://motherduck.com/blog/quacktosql/)

### [Prompting? That’s so 2024. Welcome to Quack-to-SQL.](https://motherduck.com/blog/quacktosql)

Quack to SQL — our first AI model that understands duck sounds and translates them into queries.

[![Simplifying IoT Analytics with MotherDuck](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumb_iot_693b6b1563.png&w=3840&q=75)](https://motherduck.com/blog/simplifying-iot-analytics-motherduck/)

[2025/04/03 - Faraz Hameed](https://motherduck.com/blog/simplifying-iot-analytics-motherduck/)

### [Simplifying IoT Analytics with MotherDuck](https://motherduck.com/blog/simplifying-iot-analytics-motherduck)

Exploring the sweet spot between simplicity and capability in data systems, one IoT hackathon at a time.

[View all](https://motherduck.com/blog/)

Authorization Response