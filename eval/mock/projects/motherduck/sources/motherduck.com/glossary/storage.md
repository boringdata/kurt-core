---
title: 'DuckDB Data Engineering Glossary: storage'
content_type: reference
description: Making analytics ducking awesome with DuckDB. Start using DuckDB in the
  cloud for free today.
published_date: '2024-10-20T00:00:00'
source_url: https://motherduck.com/glossary/storage
indexed_at: '2025-11-25T20:02:28.725276'
content_hash: f331529727910df3
---

# storage

[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)

[DuckDB](https://duckdb.org/) uses an efficient columnar storage format optimized for analytical queries. Unlike traditional row-based storage systems, columnar storage groups data by column rather than by row, allowing for faster data retrieval and compression when dealing with large datasets. This approach is particularly beneficial for OLAP (Online Analytical Processing) workloads, where queries often involve aggregations and scans of specific columns rather than entire rows. DuckDB's storage engine supports both in-memory and persistent disk-based storage, allowing users to work with datasets that exceed available RAM. The storage format also includes metadata and indexing structures to further enhance query performance. When data is persisted to disk, DuckDB uses a custom file format that maintains the columnar structure and includes features like checkpointing for durability and crash recovery.