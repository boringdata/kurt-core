---
title: metadata
content_type: event
source_url: https://motherduck.com/glossary/metadata
indexed_at: '2025-11-25T20:02:21.577512'
content_hash: f25c6cf7453e9c0e
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# metadata

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

Metadata is information that describes other data. In the context of data analytics and engineering, metadata provides context about datasets, including details like column names, data types, creation dates, update frequencies, and data lineage. It's crucial for data governance, discovery, and understanding the structure and meaning of data assets. Tools like [Amundsen](https://www.amundsen.io/) and [DataHub](https://datahubproject.io/) help organizations manage and explore metadata at scale. For example, in a DuckDB table, metadata might include the schema definition, table constraints, and column statistics. You can query metadata in DuckDB using system tables and functions like:

```sql
Copy code

-- View table metadata
DESCRIBE mytable;

-- Get column statistics
SELECT * FROM pragma_table_info('mytable');

-- View system-wide metadata
SELECT * FROM duckdb_tables();
```

Effective metadata management is essential for maintaining data quality, ensuring compliance, and enabling efficient data discovery and analysis across an organization.

Authorization Response