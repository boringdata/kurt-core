---
title: how-to-efficiently-load-data-into-ducklake-with-estuary
content_type: tutorial
source_url: https://motherduck.com/videos/how-to-efficiently-load-data-into-ducklake-with-estuary
indexed_at: '2025-11-25T20:44:50.287804'
content_hash: 54211f956cd60bed
has_step_by_step: true
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

How to Efficiently Load Data into DuckLake with Estuary - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[How to Efficiently Load Data into DuckLake with Estuary](https://www.youtube.com/watch?v=8uce9V9VnjY)

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

[Watch on](https://www.youtube.com/watch?v=8uce9V9VnjY&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 50:08

•Live

•

YouTube

# How to Efficiently Load Data into DuckLake with Estuary

2025/07/26

## Introduction to DuckLake and Real-Time Data Integration

DuckLake represents a new open table format created by the developers of DuckDB. Unlike traditional data lake formats that store metadata in JSON or Avro files within blob storage, DuckLake takes a different approach by storing metadata in a relational database. This architectural decision significantly speeds up metadata transactions, making operations faster and more efficient.

## Understanding MotherDuck's Cloud Data Warehouse

MotherDuck is a cloud data warehouse designed to make big data feel small. Built on top of DuckDB, it focuses on three key principles:

- **Eliminating complexity** from traditional distributed data warehouses
- **Enabling fast insights** while keeping developers in their workflow
- **Leveraging DuckDB's performance** for cost-efficient operations

The platform integrates seamlessly with existing data stack tools and supports standard SQL queries with enhanced features.

## Estuary's Real-Time Data Integration Platform

Estuary provides a real-time data integration platform that supports both streaming and batch data movement. The platform features:

### Architecture Components

- **Capture connectors** that extract data from source systems using change data capture (CDC)
- **Collections** stored in object storage (S3, GCS, or compatible systems)
- **Materialization connectors** that load data into destinations

### Key Capabilities

- Support for hundreds of source and destination systems
- Native CDC for databases like PostgreSQL, MySQL, and Oracle
- Real-time extraction from SaaS applications like Salesforce and HubSpot
- No-code setup with managed service

## Setting Up a Real-Time Pipeline to DuckLake

The process of loading data into DuckLake involves several straightforward steps:

### Source Configuration

1. Connect to your source database (PostgreSQL, MySQL, etc.)
2. Enable change data capture to track real-time changes
3. Configure schema evolution settings for automatic handling of schema changes

### DuckLake Setup

1. Create a DuckLake database in MotherDuck
2. Configure access to your S3 bucket where data will be stored
3. Set up appropriate access tokens for read/write permissions

### Pipeline Configuration

- Choose sync frequency (from real-time to scheduled batches)
- Select specific fields to materialize
- Configure merge queries for maintaining latest state

## Performance Optimization with MotherDuck

### Instant SQL Feature

MotherDuck introduces Instant SQL, which provides query results at the speed of typing by:

- Pre-caching data for immediate feedback
- Validating SQL syntax in real-time
- Enabling rapid iteration on complex queries

### Storage Trade-offs

When deciding between DuckLake and MotherDuck native storage:

**DuckLake advantages:**

- Open format with broader ecosystem compatibility
- Support for Spark and other compute engines
- Better suited for petabyte-scale workloads

**MotherDuck storage advantages:**

- 2-10x faster query performance
- Optimized for read/write throughput
- Better caching and regional performance

## Scaling Considerations

MotherDuck now offers larger instance sizes (Mega and Giga) to support intensive data lake operations. These instances are comparable to Snowflake 3XL configurations and enable:

- Terabyte to petabyte-scale operations
- Complex aggregations and sorting
- Efficient medallion architecture implementations

## Best Practices for Implementation

### Data Architecture

- Keep raw data in DuckLake for openness and flexibility
- Move silver/gold layer data to MotherDuck storage for performance
- Use Estuary's intermediate storage for reliability and replay capabilities

### Partitioning Strategy

While Estuary doesn't natively configure partitions, you can:

1. Allow Estuary to create initial tables
2. Use `ALTER TABLE` commands to add partitions
3. Subsequent writes will respect partition configuration

### Error Handling and Reliability

The architecture prevents common streaming issues:

- Intermediate storage prevents message loss
- Automatic handling of destination unavailability
- Support for backfills without re-querying sources

## Integration with Modern Data Stack

The combination of Estuary and MotherDuck integrates with existing tools:

- dbt support through DuckDB adapter
- AI-powered SQL writing assistance
- Automatic error detection and fixing
- Support for multiple materialization targets from single source

This architecture enables organizations to implement real-time data pipelines without the traditional complexity of streaming systems, making the difference between batch and streaming simply a configuration toggle rather than an architectural decision.

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