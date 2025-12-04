---
title: duckdb-ecosystem-newsletter-july-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2025
indexed_at: '2025-11-25T19:59:09.992955'
content_hash: c0e27172a0172096
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# This Month in the DuckDB Ecosystem: July 2025

2025/07/08 - 7 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

I hope you're doing well. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB, delivered straight to your inbox.

In this July issue, I gathered 9 (+2 DuckLake) links highlighting updates and news from DuckDB's ecosystem. The highlight this time is the seamless Kafka integration with Tributary and YamlQL, which enables querying your YAML files with SQL, making it convenient for long declarative data stacks. Additionally, we explore Foursquare's SQLRooms framework for browser-based data applications and various integrations with PostgreSQL, AWS SageMaker, and other enterprise tools that continue to expand DuckDB's reach across the data ecosystem.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1736993697340.jpeg&w=3840&q=75)

### Rusty Conover

[**Rusty Conover**](https://www.linkedin.com/in/rusty-conover/) is an experienced software executive and engineer with a deep background in distributed systems, databases, and real-time data processing. At DuckCon 2025, he presented _“ [Airport for DuckDB: Letting DuckDB Take Apache Arrow Flights,](https://www.youtube.com/watch?v=-AfgEiE2kaI&list=PLzIMXBizEZjggaDzjPP542En2R5SV0WiZ&index=2)”_ exploring how to connect DuckDB to Apache Arrow Flight for high-performance data transfer.

He also recently released [**Tributary**](https://duckdb.org/community_extensions/extensions/tributary.html), a DuckDB community extension built at **Query.Farm** that enables real-time SQL access to Kafka streams—making it possible to query Kafka topics directly in DuckDB without external pipelines.

Rusty is focused on practical solutions that simplify complex systems, and on building strong engineering teams that deliver meaningful tools for developers.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [YamlQL: Query your YAML files with SQL and Natural Language](https://github.com/AKSarav/YamlQL)

**TL;DR:** YamlQL is a new tool that transforms YAML files into queryable relational databases using DuckDB, allowing users to run SQL queries against complex YAML structures.

YamlQL converts YAML structures into relational schemas by flattening nested objects with underscore separators, transforming lists of objects into multi-row tables, and extracting nested lists into separate tables with appropriate JOIN capabilities. The tool features both a CLI and Python library interface, with commands for SQL querying (yamlql sql), schema discovery (yamlql discover), and natural language querying through various LLM providers, all without sending your data externally. Practically: Works well with complex configuration files such as Kubernetes manifests applications, where traditional tools like jq/yq fall short for relational queries.

### [Kafka: Tributary DuckDB Extension](https://query.farm/duckdb_extension_tributary.html)

**TL;DR:** The Tributary DuckDB extension provides Apache Kafka integration, enabling real-time data streaming and querying directly within DuckDB's SQL interface.

The [Tributary extension](https://github.com/Query-farm/tributary), developed by Query.Farm, introduces native Kafka topic scanning capabilities through SQL functions like tributary\_scan\_topic(), which allows developers to **consume messages from Kafka** topics with minimal configuration. It supports a set of Kafka connection parameters and enables multi-threaded consumption of topics across partitions. It acts as a "bridge between the stream of data and the data lake".

### [Foursquare Introduces SQLRooms](https://medium.com/@foursquare/foursquare-introduces-sqlrooms-b6397d53546c)

**TL;DR:** Foursquare has released SQLRooms, an open-source React framework for building single-node data applications powered by DuckDB, which run entirely in browsers or on laptops without requiring backend infrastructure.

SQLRooms combines five core components: RoomShell (UI container), RoomStore (state management), an embedded DuckDB instance, an AI-powered analytics assistant, and a reusable component library.

The framework automatically handles DuckDB operations, including format recognition (CSV, Parquet, JSON, Arrow), schema inference, and table registration for immediate querying. It leverages recent advances in browser capabilities (PWAs, WebAssembly, OPFS) and local AI deployment, enabling data applications that process multi-gigabyte datasets in sub-seconds while maintaining data privacy. Find its [code](https://github.com/sqlrooms/sqlrooms) and [dedicated website](https://sqlrooms.org/).

### [Quacks & Stacks: DuckLake's One‑Table Wonder vs Iceberg's Manifest Maze](https://medium.com/@tfmv/quacks-stacks-5565069a5ef0)

**TL;DR:** DuckLake introduces a simplified metadata management approach for data lakes by centralizing metadata tracking in SQL tables, contrasting with Apache Iceberg's distributed file-based approach.

Thomas demonstrates how DuckLake reimagines table metadata management by storing all tracking information directly in SQL tables, utilizing functions such as ducklake\_snapshots() and ducklake\_table\_info() to provide transparent metadata access. Unlike Iceberg's complex manifest hierarchy (involving JSON → manifest lists → manifests → data files), DuckLake uses a **single-transaction model** for updates: UPDATE lake.sales\_data SET amount = amount \* 1.15 WHERE region = 'North'.

More about DuckLake:

📺 [Understanding DuckLake: A Table Format with a Modern Architecture](https://www.youtube.com/watch?v=hrTjvvwhHEQ)

📰 [MotherDuck Managed DuckLakes Now in Preview: Scale to Petabytes](https://motherduck.com/blog/announcing-ducklake-support-motherduck-preview/)

📝 [Digging into Ducklake](https://rmoff.net/2025/06/02/digging-into-ducklake/)

### [DuckDB Wizard: A DuckDB extension that executes JS and returns a table](https://github.com/nicosuave/wizard)

**TL;DR:** Nico's Wizard extension for DuckDB enables natural language queries and direct JavaScript execution within SQL via an embedded V8 interpreter.

The Wizard extension leverages LLMs (OpenAI/Anthropic) to translate natural language into JavaScript code that executes in a sandboxed Deno environment, returning results as DuckDB tables. Users can either use the wizard() function for natural language queries like `SELECT * FROM wizard('bitcoin price')` or execute arbitrary JavaScript directly with js(). Nico emphasizes that this is highly experimental and not for production use. If you need production-ready, check out MotherDucks’s [PROMPT()](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/ai-functions/prompt/) function.

### [How to Enable DuckDB/Smallpond to Use High-Performance DeepSeek 3FS](https://blog.open3fs.com/2025/05/16/duckdb-and-smallpond-use-high-performance-deepseek-3fs.html)

**TL;DR:** The Open3FS community has developed a DuckDB-3FS plugin enabling DuckDB and Smallpond to access DeepSeek's 3FS storage using its high-performance user-space interface (hf3fs\_usrbio).

The plugin supports two path formats ( 3fs://3fs/path and /3fs/path) and requires minimal configuration. DeepSeek reported that with 3FS and Smallpond, 50 compute nodes sorted 110.5 TiB of data in just over 30 minutes (3.66 TiB/minute throughput). The implementation is available in two open-source repositories: [duckdb-3fs](https://github.com/open3fs/duckdb-3fs) and [smallpond-3fs](https://github.com/open3fs/smallpond-3fs), allowing the DuckDB ecosystem to leverage 3FS storage performance fully.

### [Using Amazon SageMaker Lakehouse with DuckDB](https://tobilg.com/using-amazon-sagemaker-lakehouse-with-duckdb)

**TL;DR:** Tobias demonstrates how to integrate Amazon SageMaker Lakehouse with DuckDB using AWS Glue Iceberg REST endpoints to query S3 Tables.

In this technical walkthrough, we learn how to connect DuckDB to AWS SageMaker Lakehouse, starting with the necessary IAM setup. Once the AWS infrastructure is configured, the DuckDB integration is straightforward, requiring only two key commands: CREATE SECRET with STS assume role configuration and ATTACH with ICEBERG type and GLUE endpoint parameters. After this setup, users can run standard SQL queries directly against the data lake. The resulting DuckDB integration provides a lightweight, SQL-based access layer to data stored in S3 Tables.

### [PostgreSQL and Ducks: The Perfect Analytical Pairing](https://motherduck.com/blog/postgres-duckdb-options/)

**TL;DR:** This article explores three methods for integrating PostgreSQL with DuckDB/MotherDuck for analytical workloads: DuckDB Postgres Extension, pg\_duckdb, and Supabase's ETL (CDC).

The DuckDB Postgres Extension offers the most straightforward approach, requiring minimal setup with commands like `INSTALL postgres; LOAD postgres; ATTACH 'dbname=postgres user=postgres host=127.0.0.1' AS db (TYPE postgres, READ_ONLY);` to query PostgreSQL data remotely. The pg\_duckdb extension embeds DuckDB directly within PostgreSQL, delivering impressive performance gains (up to 1,500x speedup on one TPC-DS query, according to Jacob and Aditya), but requires careful resource management, ideally on a dedicated read replica. And finally, Supabase's ETL provides near real-time data synchronization through PostgreSQL's logical decoding capabilities.

### [Announcing DuckDB 1.3.0](https://duckdb.org/2025/05/21/announcing-duckdb-130.html)

**TL;DR:** DuckDB 1.3.0 "Ossivalis" introduces a file cache for remote data, a new spatial join operator, and improved Parquet handling alongside several breaking changes.

Besides the major DuckLake announcement, we also got the latest release 1.3.0 (and bug-fixes [1.3.1](https://github.com/duckdb/duckdb/releases/tag/v1.3.1)). The 1.3 release introduces performance improvements through an [external file cache](https://github.com/duckdb/duckdb/pull/16463) that dynamically stores data from remote files, resulting in reduced query times on subsequent runs (e.g., S3 queries experience a 4x speedup).

New features include Python-style lambda syntax (`lambda x: x + 1`), the TRY expression for error handling `(TRY(log(0))` returns NULL instead of erroring), UUID v7 support, and **a specialized spatial join operator** that's up to 100x faster than previous implementations. Internal improvements include a complete rewrite of the Parquet reader/writer and a new string compression method (DICT\_FSST).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Small Data SF: Workshop Day!](https://www.smalldatasf.com/)

**San Francisco, CA, USA - 12:00 PM America, Los Angeles - In Person**

Make your big data feel small, and your small data feel valuable. Join leading data and AI innovators on November 4th and 5th in San Francisco!

### [Small Data SF: Keynotes and Sessions](https://www.smalldatasf.com/)

**San Francisco, CA, USA - 8:30 AM America, Los Angeles - In Person**

Make your big data feel small, and your small data feel valuable. Join leading data and AI innovators on November 4th and 5th in San Francisco!

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-july-2025/#upcoming-events)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![MotherDuck Managed DuckLakes Now in Preview: Scale to Petabytes](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FFully_Managed_30cac547cd.png&w=3840&q=75)](https://motherduck.com/blog/announcing-ducklake-support-motherduck-preview/)

[2025/07/01 - Ryan Boyd](https://motherduck.com/blog/announcing-ducklake-support-motherduck-preview/)

### [MotherDuck Managed DuckLakes Now in Preview: Scale to Petabytes](https://motherduck.com/blog/announcing-ducklake-support-motherduck-preview)

Preview support of MotherDuck includes both fully-managed DuckLake support and ability to bring your own bucket. Combined with MotherDuck's storage, you get both high-speed access to recent data and support for massive scale historical data.

[![The Data Engineer Toolkit: Infrastructure, DevOps, and Beyond](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fthumb_de_50b9010e13.png&w=3840&q=75)](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/)

[2025/07/03 - Simon Späti](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops/)

### [The Data Engineer Toolkit: Infrastructure, DevOps, and Beyond](https://motherduck.com/blog/data-engineering-toolkit-infrastructure-devops)

A comprehensive guide to advanced data engineering tools covering everything from SQL engines and orchestration platforms to DevOps, data quality, AI workflows, and the soft skills needed to build production-grade data platforms.

[View all](https://motherduck.com/blog/)

Authorization Response