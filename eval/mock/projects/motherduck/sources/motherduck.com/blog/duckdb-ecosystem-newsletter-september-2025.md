---
title: duckdb-ecosystem-newsletter-september-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025
indexed_at: '2025-11-25T19:56:34.370656'
content_hash: 2b2e5956c439f841
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# DuckDB Ecosystem: September 2025

2025/09/09 - 8 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

This month, we've achieved major performance breakthroughs with DuckDB's new spatial joins, delivering 58× speed improvements, and pg\_duckdb 1.0 officially launched to bring vectorized analytics directly into PostgreSQL. Plus, real-world cost savings stories, including one team that slashed their Snowflake BI spend by 79% using DuckDB as a smart caching layer.

\- [Simon](https://www.ssp.sh/)

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2F1625697275063.jpeg&w=3840&q=75)

### Matt Martin

[Matt Martin](https://www.linkedin.com/in/mattmartin14/) is a Staff Engineer at State Farm. He is a highly experienced data architect and ETL practitioner with strong BI expertise.

Matt also shares his knowledge through his newsletter, [High Performance DE Newsletter,](https://performancede.substack.com/) where he writes about topics like [DuckDB and the Semantic Layer](https://performancede.substack.com/p/duckdb-and-the-semantic-layer). He recently made his first [contribution to DuckDB](https://github.com/duckdb/duckdb/pull/18722), giving back to the open-source community.

Thanks, Matt, for your energy and for spreading your DuckDB knowledge!

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [Interactive SQL & DuckDB Tutorial](https://dbquacks.com/tutorial/1)

**TL;DR**: DB Quacks introduces an interactive, browser-based SQL learning platform powered by DuckDB, targeting developers and data practitioners through gamified, progressive learning challenges.

The project creates a hands-on tutorial environment where users can write and execute real SQL queries. By integrating an interactive tutorial with a potential data-driven adventure game, the platform aims to provide an engaging learning experience that allows immediate query execution and result visualization. The tutorial follows a character named Duckbert and offers progressively challenging exercises that help users master SQL fundamentals. It's a fun way of learning more about DuckDB.

### [Spatial Joins in DuckDB](https://duckdb.org/2025/08/08/spatial-joins.html)

**TL;DR:** DuckDB v1.3.0 introduced a dedicated spatial operator that delivers up to 58× performance improvement over the previous version.

The new SPATIAL\_JOIN operator builds an R-tree index on-the-fly for the smaller (right) table during join execution, then streams the left table's rows through this index to efficiently find matches. This approach replaces the previous PIECEWISE\_MERGE\_JOIN optimization that relied on bounding box inequality checks.

In benchmarks using NYC bike trip data with 58 million rows, Max demonstrated that the new point-in-polygon join now finishes in just 28.7 seconds compared to 107.6 seconds with the previous approach and 1799.6 seconds with a naive nested loop join. Future improvements will include support for larger-than-memory build sides, increased parallelism, and faster native predicate functions.

### [Querying Billions of GitHub Events Using Modal and DuckDB (Part 1: Ingesting Data)](https://noreasontopanic.com/p/querying-billions-of-github-events)

**TL;DR:** Patrick demonstrates how to download and process 3.5TB of GitHub event data using Modal's serverless infrastructure and DuckDB in just 15 minutes.

Modal is a serverless cloud engine for Python that provides highly concurrent infrastructure to efficiently download 50K+ files of GitHub event data from GitHub Archive. The implementation uses pycurl for faster downloads with failure handling, container-level concurrency, and parallelization across hundreds of containers simultaneously. While DuckDB can directly query remote files, downloading the files first enables faster and more reliable querying across billions of events.

### [DuckDB In Production](https://datamethods.substack.com/p/duckdb-in-production)

**TL;DR:** Jordan demonstrates how DuckDB can serve as a lightweight federated query engine to validate ELT pipelines and detect deduplication issues between SQL Server and Snowflake.

When facing unexplained duplicate records in Snowflake despite proper CDC configuration in Airbyte, Jordan leveraged DuckDB's ODBC extension to simultaneously query both source and target databases for comparison.  The implementation uses straightforward SQL to compare row counts, distinct primary key counts, and identify duplicates with set variables like SET ss\_conn = 'Driver={ODBC Driver 18 for SQL Server};\[...\] and SET sf\_conn = 'Driver=SnowflakeDSIIDriver;Server=\[...\].

This approach required minimal setup with no additional infrastructure, making it an ideal validation layer that can be further extended through Python scripting and containerization.

### [DuckDB Can Query Your PostgreSQL. We Built a UI For It.](https://datakit.page/)

**TL;DR:** DataKit integrates DuckDB with PostgreSQL, allowing users to perform OLAP queries on OLTP data through a browser-based UI without needing data replicas.

The integration leverages DuckDB's PostgreSQL extension to create virtual tables on top of PostgreSQL tables. The UI comes with data preview, query, notebook, visualization and an assistant. The architecture enables users to work seamlessly with multiple data sources in a single interface, opening 15GB CSV files in seconds while also connecting to PostgreSQL databases, HuggingFace datasets, and other sources.

### [How we used DuckDB to save 79% on Snowflake BI spend](https://sh.reddit.com/r/dataengineering/comments/1mk85dn/how_we_used_duckdb_to_save_79_on_snowflake_bi/)

**TL;DR**: A smart caching layer using DuckDB significantly reduced Snowflake BI spend by 79% while improving query performance, shared on Reddit.

The r/dataengineering post details a cost-saving strategy implemented using DuckDB as a caching layer for a Snowflake-based BI setup. The key implementation involves unloading Snowflake tables as Parquet files, which DuckDB then reads. A custom-built proxy routes queries to either DuckDB or Snowflake based on table size, operators, and explain plan heuristics.

The cluster setup with DuckDB nodes (32 CPU, 128GB RAM spot instances) handles a peak of 48K daily queries, with an average query time reduction from 3.7s (Snowflake) to 0.455s (DuckDB). Essentially, building a smart caching layer for Snowflake.

### [news-nlp-pipeline: A serverless, event-driven data pipeline for real-time news](https://github.com/nakuleshj/news-nlp-pipeline)

**TL;DR:** A fully serverless, event-driven data pipeline for financial news sentiment analysis built entirely on AWS free-tier services and managed with Terraform.

This project claims to provide production-grade architecture for real-time financial news processing, utilizing AWS Lambda functions triggered by EventBridge schedules and S3 events. The pipeline processes the data with VADER sentiment analysis, validates data quality using Pandas, and stores results as Parquet files in S3. It uses DuckDB to query Parquet files directly from S3 and display results through Streamlit.

The entire infrastructure is defined as code with Terraform, including Lambda functions, S3 buckets, IAM roles, and event triggers. This makes it reproducible.

### [​MySQL's New Storage and Execution Engine: DuckDB](https://www.linkedin.com/pulse/mysqls-new-storage-execution-engine-duckdb-zongzhi-chen-4woqc/)

**TL;DR**: Alibaba Cloud RDS has integrated DuckDB as a new storage engine to enhance analytical query performance within MySQL.

The integration uses MySQL's pluggable storage engine architecture to run DuckDB alongside InnoDB, with data automatically replicated and converted via Binlog replication in read-only instances. A key technical challenge was ensuring compatibility between MySQL and DuckDB, which involved extending DuckDB's parser and rewriting many functions to achieve 99% SQL compatibility based on a test suite of 170,000 SQL tests.

### [news-nlp-pipeline: A serverless, event-driven data pipeline for real-time news](https://github.com/nakuleshj/news-nlp-pipeline)

**TL;DR:** This project demonstrates a cost-efficient, serverless data pipeline for real-time financial news sentiment analysis using AWS services and DuckDB for querying Parquet files directly from S3.

The architecture implements an event-driven pipeline where AWS EventBridge triggers Lambda functions to fetch news data twice daily, process it with VADER sentiment analysis, and store enriched data as Parquet files in S3, leveraging DuckDB to query Parquet files directly from S3. The entire infrastructure is deployed as code using Terraform, including S3 buckets, Lambda functions, IAM roles, and event notifications, making it reproducible and maintainable.

A great showcase of how combining serverless components with DuckDB's ability to query Parquet files can create efficient, low-cost data pipelines.

### [Announcing pg\_duckdb Version 1.0](https://motherduck.com/blog/pg-duckdb-release/)

**TL;DR:** pg\_duckdb 1.0 is now available, embedding DuckDB's vectorized analytical engine directly into PostgreSQL for faster analytical queries without leaving your database environment.

The 1.0 release introduces enhanced MotherDuck integration, expanded support for various data types, improved stability, and enhanced performance, including parallel table scanning. It allows you to join PostgreSQL data with remote data lake files in a single query, making it possible to perform in-database ETL operations that traditionally required external tools. See [full release notes](https://github.com/duckdb/pg_duckdb/releases/tag/v1.0.0).

### [Why Semantic Layers Matter — and How to Build One with DuckDB](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)

**TL;DR:** This is my article that explores building a simple semantic layer using DuckDB, Ibis, and YAML to manage and query data consistently across different tools. It answers questions about semantic layers and how to define metrics and dimensions in YAML files, abstracting the physical data layer.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [AI Native Summit 2025 (by Zetta)](https://events.zettavp.com/zetta/rsvp/register?e=ai-native-summit-2025)

**September 10 - Online : 9:00 PM CET**

This event brings together AI leaders across research, startups and global companies for a day of discussion about the state of enterprise AI. MotherDuck CEO Jordan Tigani is speaking. We are also sponsoring and have a demo booth.

### [Modern Data Infra Summit](https://www.mdisummit.com/)

**September 18 - 🇺🇸 San Francisco, CA - 9:30 AM US, Pacific**

Ryan Boyd, co-founder at MotherDuck, speaking about DuckLake. We're also sponsoring this event along with Dragonfly, ScyllaDB, GreptimeDB, Redpanda and TiDB.

### [MotherDuck'ing Big Data London Party](https://luma.com/MotherDucking-BigParty-2025)

**September 24 - Kindred, London - 7:00 PM GMT-1**

Join us for for Beers, Bites, & Good Ducking Fun at Big Data London! Following day 1 of BDL, escape from the expo floor and come shake your tail feathers with us. Expect pints aplenty and flocking-fun game

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/#upcoming-events)

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

[![Why Semantic Layers Matter — and How to Build One with DuckDB](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fsem_picture_6d4261bdb7.png&w=3840&q=75)](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)

[2025/08/19 - Simon Späti](https://motherduck.com/blog/semantic-layer-duckdb-tutorial/)

### [Why Semantic Layers Matter — and How to Build One with DuckDB](https://motherduck.com/blog/semantic-layer-duckdb-tutorial)

Learn what a semantic layer is, why it matters, and how to build a simple one with DuckDB and Ibis using just YAML and Python

[![Announcing Pg_duckdb Version 1.0](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fpg_duckdb_0ba60b727d.png&w=3840&q=75)](https://motherduck.com/blog/pg-duckdb-release/)

[2025/09/03 - Jelte Fennema-Nio, Jacob Matson](https://motherduck.com/blog/pg-duckdb-release/)

### [Announcing Pg\_duckdb Version 1.0](https://motherduck.com/blog/pg-duckdb-release)

PostgreSQL gets a DuckDB-flavored power-up for faster analytical queries without ever leaving Postgres.

[View all](https://motherduck.com/blog/)

Authorization Response