---
title: understanding-ducklake-a-table-format-with-a-modern-architecture
content_type: tutorial
source_url: https://motherduck.com/videos/understanding-ducklake-a-table-format-with-a-modern-architecture
indexed_at: '2025-11-25T20:44:56.601076'
content_hash: 22e8aaba3d78ae31
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Understanding DuckLake: A Table Format with a Modern Architecture - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Understanding DuckLake: A Table Format with a Modern Architecture](https://www.youtube.com/watch?v=hrTjvvwhHEQ)

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

[Why am I seeing this?](https://support.google.com/youtube/answer/9004474?hl=en)

[Watch on](https://www.youtube.com/watch?v=hrTjvvwhHEQ&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 15:44

•Live

•

YouTube

# Understanding DuckLake: A Table Format with a Modern Architecture

2025/06/05

## The Evolution from Databases to Table Formats

Modern data engineering has undergone a significant transformation in how analytical data is stored and processed. Traditional OLAP databases once handled both storage and compute, but this approach led to two major challenges: vendor lock-in through proprietary formats and the inability to scale storage independently from compute.

This limitation gave birth to the data lake architecture, where analytical data is stored as files (primarily in columnar formats like Parquet) on object storage systems such as AWS S3, Google Cloud Storage, or Azure Blob Storage. This decoupling allows any compute engine - Apache Spark, Trino, or DuckDB - to query the same data.

## The Table Format Revolution

While storing data as Parquet files on blob storage provides flexibility, it sacrifices essential database features:

- **No atomicity**: Parquet files are immutable, requiring complete rewrites for updates
- **No schema evolution**: Adding or removing columns requires manual tracking
- **No time travel**: Querying historical states of data becomes complex

Table formats like Apache Iceberg and Delta Lake emerged to bridge this gap. They add a metadata layer on top of file formats, enabling:

- Metadata tracking (typically in JSON or Avro format)
- Snapshot isolation and time travel capabilities
- Schema evolution support
- Partition pruning optimization

However, these solutions introduce new complexities. They generate numerous small metadata files that are expensive to read over networks, and often require external catalogs like Unity Catalog or AWS Glue to track table locations and versions.

## DuckLake: A Fresh Approach to Table Formats

DuckLake represents a fundamental rethink of table format architecture. Despite its name, DuckLake is not tied to DuckDB - it's an open standard for managing large tables on blob storage.

### The Key Innovation: Database-Backed Metadata

Unlike Iceberg or Delta Lake, which store metadata as files on blob storage, DuckLake stores metadata in a relational database. This can be:

- DuckDB (ideal for local development)
- SQLite
- PostgreSQL (typical for production)
- MySQL

This architectural decision leverages what relational databases do best: handle small, frequent updates with transactional guarantees. Since metadata operations (tracking versions, handling deletes, updating schemas) are exactly this type of workload, a transactional database is the perfect fit.

### Performance Benefits

The metadata typically represents less than 1/100,000th of the actual data size. By storing it in a database, DuckLake eliminates the overhead of scanning dozens of metadata files on blob storage. A single SQL query can resolve all metadata operations - current snapshots, file lists, and more - dramatically reducing the round trips required for basic operations.

## DuckLake in Practice

### Architecture Overview

DuckLake maintains a clear separation of concerns:

- **Metadata**: Stored in SQL tables within a relational database
- **Data**: Stored as Parquet files on blob storage (S3, Azure, GCS)

### Key Features

DuckLake supports all the features expected from a modern lakehouse format:

- **ACID transactions** across multiple tables
- **Full schema evolution** with column additions and updates
- **Snapshot isolation** and time travel queries
- **Efficient metadata management** through SQL

### Practical Implementation

Setting up DuckLake requires three components:

1. **Data storage**: A blob storage bucket (e.g., AWS S3) with read/write access
2. **Metadata storage**: A PostgreSQL or MySQL database (services like Supabase work well)
3. **Compute engine**: DuckDB or any compatible query engine

When creating a DuckLake table, the system automatically generates metadata tables in the specified database while storing the actual data as Parquet files in the designated blob storage location. Updates to tables create new Parquet files and deletion markers, maintaining immutability while providing a mutable interface.

## The Future of Table Formats

DuckLake's approach solves many of the metadata management challenges that plague current table formats. By leveraging proven relational database technology for metadata while maintaining open file formats for data, it offers a pragmatic solution to the complexities of modern data lakes.

While still in its early stages, DuckLake shows promise for organizations looking to simplify their data lake architecture without sacrificing the flexibility and scalability that made data lakes popular in the first place. As the ecosystem matures and more compute engines add support, DuckLake could become a compelling alternative to established formats like Iceberg and Delta Lake.

...SHOW MORE

## Related Videos

[!["Data-based: Going Beyond the Dataframe" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FData_based_f32745b461.png&w=3840&q=75)](https://motherduck.com/videos/going-beyond-the-dataframe/)

[2025-11-20](https://motherduck.com/videos/going-beyond-the-dataframe/)

### [Data-based: Going Beyond the Dataframe](https://motherduck.com/videos/going-beyond-the-dataframe)

Learn how to turbocharge your Python data work using DuckDB and MotherDuck with Pandas. We walk through performance comparisons, exploratory data analysis on bigger datasets, and an end-to-end ML feature engineering pipeline.

Webinar

Python

AI, ML and LLMs

[!["Empowering Data Teams: Smarter AI Workflows with Hex & MotherDuck" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FHex_Webinar_778e3959e4.png&w=3840&q=75)](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck/)

[2025-11-14](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck/)

### [Empowering Data Teams: Smarter AI Workflows with Hex & MotherDuck](https://motherduck.com/videos/smarter-ai-workflows-with-hex-motherduck)

AI isn't here to replace data work, it's here to make it better. Watch this webinar to see how Hex and MotherDuck build AI workflows that prioritize context, iteration, and real-world impact.

Webinar

AI, ML and LLMs

[!["Lies, Damn Lies, and Benchmarks" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2FLies_Damn_Lies_and_Benchmarks_Thumbnail_404db1bf46.png&w=3840&q=75)](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

[2025-10-31](https://motherduck.com/videos/lies-damn-lies-and-benchmarks/)

### [Lies, Damn Lies, and Benchmarks](https://motherduck.com/videos/lies-damn-lies-and-benchmarks)

Why do database benchmarks so often mislead? MotherDuck CEO Jordan Tigani discusses the pitfalls of performance benchmarking, lessons from BigQuery, and why your own workload is the only benchmark that truly matters.

Stream

Interview

[View all](https://motherduck.com/videos/)

Authorization Response