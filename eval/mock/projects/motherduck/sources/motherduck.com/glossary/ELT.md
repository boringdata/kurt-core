---
title: 'DuckDB Data Engineering Glossary: ELT'
content_type: reference
description: Making analytics ducking awesome with DuckDB. Start using DuckDB in the
  cloud for free today.
published_date: '2024-10-20T00:00:00'
source_url: https://motherduck.com/glossary/ELT
indexed_at: '2025-11-25T20:02:11.326705'
content_hash: 838666fb91bebad4
---

# ELT

[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)

[ELT](https://www.fivetran.com/blog/what-is-elt) (Extract, Load, Transform) is a modern data integration process that reverses the order of traditional ETL (Extract, Transform, Load) workflows. In ELT, raw data is first extracted from various sources and loaded directly into a target data warehouse or lake without prior transformation. The transformation step occurs afterwards within the destination system, leveraging its processing power and scalability. This approach allows for greater flexibility, as analysts can transform data on-demand and iterate on transformations without re-extracting or re-loading. ELT is particularly well-suited for cloud-based data warehouses like [Snowflake](https://www.snowflake.com/), [BigQuery](https://cloud.google.com/bigquery), or [Redshift](https://aws.amazon.com/redshift/), which can handle large-scale data transformations efficiently. Tools like [dbt](https://www.getdbt.com/) have popularized ELT by providing a framework for managing and executing in-warehouse transformations using SQL.